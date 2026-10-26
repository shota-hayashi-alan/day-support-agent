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

## 習慣トラッカー
運動・小説の執筆・ピアノの練習・英語など、週ごとの目標に対する進捗と連続日数を管理します。
```bash
day-agent --seed-habits        # 上記4つを仮の週目標つきで登録（運動150分、執筆150分、ピアノ120分、英語150分）
day-agent --habits             # 今週の進捗を表示
day-agent --sync records.csv   # 外部データを取り込み（JSON/CSV: id,date,habit,amount）
```
チャットでも「ピアノを30分やった」「運動の週目標を200分に」で記録・変更できます。進捗は朝のブリーフィングにも出ます。
週は月曜始まりで、連続日数は「今日まだ未実施」でも昨日までの連続を途切れさせません。

### 外部アプリとの自動連携
`sync.py` の `Source` を実装すれば、データ源を追加できます（`(source, id)` が同じ記録は二重登録されません）。
現在は `FileSource`（JSON/CSV）のみ。スマホのショートカットやIFTTT、各アプリのエクスポートからの取り込み口として使えます。
**Google Health API(Fitbitの後継)連携:**
`healthapi.py` が `users/me/dataTypes/exercise/dataPoints`（読み取り専用スコープのみ）から運動を取得し、「運動」習慣に自動記録します。
```bash
pip install -e ".[google]"
day-agent --seed-habits                          # 初回のみ(「運動」習慣を作る)
day-agent --sync-google                          # 直近14日の運動を取り込み(初回はブラウザで認可)
day-agent --sync-google 30 --min-minutes 15      # 30日分・15分以上
day-agent --sync-google --rebuild                # 設定を変えたあと、期間内のGoogle由来の記録を入れ直す
day-agent --health-dump 14                       # 生データをJSON表示(確認用)
```
- 記録する時間は、実際に動いていた時間(`activeDuration`)の分数。日付は端末のUTCオフセットで現地日付に直します。
- 既定では10分未満の運動と、ウォーキング(`WALKING`)は除外。`--exclude-type GOLF` のように種類を指定して変更でき、`--exclude-type none` で除外なしになります。
- Fitbitの自動検出は運動の種類を取り違えることがあります（種類の名前は目安です）。
- 同じ運動は二重登録されません。ただし、あとから記録側で内容が修正されても、取り込み済みの分は更新されません。
- 毎朝の自動実行例: `30 7 * * * cd ~/day-support-agent && .venv/bin/day-agent --sync-google && .venv/bin/day-agent --brief --google`
`credentials.json` は Cloud Console のデスクトップアプリ用OAuthクライアントです（Gitには含めない）。

**Fitbitについて:** 旧Fitbit Web APIは2026年秋に終了予定で、後継はGoogle Health APIです。仕様を確認のうえ、別PRでSourceとして追加する想定です。

## 朝のブリーフィング
```bash
day-agent --brief          # 今日の予定・空き時間・やりたいことをAIが1日の計画にまとめる
day-agent --brief --plain  # AIなしで素材をそのまま表示（APIキー不要）
```
非対話で終了するので、cronなどで毎朝実行できます（例: `30 7 * * * day-agent --brief --google`）。
空き時間は 08:00〜22:00 のうち30分以上の隙間を計算します。

## Googleカレンダー連携
予定をGoogleカレンダー（primary）と同期できます。やりたいことリストはローカル保存のままです。

1. Google Cloud Consoleで Calendar API を有効化し、OAuthクライアントID（デスクトップアプリ）を作成
2. `credentials.json` をプロジェクト直下に置く（`GOOGLE_CREDENTIALS` で変更可）
3. 実行:
```bash
pip install -e ".[google]"
day-agent --google
```
初回はブラウザで認可し、トークンを `data/token.json` に保存します。タイムゾーンは `DAY_AGENT_TZ`（既定 `Asia/Tokyo`）。

## 構成
- `src/day_agent/store.py` JSON保存
- `src/day_agent/tools.py` Claude用ツール定義
- `src/day_agent/agent.py` ツール呼び出しループ
- `src/day_agent/habits.py` 習慣の目標・記録・進捗
- `src/day_agent/sync.py` 外部データ取り込み
- `src/day_agent/gcal.py` Googleカレンダー連携
- `src/day_agent/cli.py` 対話CLI

## 今後の候補
LINE/Slack連携
