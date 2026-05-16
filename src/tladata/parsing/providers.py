from __future__ import annotations

from typing import Any


def _parse_spec(model_spec: str) -> tuple[str, str]:
    if ":" in model_spec:
        provider, _, model = model_spec.partition(":")
        return provider.lower().strip(), model.strip()
    return "openai", model_spec.strip()


def create_llm(model_spec: str, api_key: str | None = None) -> Any:
    provider, model_name = _parse_spec(model_spec)

    if provider == "openai":
        return _make_openai(model_name, api_key)
    if provider == "ollama":
        return _make_ollama(model_name)
    if provider == "huggingface":
        return _make_huggingface(model_name, api_key)
    if provider == "anthropic":
        return _make_anthropic(model_name, api_key)

    raise ValueError(
        f"Unknown provider '{provider}'. Supported: openai, ollama, huggingface, anthropic"
    )


def _make_openai(model_name: str, api_key: str | None) -> Any:
    if not api_key:
        raise ValueError("OpenAI requires OPENAI_API_KEY")
    try:
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr
    except ImportError as e:
        raise ImportError("Install langchain-openai: pip install 'tladata[parsing]'") from e

    return ChatOpenAI(api_key=SecretStr(api_key), model=model_name, temperature=0)


def _make_ollama(model_name: str) -> Any:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as e:
        raise ImportError("Install langchain-ollama: pip install 'tladata[ollama]'") from e

    return ChatOllama(model=model_name, temperature=0)


def _make_anthropic(model_name: str, api_key: str | None) -> Any:
    if not api_key:
        raise ValueError("Anthropic requires ANTHROPIC_API_KEY")
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as e:
        raise ImportError("Install langchain-anthropic: pip install 'tladata[anthropic]'") from e

    return ChatAnthropic(api_key=api_key, model=model_name, temperature=0)


def _make_huggingface(model_name: str, api_key: str | None) -> Any:
    if not api_key:
        raise ValueError("HuggingFace requires HF_TOKEN")
    try:
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
    except ImportError as e:
        raise ImportError(
            "Install langchain-huggingface: pip install 'tladata[huggingface]'"
        ) from e

    endpoint = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=api_key,
        temperature=0,
    )
    return ChatHuggingFace(llm=endpoint)
