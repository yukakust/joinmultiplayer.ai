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

Gate 4C Step 2 freezes a new curriculum before changing any weights. Each of
the two skills has 192 synthetic lessons: 96 English and 96 Russian. Each skill
now covers four policy cases, six visibly different question formats, and six
answer styles. The 384 inputs are unique, and none of the Gate 4B locked entity
names occur in these lessons. This is training material, not a result. Training
status remains `not_started`. The public artifact is
`site/experiments/E005/gate-4c-lessons-v0.1.json`, with canonical content hash
`08e12b86987bb6d49103f18fe9e1e3cad305abefd3af85d2cbcb2d2bb55badf1`, and a
human-readable lesson viewer is rendered at
`/experiment/e005/gate-4/lessons/`.

Gate 4C Step 3 locks the next transfer exam before any new training. It contains
48 questions: 24 per skill and 12 per language per skill. The matching DoRA
must score at least 20/24 for each skill, at least 9/12 in each language, and
beat every control by at least 6 answers. Exact-string scoring, RAG, internet,
and changing questions after training are forbidden; final labels require owner
review. The artifact is
`site/experiments/E005/gate-4c-locked-test-v0.1.json`, with canonical content
hash `e2066400520551eba4e033b24debca1c8313994dd8ea4bde76beb3de0455a7da`, and
the human-readable exam is rendered at `/experiment/e005/gate-4/exam/`.

Gate 4C Step 4 trained two fresh correct DoRA adapters for one 192-example pass
each, using the frozen runner at commit `8798ebf`. The source-work adapter's
mean loss moved from 1.956 over the first 24 lessons to 0.204 over the last 24;
the safe-action adapter moved from 2.410 to 0.415. Each changed 1,232,896
personal parameters, while the shared base hash stayed
`cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba`.
The locked exam was not read or run, and no RAG was used. This proves only that
the training pipe changed personal weights and reduced lesson loss. The public
checkpoint is `site/experiments/E005/gate-4c-training-v0.1.json`; the readable
view is `/experiment/e005/gate-4/training/`.

Gate 4C Step 5 generated 192 raw answers from four conditions on the locked
exam. A strict preliminary structured review scored the matching source-work
DoRA 6/24 and the matching safe-action DoRA 23/24. Source work therefore failed
its 20/24 threshold and language thresholds; safe action passed its score and
control-lead thresholds. Gate 4C fails overall because both skills had to pass.
The scientific conclusion is therefore **partial**: this run gives one concrete
example in which a small personal adapter learned a skill that transferred to
new wording, but it does not establish that arbitrary skills transfer. It also
does not test routing, cooperation, or swarm composition.
All labels remain owner-reviewable. The complete raw outputs, reasons, summary,
and failed gates are preserved in
`site/experiments/E005/gate-4c-results-v0.1.json` and rendered at
`/experiment/e005/gate-4/gate-4c-results/`.

Gate 5A begins with a frozen, owner-readable composition design. One pocket i
must identify a cause but cannot know the safety restriction; the other must
identify the restriction but cannot know the cause. They answer once in
parallel, and a source i combines the two bounded capsules. The correct pair
must score at least 20/24 while either pocket alone and a wrong pair stay at or
below 8/24. Removing either capsule must destroy at least ten correct answers.
This checkpoint changes no weights and creates no training or locked exam data.
It is visible at `/experiment/e005/gate-5a/`; the exact design is
`site/experiments/E005/gate-5a-design-v0.1.json`.

Gate 5A data checkpoint freezes 384 unique training inputs, split evenly across
the two pocket roles and English/Russian, plus 24 locked questions with new
device names and wording. Every exam item declares the cause capsule, safety
capsule, and complete answer before training. The curriculum content hash is
`68ee208d666aa7a48f4627b449a012e34929d3db8afe920deac3cbb8fb90da0c`; the
exam content hash is
`20d2468ae3cb65f4c84f71c7cc3e5d133dcef1249b562d8e5df730a8b1e00cde`.
No weights changed and the exam has not run at this checkpoint.

