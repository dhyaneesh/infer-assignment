"""Build the reviewed snapshot for the retail evaluation monitor."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MONITOR_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = MONITOR_DIR / "experiments.json"
DEFAULT_OUTPUT = MONITOR_DIR / "src" / "data.json"
FINDING_DETAILS = {
    "structured_selection_and_facts": "Incorrect filtering, counts, minima, maxima, or constrained item selection before communicating or writing.",
    "policy_feasibility_and_fallback": "Policy, payment/refund feasibility, user conditions, or supplied fallbacks were not resolved before mutation.",
    "entity_action_binding": "The intended order, address, reason, payment method, or action was bound to the wrong database write.",
    "post_item_modification_write": "A later write targeted an order after item modification should have locked further modification and cancellation.",
    "action_not_in_reward_basis": "None of the 69 analyzed tasks include ACTION in final reward; action matching is diagnostic only.",
    "policy_call_count_not_scored": "The benchmark does not score the retail policy's one-tool-call-per-turn requirement.",
    "missing_golden_product": "Golden reads reference missing product 6086499569, producing replay warnings for tasks 2 and 4.",
    "email_punctuation_mismatch": "Task 38's expected email differs from the stored email punctuation and requires fallback authentication.",
}


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required monitor source is missing: {path}")
    return json.loads(path.read_text())


def resolve(path: str) -> Path:
    return (MONITOR_DIR / path).resolve()


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def task_id_key(value: str) -> tuple[int, str]:
    return (int(value), value) if value.isdigit() else (10**9, value)


def extract_experiment(spec: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    results_path = resolve(spec["results"])
    summary_path = resolve(spec["summary"])
    results = load_json(results_path)
    summary = load_json(summary_path)
    simulations = results.get("simulations")
    if not isinstance(simulations, list):
        raise ValueError(f"{results_path} has no simulations list")
    by_task = {str(row["task_id"]): row for row in simulations}
    if len(by_task) != len(simulations):
        raise ValueError(f"{results_path} contains duplicate task IDs")
    if len(simulations) != scope["task_count"]:
        raise ValueError(
            f"{spec['id']} expected {scope['task_count']} tasks, found {len(simulations)}"
        )

    excluded = set(scope["excluded_task_ids"])
    analyzed_ids = set(by_task) - excluded
    if len(analyzed_ids) != scope["diagnostic_task_count"]:
        raise ValueError(f"{spec['id']} diagnostic population is not 69 tasks")
    summary_tasks = {str(row["task_id"]): row for row in summary.get("tasks", [])}
    if set(summary_tasks) != analyzed_ids:
        raise ValueError(f"{spec['id']} summary task population does not match results")

    outcome = {
        "completion_passes": sum(
            row.get("reward_info", {}).get("reward") == 1 for row in simulations
        ),
        "db_passes": sum(
            row.get("reward_info", {}).get("db_check", {}).get("db_reward") == 1
            for row in simulations
        ),
        "read_correct": 0,
        "read_total": 0,
        "write_correct": 0,
        "write_total": 0,
    }
    task_rows: list[dict[str, Any]] = []
    legality_rows: list[dict[str, Any]] = []
    violation_counter: Counter[str] = Counter()
    for task_id in sorted(by_task, key=task_id_key):
        simulation = by_task[task_id]
        reward = simulation.get("reward_info") or {}
        actions = reward.get("action_checks") or []
        reads = [row for row in actions if row.get("tool_type") == "read"]
        writes = [row for row in actions if row.get("tool_type") == "write"]
        outcome["read_total"] += len(reads)
        outcome["read_correct"] += sum(bool(row.get("action_match")) for row in reads)
        outcome["write_total"] += len(writes)
        outcome["write_correct"] += sum(bool(row.get("action_match")) for row in writes)
        diagnostic = summary_tasks.get(task_id, {})
        checks = diagnostic.get("action_legality_checks") or []
        for check in checks:
            for violation_type in check.get("violation_types") or []:
                violation_counter[violation_type] += 1
            legality_rows.append(
                {
                    "experiment_id": spec["id"],
                    "experiment": spec["label"],
                    "task_id": task_id,
                    "benchmark_pass": reward.get("reward") == 1,
                    "call_id": check.get("call_id"),
                    "turn_idx": check.get("turn_idx"),
                    "tool_name": check.get("tool_name"),
                    "arguments": json.dumps(check.get("arguments") or {}, sort_keys=True),
                    "verdict": check.get("verdict"),
                    "violation_types": ", ".join(check.get("violation_types") or []),
                    "policy_evidence": check.get("policy_evidence"),
                    "conversation_evidence": check.get("conversation_evidence"),
                    "reasoning": check.get("reasoning"),
                    "correct_action": check.get("correct_action"),
                }
            )
        task_rows.append(
            {
                "experiment_id": spec["id"],
                "experiment": spec["label"],
                "task_id": task_id,
                "excluded": task_id in excluded,
                "benchmark_pass": reward.get("reward") == 1,
                "benchmark_reward": reward.get("reward"),
                "db_match": reward.get("db_check", {}).get("db_reward") == 1,
                "read_correct": sum(bool(row.get("action_match")) for row in reads),
                "read_total": len(reads),
                "write_correct": sum(bool(row.get("action_match")) for row in writes),
                "write_total": len(writes),
                "cardinality_turns": diagnostic.get("cardinality_error_turns"),
                "unsafe_write_turns": diagnostic.get("unsafe_write_turns"),
                "illegal_actions": diagnostic.get("illegal_actions"),
                "legal_actions": diagnostic.get("legal_actions"),
                "uncertain_actions": diagnostic.get("uncertain_actions"),
            }
        )

    diagnostics = {
        "cardinality_turns": summary["cardinality"]["violating_turns"],
        "cardinality_tasks": summary["cardinality"]["affected_tasks"],
        "unsafe_write_turns": summary["unsafe_write"]["violating_turns"],
        "unsafe_write_tasks": summary["unsafe_write"]["affected_tasks"],
        "illegal_actions": summary["action_legality"]["verdict_counts"].get(
            "illegal", 0
        ),
        "legal_actions": summary["action_legality"]["verdict_counts"].get("legal", 0),
        "uncertain_actions": summary["action_legality"]["verdict_counts"].get(
            "uncertain", 0
        ),
        "legality_tasks": summary["action_legality"]["affected_tasks"],
    }
    expected_violations = summary["action_legality"].get("violation_type_counts", {})
    if dict(sorted(violation_counter.items())) != expected_violations:
        raise ValueError(f"{spec['id']} violation counts do not reconcile")

    prompt_rows = []
    for order, prompt_file in enumerate(spec["prompt_files"], start=1):
        prompt_path = resolve(prompt_file)
        prompt_rows.append(
            {
                "experiment_id": spec["id"],
                "experiment": spec["label"],
                "order": order,
                "file": str(prompt_path.relative_to(MONITOR_DIR.parent)),
                "characters": len(prompt_path.read_text()),
                "content": prompt_path.read_text(),
            }
        )

    row = {
        "experiment_id": spec["id"],
        "experiment": spec["label"],
        "parent_id": spec["parent"],
        "change": spec["change"],
        "hypothesis": spec["hypothesis"],
        "conclusion": spec["conclusion"],
        **outcome,
        **diagnostics,
    }
    row.update(
        {
            "completion_rate": percentage(outcome["completion_passes"], len(simulations)),
            "db_rate": percentage(outcome["db_passes"], len(simulations)),
            "read_accuracy": percentage(outcome["read_correct"], outcome["read_total"]),
            "write_accuracy": percentage(outcome["write_correct"], outcome["write_total"]),
            "completion_excluded_passes": sum(
                by_task[task_id].get("reward_info", {}).get("reward") == 1
                for task_id in analyzed_ids
            ),
        }
    )
    violations = [
        {
            "experiment_id": spec["id"],
            "experiment": spec["label"],
            "violation_type": key,
            "count": value,
        }
        for key, value in sorted(expected_violations.items())
    ]
    return {
        "summary": row,
        "tasks": task_rows,
        "legality": legality_rows,
        "violations": violations,
        "prompts": prompt_rows,
        "source_files": [str(results_path), str(summary_path)],
    }


def build_snapshot(config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    scope = config["scope"]
    extracted = [extract_experiment(spec, scope) for spec in config["experiments"]]
    summaries = [item["summary"] for item in extracted]
    summary_by_id = {row["experiment_id"]: row for row in summaries}
    task_rows = [row for item in extracted for row in item["tasks"]]
    tasks_by_experiment = {
        experiment_id: {
            row["task_id"]: row
            for row in task_rows
            if row["experiment_id"] == experiment_id and not row["excluded"]
        }
        for experiment_id in summary_by_id
    }
    movements = []
    for spec in config["experiments"]:
        if not spec["parent"]:
            continue
        current = tasks_by_experiment[spec["id"]]
        parent = tasks_by_experiment[spec["parent"]]
        for task_id in sorted(current, key=task_id_key):
            parent_pass = parent[task_id]["benchmark_pass"]
            current_pass = current[task_id]["benchmark_pass"]
            movement = (
                "newly passing"
                if current_pass and not parent_pass
                else "regressed"
                if parent_pass and not current_pass
                else "still passing"
                if current_pass
                else "still failing"
            )
            movements.append(
                {
                    "experiment_id": spec["id"],
                    "experiment": summary_by_id[spec["id"]]["experiment"],
                    "parent_id": spec["parent"],
                    "parent": summary_by_id[spec["parent"]]["experiment"],
                    "task_id": task_id,
                    "movement": movement,
                }
            )

    findings_path = MONITOR_DIR.parent / "data/simulations/retail_gpt41_text_baseline_70_tasks/error_catalog.json"
    findings = load_json(findings_path)
    finding_rows = []
    for category in (
        "primary_failure_categories",
        "hidden_trajectory_errors",
        "environment_defects",
        "evaluator_defects",
        "task_data_defects",
    ):
        for finding in findings.get(category, []):
            finding_rows.append(
                {
                    "category": category,
                    "id": finding["id"],
                    "tasks": ", ".join(finding.get("tasks", [])),
                    "affected_tasks": finding.get("affected_tasks"),
                    "detail": FINDING_DETAILS.get(finding["id"])
                    or finding.get("detail")
                    or finding.get("definition")
                    or finding.get("grader"),
                    "raw": json.dumps(finding, sort_keys=True),
                }
            )

    generated_at = os.environ.get("MONITOR_GENERATED_AT") or datetime.now(
        timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    files = sorted(
        {
            str(Path(path).relative_to(MONITOR_DIR.parent))
            for item in extracted
            for path in item["source_files"]
        }
        | {
            str(config_path.resolve().relative_to(MONITOR_DIR.parent)),
            str(findings_path.relative_to(MONITOR_DIR.parent)),
        }
    )
    source = {
        "label": "Retail evaluation benchmark artifacts",
        "files": files,
        "executedAt": generated_at,
        "coverage": {"tasks": 70, "analyzedTasks": 69, "experiments": 4},
        "caveats": [
            "Task 105 is retained in raw outcomes and excluded from diagnostic comparisons because its golden action is infeasible.",
            "Each experiment contains one trial per task and is not a leaderboard estimate.",
            "Action-legality judgments are diagnostic GPT-4.1 outputs with structured parser validation.",
        ],
    }
    query_rows = {
        "experiment_summaries": summaries,
        "task_results": task_rows,
        "legality_checks": [row for item in extracted for row in item["legality"]],
        "violation_types": [row for item in extracted for row in item["violations"]],
        "prompt_sources": [row for item in extracted for row in item["prompts"]],
        "task_movements": movements,
        "baseline_findings": finding_rows,
        "milestones": config["milestones"],
        "evaluator_extensions": config["evaluator_extensions"],
    }
    return {
        "id": "dashboard:d693ef08-cef0-4933-b833-069f203c006d",
        "surface": "dashboard",
        "title": "Retail evaluation monitor",
        "generatedAt": generated_at,
        "buildStatus": "complete",
        "status": "reviewed",
        "scope": scope,
        "queries": {
            query_id: {"rows": rows, "source": source}
            for query_id, rows in query_rows.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and args.output.exists():
        current = load_json(args.output)
        os.environ.setdefault("MONITOR_GENERATED_AT", current["generatedAt"])
    snapshot = build_snapshot(args.config.resolve())
    rendered = json.dumps(snapshot, indent=2, sort_keys=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            raise SystemExit("Monitor snapshot is stale; run refresh_monitor.py")
        print("Monitor snapshot is current")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".json.tmp")
    temporary.write_text(rendered)
    temporary.replace(args.output)
    print(
        f"Wrote {args.output}: {len(snapshot['queries']['experiment_summaries']['rows'])} experiments, "
        f"{len(snapshot['queries']['task_results']['rows'])} task rows"
    )


if __name__ == "__main__":
    main()
