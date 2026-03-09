# Sanitization Notes

This public subset is intended to be safe to study, copy, and adapt.

## Explicitly Excluded

- real secrets or credentials
- real delivery endpoints or recipient identifiers
- machine-specific paths
- private digests, memos, and KB content
- session transcripts, run history, and personal memory
- generated indexes, caches, logs, reports, and backups
- operator identity details

## Included On Purpose

- sanitized templates
- workflow code
- example layouts
- synthetic examples
- architecture and runbook documentation

## Publishing Checklist

Before publishing your own version:

1. remove every generated artifact
2. remove every local path
3. remove every real transport target
4. replace private examples with synthetic ones
5. search the repo for operator names, hostnames, usernames, recipient IDs, provider secrets, and local directories
6. re-read the docs after the search, not before

## Safe Example Standard

Examples in this repo should be:

- synthetic
- non-personal
- non-client-specific
- free of live operational identifiers
- illustrative rather than historical
