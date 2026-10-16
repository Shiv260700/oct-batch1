"""20 questions with known answers. An answer counts as correct if it contains one of the expected words."""
import time

import pandas as pd

NOT_FOUND = ['not found', 'cannot see', "can't see", 'no evidence', 'not in the logs', 'no ', 'not mentioned', 'does not']

QUESTIONS = [
    # (question, expected words (any one), incident id or None)
    ('What caused the 500 errors on /api/orders on Oct 13?', ['pool', 'hikari', 'connection'], 'db-pool'),
    ('When did the database connection problem start on Oct 13?', ['10:2'], 'db-pool'),
    ('What does the runbook say to do when the Hikari pool is exhausted?', ['cancel', 'statement timeout', 'pool size', 'maximumpoolsize', 'long query', 'long-running'], 'db-pool'),
    ('Why did Apache return 502 errors around 11:02 on Oct 14?', ['outofmemory', 'heap', 'memory', 'tomcat'], 'oom'),
    ('What error did Tomcat log before it restarted on Oct 14?', ['outofmemoryerror', 'heap'], 'oom'),
    ('How should we fix a Java heap OutOfMemoryError?', ['heap dump', 'cache', 'maximum size', 'restart'], 'oom'),
    ('Why was checkout slow on the afternoon of Oct 14?', ['payment', 'gateway', 'sockettimeout', 'timed out', 'timeout'], 'gateway'),
    ('Which exception did PaymentClient throw?', ['sockettimeoutexception', 'read timed out'], 'gateway'),
    ('What should we do when the payment gateway times out?', ['circuit breaker', 'status page', 'backoff', 'retry'], 'gateway'),
    ('Which version was deployed on Oct 15 at 14:00?', ['1.4.2'], 'bad-deploy'),
    ('What error started after the v1.4.2 deploy?', ['nullpointer', 'usermapper', 'email'], 'bad-deploy'),
    ('How was the problem after the v1.4.2 deploy fixed?', ['rollback', 'roll back', 'rolled back', '1.4.1'], 'bad-deploy'),
    ('Which IP address attempted the brute-force login?', ['203.0.113.77'], 'brute-force'),
    ('Which endpoint was hit by the failed logins on Oct 15 night?', ['/api/login', 'login'], 'brute-force'),
    ('What should we do about the IP doing the brute-force login?', ['block', 'rate limit', 'firewall'], 'brute-force'),
    ('What happened at 2 am every night?', ['nightly', 'report'], None),
    ('Did the cache refresh run normally?', ['cache refresh', 'products', 'yes'], None),
    ('Was there a disk full error?', NOT_FOUND, 'trap'),
    ('Did Redis go down?', NOT_FOUND, 'trap'),
    ('Did the SSL certificate expire?', NOT_FOUND, 'trap'),
]


def correct(answer, expected):
    a = answer.lower()
    return any(e in a for e in expected)


def run(name, ask):
    """ask(question) → (answer, sources or None). Returns one row per question."""
    rows = []
    for q, exp, inc in QUESTIONS:
        t0 = time.perf_counter()
        answer, sources = ask(q)
        rows.append(dict(version=name, question=q, incident=inc, answer=answer, correct=correct(answer, exp),
                         seconds=round(time.perf_counter() - t0, 1), sources=sources))
    return pd.DataFrame(rows)
