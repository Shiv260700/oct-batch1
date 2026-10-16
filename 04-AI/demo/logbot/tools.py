"""Plain pandas helpers: the numbers the chatbot can trust (no model involved)."""
import pandas as pd


def is_problem(df):
    """Rows that matter: app/tomcat/apache_error WARN+ERROR, and HTTP 4xx/5xx in the access log."""
    return df['level'].isin(['WARN', 'ERROR'])


def summary(df):
    acc = df[df.source == 'apache_access']
    return {
        'from': str(df.time.min()), 'to': str(df.time.max()),
        'requests': int(len(acc)),
        'http_5xx': int((acc.status >= 500).sum()),
        'http_4xx': int(((acc.status >= 400) & (acc.status < 500)).sum()),
        'app_errors': int(((df.source == 'app') & (df.level == 'ERROR')).sum()),
        'app_warnings': int(((df.source == 'app') & (df.level == 'WARN')).sum()),
        'top_exceptions': df['exception'].dropna().value_counts().head(5).to_dict(),
    }


def timeline(df, freq='10min'):
    """Per time window: requests, 5xx, 401s, p95 latency, app errors."""
    acc = df[df.source == 'apache_access'].set_index('time')
    g = acc.resample(freq)
    out = pd.DataFrame({
        'requests': g.size(),
        'http_5xx': g['status'].apply(lambda s: int((s >= 500).sum())),
        'http_401': g['status'].apply(lambda s: int((s == 401).sum())),
        'p95_ms': g['latency_ms'].quantile(0.95),
    })
    app_err = df[(df.source != 'apache_access') & (df.level == 'ERROR')].set_index('time').resample(freq).size()
    out['app_errors'] = app_err.reindex(out.index, fill_value=0)
    return out.fillna(0)


def top_exceptions(df, n=10):
    return df['exception'].dropna().value_counts().head(n)


def first_last(df, text):
    """First and last time a piece of text appears in any log line."""
    hit = df[df['text'].str.contains(text, case=False, regex=False)]
    if hit.empty:
        return None
    return {'first': str(hit.time.min()), 'last': str(hit.time.max()), 'count': int(len(hit)),
            'files': sorted(hit.file.unique().tolist())}


def latest_problems(df, n=15):
    """The newest problem lines: what a naive chatbot sees when it reads the end of the logs."""
    return df[is_problem(df)].tail(n)
