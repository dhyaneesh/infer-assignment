import React, { useMemo, useState } from "react";
import {
  DataComponent,
  DataTable,
  Dropdown,
  EvidenceChart,
  SectionHeader,
  useDataApp,
  useDashboardTabs,
} from "../../data-app-public.jsx";
import "./dashboard.css";

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "journey", label: "Before the evals" },
  { id: "evaluators", label: "Evaluator extensions" },
  { id: "baseline", label: "Baseline" },
  { id: "improved", label: "Long improved" },
  { id: "short", label: "Short execution" },
  { id: "next_action", label: "Next action" },
  { id: "tasks", label: "Task explorer" },
];

const pct = value => value == null ? "—" : `${Number(value).toFixed(2)}%`;
const ratio = (value, total) => `${value}/${total} (${pct(total ? value * 100 / total : null)})`;
const rowsOf = (queries, id) => queries[id]?.rows ?? [];

function MetricStrip({ rows }) {
  return <div className="monitor-metric-grid">
    {rows.map(row => <DataComponent key={row.id} variant="card" id={`metric-${row.id}-${row.experimentId ?? "all"}`}
      queryId="experiment_summaries" kind="metric" title={row.label} displayRows={[row]} sourceRows={row.sourceRows ?? [row]}>
      <div className="monitor-metric-card">
        <div className="monitor-metric-value">{row.value}</div>
        {row.detail && <div className="monitor-metric-detail">{row.detail}</div>}
      </div>
    </DataComponent>)}
  </div>;
}

function TableCard({ id, queryId, title, description, rows, columns, sourceRows = rows, onSelect, pageSize = 10 }) {
  return <DataComponent variant="card" id={id} queryId={queryId} kind="table" title={title} description={description}
    displayRows={rows} sourceRows={sourceRows}>
    <DataTable rows={rows} columns={columns} pageSize={pageSize} rowKey="row_key" onRowSelect={onSelect}
      rowActionLabel={onSelect ? row => `Inspect ${row.task_id ?? row.label ?? row.title}` : undefined} />
  </DataComponent>;
}

function Overview({ summaries, movements }) {
  const bestCompletion = summaries.reduce((best, row) => !best || row.completion_rate > best.completion_rate ? row : best, null);
  const bestCardinality = summaries.reduce((best, row) => !best || row.cardinality_turns < best.cardinality_turns ? row : best, null);
  const bestLegality = summaries.reduce((best, row) => !best || row.illegal_actions < best.illegal_actions ? row : best, null);
  const movementRows = movements.filter(row => ["newly passing", "regressed", "still failing"].includes(row.movement))
    .map((row, index) => ({ ...row, row_key: `${row.experiment_id}:${row.task_id}:${index}` }));
  return <div className="monitor-page">
    <SectionHeader id="overview-heading" title="Evaluation and prompt experiment overview"
      description="Matched GPT-4.1 retail text runs. Outcome metrics use all 70 tasks; trajectory diagnostics use 69 tasks and exclude infeasible task 105." />
    <MetricStrip rows={[
      { id: "best-completion", label: "Best completion", value: `${bestCompletion.experiment} · ${pct(bestCompletion.completion_rate)}`, detail: `${bestCompletion.completion_passes}/70 tasks`, sourceRows: summaries },
      { id: "best-cardinality", label: "Fewest cardinality errors", value: `${bestCardinality.experiment} · ${bestCardinality.cardinality_turns}`, detail: `${bestCardinality.cardinality_tasks}/69 tasks affected`, sourceRows: summaries },
      { id: "best-legality", label: "Fewest illegal writes", value: `${bestLegality.illegal_actions}`, detail: `${bestLegality.experiment}; ${bestLegality.legality_tasks}/69 tasks affected`, sourceRows: summaries },
      { id: "recommended", label: "Current recommendation", value: "Long improved", detail: "Best outcome performance; retain targeted execution ideas only after confirmation is tightened.", sourceRows: summaries },
    ]} />
    <div className="monitor-two-column">
      <EvidenceChart variant="card" id="outcome-comparison" queryId="experiment_summaries" title="Outcome metrics by prompt"
        description="Percent of matched outcomes or actions. All four measures are higher-is-better."
        rows={summaries} sourceRows={summaries} height={320}
        spec={{ type: "bar", x: "experiment", y: "completion_rate", fields: ["completion_rate", "db_rate", "read_accuracy", "write_accuracy"],
          showLegend: true, showXAxisLabel: false, showYAxisLabel: false, yDomain: [0, 100],
          legend: { labels: { completion_rate: "Completion", db_rate: "DB match", read_accuracy: "Read accuracy", write_accuracy: "Write accuracy" } } }} />
      <EvidenceChart variant="card" id="diagnostic-comparison" queryId="experiment_summaries" title="Trajectory diagnostics by prompt"
        description="Counts use the 69-task diagnostic population. Lower is better."
        rows={summaries} sourceRows={summaries} height={320}
        spec={{ type: "bar", x: "experiment", y: "cardinality_turns", fields: ["cardinality_turns", "unsafe_write_turns", "illegal_actions"],
          showLegend: true, showXAxisLabel: false, showYAxisLabel: false,
          legend: { labels: { cardinality_turns: "Cardinality turns", unsafe_write_turns: "Unsafe-write turns", illegal_actions: "Illegal actions" } } }} />
    </div>
    <TableCard id="task-movement-overview" queryId="task_movements" title="Task movement between prompt parents"
      description="Only newly passing, regressed, and still-failing tasks are shown; task 105 is excluded."
      rows={movementRows} sourceRows={movements} pageSize={12}
      columns={[
        { field: "experiment", label: "Experiment" }, { field: "parent", label: "Compared with" },
        { field: "task_id", label: "Task" }, { field: "movement", label: "Movement", presentation: "status" },
      ]} />
  </div>;
}

