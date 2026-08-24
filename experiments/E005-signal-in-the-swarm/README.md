# E005 — Signal in the Swarm

E005 follows E004 without replacing or deleting it. E004 tested four transport
and composition interfaces on public synthetic records. E005 tests the missing
selection problem: whether a growing swarm can find a complementary combination
of understanding and evidence while preserving a credible minority and
discounting dependent copies.

The experiment begins with a public natural-language development world. No
weight training may begin until the owner has inspected that world on
joinmultiplayer.ai.

Current status: **Gate 3 is frozen. Gate 4A exposed template learning. Gate 4B
tested the same adapters on differently written questions and failed its
predeclared transfer gates. All raw answers are public and await the owner's
question-by-question review. Routing and swarm composition have not started**.

Gate 3 compared exact-word retrieval, frozen-Qwen semantic retrieval, raw
majority, the deterministic evidence graph, and an oracle source set across six
questions in English and Russian. The evidence graph and oracle recovered the
ideal records in 12/12 generations, but the frozen Qwen generator produced only
6/12 correct generations. In the two clearest failures it reversed an explicit
"keep closed" instruction and recommended an intervention despite an explicit
requirement to wait for more evidence. This is a public synthetic development
result, not evidence of learned routing or generalization. The complete artifact
is `site/experiments/E005/gate-3-public-v0.1.json`.

The primary browser review at `/experiment/e005/gate-3/` groups results by
question in a 6×5 matrix and keeps source selection separate from answer
correctness. Owner confirmations and corrections are browser-local until the
owner explicitly asks Morrow to publish the checkpoint. The previous exhaustive
method-first rendering remains available at `/experiment/e005/gate-3/raw/`.
The matrix uses one conservative bilingual rating per task and method: green
requires both RU and EN generations to be correct, red means at least one is
wrong or contradictory, and yellow covers the remaining incomplete cases. The
site-wide EN/RU control changes the complete interface and the visible raw
generation; it never changes that paired rating. All five Gate 3 columns use the
same frozen Qwen3-0.6B Base with no DoRA and no fine-tuning; only evidence
selection differs.

Owner decision on 2026-08-24: preserve Gate 3 v0.1 exactly as run and stop
iterating on retrieval stores in this branch of the experiment. In this
synthetic fixture the deterministic evidence graph matched the predeclared
oracle source set on all 12 language generations. This validates the accounting
harness only when source lineage, freshness, and claim metadata are already
correctly supplied; it does not show that a real swarm can construct those
metadata or discover the right evidence. Because identical ideal evidence still
produced only 6/12 correct generations, the next experiment isolates procedure
learning and generation rather than improving retrieval on these records.

See [PROTOCOL.md](PROTOCOL.md).

The owner authorized Gate 4 development training on 2026-08-24. The synthetic
dataset is now frozen before training: 336 bilingual examples, with disjoint
training and held-out entities and no exact prompt or answer shared between
those splits. Its public artifact is
`site/experiments/E005/gate-4-data-v0.1.json` with SHA-256
`76cbe15ec0eb7c305b1ec0dd14518ced76504ffc375466cbbacd88b1abfd909d`.
No weights had changed at this data checkpoint.

A two-step DoRA plumbing smoke then trained 1,232,896 personal parameters for
the Archivist. Loss stayed finite and moved from 1.943 to 1.410 in 7.839 seconds;
the shared model file hash was unchanged. This only shows that local DoRA
training works on yukabox. It is not evidence that the skill was learned. The
public artifact is `site/experiments/E005/gate-4-smoke-v0.1.json`.

The first real Archivist adapter then trained for one 96-example pass. A
four-question held-out microscope used only unseen entities. Human review scored
the frozen base 0/4 and the personal DoRA adapter 4/4. The first automatic
marker incorrectly scored two Russian base outputs as correct because Qwen had
repeated the question; that checker failure is preserved in the artifact. This
is a small development microscope, not the final Gate 4 result. Raw questions,
answers, preliminary labels, and manual review are public in
`site/experiments/E005/gate-4-archivist-microscope-v0.1.json`.

The Safety Keeper then trained on its separate 96-example skill. Its first four
held-out questions also scored frozen base 0/4 and personal DoRA 4/4 under human
review. In one English and one Russian base answer, Qwen proposed acting despite
the explicitly missing measurement. The raw public artifact is
`site/experiments/E005/gate-4-safety-microscope-v0.1.json`. Both microscopes are
small development checks; wrong-specialist and shuffled-label controls are
still required.

The pre-training Gate 4 checkpoint is
`site/experiments/E005/gate-4-design-v0.1.json` and is rendered at
`/experiment/e005/gate-4/`. It proposes two separate DoRA adapters: one learns
source precedence and lineage accounting; the other learns evidence-to-action
translation and safe abstention. Their held-out entities and answers do not
occur in training. This artifact is a design, not a result or permission to
train.

After owner authorization, both matching adapters and both shuffled-lesson
controls trained for one 96-example pass. The frozen base, matching adapter,
wrong specialist, and shuffled-lesson adapter then answered the held-out set
without RAG. A data audit found that the 48 held-out rows per skill were not 48
independent questions: the Archivist had 8 unique questions and the Safety
Keeper had 16. The repeated rows remain in the source dataset, but they are not
counted as new evidence.

Across the 24 unique questions, the matching personal DoRA produced the exact
predeclared answer 24/24 times. The frozen base, wrong specialist, and shuffled
control produced 0 exact answers. This is a small templated synthetic
development result. It shows that these adapters stored and reused the two
tested procedures on unseen entity names; it does not yet show broad transfer,
real-world safety, routing, or swarm composition. The automatic exact-match
result and every raw answer are public at
`site/experiments/E005/gate-4-results-v0.1.json` and rendered at
`/experiment/e005/gate-4/results/`. Owner review is still pending.

That `24/24` result was then audited for structural leakage. Although no exact
training answer crossed into the held-out split, held-out reference answers
were 94–98% similar to training targets because one generator wrote both from
the same templates. Gate 4A therefore demonstrates narrow template completion,
not reliable procedure transfer.

Gate 4B froze 16 new natural-language questions before inference. Their
reference answers were only 30–78% similar to the nearest training target. The
same existing adapters answered without new training or RAG, and exact-string
scoring was forbidden. Under Morrow's semantic review, the matching Archivist
scored 4/8 correct and the matching Safety Keeper 5/8. The frozen base scored
1/8 and 4/8 respectively. Both skills missed the predeclared 6/8 minimum, and
the Safety Keeper led its base by only 12.5 percentage points instead of the
required 25. Gate 4B therefore failed: the adapters retained parts of the
procedures but did not transfer them reliably to new wording. Every raw answer,
including the earlier template answers, remains available in
`site/experiments/E005/gate-4-transfer-results-v0.1.json` and on
`/experiment/e005/gate-4/results/`. The semantic labels still require owner
review.

Gate 4B is frozen by hashes in
`site/experiments/E005/gate-4b-checkpoint-v0.1.json`. Later training and
evaluation must create new versioned artifacts; they must not overwrite the
questions, answers, labels, or adapter identities recorded by this checkpoint.
