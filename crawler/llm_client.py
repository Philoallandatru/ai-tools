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

    def __init__(self, base_url: str = "http://127.0.0.1:1234", model: str = "qwen3.5-0.8b"):
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
        try:
            response = requests.post(
                f"{self.base_url}/v1/completions",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['text'].strip()

        except requests.RequestException as e:
            raise RuntimeError(f"LLMStudio API 调用失败: {e}")


def create_llm_client(provider: str = "mock", **kwargs) -> BaseLLMClient:
    """
    工厂函数：创建 LLM 客户端

    Args:
        provider: 提供商类型 ("mock" 或 "llmstudio")
        **kwargs: 传递给客户端的额外参数

    Returns:
        LLM 客户端实例
    """
    if provider == "mock":
        return MockLLMClient()
    elif provider == "llmstudio":
        return LLMStudioClient(**kwargs)
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