function Journey({ findings, milestones }) {
  const categories = {
    primary_failure_categories: "Observed task failures",
    hidden_trajectory_errors: "Hidden trajectory errors",
    environment_defects: "Environment defects",
    evaluator_defects: "Evaluator defects",
    task_data_defects: "Task/data defects",
  };
  return <div className="monitor-page">
    <SectionHeader id="journey-heading" title="What we saw before extending the evaluator"
      description="The baseline could reach the expected final state while taking policy-invalid or unsafe paths. These findings motivated independent trajectory diagnostics." />
    <DataComponent variant="card" id="project-milestones" queryId="milestones" kind="custom" title="Project timeline"
      displayRows={milestones} sourceRows={milestones}>
      <div className="monitor-timeline" data-reviewed-rows>
        {milestones.map(row => <div className="monitor-timeline-item" key={row.order}>
          <div className="monitor-timeline-index">{row.order}</div>
          <div><span className={`monitor-tag ${row.kind}`}>{row.kind}</span><h3>{row.title}</h3><p>{row.detail}</p></div>
        </div>)}
      </div>
    </DataComponent>
    {Object.entries(categories).map(([category, title]) => {
      const rows = findings.filter(row => row.category === category).map((row, index) => ({ ...row, row_key: `${category}:${index}` }));
      return <TableCard key={category} id={`finding-table-${category}`} queryId="baseline_findings" title={title}
        description={category === "hidden_trajectory_errors" ? "These errors can coexist and are intentionally measured independently." : undefined}
        rows={rows} sourceRows={findings}
        columns={[{ field: "id", label: "Finding" }, { field: "tasks", label: "Tasks" }, { field: "affected_tasks", label: "Affected" }, { field: "detail", label: "Evidence / definition" }]} />;
    })}
  </div>;
}

