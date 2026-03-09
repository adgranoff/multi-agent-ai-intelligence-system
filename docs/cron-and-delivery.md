# Cron And Delivery

## Delivery Rule

For delivery-facing jobs, a run is not successful unless the final payload is actually usable.

Do not treat a run as successful when:

- the output artifact is missing
- the latest pointer is stale
- the final payload is blank
- the job prints commentary instead of the summary
- the delivery adapter rejects the payload

## Wrapper Pattern

Every delivery-facing deterministic job should follow this order:

1. run the real script
2. validate the expected artifact
3. render a short plain-text summary
4. print exactly that summary

## Buffering Rule

Do not schedule the pipeline as tightly as possible.

Use explicit buffers between:

- Collector and Sentinel
- Sentinel and Librarian
- Librarian and KB runtime

Median runtime is not enough. Schedule for tail latency and occasional retries.

## Maintenance Rule

Push jobs and maintenance jobs should be separated.

Good pattern:

```text
delivery-facing intelligence first
maintenance-only retrieval refresh second
```

That avoids a long-running maintenance task breaking a user-visible delivery step.

## Debugging Order

1. inspect the run record
2. inspect the expected artifact
3. inspect the latest pointer
4. inspect the rendered summary
5. inspect the delivery adapter
6. inspect maintenance-only follow-on jobs

## Cost Rule

Do not spend expensive model tokens on jobs that only need to execute a script and print a deterministic summary.
