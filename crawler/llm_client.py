"""
LLM 客户端模块 - 支持 Mock 和真实 LLM
"""

import requests
from typing import Optional
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本
        """
        pass

    def generate_with_messages(self, messages: list, max_tokens: int = 2000) -> str:
        """
        使用消息列表生成文本（支持 vision API）

        Args:
            messages: 消息列表（OpenAI 格式）
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本
        """
        # 默认实现：提取文本内容并调用 generate
        text_parts = []
        for msg in messages:
            if isinstance(msg.get('content'), str):
                text_parts.append(msg['content'])
            elif isinstance(msg.get('content'), list):
                for item in msg['content']:
                    if item.get('type') == 'text':
                        text_parts.append(item['text'])

        prompt = '\n'.join(text_parts)
        return self.generate(prompt, max_tokens)


class MockLLMClient(BaseLLMClient):
    """Mock LLM 客户端 - 用于测试"""

    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        返回 Mock 响应

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数

        Returns:
            Mock 响应文本
        """
        # 根据提示词关键字返回不同的 mock 响应
        if "根因分析" in prompt or "root cause" in prompt.lower():
            return """根因分析：
1. 直接原因：NVMe Reset 期间状态机未正确处理 CC.EN 清零
2. 深层原因：固件未实现 CSTS.RDY 等待机制
3. 触发条件：在 Sanitize Block Erase 期间下发 NVM Reset"""

        elif "行动建议" in prompt or "recommendation" in prompt.lower():
            return """行动建议：
1. 短期：添加 CC.EN 清零后的 CSTS.RDY 轮询机制
2. 中期：完善 Reset 状态机的异常处理
3. 长期：建立 Reset 场景的自动化测试"""

        elif "类似" in prompt or "similar" in prompt.lower():
            return """找到 2 个类似问题：
1. KAN-6: APST 唤醒时 PCIe 链路重训失败
2. KAN-8: Format NVM 期间 SPOR 导致映射表重建失败"""

        elif "闭环" in prompt or "closed loop" in prompt.lower():
            return """闭环检查：
- 根因已识别：✓
- 修复方案已实施：✓
- 验证测试已通过：✓
- 结论：已闭环"""

        elif "comment" in prompt.lower() or "评论" in prompt:
            return """评论分析：
1. 时间线：问题发现 → 根因定位 → 修复验证，历时 3 天
2. 关键决策：采用轮询机制而非中断方式
3. 合理性：决策合理，符合 NVMe 规范要求"""

        else:
            return f"Mock LLM 响应 (prompt 长度: {len(prompt)} 字符)"


class LLMStudioClient(BaseLLMClient):
    """LLMStudio 客户端 - 连接本地 LLM 服务"""

    def __init__(self, base_url: str = "http://127.0.0.1:1234", model: str = "qwen3.5-4b"):
        """
        初始化 LLMStudio 客户端

        Args:
            base_url: LLMStudio 服务地址
            model: 模型名称
        """
        self.base_url = base_url.rstrip('/')
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        调用 LLMStudio API 生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本

        Raises:
            requests.RequestException: API 调用失败
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_with_messages(messages, max_tokens)

    def generate_with_messages(self, messages: list, max_tokens: int = 2000) -> str:
        """
        使用消息列表生成文本（支持 vision API）

        Args:
            messages: 消息列表（OpenAI 格式）
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本

        Raises:
            requests.RequestException: API 调用失败
        """
        try:
            # 尝试使用 chat completions API
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=120  # 增加到 120 秒
            )
            response.raise_for_status()
            response.encoding = 'utf-8'  # 确保响应使用 UTF-8 解码

            result = response.json()
            return result['choices'][0]['message']['content'].strip()

        except requests.HTTPError as e:
            # 如果 chat completions 失败，尝试 completions API（仅支持文本）
            if e.response.status_code == 404:
                # 提取文本内容
                text_parts = []
                for msg in messages:
                    if isinstance(msg.get('content'), str):
                        text_parts.append(msg['content'])
                    elif isinstance(msg.get('content'), list):
                        for item in msg['content']:
                            if item.get('type') == 'text':
                                text_parts.append(item['text'])

                prompt = '\n'.join(text_parts)

                try:
                    response = requests.post(
                        f"{self.base_url}/v1/completions",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "max_tokens": max_tokens,
                            "temperature": 0.7
                        },
                        headers={"Content-Type": "application/json; charset=utf-8"},
                        timeout=120
                    )
                    response.raise_for_status()
                    response.encoding = 'utf-8'

                    result = response.json()
                    return result['choices'][0]['text'].strip()
                except requests.RequestException as fallback_error:
                    raise RuntimeError(f"LLMStudio API 调用失败 (两种端点都失败): {fallback_error}")
            else:
                raise RuntimeError(f"LLMStudio API 调用失败: {e}")
        except requests.Timeout:
            raise RuntimeError(f"LLMStudio API 调用超时（120秒）")
        except requests.RequestException as e:
            raise RuntimeError(f"LLMStudio API 调用失败: {e}")


class LLMClientFactory:
    """LLM 客户端工厂类 - 集中管理客户端创建逻辑"""

    @staticmethod
    def create_from_config(config: dict) -> BaseLLMClient:
        """
        从配置字典创建 LLM 客户端

        Args:
            config: 配置字典，包含以下字段：
                - provider: str - 提供商类型 ("mock" 或 "llmstudio")
                - base_url: str - LLMStudio 服务地址（仅 llmstudio 需要）
                - model: str - 模型名称（仅 llmstudio 需要）
                - max_tokens: int - 最大 token 数（可选）
                - temperature: float - 温度参数（可选）

        Returns:
            BaseLLMClient: LLM 客户端实例

        Raises:
            ValueError: 不支持的提供商或配置缺失必需字段

        Example:
            >>> config = {
            ...     'provider': 'llmstudio',
            ...     'base_url': 'http://127.0.0.1:1234',
            ...     'model': 'qwen3.5-4b'
            ... }
            >>> client = LLMClientFactory.create_from_config(config)
        """
        provider = config.get('provider', 'mock')

        if provider == 'mock':
            return MockLLMClient()

        elif provider == 'llmstudio':
            # 验证必需字段
            base_url = config.get('base_url')
            model = config.get('model')

            if not base_url:
                raise ValueError("llmstudio provider requires 'base_url' in config")
            if not model:
                raise ValueError("llmstudio provider requires 'model' in config")

            return LLMStudioClient(base_url=base_url, model=model)

        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    @staticmethod
    def create(provider: str = "mock", **kwargs) -> BaseLLMClient:
        """
        直接创建 LLM 客户端（向后兼容）

        Args:
            provider: 提供商类型 ("mock" 或 "llmstudio")
            **kwargs: 传递给客户端的额外参数

        Returns:
            BaseLLMClient: LLM 客户端实例
        """
        if provider == "mock":
            return MockLLMClient()
        elif provider == "llmstudio":
            return LLMStudioClient(**kwargs)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")


def create_llm_client(provider: str = "mock", **kwargs) -> BaseLLMClient:
    """
    工厂函数：创建 LLM 客户端（向后兼容，推荐使用 LLMClientFactory）

    Args:
        provider: 提供商类型 ("mock" 或 "llmstudio")
        **kwargs: 传递给客户端的额外参数

    Returns:
        LLM 客户端实例

    Deprecated:
        使用 LLMClientFactory.create() 或 LLMClientFactory.create_from_config() 代替
    """
    return LLMClientFactory.create(provider, **kwargs)
