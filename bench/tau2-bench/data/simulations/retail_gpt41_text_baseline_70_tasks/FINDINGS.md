# Retail GPT-4.1 baseline findings

## Dataset and headline result

- Domain: `retail`
- Agent and user simulator: `gpt-4.1-2025-04-14`
- Temperature: `0.0`
- 70 non-overlapping text tasks were run; task 105 is quarantined as infeasible
- Analyzable set: 69 tasks
- Passed: 54/69 (78.26%)
- Database match: 56/69 (81.16%)
- Analyzed model cost: $4.61327 (task 105 excluded)

## Consolidated error taxonomy

Errors are separated by where they originate. Task lists overlap when one trajectory exhibits more than one behavior; the “primary” allocation assigns each of the 15 scored failures exactly once.

### A. Model behavior errors

| Category | Primary failed tasks | Also observed in | What went wrong | Best grader |
|---|---|---|---|---|
| Structured selection and factual computation | 2, 4, 20, 109 | - | Failed availability filtering, constrained maximum selection, or minimum-price selection. | Deterministic calculation plus LLM check that the communicated conclusion uses it. |
| Policy, feasibility, and fallback handling | 34, 57, 63, 91, 107 | Passing tasks 33, 66, 86; failed task 76 | Attempted unsupported removal, ignored refund/payment conditions, used an identical exchange item, or missed a supplied fallback. | Deterministic precondition and tool-result checks; LLM judges whether the selected fallback matches user intent. |
| Entity/action binding across compound requests | 38, 59, 71, 76, 98, 112 | - | Lost the correct order, address source, payment method, or cancellation reason while handling several requests. | Deterministic argument comparison plus LLM intent-to-action mapping. |
| Tool-call cardinality violations | - | 81 turns across 52/69 tasks; 39 affected tasks currently pass | An assistant turn contained more than one tool call. This metric applies regardless of whether the calls read or write data. | Deterministic: `len(tool_calls) > 1`. |
| Unsafe write turns | - | 29 turns across 25 tasks; 16 affected tasks currently pass | A turn issued multiple writes or contained a write that returned an error. The union contains 25 multi-write turns and 7 write-error turns, with 3 overlapping turns. | Deterministic: `write_call_count > 1 OR any(write_result.error)`. Count each assistant turn once. |
| Action-legality violations | 17 illegal writes across 14 tasks | Tasks 11, 33, 34, 42, 44, 57, 58, 66, 76, 86, 91, 104, 107, 112 | A database-accepted action may still violate policy, user conditions, confirmation requirements, entity binding, or transition rules. | GPT-4.1 judge over policy, conversation prefix, tool results, and exact action arguments. |
| Invalid transition ordering | - | Passing task 104 | Item modification locked the order, but an address modification was successfully applied afterward. | Deterministic state-machine replay with pre/post-state checks. |

Primary allocation of the 15 scored failures:

- Structured selection/facts: 4
- Policy/feasibility/fallback: 5
- Entity/action binding: 6

### B. Environment and state-machine defects

| Defect | Evidence | Effect |
|---|---|---|
| Loose pending-state guard | `modify_pending_order_address` checks whether the string `"pending"` occurs anywhere in status. Task 104 therefore accepts status `pending (item modified)`. | A policy-invalid post-lock mutation succeeds and still receives reward 1.0. |
| Inconsistent transition guards | Item modification and cancellation require exact status `pending`, while address modification accepts any status containing `pending`. | Tool behavior does not implement one coherent policy state machine. |
| Parallel writes bypass sequential caution | The orchestrator executes `MultiToolMessage`; task 104 submits item and address writes together in the wrong order. | The agent cannot inspect the first write’s state before issuing the second. |

### C. Evaluator defects

| Defect | Evidence | Effect |
|---|---|---|
| Final-state-only success hides bad paths | Tasks 11 and 86 make invalid calls, recover, and receive reward 1.0. | Unsafe attempts and incorrect intermediate decisions are invisible. |
| Action correctness is diagnostic only | All 69 analyzed tasks use `DB` or `DB + NL_ASSERTION`; none include `ACTION` in final reward. | Wrong or missing actions can pass when DB/NL happen to match. |
| Domain policy is not evaluated | One-tool-per-turn violations are accepted, and optional communication validation does not check call count. | 39 passing trajectories violate the explicit domain policy. |
| Action matching can be syntactically brittle | Equivalent arithmetic expressions with reordered operands can be marked unmatched. | Diagnostic false negatives that should not be confused with behavioral failures. |

