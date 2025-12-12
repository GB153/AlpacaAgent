from __future__ import annotations

import sys
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.test import TestModel

# schemas deps
mock_schemas_deps = MagicMock()


class MockDeps:
    def __init__(self, tavily, alpaca, allow_trading=True):
        self.tavily = tavily
        self.alpaca = alpaca
        self.allow_trading = allow_trading


mock_schemas_deps.Deps = MockDeps
sys.modules["schemas.deps"] = mock_schemas_deps

# schemas output
mock_schemas_output = MagicMock()


class AgentResult(BaseModel):
    message: str


mock_schemas_output.AgentResult = AgentResult
sys.modules["schemas.output"] = mock_schemas_output

# integrations
sys.modules["integrations"] = MagicMock()
sys.modules["integrations.alpaca"] = MagicMock()
sys.modules["integrations.tavily"] = MagicMock()
sys.modules["integrations.alpaca.account"] = MagicMock()
sys.modules["integrations.alpaca.assets"] = MagicMock()
sys.modules["integrations.alpaca.orders"] = MagicMock()
sys.modules["integrations.alpaca.positions"] = MagicMock()
sys.modules["integrations.tavily.search"] = MagicMock()

# core.routing
mock_routing = MagicMock()
mock_routing.build_model.return_value = TestModel()
sys.modules["core.routing"] = mock_routing


from core.agent import agent


def _tool_then_done(first: ModelResponse) -> Callable[..., object]:
    calls = {"n": 0}

    def side_effect(*args, **kwargs) -> object:
        calls["n"] += 1
        if calls["n"] == 1:
            return first
        return ModelResponse(parts=[TextPart('{"message": "Done"}')])

    return side_effect


@pytest.fixture
def mock_deps(mocker):
    mock_tavily_client = mocker.Mock(name="tavily_client")
    mock_alpaca_client = mocker.Mock(name="alpaca_client")
    return MockDeps(
        tavily=mock_tavily_client, alpaca=mock_alpaca_client, allow_trading=True
    )


def test_web_search_tool_happy_path(mocker, mock_deps):
    mock_tavily_search = mocker.patch("core.agent.tavily_web_search")
    mock_tavily_search.return_value = {"results": ["news1", "news2"]}

    agent.model = TestModel()
    agent.model.request = AsyncMock()
    first = ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="web_search",
                args={
                    "query": "What is the latest crypto news?",
                    "topic": "news",
                    "days": 7,
                },
            )
        ]
    )
    agent.model.request.side_effect = _tool_then_done(first)

    agent.run_sync("What is the latest crypto news?", deps=mock_deps)

    mock_tavily_search.assert_called_once()
    call_args = mock_tavily_search.call_args
    assert call_args.kwargs["query"] == "What is the latest crypto news?"
    assert call_args.kwargs["days"] == 7
    assert call_args.kwargs["topic"] == "news"


def test_get_account_formatting(mocker, mock_deps):
    mock_get_account = mocker.patch("core.agent.alpaca_get_account")

    mock_account_obj = mocker.Mock()
    mock_account_obj.model_dump.return_value = {"id": "123", "cash": "1000.00"}
    mock_get_account.return_value = mock_account_obj

    agent.model = TestModel(call_tools=["get_account"])
    agent.run_sync("Check my account", deps=mock_deps)

    mock_get_account.assert_called_once_with(mock_deps.alpaca)
    mock_account_obj.model_dump.assert_called_once()


def test_create_order_happy_path(mocker, mock_deps):
    mock_create_order = mocker.patch("core.agent.alpaca_create_order")
    mock_create_order.return_value = {"id": "order_123", "status": "filled"}

    mock_deps.allow_trading = True

    agent.model = TestModel()
    agent.model.request = AsyncMock()
    first = ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="create_order",
                args={"symbol": "BTC/USD", "notional": 100, "side": "buy"},
            )
        ]
    )
    agent.model.request.side_effect = _tool_then_done(first)

    agent.run_sync("Buy $100 BTC", deps=mock_deps)

    mock_create_order.assert_called_once()
    assert mock_create_order.call_args.kwargs["symbol"] == "BTC/USD"
    assert mock_create_order.call_args.kwargs["notional"] == 100
    assert mock_create_order.call_args.kwargs["side"] == "buy"


def test_create_order_trading_disabled(mocker, mock_deps):
    mock_create_order = mocker.patch("core.agent.alpaca_create_order")
    mock_deps.allow_trading = False

    agent.model = TestModel()
    agent.model.request = AsyncMock()
    first = ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="create_order",
                args={"symbol": "ETH/USD", "notional": 50, "side": "sell"},
            )
        ]
    )
    agent.model.request.side_effect = _tool_then_done(first)

    agent.run_sync("Sell ETH", deps=mock_deps)

    mock_create_order.assert_not_called()

    second_call_args = agent.model.request.call_args_list[1]
    messages = second_call_args[0][0]
    last_msg = messages[-1]
    assert isinstance(last_msg, ModelRequest)

    tool_return = next(p for p in last_msg.parts if isinstance(p, ToolReturnPart))
    assert tool_return.content["ok"] is False
    assert "Trading disabled" in tool_return.content["reason"]


def test_upstream_api_failure_handling(mocker, mock_deps):
    mock_list_positions = mocker.patch("core.agent.alpaca_list_positions")
    mock_list_positions.side_effect = RuntimeError("Alpaca API Down")

    agent.model = TestModel(call_tools=["get_positions"])

    with pytest.raises(RuntimeError, match="Alpaca API Down"):
        agent.run_sync("Show my positions", deps=mock_deps)


def test_close_position_logic(mocker, mock_deps):
    mock_close = mocker.patch("core.agent.alpaca_close_position")
    mock_close.return_value.model_dump.return_value = {"status": "closed"}

    agent.model = TestModel()
    agent.model.request = AsyncMock()
    first = ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="close_position",
                args={"symbol_or_asset_id": "BTC", "percentage": 0.5},
            )
        ]
    )
    agent.model.request.side_effect = _tool_then_done(first)

    agent.run_sync("Close half my BTC", deps=mock_deps)

    mock_close.assert_called_once()
    assert mock_close.call_args.kwargs["symbol_or_asset_id"] == "BTC"
    assert mock_close.call_args.kwargs["percentage"] == 0.5
