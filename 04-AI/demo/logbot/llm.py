"""
A small open-source chat model, run locally with Hugging Face transformers (no API, no Ollama).
Default: Qwen/Qwen2.5-0.5B-Instruct. Set the environment variable MODEL_ID to use another model,
for example Qwen/Qwen2.5-1.5B-Instruct (better answers, slower, ~3 GB download).
"""
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = os.environ.get('MODEL_ID', 'Qwen/Qwen2.5-0.5B-Instruct')


class LocalLLM:
    def __init__(self, model_id=MODEL_ID, device=None):
        self.model_id = model_id
        self.device = device or ('mps' if torch.backends.mps.is_available() else 'cpu')
        dtype = torch.float16 if self.device == 'mps' else torch.float32
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype).to(self.device).eval()

    @torch.no_grad()
    def chat(self, messages, max_new_tokens=160):
        """messages: [{'role': 'system'|'user'|'assistant', 'content': str}, …] → (reply, stats)."""
        prompt = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        ids = self.tok(prompt, return_tensors='pt').to(self.device)
        t0 = time.perf_counter()
        out = self.model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=1.1,
                                  pad_token_id=self.tok.eos_token_id)
        new = out[0, ids['input_ids'].shape[1]:]
        secs = time.perf_counter() - t0
        reply = self.tok.decode(new, skip_special_tokens=True).strip()
        return reply, {'prompt_tokens': int(ids['input_ids'].shape[1]), 'new_tokens': int(len(new)),
                       'seconds': round(secs, 2), 'tokens_per_s': round(len(new) / max(secs, 1e-6), 1)}
