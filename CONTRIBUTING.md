# Contributing

You do not need to build an entire experiment to move the main question
forward.

Read [`GAME.md`](GAME.md) to see how one contribution becomes a trace, how a
different person places the dot, and what the result unlocks.
Structured questions, traces, verifications, exports, and private notification
data follow [`DATA.md`](DATA.md).

## Bring one observation

Choose a [door](doors/). D04 and D06 accept an accountless contribution directly
on [joinmultiplayer.ai](https://joinmultiplayer.ai/); one complete AI answer is
enough to start a trace. GitHub's
[door observation](https://github.com/yukakust/joinmultiplayer.ai/issues/new?template=observation.yml)
remains available for advanced and technical contributors.

Bring:

- the door ID;
- the exact question or prompt;
- the complete, unedited answer or observation;
- model name and date when an AI was involved;
- a direct source or reproducible check when one exists;
- the context another person needs to understand the case.

An observation is not a verdict. It enters the journal only after the record is
complete enough for another person to inspect.

Website submissions are anonymous by default. A private return link lets the
contributor revisit a pending trace and add more D04 answers without creating
an account. Maintainers review the material before it becomes public.

## Change the code

The repository is public. Anyone may inspect it, fork it, run a local copy, and
open a pull request. Direct write access to the main repository and production
server is reserved for maintainers; it is not needed to experiment with the
project or propose a change.

## Propose a test

Open an
[experiment proposal](https://github.com/yukakust/joinmultiplayer.ai/issues/new?template=experiment.yml)
with the hypothesis, baseline, budget, metric, and smallest honest test.

Read [`METHOD.md`](METHOD.md) before collecting results. A pilot is welcome as
long as it is called a pilot.

## Correct the laboratory

If a source, ground truth, result, or claim is wrong, open a
[correction](https://github.com/yukakust/joinmultiplayer.ai/issues/new?template=correction.yml).
Preserve the original record and add the correction with its evidence. The
history of being wrong is part of the result.

## What happens next

1. A maintainer checks the contribution for completeness, safety, and scope.
2. The original material is preserved; interpretation is recorded separately.
3. Accepted observations enter `journal/` with a stable ID.
4. A different person may independently check the trace; no contributor places
   the dot on their own work.
5. Repeated or decisive observations may create or challenge a hypothesis.
6. Experiments publish complete records under the public result contract.
7. The contributor receives a link to the record and may use a name, handle, or
   no public credit.

## Before submitting

- Read [`ETHICS.md`](ETHICS.md) and [`PRIVACY.md`](PRIVACY.md).
- Remove secrets, personal data, client records, and restricted material.
- Confirm that your submission may be published in a public repository.
- Mark AI-generated material and identify the model when known.
- Keep quotations from third-party sources no longer than needed to verify the
  claim; link to the source instead.

By submitting, you confirm that you have the right to share the contribution
and license your original contribution under [`DATA_LICENSE.md`](DATA_LICENSE.md).
