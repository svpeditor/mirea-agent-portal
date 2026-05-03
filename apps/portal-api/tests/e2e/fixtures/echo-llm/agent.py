"""E2E fixture: один LLM-вызов через прокси, пишет ответ в report.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

from openai import OpenAI
from portal_sdk import Agent

agent = Agent()
agent.progress(0.1, "starting")

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url=os.environ["OPENROUTER_BASE_URL"],
)

resp = client.chat.completions.create(
    model="deepseek/deepseek-chat",
    messages=[{"role": "user", "content": "Скажи привет одним словом."}],
    max_tokens=10,
)

content = resp.choices[0].message.content or ""
out_path = Path(os.environ["OUTPUT_DIR"]) / "report.json"
out_path.write_text(json.dumps({"answer": content}, ensure_ascii=False), encoding="utf-8")

agent.progress(1.0, "done")
agent.result(artifacts=[{"id": "report", "path": "report.json"}])
