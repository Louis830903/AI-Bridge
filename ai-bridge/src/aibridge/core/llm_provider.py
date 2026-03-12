"""
LLM Provider - 共享 LLM 接口

支持外部智能体共享 LLM，避免重复配置。
"""

from typing import Protocol, Optional, Any, List, Dict
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    LLM 提供者抽象基类
    
    外部智能体可以实现这个接口，将 LLM 能力共享给 AI-Bridge。
    """
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """
        单次补全
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数（temperature, max_tokens 等）
        
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        对话模式
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数
        
        Returns:
            生成的回复
        """
        pass
    
    @abstractmethod
    async def vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """
        视觉理解
        
        Args:
            image_base64: base64 编码的图片
            prompt: 提示词
            **kwargs: 额外参数
        
        Returns:
            图片理解结果
        """
        pass


class OpenAILLMProvider(LLMProvider):
    """
    OpenAI LLM 提供者
    
    直接使用 OpenAI API。
    """
    
    def __init__(self, client=None, api_key: Optional[str] = None, **default_kwargs):
        """
        初始化
        
        Args:
            client: 已有的 OpenAI 客户端（优先使用）
            api_key: API 密钥（如果没有提供 client）
            **default_kwargs: 默认参数（model, temperature 等）
        """
        self.client = client
        self.api_key = api_key
        self.default_kwargs = default_kwargs
        
        if not self.client and not self.api_key:
            raise ValueError("需要提供 client 或 api_key")
    
    def _get_client(self):
        """获取或创建客户端"""
        if self.client:
            return self.client
        
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=self.api_key)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """单次补全"""
        client = self._get_client()
        
        # 合并参数
        params = {**self.default_kwargs, **kwargs}
        params["prompt"] = prompt
        
        try:
            response = await client.completions.create(**params)
            return response.choices[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式"""
        client = self._get_client()
        
        params = {**self.default_kwargs, **kwargs}
        params["messages"] = messages
        
        # 默认使用 chat 模型
        if "model" not in params:
            params["model"] = "gpt-3.5-turbo"
        
        try:
            response = await client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    async def vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """视觉理解"""
        client = self._get_client()
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        params = {**self.default_kwargs, **kwargs}
        params["messages"] = messages
        params["model"] = kwargs.get("model", "gpt-4o")
        
        try:
            response = await client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise


class AgentSharedLLM(LLMProvider):
    """
    智能体共享 LLM
    
    通过回调函数使用外部智能体的 LLM。
    """
    
    def __init__(self, callback):
        """
        初始化
        
        Args:
            callback: 回调函数，接收 (prompt, **kwargs) 返回 str
        """
        self.callback = callback
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """调用外部 LLM"""
        if asyncio.iscoroutinefunction(self.callback):
            return await self.callback(prompt, **kwargs)
        else:
            return self.callback(prompt, **kwargs)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话模式 - 转换为 prompt 调用"""
        # 将消息列表转换为 prompt
        prompt = self._messages_to_prompt(messages)
        return await self.complete(prompt, **kwargs)
    
    async def vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        """视觉理解 - 需要外部支持"""
        # 如果外部智能体支持视觉，可以扩展
        logger.warning("共享 LLM 不支持视觉，降级为文本")
        return await self.complete(f"[图片描述] {prompt}", **kwargs)
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """将消息列表转换为 prompt"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        return "\n".join(parts)


class NoOpLLMProvider(LLMProvider):
    """
    空 LLM 提供者
    
    当没有提供 LLM 时使用，所有调用返回空值。
    """
    
    async def complete(self, prompt: str, **kwargs) -> str:
        logger.debug("NoOp LLM: complete 被调用")
        return ""
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        logger.debug("NoOp LLM: chat 被调用")
        return ""
    
    async def vision(self, image_base64: str, prompt: str, **kwargs) -> str:
        logger.debug("NoOp LLM: vision 被调用")
        return ""


# ============ 便捷函数 ============

def create_llm_provider(
    provider_type: str = "shared",
    client=None,
    callback=None,
    api_key=None,
    **kwargs
) -> LLMProvider:
    """
    创建 LLM 提供者工厂函数
    
    Args:
        provider_type: 类型 ("openai", "shared", "noop")
        client: 已有的客户端（如 OpenAI client）
        callback: 共享回调函数
        api_key: API 密钥
        **kwargs: 其他参数
    
    Returns:
        LLMProvider 实例
    """
    if provider_type == "openai":
        return OpenAILLMProvider(client=client, api_key=api_key, **kwargs)
    
    elif provider_type == "shared" and callback:
        return AgentSharedLLM(callback)
    
    elif provider_type == "noop":
        return NoOpLLMProvider()
    
    else:
        raise ValueError(f"未知的 provider 类型: {provider_type}")


# ============ 使用示例 ============

async def demo_shared_llm():
    """
    演示：智能体共享 LLM 给 AI-Bridge
    """
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    # 1. 智能体统一管理 LLM
    my_llm_client = None  # 你的 LLM 客户端
    
    # 2. 创建共享 LLM 提供者
    async def my_llm_callback(prompt: str, **kwargs):
        """智能体的 LLM 调用"""
        # 这里调用你自己的 LLM
        print(f"[智能体 LLM] 处理: {prompt[:50]}...")
        return f"模拟回复: 我理解你的意图是..."
    
    shared_llm = AgentSharedLLM(my_llm_callback)
    
    # 3. 创建 AI-Bridge，注入共享 LLM
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 4. 创建意图引擎，使用共享 LLM
    from aibridge.core import IntentEngine
    intent_engine = IntentEngine(adapter, llm_provider=shared_llm)
    
    # 5. 现在意图解析会调用智能体的 LLM
    result = await intent_engine.parse("搜索 iPhone 15")
    print(f"结果: {result}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_shared_llm())
