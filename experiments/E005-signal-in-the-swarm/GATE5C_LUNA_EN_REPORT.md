# Gate 5C English semantic check

I checked 128 English answers: 16 questions asked under 8 different setups. For each answer, I checked two things:

1. Did it name the right reason (the cause)?
2. Did it say the safe thing to do?

This was a meaning check, so different words were allowed. I kept the setups hidden while judging, then matched them afterward.

## Results

| Setup | Answers | Right cause | Right safety | Complete | Contradictions | Low confidence |
|---|---:|---:|---:|---:|---:|---:|
| old_additive_merger | 16 | 16 | 1 | 1 | 0 | 0 |
| separate_shelves_correct_pair | 16 | 0 | 2 | 0 | 16 | 0 |
| cause_shelf_only | 16 | 1 | 0 | 0 | 8 | 6 |
| safety_shelf_only | 16 | 0 | 2 | 0 | 15 | 0 |
| two_cause_shelves | 16 | 4 | 0 | 0 | 6 | 6 |
| two_safety_shelves | 16 | 0 | 0 | 0 | 15 | 1 |
| swapped_shelves | 16 | 0 | 0 | 0 | 7 | 9 |
| empty_shelves | 16 | 0 | 0 | 0 | 7 | 6 |
| **All answers** | **128** | **21** | **5** | **1** | **74** | **28** |

## Biggest finding

The old additive merger named the right cause every time (16 out of 16). The separate-shelves setup named the right cause zero times (0 out of 16), and every one of its answers had an incompatible claim. So, in this test, the two setups behaved very differently.

Only one answer was fully correct. A full answer needed both the right cause and the right safe action, with no contradiction.

Among the control setups, `two_cause_shelves` was best by cause score (4 out of 16), but it still had 0 complete answers. `safety_shelf_only` had the best safety score among controls (2 out of 16). Since all controls scored 0 complete answers, “best” here only means the most right pieces, not a passing result.

## What went wrong most often

Many answers repeated the colored lights and room signs, but did not say what they meant. Others guessed a different cause, said everything was normal, or gave a different action. The safe action was especially often missing.

## What we cannot claim yet

One LLM judge is not ground truth. These numbers are an audit signal, not a final proof that one setup is better. The 28 low-confidence cases, and any decision that changes an architecture conclusion, need the experiment owner or a second independent judge. Also, the raw source had no `audit_id`; the result therefore uses stable IDs made from English source order (`E005-5C-EN-001` through `128`).
