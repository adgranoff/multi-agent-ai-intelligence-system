---
name: digest-pipeline
description: Run and debug the Collector to Sentinel digest pipeline, including collector manifest freshness, dated digest generation, digest-latest publishing, and weekly memo artifacts. Use when daily or weekly digest generation, freshness validation, or latest-pointer publishing needs inspection or repair.
---

# Digest Pipeline

## Workflow

1. Start with the collector manifest.
2. Confirm source status and source date.
3. Verify the expected Sentinel artifact exists.
4. Publish latest pointers.
5. Only then produce the delivery summary.