function Evaluators({ extensions, summaries, violations }) {
  const baseline = summaries.find(row => row.experiment_id === "baseline");
  return <div className="monitor-page">
    <SectionHeader id="evaluator-heading" title="Evaluator extensions"
      description="Two deterministic checks cover call shape and write safety. A structured LLM judge covers semantic permission. They remain diagnostic and do not modify benchmark reward." />
    <div className="monitor-extension-grid">
      {extensions.map(row => <DataComponent key={row.id} variant="card" id={`extension-${row.id}`} queryId="evaluator_extensions"
        kind="custom" displayRows={[row]} sourceRows={extensions} title={row.label} description={`${row.type} · ${row.unit}`}>
        <div className="monitor-extension-body"><code>{row.definition}</code><p>{row.purpose}</p></div>
      </DataComponent>)}
    </div>
    <MetricStrip rows={[
      { id: "baseline-cardinality", label: "Baseline cardinality", value: `${baseline.cardinality_turns} turns`, detail: `${baseline.cardinality_tasks}/69 tasks`, sourceRows: summaries },
      { id: "baseline-unsafe", label: "Baseline unsafe writes", value: `${baseline.unsafe_write_turns} turns`, detail: `${baseline.unsafe_write_tasks}/69 tasks`, sourceRows: summaries },
      { id: "baseline-illegal", label: "Baseline legality", value: `${baseline.illegal_actions} illegal`, detail: `${baseline.legal_actions} legal; ${baseline.legality_tasks}/69 tasks affected`, sourceRows: summaries },
    ]} />
    <EvidenceChart variant="card" id="violation-type-comparison" queryId="violation_types" title="Legality violation mix"
      description="Structured judge labels by prompt. A single action may have multiple labels."
      rows={violations} sourceRows={violations} height={360}
      spec={{ type: "bar", x: "violation_type", y: "count", series: "experiment", showLegend: true, showXAxisLabel: false, showYAxisLabel: false }} />
    <DataComponent variant="card" id="evaluator-validation" queryId="evaluator_extensions" kind="custom"
      displayRows={extensions} sourceRows={extensions} title="Validation and guardrails">
      <ul className="monitor-list">
        <li>Write calls are extracted in execution order and associated with tool results by call ID.</li>
        <li>The judge sees policy, conversation prefix, pre-action tool evidence, exact arguments, and result status.</li>
        <li>The parser requires exactly one result per write and rejects verdict/reasoning contradictions.</li>
        <li>Cardinality-only <code>wrong_sequence</code> judgments are normalized out of action legality.</li>
        <li>Checks are stored in <code>RewardInfo</code> and can be checkpointed/backfilled over existing trajectories.</li>
      </ul>
    </DataComponent>
  </div>;
}

