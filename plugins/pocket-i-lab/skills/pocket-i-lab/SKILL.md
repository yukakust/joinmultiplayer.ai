---
name: pocket-i-lab
description: Connect the current Codex task to a consented, redacted public experiment journal on joinmultiplayer.ai. Use when the user asks to start, continue, inspect, finish, or publicly document a Pocket i / joinmultiplayer experiment without leaving Codex. Do not use for ordinary private coding tasks or publish anything unless the user explicitly starts the journal.
---

# Pocket i Lab

This skill keeps the user inside their normal Codex task. Plugin hooks write the journal; never launch another `codex exec` process.

## Start

Tell the user that the journal is public and filtered, then ask them to send this exact opt-in prompt if they have not already done so:

`$pocket-i-lab start E002 as <pseudonym>`

Use `E003` instead when the user is working on the first three-device physical
swarm. Only experiments currently accepted by the laboratory API can start.

Use `anonymous` when they do not want a pseudonym. Starting means explicit consent to publish the filtered journal. The hook returns the public run URL as additional context. Repeat that URL to the user.

## While active

Continue the requested experiment normally in this same task. The hooks publish:

- the user's submitted prompt after local secret and path redaction;
- the final visible assistant message for each turn after the same redaction;
- tool name and completion status only;
- changed relative file names for `apply_patch`, never patch contents;
- session completion state.

The hooks never read the transcript file and never publish hidden reasoning, tool arguments, shell commands, command output, tool output, file contents, environment variables, absolute paths, credentials, session identifiers, or the private run key.

At meaningful scientific checkpoints, write the result clearly in the visible assistant message: hypothesis, change, test, metric, failure, or decision. The public journal should be understandable without exposing private execution details.

Do not describe an unverified result as proof. Preserve failed experiments and distinguish synthetic, development, locked, and replicated results.

## Finish

When the user wants to close the run, ask them to send:

`$pocket-i-lab finish`

The hook marks the run completed before the turn starts. Give a concise final summary and the public journal URL. Starting a later experiment creates a new run.

## Privacy boundary

Read [privacy.md](references/privacy.md) if the user asks what becomes public or requests a less restrictive journal. Never weaken the allowlist merely because the user says “everything”; exact transcripts can contain credentials, private paths, copyrighted material, or unrelated personal context.