Pre-training review rejected that v0.1 exam because its strings were new but
its six sentence frames were reused from training. The files remain public and
no model trained on them. Gate 5A data v0.2 uses a disjoint set of exam sentence
frames. Its curriculum content hash is
`9f23a13a079b2fe05863ef99040adaedc0fca8a4cc0504f81a7cd7f86dc3f4ce`; its
exam content hash is
`1bb8ac4664612ceaee7b438a3d4ca57e076a43230dc943db8ca484d70314127e`.
This v0.2 checkpoint is the only Gate 5A data authorized for training.

Gate 5A then trained two fresh rank-8 DoRA adapters for one pass over 192
lessons each. CAUSE-I's mean loss moved from 2.432 on the first 24 lessons to
0.000086 on the last 24; SAFETY-I moved from 2.806 to 0.000564. Each adapter
changed 1,232,896 personal parameters. The shared Qwen file hash remained
`cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba`.
The locked exam had not run at this checkpoint. These numbers show lesson fit,
not transfer or composition. The public training record is
`site/experiments/E005/gate-5a-training-v0.1.json`.

The locked Gate 5A run then preserved 216 raw generations across eight
conditions. Frozen Qwen alone, either pocket alone, frozen Qwen acting in both
roles, and both wrong same-skill pairs each produced 0/24 complete answers. The
correct CAUSE-I + SAFETY-I pair produced 22/24; oracle capsules produced 24/24.
CAUSE-I made both errors, while SAFETY-I supplied 24/24 correct capsules. All
preregistered gates passed. This supports explicit one-round text-capsule
composition with a deterministic renderer. It does not establish learned
routing, latent neural merging, multiple-device execution, or swarm scaling.
Every question and raw answer is published at
`/experiment/e005/gate-5a/results/` and in
`site/experiments/E005/gate-5a-results-v0.1.json`.

Gate 5A.2 is frozen before any synthesis run because Gate 5A's deterministic
renderer did not test a human-facing answer. It adds 24 new questions and a
frozen source-Qwen prompt. The source must preserve both real pocket capsules,
avoid JSON in at least 20/24 answers, and remain incomplete when either capsule
is missing. No source-model weights change. The visible checkpoint is
`/experiment/e005/gate-5a/human/`; its locked exam content hash is
`021cc8aa7421b28a8d13a64dc694341f408ff318fa501953c8e86ead419a66a7`.

Gate 5A.2 was then run without training, RAG, internet, or sampling. It failed:
human review found 4/24 complete natural answers against a 20/24 pass rule
(English 4/12, Russian 0/12). The strict phrase checker counted 1/24. Perfect
oracle capsules also reached only 4/24, so the frozen 0.6B source model—not just
the learned pockets—was unable to preserve both facts reliably. See every raw
answer at `/experiment/e005/gate-5a/human/results/` and the public artifact at
`site/experiments/E005/gate-5a2-results-v0.1.json`.

Gate 5A.3 is frozen before execution at `/experiment/e005/gate-5a/semantic/`.
It keeps the same 24 questions and trained pocket adapters, expands their actual
labels through one public semantic codebook, raises the answer budget to 192
tokens, and compares frozen Base Qwen with frozen instruction-trained Qwen.
This is a text-interface experiment, not latent or distributed-track merging.

Gate 5A.3 then ran and failed its 20/24 rule. Human review scored Base with
semantic capsules at 11/24 and instruction-Qwen at 17/24; the prior coded Base
interface scored 4/24. Instruction-Qwen reached 11/12 English and 6/12 Russian,
with zero cut-off main answers. All missing-pocket controls remained 0/24. The
complete 168 raw outputs are published at
`/experiment/e005/gate-5a/semantic/results/`.
