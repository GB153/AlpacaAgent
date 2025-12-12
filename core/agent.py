from __future__ import annotations

from typing import Any, Literal

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

from core.routing import build_model
from integrations.alpaca.account import get_account as alpaca_get_account
from integrations.alpaca.assets import list_crypto_assets as alpaca_list_crypto_assets
from integrations.alpaca.orders import create_order as alpaca_create_order
from integrations.alpaca.positions import close_position as alpaca_close_position
from integrations.alpaca.positions import list_positions as alpaca_list_positions
from integrations.tavily.search import web_search as tavily_web_search
from schemas.deps import Deps
from schemas.output import AgentResult

agent = Agent(
    TestModel(),
    deps_type=Deps,
    output_type=AgentResult,
    instructions=(
        """You are a crypto research/trading assistant.
        - Use tools when you need facts (news/price/context, account/positions).
        - Always include real URLs in `sources` when you used `web_search`.
        - Always output `confidence` in [0,1].
        - Always set `next_action` and `sleep_seconds`.
        - If you propose a trade, populate `order`.
        - Only call `create_order` or `close_position` if allow_trading=True.
        - If confidence < 0.75, prefer next_action='wait' or 'noop' (no trade)."""
    ),
    retries=3,
)


def configure_model(model_spec: str, *, strict: bool = True):
    """
    Call from main.py at runtime.
    """
    model = build_model(model_spec, strict=strict)
    if model is not None:
        agent.model = model
    return agent.model


@agent.tool
def web_search(
    ctx: RunContext[Deps],
    query: str,
    topic: Literal["general", "news", "finance"] = "news",
    days: int = 7,
    max_results: int = 5,
) -> dict[str, Any]:
    return tavily_web_search(
        ctx.deps.tavily,
        query=query,
        topic=topic,
        days=days,
        max_results=max_results,
    )


@agent.tool
def get_account(ctx: RunContext[Deps]) -> dict[str, Any]:
    acct = alpaca_get_account(ctx.deps.alpaca)
    return acct.model_dump()


@agent.tool
def get_crypto_assets(ctx: RunContext[Deps]) -> list[dict[str, Any]]:
    return alpaca_list_crypto_assets(ctx.deps.alpaca)


@agent.tool
def get_positions(ctx: RunContext[Deps]) -> dict[str, Any]:
    positions = alpaca_list_positions(ctx.deps.alpaca)
    return {"positions": [p.model_dump() for p in positions]}


@agent.tool
def create_order(
    ctx: RunContext[Deps],
    symbol: str,
    notional: float,
    side: Literal["buy", "sell"],
    time_in_force: Literal["gtc", "ioc"] = "ioc",
) -> dict[str, Any]:
    if not ctx.deps.allow_trading:
        return {"ok": False, "reason": "Trading disabled (allow_trading=False)."}

    result = alpaca_create_order(
        ctx.deps.alpaca,
        symbol=symbol,
        notional=notional,
        side=side,
        time_in_force=time_in_force,
        order_type="market",
    )
    return {"ok": True, "order": result}


@agent.tool
def close_position(
    ctx: RunContext[Deps],
    symbol_or_asset_id: str,
    qty: float | None = None,
    percentage: float | None = None,
) -> dict[str, Any]:
    if not ctx.deps.allow_trading:
        return {"ok": False, "reason": "Trading disabled (allow_trading=False)."}

    order = alpaca_close_position(
        ctx.deps.alpaca,
        symbol_or_asset_id=symbol_or_asset_id,
        qty=qty,
        percentage=percentage,
    )
    return {"ok": True, "order": order.model_dump()}
