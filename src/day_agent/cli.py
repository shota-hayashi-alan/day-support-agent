"""対話CLI。"""
import argparse

from .agent import Agent


def main() -> None:
    ap = argparse.ArgumentParser(prog="day-agent")
    ap.add_argument("--google", action="store_true",
                    help="予定をGoogleカレンダーと同期する(要 credentials.json)")
    args = ap.parse_args()

    calendar = None
    if args.google:
        from .gcal import GoogleCalendar
        calendar = GoogleCalendar.from_oauth()
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
