# Retail evaluator and prompt experiments

**Date:** 2026-09-24  
**Project:** Infer AI Engineer task / tau2-bench retail domain

> This transcript preserves every user message available in the active chat context. Earlier assistant replies and tool output were compacted by the chat runtime, so those portions are recorded as faithful implementation summaries rather than invented verbatim dialogue.

## Conversation

### User

Okay so we have just setup this project check Infer-AI-engineer-task.pdf for the task statement and the repo in general to see everything being setup , I saw the website for the trajectories let's just go with retail it has a claude sonnet baseline of 20% so our gpt 4.1 should get more problems so let's run 10 random text based tests and see get started from there

### User

Okay so we have just setup this project check Infer-AI-engineer-task.pdf for the task statement and the repo in general to see everything being setup , I saw the website for the trajectories let's just go with retail it has a claude sonnet baseline of 20% so our gpt 4.1 should get more problems so let's run 10 random text based tests and see get started from there

### User

Let's run another 10 different ones and reconconcile the outputs in one folder and files

### User

Run 50 ones please

### User

Okay looking at the logs I see some similarities in the erros so Tasks 2,4,109,20 are selection errors and inaccuracies in facts where we have given wrong counts prices etc Tasks 57,91,107 ,34,76 ,112 seem to be database failiures as in we have difference in what the tool used and what the policy permits there is also a worrying trend where the policy directly states that "You should at most make one tool call at a time" But a lot of the logs seem to grade them as passing even though it is against the policy to do so ? can you please verify my findings with data first and remove the previous .md in the simulations folder and replace them with the findings we have found now ?

### User

Go through the the logs and then through the policy my hunch is that there is a lot of state errors hiding in this as in a transition state might be wrong and then the agent changes it later we need that too in our new grader give me the logs and then what issue you found so that I can verify it please

### User

Okay I think a mix of deterministic checks and LLM basedd judgement would be the way to improve this grader, let's first consolidate all the errors and put them into categories please

### User

### 3. Environment/evaluator defects

- Loose pending-state guard allows task 104 to modify a locked order.
- Task 105 passes because both golden and agent actions fail, leaving identical unchanged databases.
- Task 105’s NL judge admits the exchange was incomplete but awards success.
- ACTION is absent from the reward basis of all 70 sampled tasks.
- Domain-policy violations are not scored.

### 4. Task/data defects

- Missing golden product ID: tasks 2, 4
- Email punctuation mismatch: task 38
- Infeasible golden payment/action: task 105

then there is no way to solve 105 is it ? then we cant scrutinize that let's remove that from our analysis and focus on the hidden trajectory errors first let's just focus on the Evals and then the prompt changes

### User

- 81 multi-tool turns across 52/69 tasks
- 39 passing tasks violated the one-tool-per-turn rule

These two are the same error in differnt metrics let's combine them into one metric with a deterministic defeition turn wise

- 25 turns contained multiple writes
- 8 invalid write attempts, including 5 in passing trajectories

same here

### User

Actually unsafe writes are worse than a simple cardinality issue so let's split that into two first

### User

I think we also need an Action legality LLM based checker on the side for permitted in database actions but not by policy right ? Which errors would we catch using that that cant be caught using the above deterministic checkers ?

### User

Okay so we have 3 changes now any cardinality should go in an cardinality error and any unsafe DB error should go to Unsafe write turn and then Action Legality should be seperate

### User

Okay let's plan out how to implement action legality

### User

1. Add ActionLegalityCheck model.
2. Build write-action extraction and call/result association.
3. Create the structured LLM prompt and parser.
4. Store legality checks diagnostically in RewardInfo.
5. Add unit tests with synthetic trajectories.
6. Backfill the 69 analyzed trajectories.

In a seperate evaluator add these and backtest them with the other two deterministic checks and let me know the results

### User

continue

### User

continue

### User

We need the half duplex ie text ones not full duplex adapter

### User

continue

### Assistant implementation summary

The evaluator work was completed against the half-duplex/text trajectory format. Three independent diagnostic signals were established:

1. **Cardinality errors** — deterministic, turn-wise detection of more than one tool call in an assistant turn.
2. **Unsafe write turns** — deterministic detection of multiple writes or invalid/failed write attempts in a turn.
3. **Action legality** — structured LLM judgment for actions accepted by the database/tool layer but forbidden by retail policy, including confirmation, state-transition, sequencing, and post-modification restrictions.

