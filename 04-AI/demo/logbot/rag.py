"""
v2: retrieval-augmented answers.

1. Chunk: problem windows of the logs (per file, 10 minutes, repeated messages counted) + runbook sections.
2. Embed every chunk with all-MiniLM-L6-v2 (local cache, no download).
3. Search: cosine similarity + a small bonus for exact word matches (IPs, versions, class names).
4. Answer: the local model reads only the top chunks and must cite them [S1], [S2] …
"""
import json
import re

import numpy as np
import pandas as pd

from . import INDEX, KB
from .prompts import SYSTEM_V2
from .tools import first_last

EMBED_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
WINDOW = '10min'


def _fmt(t):
    return t.strftime('%Y-%m-%d %H:%M')


def log_chunks(df):
    """One chunk per (file, 10-minute window) that contains something worth reading."""
    chunks = []
    df = df.copy()
    df['window'] = df['time'].dt.floor(WINDOW)
    acc = df[df.source == 'apache_access']
    for win, g in acc.groupby('window'):
        n5, n401, p95 = int((g.status >= 500).sum()), int((g.status == 401).sum()), float(g.latency_ms.quantile(0.95))
        if n5 == 0 and n401 < 20 and p95 < 2000:
            continue                                  # a normal window: nothing to read
        bad = g[(g.status >= 400) | (g.latency_ms >= 2000)]
        top = bad.groupby(['endpoint', 'status']).size().sort_values(ascending=False).head(4)
        ips = bad.ip.value_counts().head(2)
        head = (f'apache/access_log {_fmt(win)}–{_fmt(win + pd.Timedelta(WINDOW))}: {len(g)} requests, {n5} HTTP 5xx, '
                f'{n401} HTTP 401, p95 latency {p95:.0f} ms. Top problems: '
                + '; '.join(f'{ep} {st} ×{c}' for (ep, st), c in top.items())
                + '. Top client IPs: ' + ', '.join(f'{ip} ×{c}' for ip, c in ips.items()) + '.')
        samples = '\n'.join(bad['text'].head(3))
        chunks.append(dict(kind='log', file='apache/access_log', start=_fmt(win), line=int(bad.line.iloc[0]), text=head + '\n' + samples))
    other = df[df.source != 'apache_access']
    for (file, win), g in other.groupby(['file', 'window']):
        first = g['logger'].fillna('').str.split('.').str[-1].where(g['logger'].notna(), '') + ': ' + g['message'].fillna('')
        counts = g.assign(first=first.str.lstrip(': ')).groupby(['level', 'first'], sort=False).size()
        lines = [f'{lvl} ×{c}: {first[:260]}' for (lvl, first), c in counts.items()]
        trace = next((t for t in g['text'] if '\n' in t), '')
        extra = ('\nstack trace: ' + ' | '.join(trace.split('\n')[1:3]).replace('\t', '')) if trace else ''
        chunks.append(dict(kind='log', file=file, start=_fmt(win), line=int(g.line.iloc[0]),
                           text=f'{file} {_fmt(win)}–{_fmt(win + pd.Timedelta(WINDOW))}:\n' + '\n'.join(lines[:8]) + extra))
    return chunks


def kb_chunks():
    """One chunk per knowledge-base document (they are short; keeping them whole keeps the Fix with its Symptoms)."""
    return [dict(kind='kb', file=f'kb/{p.relative_to(KB)}', start='', line=1, text=p.read_text()) for p in sorted(KB.rglob('*.md'))]


