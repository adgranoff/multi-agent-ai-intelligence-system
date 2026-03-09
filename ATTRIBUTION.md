# Attribution

This repository is an overlay for a specific OpenClaw workflow, not a repackaging of the full upstream project.

## Upstream Dependency

This system is designed to run on top of upstream OpenClaw:

- GitHub: `https://github.com/openclaw/openclaw`

The upstream OpenClaw repository declares the `MIT` license in:

- `package.json`
- `LICENSE`

## What This Repo Contains

This public repository contains only the workflow overlay:

- Collector, Sentinel, and Librarian workspace templates
- custom skills for this workflow
- sanitized advanced knowledge-base code and config templates
- documentation for the AI intelligence pipeline

## What This Repo Does Not Contain

This public repository does not include:

- the bundled OpenClaw package code
- OpenClaw's full default feature set
- private runtime data, secrets, or session history
- generated indexes, logs, or delivery endpoints

## Recommended Usage

Users should:

1. install upstream OpenClaw separately
2. use this repository as a workflow overlay and template pack
3. keep their own secrets and runtime data outside version control

## Licensing Note

The files in this overlay repository are released under the repository `LICENSE`.

Upstream OpenClaw remains separately licensed by its maintainers. If you redistribute upstream code, keep upstream notices and license terms intact.
