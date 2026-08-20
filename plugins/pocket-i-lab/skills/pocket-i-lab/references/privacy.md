# Public journal boundary

Pocket i Lab is opt-in per Codex session. An inactive hook exits without network access.

Public fields:

- redacted user-visible prompt;
- redacted final assistant message;
- tool name and coarse status;
- relative changed-file names for patch operations;
- run timestamps and status.

Always private:

- chain-of-thought and raw reasoning;
- transcript files and session/turn identifiers;
- tool arguments and results;
- shell commands and output;
- file contents and patch bodies;
- environment variables;
- home-directory and other absolute paths;
- credentials and the private publication token.

The redactor recognizes common OpenAI, GitHub, Slack, AWS, bearer-token, password, private-key, and local-path patterns. Detection is defense in depth, not a mathematical guarantee. A participant should still use a clean public workspace and avoid placing secrets in the prompt.
