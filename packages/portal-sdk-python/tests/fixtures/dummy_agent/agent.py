"""Минимальный агент для тестирования local_runner."""
from portal_sdk import Agent

agent = Agent()
msg = agent.params["message"]

agent.log("info", f"Echoing: {msg}")
agent.progress(0.5, "Half")

(agent.output_dir / "echoed.txt").write_text(msg, encoding="utf-8")

agent.progress(1.0, "Done")
agent.result(artifacts=[{"id": "echoed", "path": "echoed.txt"}])
