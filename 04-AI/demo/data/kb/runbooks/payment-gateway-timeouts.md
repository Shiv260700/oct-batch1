# Runbook: payment gateway timeouts

## Symptoms
- `java.net.SocketTimeoutException: Read timed out` from PaymentClient.
- /api/checkout slow (over 5 s) and 504 Gateway Timeout from Apache.

## Fix
1. Check the payment provider status page.
2. Turn on the circuit breaker so checkout fails fast with a friendly message.
3. Retry with exponential backoff; never retry a payment without an idempotency key.
