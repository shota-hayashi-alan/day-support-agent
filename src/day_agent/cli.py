"""対話CLI。"""
from .agent import Agent


def main() -> None:
    agent = Agent()
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
