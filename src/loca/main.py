import argparse

from loca.core.agent_session import AgentSession


def main(model_name: str, provider: str) -> None:
    session = AgentSession(model_name=model_name, provider=provider)
    session.run()


def cli():
    import loca.config as config
    parser = argparse.ArgumentParser(description="Loca - Autonomous AI Coding Assistant")
    parser.add_argument(
        "-p", "--provider", type=str, default=config.DEFAULT_PROVIDER,
        choices=["ollama", "openai", "anthropic", "gemini"],
        help="LLMのプロバイダー",
    )
    parser.add_argument(
        "-m", "--model", type=str, default=config.DEFAULT_MODEL,
        help="使用するモデル名",
    )

    args = parser.parse_args()
    main(model_name=args.model, provider=args.provider)


if __name__ == "__main__":
    cli()
