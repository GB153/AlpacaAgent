# Agents Demo

A small, opinionated template for building an “agentic” crypto research + trading assistant:

- **Tavily**: web search tool for news/market context
- **Alpaca**: paper trading (account, assets, positions, orders)
- **PydanticAI**: enforces structured outputs (e.g., buy/sell/hold + confidence) and tool calling
- **State file**: minimal persistence so the “runner” can reconcile what happened after placing an order

This is intentionally minimal - feel free to fork or suggest PRs to add to existing codebase. This acts more as an experiment to let the model 'think' for itself and reason what to do next whilst providing the necessary tools to act on it. 

NOTE: To change the model use, navigate to core/agent.py where it will be listed below imports. It would be useful to
make this more compatible with other models, this demo only uses anthropic,

NOTE: To change level of logging, simply navigate to utils/logging.py and change to logging.INFO for all logs.

---

## Setup

- Python 3.11+
- `uv` (recommended) or `pip`
- make sure to run `uv sync` then run the main.py via the command `uv run python main.py`


- Or can just use Docker setup too to run via the command `docker compose up --build -d`
- To see docker logs in terminal (not just Docker dashboard) run `docker compose logs -f agent`

- NOTE: Need to create an env file that imitates the following pattern, be sure to get the corresponding keys
and secrets from corresponding sources:

  ```
  TAVILY_API_KEY=your_tavily_key_here
  ALPACA_KEY=your_alpaca_key_id_here
  APCA_API_SECRET_KEY=your_alpaca_secret_key_here
  ALPACA_URL=https://paper-api.alpaca.markets/v2
  ANTHROPIC_API_KEY= your_anthropic_key_here
  ```
