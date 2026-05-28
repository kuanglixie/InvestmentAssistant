from __future__ import annotations

from typing import Any


def create_chat_model(task: str, **kwargs: Any) -> Any:
    """Create an OpenAI chat model through LangChain when dependencies are installed."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "langchain-openai is not installed. Install project dependencies before using LLM-backed agents."
        ) from exc

    temperature = kwargs.pop("temperature", 0)
    model = kwargs.pop("model", "gpt-4.1-mini")
    return ChatOpenAI(model=model, temperature=temperature, metadata={"task": task}, **kwargs)

