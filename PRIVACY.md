# Privacy

_Last updated: 2026-08-20._

The website has no account system, advertising, or project analytics. D04 and
D06 accept contributions through the project server without requiring GitHub
or an email address.

## Website visits

The hosting and network providers may process ordinary request metadata such as
IP address, timestamp, requested path, and user agent for delivery, security,
and operational logs. The contribution service uses an IP address briefly in
memory to limit automated abuse, but does not store it in the contribution
database or use it to build participant profiles.

## Contributions

New submissions enter a private moderation queue. The database stores the door,
question, complete AI answers, door-specific observation, optional pseudonym,
publication consent, timestamps, moderation state, and a hash of the private
return token. It does not ask for an email address or exact location.

The private return link contains the only copy of its token. Treat that link as
a password: anyone who receives it can see the pending contribution and may be
able to add another D04 answer. The server stores only a one-way hash of the
token.

Nothing enters the public research record until a maintainer reviews it. An
accepted record may expose everything shown on the final preview screen,
including a supplied pseudonym. Anonymous publication hides public credit but
does not make submitted text anonymous if the text itself contains identifying
details.

GitHub remains available for source-code contributions and advanced research
work. A GitHub issue or pull request exposes the account identity and content
under GitHub's own terms and privacy policy.

## Public experiment runs

Starting an experiment run requires explicit consent to live publication and
creates a private run key. The key is shown once, kept in the browser URL
fragment, sent only in POST bodies, and stored by the server only as a one-way
hash.

The Codex Lab Connector uses an existing Codex login and does not ask for an
OpenAI API key. It publishes an allowlisted run journal: filtered agent
messages, plan text, action status, relative changed filenames, and explicit
metrics. It does not publish raw reasoning, command output, file contents, tool
arguments or results, environment variables, thread identifiers, local
absolute paths, or the private run key. Obvious credential patterns are blocked
again by the server. Automated redaction is not a guarantee, so the connector
is restricted to a public checkout of this repository and must not be used for
private work.

Do not submit:

- personal or identifying data that the experiment does not require;
- private AI conversations;
- client, patient, employee, or account records;
- credentials, API keys, private links, or unpublished source material;
- content you do not have permission to publish.

Use a redacted transcript when the removed information is not part of the
claim. Say what category was removed so the record remains interpretable.

## Removal and corrections

For a pending website submission, keep the private link and request a change or
withdrawal through the maintainers. For published material, open a correction
or contact the maintainers through the repository. We can remove it from the
current project view, but cannot guarantee removal from Git history, forks,
caches, or third-party archives.

If private data was exposed, do not repeat it in a public issue. Use GitHub's
private vulnerability reporting channel for this repository.