### D. Task/data defects and caveats

| Defect | Tasks | Effect |
|---|---|---|
| Golden read references missing product `6086499569` | 2, 4 | Golden replay warning and read-action mismatch, independent of the genuine incorrect count. |
| Expected email differs from stored email punctuation | 38 | Initial lookup fails and requires fallback authentication. |

### Recommended grader split

1. **Deterministic trajectory grader:** tool-call count, write preconditions, tool errors, state transitions, locked states, exact entity/payment/address binding, availability, same-item exchange, and successful completion.
2. **Deterministic task validator:** replay every golden action before evaluation and quarantine tasks whose golden path raises an exception.
3. **LLM intent judge:** nuanced conditional intent, fallback semantics, whether all parts of a compound request were retained, and factual communication quality.
4. **Hybrid verdict:** deterministic safety/policy failures cannot be overridden by the LLM judge; the LLM contributes only where semantics cannot be resolved from state and arguments.

## Finding 1: structured selection and factual accuracy

The proposed grouping of tasks 2, 4, 20, and 109 is supported by the trajectories.

| Task | Observed failure | DB match | Interpretation |
|---|---|---:|---|
| 2 | Reported 12 T-shirt options instead of counting only the 10 available variants. | Yes | Pure factual aggregation error. |
| 4 | Reported 11 T-shirt options instead of 10 available variants. | Yes | Repeat of task 2; pure factual aggregation error. |
| 20 | Chose incorrect replacement variants while trying to maximize price under product and shoe-size constraints. | No | Constrained-selection error that produced the wrong mutation. |
| 109 | Claimed to choose the cheapest tablet but selected item `4913411651`; the reference cheapest valid item was `2106335193`. | No | Minimum-selection error that produced the wrong mutation. |

The common behavior is failure to deterministically filter and optimize over structured tool output before answering or writing. Tasks 2 and 4 only corrupt the communicated fact; tasks 20 and 109 also corrupt database state.

## Finding 2: policy, fallback, and database-state failures

All six proposed tasks have a final DB mismatch, but they are not all the same subtype.

| Task | Evidence | Refined classification |
|---|---|---|
| 57 | The user permitted cancellation only if the refund could go to a gift card. Policy required a cancellation refund to the original credit card, yet the agent cancelled first and explained the conflict afterward. | Conditional-policy violation and premature irreversible write. |
| 91 | The agent exchanged an e-reader for the identical item ID. Retail policy requires a different product option; it should have used the requested 32GB fallback. | Tool arguments violated exchange policy and skipped a fallback. |
| 107 | The agent exchanged hiking boots for the identical item ID instead of selecting the leather, waterproof fallback. | Same-item exchange policy violation and skipped fallback. |
| 34 | The agent attempted unsupported item removal twice, receiving `The number of items to be exchanged should match`, then updated the order with the wrong New York address. | Invalid mutation attempt followed by incorrect address-source selection. |
| 76 | The agent attempted removal through `modify_pending_order_items` with no replacements, then cancelled both orders but used `no longer needed` where the fleece-jacket order required `ordered by mistake`. | Invalid mutation attempt plus loss of the per-order cancellation reason. |
| 112 | Both item modifications were correct, but the inferred address was applied to order `#W9810810` instead of target order `#W3730488`. | Wrong-target/entity-routing failure; the tool itself was policy-permitted. |

Therefore, “database failures” is accurate at the outcome level, while the actionable behavior spans policy validation, conditional fallback handling, and entity-to-action mapping.

## Finding 3: turn-level trajectory violations are not scored

The retail policy states:

> You should at most make one tool call at a time.

### Tool-call cardinality violation

Deterministic definition: `len(tool_calls) > 1`. This metric is independent of write safety, so a multi-write turn is correctly counted here and may also trigger the unsafe-write metric.

| Measure | Result |
|---|---:|
| Cardinality-violation turns | 81 |
| Affected tasks | 52/69 |
| Passing affected tasks | 39 |
| Failing affected tasks | 13 |
| Maximum tool calls in one turn | 12 |

### Unsafe write turn

Deterministic definition: an assistant turn violates the metric when `write_call_count > 1 OR any(write_result.error)`. Each turn is counted once even when both conditions hold.

| Measure | Result |
|---|---:|
| Unsafe write turns | 29 |
| Affected tasks | 25/69 |
| Passing affected tasks | 16 |
| Failing affected tasks | 9 |
| Turns with multiple writes | 25 |
| Turns with at least one failed write | 7 |
| Turns satisfying both conditions | 3 |
| Individual failed write attempts | 8 |

