# Runbook: errors right after a deploy

## Symptoms
- A new exception type (for example NullPointerException) starts within minutes of a deploy in deploys.log.
- 500s on the endpoints touched by the change.

## Fix
1. Roll back to the previous version (`deploy rollback shop-app`).
2. Reproduce with the failing input, add a test, then redeploy.
