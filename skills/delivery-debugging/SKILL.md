---
name: delivery-debugging
description: Debug delivery failures for notification-facing jobs, especially blank final responses, not-delivered payloads, missing artifacts, or meta commentary leaking into payloads. Use when job work partly happened but the final delivery payload was missing, unsafe, or not delivered.
---

# Delivery Debugging

## Workflow

1. Inspect latest run status and delivery status.
2. Inspect the related session log and final stdout path.
3. Verify the expected artifact exists and is non-empty.
4. Verify the wrapper or renderer prints exactly one delivery-safe payload.
