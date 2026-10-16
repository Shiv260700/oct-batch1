"""
v1: a plain chatbot. Its context is a short summary of the logs + the newest problem lines
(what fits in a small model's prompt). It keeps the chat history per session.
"""
import json

from .prompts import SYSTEM_V1
from .tools import latest_problems, summary


def v1_context(df, n_lines=15):
    s = summary(df)
    lines = '\n'.join(t.splitlines()[0][:220] for t in latest_problems(df, n_lines)['text'])
    return f"LOG SUMMARY: {json.dumps(s)}\n\nMOST RECENT PROBLEM LINES:\n{lines}"


class ChatV1:
    def __init__(self, llm, df, history_turns=3):
        self.llm, self.context, self.history_turns = llm, v1_context(df), history_turns
        self.sessions = {}

    def ask(self, message, session_id='default'):
        history = self.sessions.setdefault(session_id, [])
        messages = [{'role': 'system', 'content': SYSTEM_V1 + '\n\n' + self.context}]
        messages += history[-2 * self.history_turns:]
        messages.append({'role': 'user', 'content': message})
        reply, stats = self.llm.chat(messages)
        history += [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}]
        return reply, stats
