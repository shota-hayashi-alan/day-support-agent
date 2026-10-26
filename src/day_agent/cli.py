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
    args = ap.parse_args()

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


if __name__ == "__main__":
    main()
