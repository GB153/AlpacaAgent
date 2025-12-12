import os
import time

from tavily import TavilyClient

from core.agent import configure_model
from core.runner import run_once
from integrations.alpaca.config import load_config
from schemas.deps import Deps

# model
MODEL = "anthropic:claude-3-5-haiku-latest"

# sqllite db
DB_PATH = "state/state.db"

# example identifer
STATE_KEY = "sol-agent"

# prompt - change to BTC, ETH or crypto of choice (as long as alpaca supports)
BASE_PROMPT = "Scan recent news for SOL and give buy/sell/hold with sources."


def main():
    configure_model(MODEL, strict=True)

    tavily_key = os.environ["TAVILY_API_KEY"]

    deps = Deps(
        alpaca=load_config(),
        tavily=TavilyClient(api_key=tavily_key),
        allow_trading=False,
    )

    try:
        while True:
            try:
                sleep_s = run_once(
                    deps,
                    base_prompt=BASE_PROMPT,
                    conf_threshold=0.75,
                    poll_sleep_seconds=30,
                    db_path=DB_PATH,
                    state_key=STATE_KEY,
                )
            except Exception as e:
                print("Loop error:", repr(e))
                sleep_s = 30

            time.sleep(max(int(sleep_s), 1))
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
