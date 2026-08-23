# Checkpoint 1 draft — approve Architecture Arena before training

Status: `NEEDS OWNER REVIEW · NO MODEL DOWNLOADED · NO TRAINING`

## What changed

E004 no longer assumes DoRA is the solution. It is now a tournament asking
which personal storage method and which one-pass composition interface, if any,
make useful knowledge grow with the number of independent pocket i.

Repeated multi-round model conversation is excluded.

## What the owner will inspect

The public Checkpoint 1 page will show:

- five architecture cards: RAG, neural memory, latent delta, token-MoE, and
  DoRA assembly;
- eight final pocket slots and one post-freeze plug-in slot;
- readable examples from a separate public fictional world;
- controls and pre-registered success thresholds;
- yukabox's allowed execution window and resource ceiling;
- the exact boundary: this is still only a design, not a result.

## Data plan

A deterministic generator creates 16 surrogate books for router/merger
training, 8 disjoint final books for locked evaluation, and `I09` only after the
central system is frozen. Each private book contains 256 exact facts, 256
procedure examples, and 64 update/deletion records. Final books and labels never
enter central training.

## Training plan after approval

The shared Qwen 0.6B lineage is reused, but its base remains an audited frozen
reference. Actual gradient training compares DoRA, a partial/full fine-tuning
capacity control, trainable neural memory, personal MoE experts, routers, and
mergers. RAG is the non-weight control.

The first optimizer work is only a two-surrogate smoke. It must publish visible
before/after evidence and stop at Checkpoint 2 before full arena training.

## Decision conditions

At least one architecture must show near-linear growth of accessible unique
items, a clear multi-pocket advantage over singles and pairs, correct behavior
when a required pocket is absent, and post-freeze attachment of unseen `I09`
without central retraining. Exact RAG wins and failed neural variants remain
visible.

## Hardware boundary

Heavy jobs may run only `08:00–23:45` Central European local time, checkpoint
at `23:45`, and stop by `23:55`. The initial ceiling is 22 CPU threads and 52
GiB RAM. Accelerator use requires a measured compatibility smoke.

## Owner-visible evidence rule

Every meaningful stage must show what changed, something inspectable, the
metric or failure, and the proposed next step—preferably on the E004 page. No
checkpoint silently advances.

## Decision requested

Review the public data-world examples, architectures, controls, thresholds, and
schedule. Approval authorizes only environment preparation, pinned model
download, and short development smokes. It does not authorize full arena
training or a locked evaluation.
