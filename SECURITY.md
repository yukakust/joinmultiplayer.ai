# Security

The repository contains the public website, a small accountless contribution
inbox, research records, and a one-file Codex Lab Connector. It does not contain
or distribute the legacy agent-to-agent installer or client. The lab connector
is not a pocket i: it can run Codex only inside an explicitly selected public
checkout and publish a narrow, filtered progress journal.

Private contribution tokens never appear in URL paths or query strings. The
browser keeps the token in the URL fragment and sends it to the API in a POST
body; the database stores only its SHA-256 hash. The service accepts same-origin
JSON, limits request size and submission rate, and stores pending material in a
non-public SQLite database.

Experiment run keys follow the same fragment/POST/hash pattern. Run publication
is explicitly live rather than moderated. The connector drops common secret
environment variables, omits raw reasoning, command output, file contents, and
tool payloads, and sends only allowlisted event fields. The server rejects
known credential shapes and redacts local absolute paths. These controls reduce
risk but cannot prove that arbitrary prose contains no sensitive information;
run the connector only against public project material and inspect its source
before use.

Production credentials, moderation access, and the contribution database do
not belong in Git. Direct repository and server write access stays limited to
maintainers. Anyone may inspect and fork the public repository or propose a
change through a pull request without receiving production access.

Report a vulnerability or accidental exposure through the repository's private
vulnerability reporting channel. Do not include secrets or personal data in a
public issue.

Research corrections that do not expose private information belong in the
public correction form so the evidence trail remains visible.