function PromptTab({ experimentId, summaries, tasks, violations, prompts, movements }) {
  const summary = summaries.find(row => row.experiment_id === experimentId);
  const taskRows = tasks.filter(row => row.experiment_id === experimentId && !row.excluded);
  const violationRows = violations.filter(row => row.experiment_id === experimentId);
  const promptRows = prompts.filter(row => row.experiment_id === experimentId);
  const movementRows = movements.filter(row => row.experiment_id === experimentId && ["newly passing", "regressed", "still failing"].includes(row.movement));
  const metricRows = [
    { id: "completion", label: "Completion", value: ratio(summary.completion_passes, 70), detail: "Higher is better" },
    { id: "db", label: "DB match", value: ratio(summary.db_passes, 70), detail: "Higher is better" },
    { id: "read", label: "Read accuracy", value: ratio(summary.read_correct, summary.read_total), detail: "Higher is better" },
    { id: "write", label: "Write accuracy", value: ratio(summary.write_correct, summary.write_total), detail: "Higher is better" },
    { id: "cardinality", label: "Cardinality", value: `${summary.cardinality_turns} turns`, detail: `${summary.cardinality_tasks}/69 tasks · lower is better` },
    { id: "unsafe", label: "Unsafe writes", value: `${summary.unsafe_write_turns} turns`, detail: `${summary.unsafe_write_tasks}/69 tasks · lower is better` },
    { id: "legality", label: "Illegal actions", value: `${summary.illegal_actions}`, detail: `${summary.legality_tasks}/69 tasks · lower is better` },
  ].map(row => ({ ...row, experimentId, sourceRows: [summary] }));
  const outcomeRows = taskRows.map(row => ({ ...row, row_key: `${experimentId}:${row.task_id}` }));
  return <div className="monitor-page">
    <SectionHeader id={`${experimentId}-heading`} title={summary.experiment} description={summary.change} />
    <div className="monitor-hypothesis-grid">
      <div><span>Hypothesis</span><p>{summary.hypothesis}</p></div>
      <div><span>Observed conclusion</span><p>{summary.conclusion}</p></div>
    </div>
    <MetricStrip rows={metricRows} />
    <div className="monitor-two-column">
      <EvidenceChart variant="card" id={`${experimentId}-violations`} queryId="violation_types" title="Legality violations"
        description="Violation labels from attempted writes in the 69-task diagnostic population."
        rows={violationRows} sourceRows={violationRows} height={300}
        spec={{ type: "bar", x: "violation_type", y: "count", showLegend: false, showXAxisLabel: false, showYAxisLabel: false }} />
      <TableCard id={`${experimentId}-movement`} queryId="task_movements" title="Movement versus parent prompt"
        description={summary.parent_id ? "Task 105 excluded. Only changed or still-failing tasks shown." : "Baseline has no parent prompt; failures are shown below."}
        rows={movementRows.map((row, index) => ({ ...row, row_key: `${experimentId}:move:${index}` }))} sourceRows={movements}
        columns={[{ field: "task_id", label: "Task" }, { field: "movement", label: "Movement", presentation: "status" }, { field: "parent", label: "Parent" }]} />
    </div>
    <TableCard id={`${experimentId}-tasks`} queryId="task_results" title="Task outcomes and diagnostics"
      description="Exact task-level counts. Use Task explorer for legality reasoning and action arguments."
      rows={outcomeRows} sourceRows={taskRows} pageSize={12}
      columns={[
        { field: "task_id", label: "Task" }, { field: "benchmark_pass", label: "Pass", presentation: "status" },
        { field: "db_match", label: "DB", presentation: "status" }, { field: "cardinality_turns", label: "Cardinality" },
        { field: "unsafe_write_turns", label: "Unsafe writes" }, { field: "illegal_actions", label: "Illegal" },
      ]} />
    <DataComponent variant="card" id={`${experimentId}-prompt-source`} queryId="prompt_sources" kind="custom"
      title="Prompt lineage" description="Reviewed source files are shown in assembly order." displayRows={promptRows} sourceRows={promptRows}>
      <div className="monitor-prompt-files" data-reviewed-rows>
        {promptRows.map(row => <details key={row.file}>
          <summary><span>{row.order}. {row.file}</span><span>{row.characters.toLocaleString()} characters</span></summary>
          <pre>{row.content}</pre>
        </details>)}
      </div>
    </DataComponent>
  </div>;
}

