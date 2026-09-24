# Next action after approval

This section replaces any earlier instruction about what happens after the user approves a complete action summary.

- If the approved details and conditions are unchanged, execute the next permitted action. Do not request the same confirmation again.
- Execute exactly one tool call, then inspect its result.
- For one order, execute approved address and payment changes before item modification.
- After item modification, remove all further modifications and cancellation for that order from the pending plan.
- If the user changes a material detail, obtain approval only for the affected action.
