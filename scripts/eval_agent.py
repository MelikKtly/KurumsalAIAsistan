"""Agent'ları araç seçimi ve görev başarısı açısından değerlendirir.

Her görev için: hangi araçlar çağrıldı (beklenenle aynı mı), son cevap beklenen bilgiyi
içeriyor mu, kaç LLM çağrısı / ne kadar süre / kaç token harcandı.

Kullanım:
    uv run python -m scripts.eval_agent --agent simple --out docs/agent_simple.md
"""

import argparse
import statistics
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.config import get_settings
from app.evaluation.scoring import contains_all


class AgentTask(BaseModel):
    id: str
    question: str
    expected_tools: list[str]
    must_contain: list[str] = []


def load_tasks(path: str | Path) -> list[AgentTask]:
    return [AgentTask.model_validate(t) for t in yaml.safe_load(Path(path).read_text(encoding="utf-8"))["tasks"]]


def get_runner(name: str):
    """Agent adını çalıştırma fonksiyonuna çevirir (import'lar burada: yalnızca seçilen yüklenir)."""
    if name == "simple":
        from app.agent.simple_agent import run_simple_agent

        return run_simple_agent
    if name == "graph":
        from app.agent.graph import run_graph_agent

        return run_graph_agent
    if name == "multi":
        from app.agent.multi_agent import run_multi_agent

        return run_multi_agent
    raise SystemExit(f"Bilinmeyen agent: {name}")


def cell(text: str, limit: int = 110) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", choices=["simple", "graph", "multi"], default="graph")
    parser.add_argument("--tasks", default="data/eval/agent_tasks.yaml")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    run = get_runner(args.agent)
    rows = []
    for task in load_tasks(args.tasks):
        result = run(task.question)
        called = sorted({s.tool for s in result.steps})  # Çağrılan araçlar (tekrarlar tek sayılır)
        tools_ok = called == sorted(task.expected_tools)
        content_ok = contains_all(result.answer, task.must_contain)
        rows.append((task, result, called, tools_ok, content_ok))
        mark = "✅" if tools_ok and content_ok else "❌"
        print(f"{mark} {task.id} araçlar={called} ({result.total_ms / 1000:.1f} sn) | {cell(result.answer, 80)}")

    n = len(rows)
    success = sum(r[3] and r[4] for r in rows)
    lines = [
        f"# Agent Değerlendirmesi: `{args.agent}`",
        "",
        f"**Tarih:** {date.today().isoformat()} · **Model:** `{get_settings().llm_model}` · **Görev seti:** `{args.tasks}` ({n} görev)  ",
        f"**Yeniden üretmek için:** `uv run python -m scripts.eval_agent --agent {args.agent} --out {args.out}`",
        "",
        "| Ölçüt | Sonuç |",
        "| --- | --- |",
        f"| **Görev başarısı** (doğru araçlar + beklenen bilgi) | **{success}/{n}** |",
        f"| Doğru araç seçimi | {sum(r[3] for r in rows)}/{n} |",
        f"| Beklenen bilgi cevapta | {sum(r[4] for r in rows)}/{n} |",
        f"| Ortalama LLM çağrısı | {statistics.mean(r[1].llm_calls for r in rows):.1f} |",
        f"| Ortalama süre | {statistics.mean(r[1].total_ms for r in rows) / 1000:.1f} sn |",
        f"| Ortalama token | {statistics.mean(r[1].tokens.total_tokens for r in rows):.0f} |",
        "",
        "| id | Soru | Beklenen araçlar | Çağrılan araçlar | Sonuç | Cevap |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for task, result, called, tools_ok, content_ok in rows:
        mark = "✅" if tools_ok and content_ok else ("❌ araç" if not tools_ok else "❌ içerik")
        lines.append(
            f"| {task.id} | {cell(task.question, 60)} | {', '.join(task.expected_tools) or '—'} | "
            f"{', '.join(called) or '—'} | {mark} | {cell(result.answer)} |"
        )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nGörev başarısı {success}/{n} · Rapor: {args.out}")


if __name__ == "__main__":
    main()