function TaskExplorer({ tasks, legality, summaries }) {
  const experimentChoices = summaries.map(row => row.experiment);
  const [experiment, setExperiment] = useState(experimentChoices[0]);
  const [outcome, setOutcome] = useState("All");
  const [diagnostic, setDiagnostic] = useState("All");
  const [selectedTask, setSelectedTask] = useState(null);
  const filtered = useMemo(() => tasks.filter(row => row.experiment === experiment && !row.excluded)
    .filter(row => outcome === "All" || (outcome === "Passing") === row.benchmark_pass)
    .filter(row => diagnostic === "All"
      || diagnostic === "Cardinality" && row.cardinality_turns > 0
      || diagnostic === "Unsafe write" && row.unsafe_write_turns > 0
      || diagnostic === "Action legality" && row.illegal_actions > 0)
    .map(row => ({ ...row, row_key: `${row.experiment_id}:${row.task_id}` })), [tasks, experiment, outcome, diagnostic]);
  const selected = selectedTask && selectedTask.experiment === experiment ? selectedTask : filtered[0];
  const checks = legality.filter(row => row.experiment === experiment && row.task_id === selected?.task_id)
    .map((row, index) => ({ ...row, row_key: `${row.call_id}:${index}` }));
  const controls = <div className="monitor-controls">
    <Dropdown label="Experiment" value={experiment} choices={experimentChoices} onChange={value => { setExperiment(value); setSelectedTask(null); }} showLabel />
    <Dropdown label="Outcome" value={outcome} choices={["All", "Passing", "Failing"]} onChange={setOutcome} showLabel />
    <Dropdown label="Diagnostic" value={diagnostic} choices={["All", "Cardinality", "Unsafe write", "Action legality"]} onChange={setDiagnostic} showLabel />
  </div>;
  return <div className="monitor-page">
    <SectionHeader id="task-explorer-heading" title="Task-level evidence"
      description="Inspect benchmark outcomes and diagnostic evidence without embedding complete conversations." filters={controls} />
    <TableCard id="task-explorer-table" queryId="task_results" title={`${filtered.length} matching tasks`}
      description="Select a task to inspect its action-legality checks. Task 105 is intentionally omitted."
      rows={filtered} sourceRows={tasks.filter(row => row.experiment === experiment)} onSelect={setSelectedTask} pageSize={14}
      columns={[
        { field: "task_id", label: "Task" }, { field: "benchmark_pass", label: "Pass", presentation: "status" },
        { field: "db_match", label: "DB", presentation: "status" }, { field: "read_correct", label: "Read correct" },
        { field: "read_total", label: "Read total" }, { field: "write_correct", label: "Write correct" },
        { field: "write_total", label: "Write total" }, { field: "cardinality_turns", label: "Cardinality" },
        { field: "unsafe_write_turns", label: "Unsafe" }, { field: "illegal_actions", label: "Illegal" },
      ]} />
    {selected && <TableCard id="task-legality-detail" queryId="legality_checks" title={`Task ${selected.task_id} write-legality evidence`}
      description={checks.length ? "Each attempted write is judged independently from the golden trajectory." : "No attempted writes were recorded for this task."}
      rows={checks} sourceRows={legality.filter(row => row.experiment === experiment)} pageSize={10}
      columns={[
        { field: "turn_idx", label: "Turn" }, { field: "tool_name", label: "Tool" },
        { field: "verdict", label: "Verdict", presentation: "status" }, { field: "violation_types", label: "Violation" },
        { field: "arguments", label: "Arguments" }, { field: "reasoning", label: "Reasoning" },
        { field: "correct_action", label: "Correct action" },
      ]} />}
  </div>;
}

export function DashboardContent({ initialView = {} }) {
  const { queries } = useDataApp();
  const { activeTabId } = useDashboardTabs(tabs);
  const tab = initialView.tab ?? (tabs.some(item => item.id === activeTabId) ? activeTabId : "overview");
  const summaries = rowsOf(queries, "experiment_summaries");
  const tasks = rowsOf(queries, "task_results");
  const legality = rowsOf(queries, "legality_checks");
  const violations = rowsOf(queries, "violation_types");
  const prompts = rowsOf(queries, "prompt_sources");
  const movements = rowsOf(queries, "task_movements");
  const findings = rowsOf(queries, "baseline_findings");
  const milestones = rowsOf(queries, "milestones");
  const extensions = rowsOf(queries, "evaluator_extensions");
  if (!summaries.length) return <div className="monitor-empty">Run the monitor refresh command to load reviewed experiment data.</div>;
  if (tab === "overview") return <Overview summaries={summaries} movements={movements} />;
  if (tab === "journey") return <Journey findings={findings} milestones={milestones} />;
  if (tab === "evaluators") return <Evaluators extensions={extensions} summaries={summaries} violations={violations} />;
  if (["baseline", "improved", "short", "next_action"].includes(tab)) return <PromptTab experimentId={tab} summaries={summaries}
    tasks={tasks} violations={violations} prompts={prompts} movements={movements} />;
  return <TaskExplorer tasks={tasks} legality={legality} summaries={summaries} />;
}
