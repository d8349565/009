"""
LLM提供商管理模块
支持多个LLM供应商：DeepSeek、智谱GLM、OpenRouter等
"""
from typing import Optional, Dict, Any, List
from openai import OpenAI
import os

from runtime_config import load_runtime_config


def _provider_spec(provider_name: str) -> Dict[str, Any]:
    runtime = load_runtime_config()
    if not isinstance(runtime, dict):
        return {}
    providers = runtime.get("providers", {})
    if not isinstance(providers, dict):
        return {}
    spec = providers.get(provider_name, {})
    return spec if isinstance(spec, dict) else {}


class LLMProvider:
    """LLM提供商基类"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        capabilities: Optional[Dict[str, Any]] = None,
        model_overrides: Optional[List[Dict[str, Any]]] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.capabilities = capabilities if isinstance(capabilities, dict) else {}
        self.model_overrides = model_overrides if isinstance(model_overrides, list) else []

    def _effective_capabilities(self, model_name: str) -> Dict[str, Any]:
        effective = dict(self.capabilities or {})
        for ov in self.model_overrides:
            if not isinstance(ov, dict):
                continue
            prefix = ov.get("model_prefix")
            if prefix and isinstance(prefix, str) and model_name.startswith(prefix):
                caps = ov.get("capabilities")
                if isinstance(caps, dict):
                    effective.update(caps)
        return effective
    
    def call(self, 
             messages: list,
             model: Optional[str] = None,
             temperature: Optional[float] = 0.7,
             **kwargs) -> str:
        """
        调用LLM API
        
        Args:
            messages: 消息列表 [{"role": "system", "content": "..."}, ...]
            model: 模型名称（可选，默认使用default_model）
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            AI响应内容
        """
        try:
            model_to_use = model or self.default_model
            effective_caps = self._effective_capabilities(model_to_use)
            supports_temperature = bool(effective_caps.get("supports_temperature", True))

            request_kwargs: Dict[str, Any] = {
                "model": model_to_use,
                "messages": messages,
            }
            if temperature is not None and supports_temperature:
                request_kwargs["temperature"] = temperature
            if kwargs:
                request_kwargs.update(kwargs)
            response = self.client.chat.completions.create(
                **request_kwargs
            )
            
            content = response.choices[0].message.content
            
            # 处理思考模式（DeepSeek Reasoner）
            if hasattr(response.choices[0].message, 'reasoning_content'):
                reasoning = response.choices[0].message.reasoning_content
                if reasoning:
                    return content, reasoning  # 返回内容和推理过程
            
            return content
        except Exception as e:
            raise Exception(f"LLM API调用失败: {e}")


class DeepSeekProvider(LLMProvider):
    """DeepSeek提供商"""
    
    def __init__(self, api_key: str):
        spec = _provider_spec("deepseek")
        base_url = os.getenv(spec.get("base_url_env", "DEEPSEEK_BASE_URL"), "https://api.deepseek.com")
        default_model = spec.get("default_model", "deepseek-chat")
        self.reasoner_model = spec.get("reasoner_model", "deepseek-reasoner")
        super().__init__(
            api_key,
            base_url,
            default_model,
            capabilities=spec.get("capabilities"),
            model_overrides=spec.get("model_overrides"),
        )
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称"""
        return self.reasoner_model if use_reasoner else self.default_model


class ZhipuProvider(LLMProvider):
    """智谱AI (GLM)提供商"""
    
    def __init__(self, api_key: str):
        spec = _provider_spec("zhipu")
        base_url = os.getenv(spec.get("base_url_env", "ZHIPU_BASE_URL"), "https://open.bigmodel.cn/api/paas/v4")
        default_model_env = spec.get("default_model_env", "ZHIPU_DEFAULT_MODEL")
        reasoner_model_env = spec.get("reasoner_model_env", "ZHIPU_ADVANCED_MODEL")
        default_model = os.getenv(default_model_env, spec.get("default_model", "glm-4.7"))
        self.advanced_model = os.getenv(reasoner_model_env, spec.get("reasoner_model", "glm-4-plus"))
        super().__init__(
            api_key,
            base_url,
            default_model,
            capabilities=spec.get("capabilities"),
            model_overrides=spec.get("model_overrides"),
        )
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称（use_reasoner时使用plus版本）"""
        return self.advanced_model if use_reasoner else self.default_model


class OpenRouterProvider(LLMProvider):
    """OpenRouter提供商（聚合多个模型）"""
    
    def __init__(self, api_key: str):
        spec = _provider_spec("openrouter")
        base_url = spec.get("base_url") or "https://openrouter.ai/api/v1"
        default_model_env = spec.get("default_model_env", "OPENROUTER_DEFAULT_MODEL")
        default_model = os.getenv(default_model_env, "xiaomi/mimo-v2-flash:free")
        super().__init__(
            api_key,
            base_url,
            default_model,
            capabilities=spec.get("capabilities"),
            model_overrides=spec.get("model_overrides"),
        )
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称"""
        # OpenRouter支持多种模型，可以通过环境变量配置
        spec = _provider_spec("openrouter")
        reasoner_model_env = spec.get("reasoner_model_env", "OPENROUTER_REASONER_MODEL")
        reasoner_model = os.getenv(reasoner_model_env, "openai/o1-preview")
        return reasoner_model if use_reasoner else self.default_model


class LLMProviderManager:
    """LLM提供商管理器"""
    
    # 支持的提供商映射
    PROVIDERS = {
        "deepseek": DeepSeekProvider,
        "zhipu": ZhipuProvider,
        "glm": ZhipuProvider,  # 别名
        "openrouter": OpenRouterProvider,
    }
    
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._load_providers()
    
    def _load_providers(self):
        """加载所有配置的提供商"""
        # DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self._providers["deepseek"] = DeepSeekProvider(deepseek_key)
        
        # 智谱GLM
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key:
            provider = ZhipuProvider(zhipu_key)
            self._providers["zhipu"] = provider
            self._providers["glm"] = provider  # 添加别名
        
        # OpenRouter
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self._providers["openrouter"] = OpenRouterProvider(openrouter_key)
    
    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """
        获取指定的提供商
        
        Args:
            provider_name: 提供商名称 (deepseek/zhipu/glm/openrouter)
            
        Returns:
            LLMProvider实例，如果不存在返回None
        """
        provider = self._providers.get(provider_name.lower())
        if not provider:
            available = ", ".join(self._providers.keys())
            print(f"[警告] 提供商 '{provider_name}' 未配置，可用的提供商: {available}")
        return provider
    
    def get_available_providers(self) -> list:
        """获取所有可用的提供商列表"""
        return list(self._providers.keys())
    
    def call_llm(self,
                 provider_name: str,
                 messages: list,
                 model: Optional[str] = None,
                 use_reasoner: bool = False,
                 temperature: Optional[float] = 0.7,
                 **kwargs) -> str:
        """
        统一的LLM调用接口
        
        Args:
            provider_name: 提供商名称
            messages: 消息列表
            model: 模型名称（可选）
            use_reasoner: 是否使用推理模型
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            AI响应内容（或元组：(内容, 推理过程)）
        """
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"提供商 '{provider_name}' 不可用")
        
        # 如果没有指定模型，根据use_reasoner自动选择
        if not model:
            model = provider.get_model(use_reasoner)
        
        return provider.call(messages, model, temperature, **kwargs)


# 全局提供商管理器实例
_manager = None

def get_llm_manager() -> LLMProviderManager:
    """获取全局LLM管理器实例"""
    global _manager
    if _manager is None:
        _manager = LLMProviderManager()
    return _manager
