"""LLM provider abstraction and runtime-config-driven provider loading."""

from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from runtime_config import load_runtime_config


DEFAULT_PROVIDER_SPECS: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "type": "openai_compatible",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "reasoner_model": "deepseek-reasoner",
        "capabilities": {"supports_temperature": True},
    },
    "zhipu": {
        "type": "openai_compatible",
        "api_key_env": "ZHIPU_API_KEY",
        "base_url_env": "ZHIPU_BASE_URL",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model_env": "ZHIPU_DEFAULT_MODEL",
        "reasoner_model_env": "ZHIPU_ADVANCED_MODEL",
        "default_model": "glm-4.7",
        "reasoner_model": "glm-4-plus",
        "aliases": ["glm"],
        "capabilities": {"supports_temperature": True},
    },
    "openrouter": {
        "type": "openai_compatible",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model_env": "OPENROUTER_DEFAULT_MODEL",
        "reasoner_model_env": "OPENROUTER_REASONER_MODEL",
        "default_model": "xiaomi/mimo-v2-flash:free",
        "reasoner_model": "openai/o1-preview",
        "capabilities": {"supports_temperature": True},
    },
    "qwen": {
        "type": "openai_compatible",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model_env": "QWEN_DEFAULT_MODEL",
        "reasoner_model_env": "QWEN_REASONER_MODEL",
        "default_model": "qwen-plus",
        "reasoner_model": "qwq-plus",
        "aliases": ["dashscope"],
        "capabilities": {"supports_temperature": True},
    },
}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_provider_specs() -> Dict[str, Dict[str, Any]]:
    runtime = load_runtime_config()
    runtime_providers = runtime.get("providers", {}) if isinstance(runtime, dict) else {}
    runtime_providers = runtime_providers if isinstance(runtime_providers, dict) else {}

    merged_specs = deepcopy(DEFAULT_PROVIDER_SPECS)
    for provider_name, provider_spec in runtime_providers.items():
        if not isinstance(provider_spec, dict):
            continue
        merged_specs[provider_name] = _deep_merge_dict(
            merged_specs.get(provider_name, {}), provider_spec
        )
    return merged_specs


def _resolve_model(spec: Dict[str, Any], env_key_name: str, direct_key_name: str, fallback: str = "") -> str:
    model_env = spec.get(env_key_name)
    if isinstance(model_env, str) and model_env.strip():
        env_value = os.getenv(model_env.strip(), "").strip()
        if env_value:
            return env_value
    direct_value = spec.get(direct_key_name)
    if isinstance(direct_value, str) and direct_value.strip():
        return direct_value.strip()
    return fallback


@dataclass
class LLMResult:
    content: str
    reasoning: Optional[str] = None
    model: str = ""


class LLMProvider:
    """Base provider contract."""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        default_model: str,
        reasoner_model: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        model_overrides: Optional[List[Dict[str, Any]]] = None,
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self.reasoner_model = reasoner_model or default_model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.capabilities = capabilities if isinstance(capabilities, dict) else {}
        self.model_overrides = model_overrides if isinstance(model_overrides, list) else []

    def get_model(self, use_reasoner: bool = False) -> str:
        return self.reasoner_model if use_reasoner else self.default_model

    def _effective_capabilities(self, model_name: str) -> Dict[str, Any]:
        effective = dict(self.capabilities or {})
        for override in self.model_overrides:
            if not isinstance(override, dict):
                continue
            prefix = override.get("model_prefix")
            if isinstance(prefix, str) and prefix and model_name.startswith(prefix):
                caps = override.get("capabilities")
                if isinstance(caps, dict):
                    effective.update(caps)
        return effective

    def call(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = 0.7,
        **kwargs: Any,
    ) -> LLMResult:
        try:
            model_to_use = model or self.default_model
            effective_caps = self._effective_capabilities(model_to_use)
            supports_temperature = bool(effective_caps.get("supports_temperature", True))

            request_kwargs: Dict[str, Any] = {"model": model_to_use, "messages": messages}
            if temperature is not None and supports_temperature:
                request_kwargs["temperature"] = temperature
            if kwargs:
                request_kwargs.update(kwargs)

            response = self.client.chat.completions.create(**request_kwargs)
            message = response.choices[0].message
            content = message.content or ""
            reasoning = getattr(message, "reasoning_content", None)
            if isinstance(reasoning, str):
                reasoning = reasoning.strip() or None

            return LLMResult(content=content, reasoning=reasoning, model=model_to_use)
        except Exception as e:
            raise RuntimeError(f"LLM API call failed ({self.name}/{model or self.default_model}): {e}") from e


