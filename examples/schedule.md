# Example Schedule

This is an example operating cadence for the AI intelligence workflow.

- `11:30 AM daily` — Collector daily run
- `12:15 PM daily` — Sentinel daily digest
- `1:00 PM daily` — Librarian daily KB curation
- `1:30 PM daily` — KB runtime refresh
- `2:00 PM Sunday` — Sentinel weekly memo

The exact times are less important than the ordering:

1. Collector first
2. Sentinel second
3. Librarian third
4. KB runtime fourth

Never schedule downstream agents before upstream artifacts exist.
