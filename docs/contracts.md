# Contract Schemas

This repository includes machine-readable schemas for pipeline handoffs.

## Included Schemas

- `docs/contracts/collector-manifest.schema.json`
- `docs/contracts/sentinel-manifest.schema.json`
- `docs/contracts/librarian-update.schema.json`
- `docs/contracts/editor-actions.schema.json`
- `docs/contracts/editor-verification.schema.json`

## Why They Matter

These schemas make orchestration safer when you build this in another stack:

- every stage can validate upstream artifacts before processing
- retries can distinguish data-contract failures from transient runtime failures
- coding agents can generate validators and tests from explicit shape definitions

## Validation Pattern

Use schema validation at every handoff boundary.

Recommended order:

1. Collector output validates against collector manifest schema
2. Sentinel output validates against sentinel manifest schema
3. Librarian run report validates against librarian update schema
4. Editor action and rerun verification artifacts validate against editor schemas

## Implementation Guidance

- fail fast on schema violations
- include source date and generated timestamp in all handoff artifacts
- treat unknown required fields as failures, not warnings
- keep schema versioning explicit when contracts evolve
