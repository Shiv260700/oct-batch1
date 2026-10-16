"""
Generate 3 days of synthetic server logs for `shop-app`:
Apache httpd (mod_proxy) → Java 17 Spring Boot on Tomcat (HikariCP → PostgreSQL) → external payment gateway.

Five incidents are planted at known times; their details go to data/incidents.json (the answer key).
A small knowledge base (runbooks, architecture, past post-mortems) goes to data/kb/.
Everything is deterministic (seed 7).
"""
import json
import random
from datetime import datetime, timedelta, timezone

from . import DATA, KB, LOGS

UTC = timezone.utc
START = datetime(2026, 10, 13, 0, 0, tzinfo=UTC)
END = datetime(2026, 10, 16, 0, 0, tzinfo=UTC)

ENDPOINTS = [  # (method, path, share, normal latency ms, service class)
    ('GET', '/api/products', 0.30, 40, 'c.shop.catalog.ProductService'),
    ('GET', '/api/orders/{id}', 0.18, 55, 'c.shop.orders.OrderService'),
    ('POST', '/api/orders', 0.07, 120, 'c.shop.orders.OrderService'),
    ('POST', '/api/checkout', 0.06, 300, 'c.shop.payments.PaymentClient'),
    ('GET', '/api/users/{id}', 0.12, 45, 'c.shop.users.UserController'),
    ('POST', '/api/login', 0.10, 80, 'c.shop.auth.LoginController'),
    ('GET', '/health', 0.17, 3, 'c.shop.HealthController'),
]
AGENTS = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5)',
          'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5)', 'okhttp/4.12.0', 'kube-probe/1.30']

T = lambda d, h, m, s=0: datetime(2026, 10, d, h, m, s, tzinfo=UTC)
INCIDENTS = [
    {'id': 'db-pool', 'title': 'Database connection pool exhausted',
     'start': T(13, 10, 20), 'end': T(13, 10, 45), 'endpoint': '/api/orders',
     'root_cause': 'HikariCP connection pool exhausted (all 10 connections busy, a slow report query held them); requests waited 30 s and failed',
     'symptom': 'HTTP 500 on /api/orders with ~30 s latency',
     'evidence': 'SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms',
     'fix': 'kill the long-running report query, raise maximumPoolSize, add a statement timeout (runbook: hikari-pool.md)',
     'keywords': ['hikari', 'pool', 'connection']},
    {'id': 'oom', 'title': 'Memory leak → OutOfMemoryError → Tomcat restart',
     'start': T(14, 8, 0), 'end': T(14, 11, 4), 'endpoint': 'all',
     'root_cause': 'memory leak in the product cache: heap grew from 60% to 98% until java.lang.OutOfMemoryError: Java heap space; Tomcat restarted',
     'symptom': 'Apache 502/503 and AH01102 proxy errors between 11:02 and 11:03:40 while Tomcat restarted',
     'evidence': 'java.lang.OutOfMemoryError: Java heap space',
     'fix': 'restart, take a heap dump, cap the product cache size (runbook: java-heap-oom.md)',
     'keywords': ['outofmemoryerror', 'heap', 'memory']},
    {'id': 'gateway', 'title': 'Slow payment gateway',
     'start': T(14, 16, 10), 'end': T(14, 16, 35), 'endpoint': '/api/checkout',
     'root_cause': 'the external payment gateway responded slowly: java.net.SocketTimeoutException: Read timed out after 5 s',
     'symptom': '/api/checkout slow (5–10 s) and some 504s',
     'evidence': 'java.net.SocketTimeoutException: Read timed out',
     'fix': 'check the gateway status page, enable the circuit breaker, retry with backoff (runbook: payment-gateway-timeouts.md)',
     'keywords': ['sockettimeoutexception', 'payment', 'gateway', 'timed out']},
    {'id': 'bad-deploy', 'title': 'Bad deploy v1.4.2',
     'start': T(15, 14, 0), 'end': T(15, 14, 40), 'endpoint': '/api/users',
     'root_cause': 'deploy v1.4.2 introduced a NullPointerException in UserMapper.toDto (users without an email); rolled back to v1.4.1 at 14:40',
     'symptom': 'HTTP 500 on /api/users/{id} from 14:00 to 14:40',
     'evidence': 'java.lang.NullPointerException',
     'fix': 'roll back to v1.4.1, add a null check and a test (runbook: bad-deploy-rollback.md)',
     'keywords': ['nullpointerexception', 'usermapper', 'v1.4.2', 'deploy']},
    {'id': 'brute-force', 'title': 'Login brute force',
     'start': T(15, 22, 5), 'end': T(15, 22, 20), 'endpoint': '/api/login',
     'root_cause': 'brute-force login attempts from IP 203.0.113.77',
     'symptom': 'about 600 HTTP 401 responses on POST /api/login from one IP',
     'evidence': '203.0.113.77 "POST /api/login HTTP/1.1" 401',
     'fix': 'block the IP at Apache, enable login rate limiting (runbook: brute-force-login.md)',
     'keywords': ['203.0.113.77', 'brute', '401', 'login']},
]


