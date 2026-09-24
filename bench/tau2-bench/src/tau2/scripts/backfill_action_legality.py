"""Backfill text trajectories with independent policy diagnostics."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

from tau2.config import DEFAULT_LLM_ACTION_LEGALITY
from tau2.data_model.simulation import Results, RewardInfo
from tau2.environment.toolkit import get_tool_types
from tau2.evaluator.evaluator_action_legality import (
    ActionLegalityEvaluator,
    TrajectoryPolicyDiagnostics,
    evaluate_deterministic_trajectory_checks,
    normalize_action_legality_checks,
)
from tau2.registry import registry


def backfill(
    input_path: Path,
    output_path: Path,
    summary_path: Path,
    excluded_task_ids: set[str],
    model: str,
    workers: int,
    checkpoint_dir: Path | None = None,
    refresh_task_ids: set[str] | None = None,
) -> dict:
    results = Results.load(input_path)
    domain = results.info.environment_info.domain_name
    env = registry.get_env_constructor(domain)(solo_mode=False)
    policy = results.info.environment_info.policy or env.get_policy()
    tool_types = get_tool_types(env.tools)
    tasks = {task.id: task for task in results.tasks}
    selected = [
        simulation
        for simulation in results.simulations
        if simulation.task_id not in excluded_task_ids
    ]

    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_one(simulation):
        checkpoint = (
            checkpoint_dir / f"task_{simulation.task_id}.json"
            if checkpoint_dir is not None
            else None
        )
        should_refresh = simulation.task_id in (refresh_task_ids or set())
        if checkpoint is not None and checkpoint.exists() and not should_refresh:
            cached = json.loads(checkpoint.read_text())
            legality = RewardInfo.model_validate(cached["legality"])
            legality.action_legality_checks = normalize_action_legality_checks(
                legality.action_legality_checks or []
            )
            return (
                simulation.id,
                TrajectoryPolicyDiagnostics.model_validate(cached["deterministic"]),
                legality,
            )
        messages = simulation.get_messages()
        deterministic = evaluate_deterministic_trajectory_checks(
            messages, tool_types
        )
        legality = ActionLegalityEvaluator.calculate_reward(
            task=tasks[simulation.task_id],
            full_trajectory=messages,
            policy=policy,
            tool_types=tool_types,
            model=model,
        )
        result = simulation.id, deterministic, legality
        if checkpoint is not None:
            checkpoint.write_text(
                json.dumps(
                    {
                        "deterministic": deterministic.model_dump(),
                        "legality": legality.model_dump(mode="json"),
                    },
                    indent=2,
                )
                + "\n"
            )
        return result

    completed = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(evaluate_one, sim): sim for sim in selected}
        for future in as_completed(futures):
            simulation = futures[future]
            try:
                completed[simulation.id] = future.result()
                logger.info(f"Evaluated task {simulation.task_id}")
            except Exception:
                logger.exception(f"Failed task {simulation.task_id}")
                raise

    task_rows = []
    verdict_counts: Counter[str] = Counter()
    violation_counts: Counter[str] = Counter()
    for simulation in selected:
        _, deterministic, legality = completed[simulation.id]
        checks = legality.action_legality_checks or []
        if simulation.reward_info is not None:
            simulation.reward_info.action_legality_checks = checks
            simulation.reward_info.info = simulation.reward_info.info or {}
            simulation.reward_info.info["trajectory_policy_diagnostics"] = (
                deterministic.model_dump()
            )
            simulation.reward_info.info["action_legality"] = {
                "diagnostic_only": True,
                "reward": legality.reward,
                "model": model,
            }
        verdict_counts.update(check.verdict for check in checks)
        for check in checks:
            violation_counts.update(check.violation_types)
        task_rows.append(
            {
                "task_id": simulation.task_id,
                "benchmark_reward": simulation.reward_info.reward
                if simulation.reward_info is not None
                else None,
                "cardinality_error_turns": len(
                    deterministic.cardinality_violations
                ),
                "unsafe_write_turns": len(deterministic.unsafe_write_turns),
                "legal_actions": sum(c.verdict == "legal" for c in checks),
                "illegal_actions": sum(c.verdict == "illegal" for c in checks),
                "uncertain_actions": sum(c.verdict == "uncertain" for c in checks),
                "action_legality_checks": [c.model_dump() for c in checks],
            }
        )

    summary = {
        "scope": {
            "input": str(input_path),
            "simulations_run": len(results.simulations),
            "simulations_analyzed": len(selected),
            "excluded_task_ids": sorted(excluded_task_ids),
            "model": model,
        },
        "cardinality": {
            "violating_turns": sum(r["cardinality_error_turns"] for r in task_rows),
            "affected_tasks": sum(r["cardinality_error_turns"] > 0 for r in task_rows),
        },
        "unsafe_write": {
            "violating_turns": sum(r["unsafe_write_turns"] for r in task_rows),
            "affected_tasks": sum(r["unsafe_write_turns"] > 0 for r in task_rows),
        },
        "action_legality": {
            "verdict_counts": dict(sorted(verdict_counts.items())),
            "affected_tasks": sum(r["illegal_actions"] > 0 for r in task_rows),
            "violation_type_counts": dict(sorted(violation_counts.items())),
        },
        "overlap": {
            "cardinality_and_unsafe_tasks": sum(
                r["cardinality_error_turns"] > 0 and r["unsafe_write_turns"] > 0
                for r in task_rows
            ),
            "legality_only_tasks": sum(
                r["illegal_actions"] > 0
                and r["cardinality_error_turns"] == 0
                and r["unsafe_write_turns"] == 0
                for r in task_rows
            ),
        },
        "tasks": task_rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.save(output_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--exclude-task-id", action="append", default=[])
    parser.add_argument("--model", default=DEFAULT_LLM_ACTION_LEGALITY)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--refresh-task-id", action="append", default=[])
    args = parser.parse_args()
    summary = backfill(
        input_path=args.input,
        output_path=args.output,
        summary_path=args.summary,
        excluded_task_ids=set(args.exclude_task_id),
        model=args.model,
        workers=args.workers,
        checkpoint_dir=args.checkpoint_dir,
        refresh_task_ids=set(args.refresh_task_id),
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "tasks"}, indent=2))


if __name__ == "__main__":
    main()
