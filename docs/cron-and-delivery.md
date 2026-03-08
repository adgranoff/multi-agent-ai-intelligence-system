# Cron And Delivery

## Delivery Rule

For scheduled announce jobs, a run is not successful unless the final payload is actually deliverable.

Do not treat `status=ok` as success when:

- `deliveryStatus != delivered`
- the output artifact is missing
- the final stdout is blank
- the job prints commentary instead of the summary

## Wrapper Pattern

Every delivery-facing deterministic job should follow this sequence:

1. run the real script
2. validate the expected artifact
3. render a short plain-text summary
4. print exactly that summary

## Why This Matters

Many cron failures are not scheduler failures. They are end-of-pipeline failures:

- blank payloads
- stale or empty artifacts
- meta commentary leaking into stdout
- partially successful runs with failed delivery

## Recommended Files

- shell wrapper: `run-...-for-cron.sh`
- renderer: `render_....py`
- artifact file written before delivery

## Debugging Order

1. inspect cron run record
2. inspect delivery status
3. inspect expected artifact
4. inspect wrapper stdout path
5. inspect renderer output

## Cost Rule

Do not spend strong-model tokens on jobs that only need to run a script and print a summary.