def apache_time(t):
    return t.strftime('%d/%b/%Y:%H:%M:%S +0000')


def apache_err_time(t):
    return t.strftime('%a %b %d %H:%M:%S.') + f'{t.microsecond // 1000:03d}' + t.strftime(' %Y')


def app_time(t):
    return t.strftime('%Y-%m-%d %H:%M:%S.') + f'{t.microsecond // 1000:03d}'


def tomcat_time(t):
    return t.strftime('%d-%b-%Y %H:%M:%S.') + f'{t.microsecond // 1000:03d}'


def in_inc(t, iid, pad=0):
    inc = next(i for i in INCIDENTS if i['id'] == iid)
    return inc['start'] - timedelta(seconds=pad) <= t < inc['end'] + timedelta(seconds=pad)


def generate(seed=7):
    rng = random.Random(seed)
    access, apache_err, app, tomcat, deploys = [], [], [], [], []
    ips = [f'10.0.{rng.randint(1, 9)}.{rng.randint(2, 250)}' for _ in range(120)]
    thread = lambda: f'nio-8080-exec-{rng.randint(1, 40)}'
    pid = 4512

    def app_line(t, level, logger, msg, trace=None):
        app.append((t, f'{app_time(t)} {level:>5} {pid} --- [{thread():>18}] {logger:<40} : {msg}' + ('\n' + trace if trace else '')))

    # ---- normal traffic: busier by day
    t = START
    while t < END:
        hour = t.hour
        rate = 3 + (6 if 8 <= hour < 22 else 0)              # requests per minute
        for _ in range(rng.randint(rate - 2, rate + 2)):
            ts = t + timedelta(seconds=rng.random() * 60, microseconds=rng.randint(0, 999) * 1000)
            method, path, _, lat, _cls = rng.choices(ENDPOINTS, weights=[e[2] for e in ENDPOINTS])[0]
            p = path.replace('{id}', str(rng.randint(1, 5000)))
            status, latency = 200, max(1, int(rng.gauss(lat, lat * 0.3)))
            if path == '/api/orders' and method == 'POST':
                status = 201
            if path == '/api/login' and rng.random() < 0.06:
                status = 401
            noise = rng.random() < 0.004
            if noise:
                p, status, latency = '/favicon.ico', 404, 2
            ip = 'kube-probe' if path == '/health' else rng.choice(ips)
            agent = AGENTS[4] if path == '/health' else rng.choice(AGENTS[:4])
            if ip == 'kube-probe':
                ip = '10.0.0.1'
            # incidents that change normal requests
            if noise:
                pass
            elif in_inc(ts, 'db-pool') and path.startswith('/api/orders') and rng.random() < 0.85:
                status, latency = 500, 30000 + rng.randint(0, 40)
                app_line(ts + timedelta(milliseconds=latency), 'ERROR', 'c.shop.orders.OrderService',
                         'java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms.',
                         '\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:696)\n'
                         '\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:181)\n'
                         '\tat c.shop.orders.OrderRepository.findById(OrderRepository.java:42)\n'
                         '\tat c.shop.orders.OrderService.getOrder(OrderService.java:58)')
            if not noise and in_inc(ts, 'oom') and T(14, 11, 2, 10) <= ts < T(14, 11, 3, 40) and path != '/health':
                status, latency = rng.choice([502, 503]), rng.randint(5, 60000)
            if not noise and in_inc(ts, 'gateway') and path == '/api/checkout':
                if rng.random() < 0.4:
                    status, latency = 504, 10000 + rng.randint(0, 50)
                else:
                    latency = rng.randint(5000, 9800)
                app_line(ts + timedelta(milliseconds=latency), 'ERROR', 'c.shop.payments.PaymentClient',
                         'Payment authorisation failed: java.net.SocketTimeoutException: Read timed out',
                         'java.net.SocketTimeoutException: Read timed out\n'
                         '\tat java.base/sun.nio.ch.NioSocketImpl.timedRead(NioSocketImpl.java:288)\n'
                         '\tat c.shop.payments.PaymentClient.authorise(PaymentClient.java:77)')
            if not noise and in_inc(ts, 'bad-deploy') and path == '/api/users/{id}' and rng.random() < 0.7:
                status = 500
                app_line(ts + timedelta(milliseconds=latency), 'ERROR', 'c.shop.users.UserController',
                         'Request failed: java.lang.NullPointerException: Cannot invoke "String.toLowerCase()" because "user.email" is null',
                         'java.lang.NullPointerException: Cannot invoke "String.toLowerCase()" because "user.email" is null\n'
                         '\tat c.shop.users.UserMapper.toDto(UserMapper.java:31)\n'
                         '\tat c.shop.users.UserController.get(UserController.java:44)')
            size = rng.randint(200, 4000) if status < 400 else rng.randint(100, 400)
            access.append((ts, f'{ip} - - [{apache_time(ts)}] "{method} {p} HTTP/1.1" {status} {size} "-" "{agent}" {latency}ms'))
        t += timedelta(minutes=1)

    # ---- brute force
    bf = next(i for i in INCIDENTS if i['id'] == 'brute-force')
    for k in range(600):
        ts = bf['start'] + timedelta(seconds=k * 1.5 + rng.random())
        access.append((ts, f'203.0.113.77 - - [{apache_time(ts)}] "POST /api/login HTTP/1.1" 401 112 "-" "python-requests/2.31" {rng.randint(60, 120)}ms'))
        if k % 50 == 0:
            app_line(ts, ' WARN', 'c.shop.auth.LoginController', f'Failed login for user "admin" from 203.0.113.77 ({k + 1} failures in a row)')

    # ---- memory leak: GC warnings with growing heap, then OOM + restart
    for k, minute in enumerate(range(0, 182, 10)):
        ts = T(14, 8, 0) + timedelta(minutes=minute, seconds=rng.randint(0, 50))
        heap = min(98, 60 + k * 2 + (k // 6) * 2)
        level = ' WARN' if heap >= 80 else ' INFO'
        app_line(ts, level, 'c.shop.catalog.ProductCache', f'Heap usage {heap}% after GC; product cache size {12000 + k * 4300} entries')
    oom_t = T(14, 11, 2, 9)
    tomcat.append((oom_t, f'Exception in thread "http-nio-8080-exec-17" java.lang.OutOfMemoryError: Java heap space\n'
                          '\tat java.base/java.util.Arrays.copyOf(Arrays.java:3537)\n'
                          '\tat c.shop.catalog.ProductCache.put(ProductCache.java:63)'))
    tomcat.append((oom_t + timedelta(seconds=1), f'{tomcat_time(oom_t + timedelta(seconds=1))} SEVERE [main] org.apache.catalina.core.StandardServer.await Tomcat is shutting down after a fatal error'))
    up = T(14, 11, 3, 35)
    tomcat.append((up, f'{tomcat_time(up)} INFO [main] org.apache.catalina.startup.Catalina.start Server startup in [5432] milliseconds'))
    for k in range(18):
        ts = T(14, 11, 2, 10) + timedelta(seconds=k * 5)
        msg = (f'[{apache_err_time(ts)}] [proxy_http:error] [pid 2211] (70007)The timeout specified has expired: AH01102: error reading status line from remote server 127.0.0.1:8080'
               if k % 2 == 0 else
               f'[{apache_err_time(ts)}] [proxy:error] [pid 2211] (111)Connection refused: AH00957: http: attempt to connect to 127.0.0.1:8080 (localhost) failed')
        apache_err.append((ts, msg))

    # ---- normal app + tomcat + apache noise
    for day in (13, 14, 15):
        for hh in range(0, 24, 3):
            ts = T(day, hh, rng.randint(0, 59), rng.randint(0, 59))
            app_line(ts, ' INFO', 'c.shop.catalog.ProductCache', f'Cache refresh done: {rng.randint(9000, 13000)} products in {rng.randint(200, 900)} ms')
        ts = T(day, 2, 0, 5)
        app_line(ts, ' INFO', 'c.shop.jobs.NightlyReport', 'Nightly sales report finished in 41 s')
        for _ in range(4):
            ts = T(day, rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59))
            apache_err.append((ts, f'[{apache_err_time(ts)}] [core:info] [pid 2211] [client {rng.choice(ips)}:{rng.randint(30000, 60000)}] AH00128: File does not exist: /var/www/html/favicon.ico'))
    for day in (13, 14, 15):
        ts = T(day, 0, 0, 1)
        tomcat.append((ts, f'{tomcat_time(ts)} INFO [Catalina-utility-1] org.apache.catalina.core.StandardContext.reload Log rotation complete'))
    # DB pool: report query + pool warnings
    app_line(T(13, 10, 19, 40), ' INFO', 'c.shop.reports.SalesReport', 'Started ad-hoc sales report for 2026-Q3 (requested by finance)')
    app_line(T(13, 10, 21, 5), ' WARN', 'com.zaxxer.hikari.pool.HikariPool', 'HikariPool-1 - Pool stats (total=10, active=10, idle=0, waiting=37)')
    app_line(T(13, 10, 44, 50), ' INFO', 'c.shop.reports.SalesReport', 'Ad-hoc sales report cancelled by DBA after 25 min')
    # gateway
    app_line(T(14, 16, 36, 0), ' INFO', 'c.shop.payments.PaymentClient', 'Payment gateway latency back to normal (p95 310 ms)')
    # deploys
    for ts, line in [(T(13, 9, 0), 'deploy shop-app v1.4.1 (ok)'), (T(15, 14, 0), 'deploy shop-app v1.4.2 (by ci-bot, commit 9f2c1ab "map user email to lowercase")'),
                     (T(15, 14, 40), 'rollback shop-app to v1.4.1 (by on-call: errors on /api/users)')]:
        deploys.append((ts, f'{ts.strftime("%Y-%m-%d %H:%M:%S")} {line}'))
        app_line(ts + timedelta(seconds=40), ' INFO', 'c.shop.ShopApplication', f'Started ShopApplication {line.split()[2] if line.startswith("deploy") else "v1.4.1"} in 6.2 seconds')

    # ---- write files (sorted by time)
    files = {'apache/access_log': access, 'apache/error_log': apache_err, 'app/application.log': app,
             'tomcat/catalina.out': tomcat, 'deploys.log': deploys}
    counts = {}
    for name, rows in files.items():
        path = LOGS / name
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.sort(key=lambda r: r[0])
        path.write_text('\n'.join(line for _, line in rows) + '\n')
        counts[name] = sum(line.count('\n') + 1 for _, line in rows)
    key = [{**i, 'start': i['start'].isoformat(), 'end': i['end'].isoformat()} for i in INCIDENTS]
    (DATA / 'incidents.json').write_text(json.dumps(key, indent=2))
    write_kb()
    return counts


KB_DOCS = {
    'architecture.md': """# shop-app architecture

- Apache httpd 2.4 on port 443 terminates TLS and proxies to Tomcat with mod_proxy (127.0.0.1:8080, timeout 60 s).
- shop-app: Java 17, Spring Boot 3 on Tomcat 10, heap -Xmx2g, 40 request threads.
- Database: PostgreSQL 15 through HikariCP (maximumPoolSize 10, connectionTimeout 30000 ms).
- Payments: external gateway over HTTPS, read timeout 5 s.
- Logs: Apache access_log and error_log; application.log (logback); catalina.out (Tomcat); deploys.log (CI).
""",
    'runbooks/hikari-pool.md': """# Runbook: HikariCP connection pool exhausted

## Symptoms
- `java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms` in application.log.
- HTTP 500 with ~30 s latency on endpoints that use the database (often /api/orders).
- Pool stats show active=10, idle=0, waiting > 0.

## Likely causes
- A long-running query (reports, missing index) holds connections.
- Connection leak: code that does not close connections.

## Fix
1. Find and cancel the long query in PostgreSQL (`pg_stat_activity`, `pg_cancel_backend`).
2. Raise `maximumPoolSize` only if the database can take it.
3. Add a statement timeout for report queries; run reports on a read replica.
""",
    'runbooks/java-heap-oom.md': """# Runbook: Java heap OutOfMemoryError

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
""",
    'runbooks/payment-gateway-timeouts.md': """# Runbook: payment gateway timeouts

## Symptoms
- `java.net.SocketTimeoutException: Read timed out` from PaymentClient.
- /api/checkout slow (over 5 s) and 504 Gateway Timeout from Apache.

## Fix
1. Check the payment provider status page.
2. Turn on the circuit breaker so checkout fails fast with a friendly message.
3. Retry with exponential backoff; never retry a payment without an idempotency key.
""",
    'runbooks/bad-deploy-rollback.md': """# Runbook: errors right after a deploy

## Symptoms
- A new exception type (for example NullPointerException) starts within minutes of a deploy in deploys.log.
- 500s on the endpoints touched by the change.

## Fix
1. Roll back to the previous version (`deploy rollback shop-app`).
2. Reproduce with the failing input, add a test, then redeploy.
""",
    'runbooks/brute-force-login.md': """# Runbook: login brute force

## Symptoms
- Hundreds of 401 responses on POST /api/login from one IP in the Apache access log.
- `Failed login ... N failures in a row` warnings in application.log.

## Fix
1. Block the IP in Apache (`Require not ip 203.0.113.77`) or at the firewall.
2. Enable rate limiting on /api/login and lock accounts after repeated failures.
""",
    'postmortems/2026-09-02-db-pool.md': """# Post-mortem 2026-09-02: checkout down 18 min (DB pool)

A month-end report ran on the primary database and held all 10 Hikari connections. Orders and checkout returned 500 after 30 s waits.
Fix: cancelled the query; moved reports to the read replica; added a 60 s statement timeout for report users.
Lesson: watch Hikari pool stats (active, waiting) and alert when waiting > 10.
""",
    'postmortems/2026-08-14-oom.md': """# Post-mortem 2026-08-14: Tomcat OutOfMemoryError

An image cache without a size limit grew until `java.lang.OutOfMemoryError: Java heap space`. Tomcat restarted; Apache returned 502 for 90 s.
Fix: added a maximum size to the cache; enabled heap dumps on OOM.
Lesson: alert when heap after GC stays above 80%.
""",
}


def write_kb():
    for name, text in KB_DOCS.items():
        path = KB / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


if __name__ == '__main__':
    print(generate())
