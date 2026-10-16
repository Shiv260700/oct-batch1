# Runbook: Java heap OutOfMemoryError

## Symptoms
- `java.lang.OutOfMemoryError: Java heap space` in catalina.out; Tomcat restarts.
- Heap usage after GC climbing over hours (warnings in application.log).
- Apache returns 502/503 and logs AH01102 / AH00957 while Tomcat is down.

## Likely causes
- A cache or collection without a size limit (memory leak).

## Fix
1. Restart Tomcat to recover service.
2. Take a heap dump next time (`-XX:+HeapDumpOnOutOfMemoryError`) and find the largest objects.
3. Put a maximum size and expiry on caches (for example Caffeine `maximumSize`).
