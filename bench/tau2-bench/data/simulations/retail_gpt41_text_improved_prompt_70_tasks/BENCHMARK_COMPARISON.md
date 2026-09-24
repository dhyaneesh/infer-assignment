# Improved retail prompt: 70-task benchmark comparison

The improved prompt was run on the same 70 GPT-4.1 text trajectories as the
baseline. Task 105 is retained in the raw benchmark totals below, but excluded
from the diagnostic comparison because its golden action is infeasible and its
pass is caused by the evaluator defect previously identified.

## Completion metrics (all 70 tasks)

| Metric | Baseline | Improved prompt | Change |
|---|---:|---:|---:|
| Task completion | 55/70 (78.57%) | 58/70 (82.86%) | +3 tasks (+4.29 pp) |
| Database match | 57/70 (81.43%) | 59/70 (84.29%) | +2 tasks (+2.86 pp) |
| Read-action accuracy | 211/218 (96.79%) | 213/218 (97.71%) | +2 actions (+0.92 pp) |
| Write-action accuracy | 99/114 (86.84%) | 94/114 (82.46%) | -5 actions (-4.39 pp) |

## New trajectory metrics (69 analyzed tasks; task 105 excluded)

Lower is better for every row.

| Metric | Baseline | Improved prompt | Change |
|---|---:|---:|---:|
| Cardinality-error turns | 81 turns / 52 tasks | 79 turns / 48 tasks | -2 turns / -4 tasks |
| Unsafe-write turns | 29 turns / 25 tasks | 26 turns / 22 tasks | -3 turns / -3 tasks |
| Illegal actions | 17 actions / 14 tasks | 19 actions / 15 tasks | +2 actions / +1 task |

The action-legality counts exclude cardinality-only findings. Six improved-run
write actions (four in task 87 and two in task 113) had originally been labeled
`wrong_sequence` solely because multiple calls appeared in one assistant turn.
Those are now classified only by the deterministic cardinality evaluator.

## Comparable task completion (task 105 excluded)

- Baseline: 54/69 (78.26%)
- Improved prompt: 57/69 (82.61%)
- Net: +3 tasks (+4.35 percentage points)
- Newly passing: 4, 34, 38, 57, 63, 71, 98
- Regressed: 30, 79, 94, 100
- Still failing: 2, 20, 59, 76, 91, 107, 109, 112

## Interpretation

The prompt improved overall completion, database matching, read accuracy,
cardinality, and unsafe-write behavior. It did not improve action legality or
write-action matching in this sample. The legality shift is concentrated in
state preconditions and missing informed confirmation: the improved policy makes
those requirements explicit, and the agent still violates them in several
trajectories. The next prompt iteration should target state-machine discipline
and confirmation immediately before writes without weakening the completion
mandate.
