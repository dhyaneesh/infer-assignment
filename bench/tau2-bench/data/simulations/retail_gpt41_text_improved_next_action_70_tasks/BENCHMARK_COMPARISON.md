# Next-action override: 70-task benchmark comparison

This experiment uses the complete long improved policy unchanged, followed by a
631-character override governing only what happens after approval. It ran the
same 70 retail task IDs with GPT-4.1 agent/user, temperature 0, seed 20260926,
and half-duplex text mode.

## Completion metrics (all 70 tasks)

| Metric | Long improved | Next-action override | Change |
|---|---:|---:|---:|
| Task completion | 58/70 (82.86%) | 55/70 (78.57%) | -3 tasks (-4.29 pp) |
| Database match | 59/70 (84.29%) | 57/70 (81.43%) | -2 tasks (-2.86 pp) |
| Read-action accuracy | 213/218 (97.71%) | 210/218 (96.33%) | -3 actions (-1.38 pp) |
| Write-action accuracy | 94/114 (82.46%) | 95/114 (83.33%) | +1 action (+0.88 pp) |

Task 105 passed under the long prompt but failed under this experiment. Because
task 105 has an infeasible golden action, the comparable completion result is
57/69 (82.61%) versus 55/69 (79.71%): a net loss of two tasks.

## Trajectory diagnostics (69 tasks; task 105 excluded)

Lower is better.

| Metric | Long improved | Next-action override | Change |
|---|---:|---:|---:|
| Cardinality-error turns | 79 / 48 tasks | 64 / 39 tasks | -15 turns / -9 tasks |
| Unsafe-write turns | 26 / 22 tasks | 24 / 23 tasks | -2 turns / +1 task |
| Illegal actions | 19 / 15 tasks | 16 / 14 tasks | -3 actions / -1 task |

The largest legality improvement was in state-precondition violations, which
fell from 7 to 2. Unsatisfied-user-condition violations fell from 2 to 1.
Missing-confirmation violations increased from 6 to 7.

## Task movement (task 105 excluded)

- Newly passing: 30, 79, 94, 100
- Regressed: 22, 34, 80, 90, 98, 102
- Still failing: 2, 20, 59, 76, 91, 107, 109, 112

## Interpretation

The override materially improved execution discipline: fewer multi-call turns,
fewer illegal actions, and far fewer state-precondition violations. It also
slightly improved write-action matching. However, completion, database matching,
and read accuracy regressed. The result supports retaining the next-action idea,
but not this exact wording as the final prompt. The next refinement should keep
the post-approval execution and plan-pruning rules while reducing the new
missing-confirmation errors and investigating the six regressed tasks.
