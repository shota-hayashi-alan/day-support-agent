"""ツール呼び出しループ本体。"""
from __future__ import annotations

import anthropic

from .store import Store
from .tools import TOOLS, run_tool

MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = """あなたはユーザーの日常生活をサポートするパーソナルアシスタントです。
- スケジュール管理と「やりたいこと」リストの管理を、ツールを使って行います。
- 日付が相対表現(今日・明日・来週など)の場合は、まず get_today で基準日を確認してください。
- 予定追加で conflicts があれば、必ずユーザーに伝えて調整案を出してください。
- 「今日何する？」のような相談では、今日の予定と未完了のやりたいこと(期限・優先度・所要時間)を
  両方確認し、空き時間に無理なく収まる具体的な1日の計画を提案してください。
- 簡潔で親しみやすい日本語で答え、勝手に予定を削除しないでください。"""


class Agent:
    def __init__(self, store: Store | None = None,
                 client: anthropic.Anthropic | None = None, calendar=None):
        self.store = store or Store()
        self.calendar = calendar or self.store
        self.client = client or anthropic.Anthropic()
        self.messages: list[dict] = []

    def chat(self, user_text: str, max_turns: int = 10) -> str:
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(max_turns):
            resp = self.client.messages.create(
                model=MODEL, max_tokens=2048, system=SYSTEM_PROMPT,
                tools=TOOLS, messages=self.messages)
            self.messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            results = [
                {"type": "tool_result", "tool_use_id": b.id,
                 "content": run_tool(self.store, b.name, b.input, self.calendar)}
                for b in resp.content if b.type == "tool_use"]
            self.messages.append({"role": "user", "content": results})
        return "(処理が長くなりすぎたため中断しました)"
