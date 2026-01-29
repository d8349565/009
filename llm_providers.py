"""
LLM提供商管理模块
支持多个LLM供应商：DeepSeek、智谱GLM、OpenRouter等
"""
from typing import Optional, Dict, Any
from openai import OpenAI
import os


class LLMProvider:
    """LLM提供商基类"""
    
    def __init__(self, api_key: str, base_url: str, default_model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
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
            request_kwargs: Dict[str, Any] = {
                "model": model or self.default_model,
                "messages": messages,
            }
            if temperature is not None:
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
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        super().__init__(api_key, base_url, "deepseek-chat")
        self.reasoner_model = "deepseek-reasoner"
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称"""
        return self.reasoner_model if use_reasoner else self.default_model


class ZhipuProvider(LLMProvider):
    """智谱AI (GLM)提供商"""
    
    def __init__(self, api_key: str):
        base_url = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        default_model = os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.7")  # 从环境变量读取，默认 glm-4.7
        super().__init__(api_key, base_url, default_model)
        self.advanced_model = os.getenv("ZHIPU_ADVANCED_MODEL", "glm-4-plus")  # 高级模型
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称（use_reasoner时使用plus版本）"""
        return self.advanced_model if use_reasoner else self.default_model


class OpenRouterProvider(LLMProvider):
    """OpenRouter提供商（聚合多个模型）"""
    
    def __init__(self, api_key: str):
        base_url = "https://openrouter.ai/api/v1"
        default_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "xiaomi/mimo-v2-flash:free")
        super().__init__(api_key, base_url, default_model)
    
    def get_model(self, use_reasoner: bool = False) -> str:
        """获取模型名称"""
        # OpenRouter支持多种模型，可以通过环境变量配置
        reasoner_model = os.getenv("OPENROUTER_REASONER_MODEL", "openai/o1-preview")
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
