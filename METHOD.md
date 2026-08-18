# Method v0.1

The public question is deliberately simple:

> Can many small intelligences become smarter than one big AI?

An experiment must make every word measurable before it begins.

## Define the comparison

Every experiment records:

- what counts as one `i`: a model, an agent, a person, or a person-and-AI pair;
- how many `i` participate;
- what makes them meaningfully different;
- the task and why it can or cannot be decomposed;
- the frontier or single-system baseline;
- the shared resource budget: cost, tokens, time, tools, and latency;
- the primary metric and pass/fail condition chosen before the run.

Do not call several prompts to the same base model independent without testing
that assumption. Record model family, language, tools, context, and information
sources as possible sources of diversity.

## Name the stage honestly

- **Observation:** something happened once.
- **Pilot:** the procedure was tested; the hypothesis was not.
- **Case:** one bounded example worth investigating.
- **Experiment:** a pre-specified comparison with a baseline and enough trials
  to support its stated conclusion.
- **Replication:** an independent repeat of an existing experiment.

A striking case may open a door. It does not prove a general claim.

## Public result contract

A result is publishable only when its record contains:

```text
experiment ID:
source doors:
source hypotheses:
question and complete prompt:
complete, unedited outputs:
exact model names and versions:
date and environment:
settings, tools, and available context:
baseline:
resource budget:
ground truth and direct sources:
evaluation method:
analysis code or reproducible calculation:
result:
limitations:
reproduction instructions:
```

If a field does not apply, say why. Do not silently omit it.

## Ground truth

- Prefer primary sources.
- Preserve direct URLs, document versions, access dates, and relevant excerpts.
- Separate who first made a claim from whether evidence supports it.
- Record disagreement between sources.
- For expert judgment, state who can verify it and how disagreements are
  resolved.
- For time-sensitive facts, attach the date on which the answer was judged.

The laboratory's own reference answer may be wrong. Corrections remain part of
the record.

## Model runs

Preserve the entire interaction needed to reproduce the result, including the
system instructions when they are known. Record whether browsing, retrieval,
code execution, memory, or other tools were available. Repeat stochastic runs
when a conclusion depends on one sampled answer.

Model names are not enough: hosted models change. Record the provider's exact
version or dated identifier when available and the run date in every case.

## Conclusions

Use the narrowest conclusion the evidence supports:

```text
supports | challenges | inconclusive
```

Report effect size and uncertainty when possible. A result must state how it
changes—or fails to change—the main question.

## Human participation

Public participation is not automatically formal human-subject research. Do
not claim scientific generality from a self-selected online sample. Collect
only what the question needs, obtain explicit publication permission, and do
not solicit secrets, private records, or identifying data.