### Action-legality violation

The half-duplex GPT-4.1 legality judge evaluated 122 attempted write actions without using golden actions. It classified 105 as legal, 17 as illegal, and none as uncertain. The 17 illegal actions occurred in 14 tasks: 11, 33, 34, 42, 44, 57, 58, 66, 76, 86, 91, 104, 107, and 112.

| Measure | Result |
|---|---:|
| Attempted writes evaluated | 122 |
| Illegal writes | 17 |
| Tasks with at least one illegal write | 14/69 |
| Passing benchmark tasks flagged | 8 |
| Failed benchmark tasks flagged | 6 |
| Tasks flagged by all three checks | 10 |
| Legality-only tasks | 2 (44, 57) |

The judge recovered all seven manually identified legality candidates: 34, 57, 76, 91, 104, 107, and 112. It also exposed missing confirmation or invalid attempts in passing tasks. During validation, its initial outputs for tasks 4 and 95 incorrectly treated cardinality as action illegality; the prompt was corrected to keep these dimensions independent, both tasks were re-evaluated as legal, and a parser guard now rejects verdict/reasoning contradictions.

This is a real policy-compliance gap, not a logging artifact. For example, passing task 87 issued four writes in one assistant turn, and passing task 104 issued three returns in one turn.

### Why these trajectories still pass

1. Of the 69 analyzed tasks, 67 use reward basis `DB + NL_ASSERTION` and two use `DB` only. None include `ACTION` or a policy-adherence criterion in the final reward.
2. Action matching is calculated and displayed diagnostically, but it is multiplied into the final reward only when `ACTION` appears in the task's `reward_basis`.
3. The orchestrator explicitly supports parallel tool calls through `MultiToolMessage` and executes their results.
4. `--enforce-communication-protocol` defaults to false. Even when enabled, its validator checks empty messages, mixed text-plus-tool messages, and solo-mode text. It does not reject multiple tool calls in one message.
5. No trajectory mixed text and tool calls in the same assistant message, so the implemented communication protocol was not violated even though the domain policy was.

The current headline pass rate should therefore be read as task-outcome success, not strict retail-policy compliance.

## Consolidated failure taxonomy

The 15 failed tasks support three prompt/eval behaviors:

1. **Structured-data verification:** filter unavailable variants, preserve constraints, and verify counts, minima, maxima, and price calculations before responding or writing.
2. **Policy and fallback validation:** validate the proposed tool arguments and payment/refund feasibility before confirmation and before irreversible writes.
3. **Explicit action ledger:** track each order's ID, requested operation, target address, payment method, fallback, and cancellation reason independently.

The grader should expose three independent dimensions: **tool-call cardinality violation**, **unsafe write turn**, and **action-legality violation**. Overlap is intentional because they answer different questions: call shape, database-write safety, and semantic permission. Action legality should be judged from the policy, conversation, pre-action state, and exact action arguments; database acceptance must not imply legality.

## Benchmark and data caveats

- Tasks 2 and 4 expect a read of missing product ID `6086499569`; this causes a diagnostic action mismatch but does not explain their failed natural-language count.
- Task 38's expected email omits the dot present in the database, so fallback authentication is necessary.
- Task 105 is excluded from every aggregate and error category because its golden exchange is infeasible with the supplied payment state. It remains only in the raw 70-run archive for reproducibility.
- Exact action matching is sometimes stricter than semantic equivalence, including arithmetic expressions with reordered operands.
- These are 69 analyzable convenience-sampled tasks with one trial each, not a leaderboard-comparable estimate.

## Artifacts

- `combined_results.json`: merged tasks and full trajectories for all 70 simulations.
- `metrics.json`: compact aggregate outcome metrics for the 69-task analyzed set.
- `policy_compliance_metrics.json`: machine-readable multi-tool policy statistics and every violating turn.
- `action_legality_backtest_summary.json`: per-task results and overlap across all three trajectory checks.
- `action_legality_backfilled_results.json`: full trajectories with diagnostic legality checks stored in `RewardInfo`.
- `error_catalog.json`: machine-readable consolidated taxonomy and task mappings.
- `write_transition_timeline.json`: all write attempts with arguments, result status, and errors.
- `tool_error_timeline.json`: every tool error, including reads and writes.
- `task_results.csv`: one row per task.
- `raw_batches/`: untouched 10-task, 10-task, and 50-task result files.
- `CHECKSUMS.txt`: SHA-256 checksums for all consolidated artifacts.
