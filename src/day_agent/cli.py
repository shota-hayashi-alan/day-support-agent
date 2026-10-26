"""対話CLI。"""
import argparse

from .agent import Agent


def main() -> None:
    ap = argparse.ArgumentParser(prog="day-agent")
    ap.add_argument("--google", action="store_true",
                    help="予定をGoogleカレンダーと同期する(要 credentials.json)")
    ap.add_argument("--brief", action="store_true",
                    help="朝のブリーフィングを表示して終了(cron等で使える)")
    ap.add_argument("--plain", action="store_true",
                    help="--brief をAIを使わず素材のまま表示する(APIキー不要)")
    ap.add_argument("--seed-habits", action="store_true",
                    help="運動・小説の執筆・ピアノの練習・英語を初期目標つきで登録")
    ap.add_argument("--habits", action="store_true", help="今週の習慣の進捗を表示")
    ap.add_argument("--sync", metavar="FILE",
                    help="JSON/CSVから習慣の実績を取り込む(列: id,date,habit,amount)")
    ap.add_argument("--health-dump", type=int, metavar="DAYS",
                    help="Google Healthから直近DAYS日の運動の生データをJSON表示(仕様確認用)")
    ap.add_argument("--sync-google", type=int, nargs="?", const=14, metavar="DAYS",
                    help="Google Health(Fitbit)の直近DAYS日(既定14)の運動を「運動」習慣に取り込む")
    ap.add_argument("--exclude-type", action="append", metavar="TYPE",
                    help="--sync-google で除外する運動の種類。複数指定可。未指定ならWALKINGを除外、'none'で除外なし")
    ap.add_argument("--rebuild", action="store_true",
                    help="--sync-google の期間内のGoogle由来の記録をいったん消して入れ直す(手入力は消さない)")
    ap.add_argument("--min-minutes", type=float, default=10,
                    help="--sync-google で取り込む最短の運動時間(分)。既定10")
    args = ap.parse_args()

    if args.health_dump:
        _health_dump(args.health_dump)
        return

    if args.seed_habits or args.habits or args.sync or args.sync_google:
        _habit_commands(args)
        return

    calendar = None
    if args.google:
        from .gcal import GoogleCalendar
        calendar = GoogleCalendar.from_oauth()
    if args.brief:
        from .brief import morning_brief
        from .store import Store
        print(morning_brief(Store(), calendar, plain=args.plain))
        return
    agent = Agent(calendar=calendar)
    print("日常サポートエージェント (終了: Ctrl+D / 'exit')")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text in ("exit", "quit"):
            break
        if text:
            print(agent.chat(text))



SEED = [("運動", "min", 150, ["exercise", "workout"]),
        ("小説の執筆", "min", 150, ["執筆", "writing"]),
        ("ピアノの練習", "min", 120, ["ピアノ", "piano"]),
        ("英語", "min", 150, ["english"])]


def _habit_commands(args) -> None:
    from datetime import date

    from .brief import _fmt_habit
    from .habits import HabitTracker
    from .store import Store
    from .sync import FileSource, sync

    ht = HabitTracker(Store())
    if args.seed_habits:
        for name, unit, target, aliases in SEED:
            if not ht.find(name):
                ht.create(name, unit, target, aliases)
        print("登録しました。目標は仮置きです。チャットで「運動の週目標を200分に」などと変更できます。")
    if args.sync:
        print(sync(ht, FileSource(args.sync)))
    if args.sync_google:
        from datetime import timedelta

        from .healthapi import (GoogleHealthSource, HealthClient, authorized_session,
                                resolve_excludes)
        source = GoogleHealthSource(
            HealthClient(authorized_session()), days=args.sync_google,
            exclude_types=resolve_excludes(args.exclude_type),
            min_minutes=args.min_minutes)
        if args.rebuild:
            start = source.today - timedelta(days=source.days - 1)
            n = ht.remove_source_logs(source.name, start.isoformat(),
                                      source.today.isoformat())
            print(f"Google由来の記録を{n}件削除して入れ直します")
        print(sync(ht, source))
    if args.habits or args.seed_habits or args.sync or args.sync_google:
        for p in ht.all_progress(date.today()):
            print(_fmt_habit(p))


def _health_dump(days: int) -> None:
    import json
    from datetime import date, timedelta

    from .healthapi import HealthClient, authorized_session

    today = date.today()
    points = HealthClient(authorized_session()).list_exercises(
        today - timedelta(days=days - 1), today)
    print(json.dumps(points, ensure_ascii=False, indent=2))
    print(f"# {len(points)}件", flush=True)


if __name__ == "__main__":
    main()
