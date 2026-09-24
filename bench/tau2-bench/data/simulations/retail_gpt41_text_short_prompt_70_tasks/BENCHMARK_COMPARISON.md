# Short execution prompt: 70-task benchmark comparison

The short prompt was evaluated on the same 70 retail task IDs with GPT-4.1 for
both agent and user, temperature 0, seed 20260926, and half-duplex text mode.
Task 105 is included in raw completion metrics but excluded from the three
trajectory diagnostics because its golden action is infeasible.

## Completion metrics (70 tasks)

| Metric | Baseline | Long improved | Short prompt |
|---|---:|---:|---:|
| Task completion | 55/70 (78.57%) | 58/70 (82.86%) | 53/70 (75.71%) |
| Database match | 57/70 (81.43%) | 59/70 (84.29%) | 55/70 (78.57%) |
| Read-action accuracy | 211/218 (96.79%) | 213/218 (97.71%) | 204/218 (93.58%) |
| Write-action accuracy | 99/114 (86.84%) | 94/114 (82.46%) | 96/114 (84.21%) |

Excluding task 105, completion is baseline 54/69 (78.26%), long improved 57/69
(82.61%), and short 53/69 (76.81%).

## Trajectory diagnostics (69 tasks; task 105 excluded)

Lower is better.

| Metric | Baseline | Long improved | Short prompt |
|---|---:|---:|---:|
| Cardinality-error turns | 81 / 52 tasks | 79 / 48 tasks | 63 / 45 tasks |
| Unsafe-write turns | 29 / 25 tasks | 26 / 22 tasks | 28 / 27 tasks |
| Illegal actions | 17 / 14 tasks | 19 / 15 tasks | 16 / 15 tasks |

## Result

The compact sequence strongly reduced multi-tool turns: 18 fewer than baseline
and 16 fewer than the long prompt. It did not reduce unsafe-write prevalence;
unsafe writes affected 27 tasks, the worst of the three variants. It produced
the fewest illegal actions, but legality still affected 15 tasks because the
errors were spread across more trajectories.

The completion tradeoff is unfavorable. Relative to the long improved prompt,
the short prompt lost five completed tasks, four database matches, nine correct
read actions, and gained two correct write actions. The short protocol is useful
for the cardinality instruction, but is not a suitable wholesale replacement
for the long prompt.

Short-prompt failures excluding task 105: 2, 20, 21, 28, 34, 39, 59, 71, 76,
91, 95, 98, 104, 107, 109, 112.