The action-legality implementation included structured models, write-action extraction, call/result association, parsing, `RewardInfo` diagnostic storage, synthetic unit tests, and a backfill over the 69 analyzable trajectories. Task 105 was excluded from diagnostic comparisons because the task/golden action is infeasible.

### User

Amazing, that finishes the first part of our work, now we have to move to the prompt changing to solve these problems now that our evals are working, can you show me the current System prompt along with ways that you would improve behaviour

### User

“A policy-compliant trajectory is more important than completing the request.” we need to require completion of every perimitted request otherwise refusal will become an way to improve legality and also we need not check if every selected item is avaiable only when the user is looking to buy a new one or is trying to get it replaced

### User

Okay I like this new prompt let's use this in our new benchmark

### User

Okay I like this new prompt let's use this in our new benchmark and run the same 70 ones here so we can check give me all four completion and our new three metrics too

### User

2. Replace the long checklist with a short execution sequence

The agent still performs actions before confirmation and uses the wrong order of operations. Give it a compact procedure:

For each request, follow this sequence:

READ → CHECK → SUMMARIZE → WAIT FOR APPROVAL → EXECUTE → VERIFY

Do not skip a stage.

Select the tool from the verified order status, not the user's wording.
A user may say "exchange" when the order requires pending-item modification.

After valid approval, execute the unchanged approved action.
Do not request the same approval again.

For one order, complete approved address/payment changes before item
modification. After item modification, do not modify or cancel that order.

Make exactly one tool call per turn, including read-only calls.

Let's try one with a short prompt to see what difference this makes

### User

For the next prompt experiment, change one behavior in the long prompt: the next action after approval.
After the user approves a complete action summary:

- If the approved details and conditions are unchanged, execute the next
  permitted action. Do not request the same confirmation again.
- Execute exactly one tool call, then inspect its result.
- For one order, execute approved address and payment changes before
  item modification.
- After item modification, remove all further modifications and
  cancellation for that order from the pending plan.
- If the user changes a material detail, obtain approval only for
  the affected action.

### User

Okay let's go ahead

### Assistant benchmark summary

Four 70-task experiments were consolidated:

| Experiment | Completion | DB | Read actions | Write actions | Cardinality errors | Unsafe writes | Illegal writes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 55/70 | 57/70 | 211/218 | 99/114 | 81 | 29 | 17 |
| Long improved | 58/70 | 59/70 | 213/218 | 94/114 | 79 | 26 | 19 |
| Short execution | 53/70 | 55/70 | 204/218 | 96/114 | 63 | 28 | 16 |
| Next-action override | 55/70 | 57/70 | 210/218 | 95/114 | 64 | 24 | 16 |

The long prompt produced the best completion rate, while the short and next-action prompts substantially reduced tool-cardinality errors. The next-action override had the fewest unsafe writes, and the short and next-action variants tied for the fewest illegal writes.

### User

okay ;et's move forward with an montior that shows what changes we've made and what we noticed you can use this chat history

### User

not just prompting I want the evals extensions we did as well please what we saw before making the evals and then tab by tab difference between the prompts please

### User

Implement the plan.

### Assistant

Implemented the complete evaluation and prompt-experiment monitor.

Key features:

- Overview comparing all four 70-task benchmarks.
- “Before the evals” timeline and original failure findings.
- Evaluator-extension documentation for:
  - Tool cardinality
  - Unsafe write turns
  - Action legality
- Separate tabs for each prompt experiment with exact prompt lineage.
- Task explorer with outcome and diagnostic filters plus legality evidence.
- Task 105 explicitly excluded from diagnostic comparisons.
- Reproducible data refresh and validation pipeline.

Main files:

- `bench/tau2-bench/monitor/README.md`
- `bench/tau2-bench/monitor/src/content/dashboard/DashboardContent.jsx`
- `bench/tau2-bench/monitor/experiments.json`
- `bench/tau2-bench/monitor/scripts/refresh_monitor.py`
- `bench/tau2-bench/monitor/dist/index.html`

Validation completed:

- 4/4 snapshot tests passed.
- All four benchmark metric sets reconciled.
- 280 experiment-task records verified.
- 207 cross-prompt task movements verified.
- Refresh consistency and lint checks passed.
- Production dashboard build passed.
- Desktop and mobile layouts visually verified.
- Filters and task evidence drill-down verified.
- Browser console: zero errors or warnings.

### User

can you extract the contents of this chat and put it into the transcripts folder please ?

## Resulting artifacts

- Evaluator and benchmark monitor: `bench/tau2-bench/monitor/`
- Transcript: `Session Transcripts/Retail evaluator and prompt experiments.md`
