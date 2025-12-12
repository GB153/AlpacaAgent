from __future__ import annotations

from pydantic_ai.exceptions import UserError
from pydantic_ai.models import infer_model

from utils.logging import get_logger

log = get_logger(__name__)


def _normalize_spec(spec: str) -> str:
    spec = (spec or "").strip()
    if not spec:
        raise ValueError("Model spec is empty.")
    if ":" not in spec:
        raise ValueError(f"Invalid model spec '{spec}'. Expected '<provider>:<model>'.")
    provider, model = spec.split(":", 1)
    provider = provider.strip()
    model = model.strip()
    if not provider or not model:
        raise ValueError(f"Invalid model spec '{spec}'. Expected '<provider>:<model>'.")
    return f"{provider}:{model}"


def build_model(spec: str, *, strict: bool = True):
    """
    Build a PydanticAI model from an explicit format, e.g. "anthropic:claude-3-5-haiku-latest"
    """
    spec = _normalize_spec(spec)

    try:
        model = infer_model(spec)
        log.info("Built model from spec: %s", spec)
        return model
    except (UserError, ValueError, ImportError) as e:
        msg = f"Failed to build model '{spec}': {e}"
        if strict:
            raise ValueError(msg) from e
        log.warning(msg)
        return None
