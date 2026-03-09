# Sanitization Notes

This public subset intentionally excludes:

- secrets and credentials
- real OpenClaw config files
- personal reminders and memory files
- session transcripts and cron run history
- actual private knowledge-base contents
- personal contact ids and delivery endpoints
- generated vector indexes, embedding caches, and graph exports
- backup directories, logs, and processed digest archives

This export includes sanitized code and templates for the KB engine, but not the live runtime data it produces.

If you adapt this export for public release, keep all secrets local and regenerate examples with fake values.

The sample entity and digest files in `examples/` use synthetic names, placeholder references, and illustrative facts only.