class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for OpenAI-compatible endpoints."""

    def __init__(self, provider_name: str, api_key: str, spec: Dict[str, Any]):
        base_url = ""
        base_url_env = spec.get("base_url_env")
        if isinstance(base_url_env, str) and base_url_env.strip():
            base_url = os.getenv(base_url_env.strip(), "").strip()
        if not base_url:
            base_url = (spec.get("base_url") or "").strip()

        default_model = _resolve_model(
            spec,
            env_key_name="default_model_env",
            direct_key_name="default_model",
            fallback="",
        )
        reasoner_model = _resolve_model(
            spec,
            env_key_name="reasoner_model_env",
            direct_key_name="reasoner_model",
            fallback=default_model,
        )

        if not base_url:
            raise ValueError(f"Provider '{provider_name}' missing base_url/base_url_env")
        if not default_model:
            raise ValueError(f"Provider '{provider_name}' missing default_model/default_model_env")

        super().__init__(
            name=provider_name,
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            reasoner_model=reasoner_model,
            capabilities=spec.get("capabilities"),
            model_overrides=spec.get("model_overrides"),
        )


class LLMProviderManager:
    """Runtime provider manager."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_specs: Dict[str, Dict[str, Any]] = _load_provider_specs()
        self._load_providers()

    def _register_aliases(self, provider: LLMProvider, spec: Dict[str, Any]):
        aliases = spec.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []
        for alias in aliases:
            if isinstance(alias, str) and alias.strip():
                self._providers[alias.strip().lower()] = provider

    def _load_providers(self):
        for provider_name, spec in self._provider_specs.items():
            if not isinstance(spec, dict):
                continue
            provider_type = (spec.get("type") or "openai_compatible").strip().lower()
            if provider_type != "openai_compatible":
                print(f"[warning] Unsupported provider type '{provider_type}' for '{provider_name}', skipped")
                continue

            api_key_env = (spec.get("api_key_env") or f"{provider_name.upper()}_API_KEY").strip()
            api_key = os.getenv(api_key_env, "").strip()
            if not api_key:
                continue

            try:
                provider = OpenAICompatibleProvider(provider_name=provider_name, api_key=api_key, spec=spec)
                self._providers[provider_name.lower()] = provider
                self._register_aliases(provider, spec)
            except Exception as e:
                print(f"[warning] Failed to initialize provider '{provider_name}': {e}")

    def has_provider(self, provider_name: str) -> bool:
        return provider_name.strip().lower() in self._providers if provider_name else False

    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        normalized = provider_name.lower() if isinstance(provider_name, str) else ""
        provider = self._providers.get(normalized)
        if not provider:
            available = ", ".join(self.get_available_providers())
            print(f"[warning] Provider '{provider_name}' is not available. Available: {available}")
        return provider

    def get_available_providers(self) -> List[str]:
        return sorted(self._providers.keys())

    def call_llm(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        use_reasoner: bool = False,
        temperature: Optional[float] = 0.7,
        **kwargs: Any,
    ) -> LLMResult:
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' is not available")

        if not model:
            model = provider.get_model(use_reasoner)
        return provider.call(messages=messages, model=model, temperature=temperature, **kwargs)


_manager: Optional[LLMProviderManager] = None


def get_llm_manager() -> LLMProviderManager:
    global _manager
    if _manager is None:
        _manager = LLMProviderManager()
    return _manager


def reset_llm_manager() -> None:
    """重置LLM管理器单例，使其在下次调用时重新从配置加载。"""
    global _manager
    _manager = None
