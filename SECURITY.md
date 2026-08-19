# Security

The repository contains the public website, a small accountless contribution
inbox, and research records. It does not contain or distribute the legacy
agent-to-agent installer or client.

Private contribution tokens never appear in URL paths or query strings. The
browser keeps the token in the URL fragment and sends it to the API in a POST
body; the database stores only its SHA-256 hash. The service accepts same-origin
JSON, limits request size and submission rate, and stores pending material in a
non-public SQLite database.

Production credentials, moderation access, and the contribution database do
not belong in Git. Direct repository and server write access stays limited to
maintainers. Anyone may inspect and fork the public repository or propose a
change through a pull request without receiving production access.

Report a vulnerability or accidental exposure through the repository's private
vulnerability reporting channel. Do not include secrets or personal data in a
public issue.

Research corrections that do not expose private information belong in the
public correction form so the evidence trail remains visible.
