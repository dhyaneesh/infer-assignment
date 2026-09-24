# Five-minute demo script

Target length: approximately 5 minutes at a natural speaking pace.

## 0:00-0:25 - Introduction

**On screen:** Repository root, then briefly show the task PDF.

Hi, I'm Dhyaneesh. I evaluated GPT-4.1 on the Tau Bench retail domain, built evaluators for three failure behaviors, and tested whether prompt changes improved them. I used half-duplex text trajectories to isolate policy and tool use from speech-to-text and text-to-speech variance.

## 0:25-0:55 - Experimental setup

**On screen:** Open the monitor's Overview tab.

I ran the same 70 retail tasks with GPT-4.1 using a fixed task set, model, temperature, and nominal seed. Because the agent and user simulator are LLMs and each prompt was run once, these are descriptive results, not repeatable causal estimates.

Task 105 remains in the outcome results but is excluded from diagnostics because its golden exchange is infeasible with the supplied payment state. That leaves 69 valid trajectories.

## 0:55-1:30 - What the original evaluation missed

**On screen:** Select the Before the evals tab and scroll through the findings.

The original reward measured final task outcome but not the full trajectory. Action-level policy compliance was absent from all 69 analyzed reward bases.

An agent could therefore make multiple calls in one turn, attempt invalid writes, or perform a database-accepted action that policy forbids—for example, acting before confirmation or modifying an order after an item-changing transition. A later action could hide the earlier mistake from final-state grading.

## 1:30-2:25 - The three evaluator extensions

**On screen:** Select Evaluator extensions. Point to each evaluator card and the baseline diagnostic chart.

I split these failures into three independent evaluator dimensions.

First is tool-call cardinality: a deterministic violation whenever an assistant turn contains more than one tool call.

Second is unsafe write turn. A turn is unsafe if it contains multiple writes or any write returns an error. This is separate because harmless batched reads are not equivalent to batched mutations.

Third is an LLM-based action-legality check for each attempted write. It judges policy, pre-action state, user authorization, entity, and arguments. This catches missing confirmation, the wrong action for an order status, and prohibited post-transition changes.

The implementation associates every write with its result, validates the judge's structured response, stores it in `RewardInfo`, and backfills all 69 valid trajectories. Synthetic tests cover legal actions, policy violations, tool failures, and parser contradictions.

## 2:25-3:30 - Prompt experiments and results

**On screen:** Return to Overview. Show the completion and diagnostic comparison charts, then click through the four prompt tabs.

I compared four prompts.

The baseline completed 55 of 70 tasks. It produced 81 cardinality errors, 29 unsafe write turns, and 17 illegal writes.

The long improved prompt added request tracking, conditional availability, confirmation, and transition rules. This run completed 58 of 70 tasks and matched 59 databases. But cardinality only fell to 79, illegal writes rose to 19, and correct write actions fell from the baseline's 99 to 94.

The short prompt replaced that checklist with: read, check, summarize, wait for approval, execute, and verify. Cardinality improved substantially to 63, and illegal writes fell to 16, but completion dropped to 53 of 70 and unsafe writes remained at 28.

The next-action override kept the long prompt but precisely defined behavior after approval. This run recorded 64 cardinality errors, 24 unsafe writes, and 16 illegal writes. Completion returned to 55 of 70, and correct write actions remained below baseline at 95.

The only substantial observed movement was cardinality, which fell from 81 to 63 or 64 for two variants. Unsafe and illegal-write differences were small or worse, and all prompt variants reduced write-action accuracy. Repeated runs are needed before attributing any difference to the prompts.

## 3:30-4:15 - Task-level evidence and reproducibility

**On screen:** Open Task explorer. Filter Diagnostic to Action legality, switch between Baseline and Long improved, and select a task.

The task explorer makes aggregate numbers auditable. I can filter by experiment, outcome, or diagnostic, then inspect each write, its arguments, verdict, reasoning, and suggested correction.

The monitor reads checked-in artifacts and does not rerun models. Its refresh script requires 70 unique outcome records and the same 69 diagnostic tasks per experiment. It rejects duplicate IDs, mismatched populations, and unreconciled legality counts. Unit tests verify the metrics without embedding full trajectories.

## 4:15-4:45 - Trade-offs and alternatives

**On screen:** Return to Evaluator extensions or show the relevant evaluator files in the editor.

The hybrid design is deliberate. Deterministic checks are cheap and reproducible but cannot interpret authorization or policy semantics. An LLM judge can, but adds cost and nondeterminism. Combining both limits judgment to the semantic problem.

I store the signals separately instead of immediately creating one reward, preserving interpretability and avoiding arbitrary penalty weights before calibration.

## 4:45-5:00 - Future improvements and close

**On screen:** Return to Overview and finish on the recommendation cards.

Next, I would repeat every prompt run and report uncertainty, calibrate legality against human labels, and use a different judge family to reduce self-evaluation bias. I would then test audio trajectories to measure STT and TTS effects separately.

The repository includes the implementation, technical evidence, reproducible monitor, and Codex session transcripts. Thank you.

## Recording checklist

- Keep the browser at a readable zoom and close unrelated tabs.
- Start the local monitor using the commands in `bench/tau2-bench/monitor/README.md`.
- Preselect the Overview tab before recording.
- Avoid reading every metric card; emphasize the three diagnostic metrics and the completion trade-off.
- Aim for 4:45 to 4:55 during rehearsal to leave a small timing buffer.
