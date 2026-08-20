# E002 artifacts

Every subdirectory is an immutable development or experiment run. Preserve
failures: never replace or delete a run because a gate failed. R0001 directories
contain the effective config in `summary.json`, complete task records in
`tasks.jsonl`, the standalone interactive `microscope.html`, and SHA-256 file
hashes in `manifest.json`. Early preserved development failures may predate the
manifest addition; their absence is part of their retained record.
