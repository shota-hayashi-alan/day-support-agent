# day-support-agent

スケジュール管理と「やりたいこと」を一緒に整理してくれる、日常生活サポートエージェント。

## できること
- 予定の追加・一覧・削除（時間の重複を自動チェック）
- やりたいことリスト（優先度・所要時間・期限）の管理
- 「今日何する？」で、予定と空き時間を踏まえた1日の計画を提案

## 使い方
```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...
day-agent
> 明日の10時から1時間、歯医者の予定を入れて
> 英語の勉強を30分、優先度高でやりたいことに追加
> 今日は何をすればいい？
```
データは `data/store.json`（`DAY_AGENT_DATA` で変更可）に保存されます。

## 構成
- `src/day_agent/store.py` JSON保存
- `src/day_agent/tools.py` Claude用ツール定義
- `src/day_agent/agent.py` ツール呼び出しループ
- `src/day_agent/cli.py` 対話CLI

## 今後の候補
Googleカレンダー連携、毎朝の自動ブリーフィング、習慣トラッカー、LINE/Slack連携