class RagIndex:
    def __init__(self, chunks, embedder=None):
        from sentence_transformers import SentenceTransformer
        self.chunks = chunks
        self.embedder = embedder or SentenceTransformer(EMBED_MODEL)
        self.vectors = self.embedder.encode([c['text'] for c in chunks], normalize_embeddings=True, batch_size=64)

    @classmethod
    def build(cls, df, embedder=None):
        return cls(log_chunks(df) + kb_chunks(), embedder)

    def add(self, chunks):
        vec = self.embedder.encode([c['text'] for c in chunks], normalize_embeddings=True)
        self.chunks += chunks
        self.vectors = np.vstack([self.vectors, vec])

    def save(self, folder=INDEX):
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / 'vectors.npy', self.vectors)
        (folder / 'chunks.json').write_text(json.dumps(self.chunks, indent=1))

    @classmethod
    def load(cls, folder=INDEX, embedder=None):
        from sentence_transformers import SentenceTransformer
        self = cls.__new__(cls)
        self.embedder = embedder or SentenceTransformer(EMBED_MODEL)
        self.vectors = np.load(folder / 'vectors.npy')
        self.chunks = json.loads((folder / 'chunks.json').read_text())
        return self

    def search(self, question, k_logs=3, k_kb=1, k_extra=2, file=None, since=None, until=None):
        q = self.embedder.encode([question], normalize_embeddings=True)[0]
        sim = self.vectors @ q
        words = {w for w in re.findall(r'[\w.:/-]{3,}', question.lower())}
        d = re.search(r'(?:oct(?:ober)?\.? ?(\d{1,2}))|(?:(\d{1,2}) ?oct)|(?:2026-10-(\d{2}))', question.lower())
        day = next((x.zfill(2) for x in d.groups() if x), None) if d else None
        h = re.search(r'\b(\d{1,2}):\d{2}\b', question)
        hour = h[1].zfill(2) if h else None
        scored = []
        for i, c in enumerate(self.chunks):
            if file and not c['file'].startswith(file):
                continue
            if c['kind'] == 'log' and ((since and c['start'] < since) or (until and c['start'] > until)):
                continue
            text = c['text'].lower()
            bonus = 0.05 * sum(1 for w in words if w in text and not w.isalpha())   # exact IPs, versions, paths
            if c['kind'] == 'log' and day and c['start'][8:10] == day:
                bonus += 0.08 + (0.06 if hour and c['start'][11:13] == hour else 0)
            scored.append((float(sim[i]) + bonus, i))
        scored.sort(reverse=True)
        logs = [(s, i) for s, i in scored if self.chunks[i]['kind'] == 'log'][:k_logs]
        kb = [(s, i) for s, i in scored if self.chunks[i]['kind'] == 'kb'][:k_kb]
        # same time window, other log files: the Apache symptom and the Java cause sit side by side
        seen = {i for _, i in logs}
        windows = {self.chunks[i]['start'] for _, i in logs}
        win_score = {self.chunks[i]['start']: s for s, i in logs}
        extra = [(win_score[c['start']] - 0.001, i) for i, c in enumerate(self.chunks)
                 if c['kind'] == 'log' and c['start'] in windows and i not in seen and c['file'] != 'apache/access_log']
        extra.sort(key=lambda x: ('ERROR' not in self.chunks[x[1]]['text'], self.chunks[x[1]]['start']))
        ranked = sorted(logs + extra[:k_extra] + kb, reverse=True)      # most relevant first: small models read the top best
        return [{**self.chunks[i], 'score': round(s, 3)} for s, i in ranked]


FACT = re.compile(r'((?:java|javax)\.[\w.]+(?:Exception|Error))|(AH0\d{4})|(v\d\.\d\.\d)|(\b\d{1,3}(?:\.\d{1,3}){3}\b)')


def facts(hits, df):
    """Code finds the facts: for each exception / Apache code / version / outside IP in the sources, when and how often (pandas)."""
    seen, out = set(), []
    for h in hits[:3]:                                   # only the most relevant sources
        if h['kind'] != 'log':
            continue
        for m in FACT.finditer(h['text']):
            k = next(g for g in m.groups() if g)
            if k in seen or k.startswith('10.0.') or k == '127.0.0.1':
                continue
            seen.add(k)
            fl = first_last(df, k)
            if fl:
                out.append(f"- {k}: first {fl['first'][:19]}, last {fl['last'][:19]}, {fl['count']} lines in {', '.join(fl['files'])}")
            else:                                        # e.g. newly ingested logs, not in the table
                out.append(f"- {k}: {h['text'].count(k)} lines in {h['file']}")
    return '\n'.join(out[:6])


def build_messages(question, hits, df=None):
    sources = '\n\n'.join(f'[S{n}] {h["text"][:500]}' for n, h in enumerate(hits, 1))
    f = facts(hits, df) if df is not None else ''
    head = f'FACTS (counted from the logs):\n{f}\n\n' if f else ''
    return [{'role': 'system', 'content': SYSTEM_V2},
            {'role': 'user', 'content': f'{head}SOURCES:\n{sources}\n\nQUESTION: {question}'}]


class AskV2:
    def __init__(self, llm, index, df=None):
        self.llm, self.index, self.df = llm, index, df

    def ask(self, question, **filters):
        hits = self.index.search(question, **filters)
        reply, stats = self.llm.chat(build_messages(question, hits, self.df))
        sources = [{'id': f'S{n}', 'file': h['file'], 'line': h['line'], 'start': h['start'], 'score': h['score'],
                    'text': h['text'].splitlines()[0][:200]} for n, h in enumerate(hits, 1)]
        return reply, sources, stats
