"""
Read Apache + Java logs into one table.

Columns: time, source, file, line, level, method, endpoint, status, latency_ms, ip, logger, exception, message, text
Multi-line Java stack traces are joined onto the line that started them.
"""
import re
from datetime import datetime, timezone

import pandas as pd

from . import LOGS

ACCESS = re.compile(r'(?P<ip>\S+) \S+ \S+ \[(?P<t>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) [^"]*" (?P<status>\d{3}) (?P<size>\d+) "[^"]*" "(?P<agent>[^"]*)" (?P<lat>\d+)ms')
APACHE_ERR = re.compile(r'\[(?P<t>[A-Z][a-z]{2} [A-Z][a-z]{2} \d{2} [\d:.]+ \d{4})\] \[(?P<mod>[^:\]]+):(?P<level>[a-z]+)\] \[pid \d+\] (?P<msg>.*)')
APP = re.compile(r'(?P<t>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(?P<level>[A-Z]+) \d+ --- \[\s*(?P<thread>[^\]]+)\] (?P<logger>\S+)\s+: (?P<msg>.*)')
TOMCAT = re.compile(r'(?P<t>\d{2}-[A-Z][a-z]{2}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) (?P<level>[A-Z]+) \[(?P<thread>[^\]]+)\] (?P<logger>\S+) (?P<msg>.*)')
DEPLOY = re.compile(r'(?P<t>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<msg>.*)')
EXC = re.compile(r'((?:java|javax|com|org|c)\.(?:[a-z0-9_]+\.)+[A-Z]\w*(?:Exception|Error))')
UTC = timezone.utc
LEVELS = {'error': 'ERROR', 'crit': 'ERROR', 'warn': 'WARN', 'info': 'INFO', 'notice': 'INFO', 'SEVERE': 'ERROR', 'WARNING': 'WARN'}


def _endpoint(path):
    """/api/orders/42 → /api/orders/{id} (so requests group by endpoint)."""
    path = path.split('?')[0]
    return re.sub(r'/\d+(?=/|$)', '/{id}', path)


def _records(name):
    """Yield (line_no, text) records; continuation lines (stack traces) are joined to the record above."""
    path = LOGS / name
    rec, start = None, 0
    for no, raw in enumerate(path.read_text().splitlines(), 1):
        is_cont = raw.startswith(('\t', ' ', 'Caused by')) or (rec is not None and EXC.match(raw) and not raw[:4].isdigit())
        if is_cont and rec is not None:
            rec += '\n' + raw
            continue
        if rec is not None:
            yield start, rec
        rec, start = raw, no
    if rec is not None:
        yield start, rec


def read_logs():
    rows = []
    for no, text in _records('apache/access_log'):
        m = ACCESS.match(text)
        if not m:
            continue
        status = int(m['status'])
        rows.append(dict(time=datetime.strptime(m['t'], '%d/%b/%Y:%H:%M:%S %z'), source='apache_access', file='apache/access_log', line=no,
                         level='ERROR' if status >= 500 else 'WARN' if status >= 400 else 'INFO', method=m['method'],
                         endpoint=_endpoint(m['path']), status=status, latency_ms=int(m['lat']), ip=m['ip'], text=text,
                         message=f'{m["method"]} {m["path"]} {status} {m["lat"]}ms'))
    for no, text in _records('apache/error_log'):
        m = APACHE_ERR.match(text)
        if not m:
            continue
        code = re.search(r'AH\d{5}', m['msg'])
        rows.append(dict(time=datetime.strptime(m['t'], '%a %b %d %H:%M:%S.%f %Y').replace(tzinfo=UTC), source='apache_error', file='apache/error_log',
                         line=no, level=LEVELS.get(m['level'], 'INFO'), logger=m['mod'], exception=code[0] if code else None, message=m['msg'], text=text))
    for no, text in _records('app/application.log'):
        m = APP.match(text)
        if not m:
            continue
        exc = EXC.search(text)
        rows.append(dict(time=datetime.strptime(m['t'], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=UTC), source='app', file='app/application.log', line=no,
                         level=m['level'], logger=m['logger'], exception=exc[1] if exc else None, message=m['msg'], text=text))
    last = None
    for no, text in _records('tomcat/catalina.out'):
        m = TOMCAT.match(text)
        exc = EXC.search(text)
        if m:
            last = datetime.strptime(m['t'], '%d-%b-%Y %H:%M:%S.%f').replace(tzinfo=UTC)
            rows.append(dict(time=last, source='tomcat', file='tomcat/catalina.out', line=no, level=LEVELS.get(m['level'], m['level']),
                             logger=m['logger'], exception=exc[1] if exc else None, message=m['msg'], text=text))
        elif exc:   # "Exception in thread ..." lines have no timestamp: use the next timestamped line (filled below)
            rows.append(dict(time=None, source='tomcat', file='tomcat/catalina.out', line=no, level='ERROR', exception=exc[1],
                             message=text.splitlines()[0], text=text))
    for no, text in _records('deploys.log'):
        m = DEPLOY.match(text)
        if m:
            rows.append(dict(time=datetime.strptime(m['t'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC), source='deploy', file='deploys.log', line=no,
                             level='INFO', message=m['msg'], text=text))
    df = pd.DataFrame(rows)
    df['time'] = pd.to_datetime(df['time'], utc=True)
    tom = df['source'] == 'tomcat'
    df.loc[tom, 'time'] = df.loc[tom, 'time'].bfill()   # an untimed tomcat exception takes the time of the next tomcat line
    df = df.sort_values(['time', 'file', 'line']).reset_index(drop=True)
    for col in ['method', 'endpoint', 'ip', 'logger', 'exception']:
        if col not in df:
            df[col] = None
    return df
