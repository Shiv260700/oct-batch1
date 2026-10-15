"""The model, the tokenizer and generation: shared by the notebook (training) and the web service (serving)."""
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class Config:
    vocab: str            # every character the model knows, in index order
    topics: list          # e.g. ["graphics", "autos", ...]; each becomes a tag like "<autos> "
    context: int = 128    # characters the model sees at once
    dim: int = 192        # numbers per character
    layers: int = 4       # Transformer blocks
    heads: int = 4        # attention heads per block
    dropout: float = 0.1


class Tokenizer:
    """Characters ↔ integers. Unknown characters are dropped."""

    def __init__(self, vocab: str):
        self.vocab = vocab
        self.stoi = {c: i for i, c in enumerate(vocab)}

    def encode(self, text: str) -> list:
        return [self.stoi[c] for c in text if c in self.stoi]

    def decode(self, ids) -> str:
        return "".join(self.vocab[i] for i in ids)


def tag(topic: str) -> str:
    return f"<{topic}> "


class Block(nn.Module):
    """Attention (words discuss) → small network (each thinks), with shortcuts and normalisation."""

    def __init__(self, c: Config):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(c.dim), nn.LayerNorm(c.dim)
        self.attn = nn.MultiheadAttention(c.dim, c.heads, dropout=c.dropout, batch_first=True)
        self.mlp = nn.Sequential(nn.Linear(c.dim, 4 * c.dim), nn.GELU(), nn.Linear(4 * c.dim, c.dim), nn.Dropout(c.dropout))

    def forward(self, x, mask):
        h = self.ln1(x)
        x = x + self.attn(h, h, h, attn_mask=mask, need_weights=False)[0]
        return x + self.mlp(self.ln2(x))


class GPT(nn.Module):
    """Decoder-only Transformer: each character may look only at earlier characters (the mask)."""

    def __init__(self, c: Config):
        super().__init__()
        self.config = c
        V = len(c.vocab)
        self.tok = nn.Embedding(V, c.dim)
        self.pos = nn.Embedding(c.context, c.dim)
        self.drop = nn.Dropout(c.dropout)
        self.blocks = nn.ModuleList([Block(c) for _ in range(c.layers)])
        self.ln = nn.LayerNorm(c.dim)
        self.head = nn.Linear(c.dim, V)

    def forward(self, idx):
        t = idx.shape[1]
        mask = torch.triu(torch.ones(t, t, dtype=torch.bool, device=idx.device), 1)   # hide the future
        x = self.drop(self.tok(idx) + self.pos(torch.arange(t, device=idx.device)))
        for b in self.blocks:
            x = b(x, mask)
        return self.head(self.ln(x))

    @torch.no_grad()
    def generate(self, tok: Tokenizer, topic: str, prompt: str = "", max_chars: int = 300,
                 temperature: float = 0.8, top_k: int = 0, seed=None) -> str:
        """Continue `prompt` as a post about `topic`. Returns only the new text."""
        self.eval()
        dev = next(self.parameters()).device
        g = torch.Generator(device="cpu").manual_seed(seed) if seed is not None else None
        head = torch.tensor([tok.encode(tag(topic))], device=dev)          # the topic tag stays in view
        body = tok.encode(prompt)
        out = []
        for _ in range(max_chars):
            keep = self.config.context - head.shape[1]
            ctx = torch.cat([head, torch.tensor([body[-keep:]], device=dev, dtype=torch.long)], 1) if body else head
            logits = self(ctx)[0, -1] / max(temperature, 1e-4)
            if top_k:
                v, _ = torch.topk(logits, top_k)
                logits[logits < v[-1]] = -float("inf")
            probs = F.softmax(logits, -1).cpu()
            nxt = int(torch.multinomial(probs, 1, generator=g))
            body.append(nxt)
            out.append(nxt)
        return tok.decode(out)


def save(model: GPT, folder, extra: dict | None = None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), folder / "weights.pt")
    (folder / "config.json").write_text(json.dumps({**asdict(model.config), **({"meta": extra} if extra else {})}, indent=1))


def load(folder, device="cpu"):
    folder = Path(folder)
    raw = json.loads((folder / "config.json").read_text())
    meta = raw.pop("meta", {})
    c = Config(**raw)
    m = GPT(c)
    m.load_state_dict(torch.load(folder / "weights.pt", map_location=device))
    return m.to(device).eval(), Tokenizer(c.vocab), meta
