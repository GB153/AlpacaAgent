import os
import time

from dotenv import load_dotenv
from tavily import TavilyClient

from core.agent import configure_model
from core.runner import run_once
from integrations.alpaca.config import load_config
from schemas.deps import Deps

# model format is <provide_namer:model_name.
MODEL = "anthropic:claude-3-5-haiku-latest"


def main():
    load_dotenv()

    configure_model(MODEL, strict=True)

    deps = Deps(
        alpaca=load_config(),
        tavily=TavilyClient(api_key=os.environ["TAVILY_API_KEY"]),
        allow_trading=False,
    )

    base_prompt = "Scan recent news for SOL and give buy/sell/hold with sources."
    state_path = "state/state.json"

    try:
        while True:
            try:
                sleep_s = run_once(
                    deps,
                    base_prompt=base_prompt,
                    conf_threshold=0.75,
                    poll_sleep_seconds=30,
                    state_path=state_path,
                )
            except Exception as e:
                print("Loop error:", repr(e))
                sleep_s = 30

            time.sleep(max(int(sleep_s), 1))
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
