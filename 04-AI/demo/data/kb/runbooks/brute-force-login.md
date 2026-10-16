# Runbook: login brute force

## Symptoms
- Hundreds of 401 responses on POST /api/login from one IP in the Apache access log.
- `Failed login ... N failures in a row` warnings in application.log.

## Fix
1. Block the IP in Apache (`Require not ip 203.0.113.77`) or at the firewall.
2. Enable rate limiting on /api/login and lock accounts after repeated failures.
