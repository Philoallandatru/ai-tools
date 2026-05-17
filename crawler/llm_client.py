"""
LLM 客户端模块 - 支持 Mock 和真实 LLM
"""

import requests
from typing import Optional
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0.0-1.0），控制生成的随机性

        Returns:
            生成的文本
        """
        pass

    def generate_with_messages(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        使用消息列表生成文本（支持 vision API）

        Args:
            messages: 消息列表（OpenAI 格式）
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0.0-1.0），控制生成的随机性

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
        return self.generate(prompt, max_tokens, temperature)


class MockLLMClient(BaseLLMClient):
    """Mock LLM 客户端 - 用于测试"""

    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        返回 Mock 响应

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数（忽略）

        Returns:
            Mock 响应文本
        """
        # 优先匹配 JSON 提取（问题摘要）
        if ("提取" in prompt or "extract" in prompt.lower()) and ("json" in prompt.lower() or "客户名称" in prompt):
            # 问题摘要提取
            return """```json
{
  "customer": "Micron",
  "test_project": "SSD1250, Sanitize",
  "test_platform": "Platform: AMD Ryzen 7000 Series, OS: Ubuntu 22.04 LTS, Form Factor: M.2 2280",
  "test_steps": [
    "发起 Sanitize (Block Erase) 操作",
    "轮询 Sanitize Status，在进度 30%-50% 期间触发 NVM Reset",
    "等待设备重新枚举并 Ready",
    "尝试进行 4K Random Write"
  ],
  "root_cause": "固件未实现 CSTS.RDY 等待机制",
  "fix_solution": "在 Sanitize Block Erase 阶段检测到 NVM Reset 时，先完成当前 block 的 erase，再进入 reset handler"
}
```"""

        # 根据提示词关键字返回不同的 mock 响应
        elif "根因分析" in prompt or "root cause" in prompt.lower():
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


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible API 客户端 - 支持本地 LLM 服务（Ollama, LM Studio, vLLM, LocalAI 等）和 OpenAI API"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        model: str = "qwen3.5-4b",
        timeout: int = 120,
    ):
        """
        初始化 OpenAI-compatible 客户端

        Args:
            base_url: API 服务地址（应包含 API 版本路径，如 http://127.0.0.1:1234/v1）
            model: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        调用 OpenAI-compatible API 生成文本

        Args:
            prompt: 输入提示词
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0.0-1.0），控制生成的随机性

        Returns:
            生成的文本

        Raises:
            requests.RequestException: API 调用失败
        """
        messages = [{"role": "user", "content": prompt}]
        return self.generate_with_messages(messages, max_tokens, temperature)

    def generate_with_messages(self, messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        """
        使用消息列表生成文本（支持 vision API）

        Args:
            messages: 消息列表（OpenAI 格式）
            max_tokens: 最大生成 token 数
            temperature: 温度参数（0.0-1.0），控制生成的随机性

        Returns:
            生成的文本

        Raises:
            requests.RequestException: API 调用失败
        """
        try:
            # 尝试使用 chat completions API
            # 构建请求参数
            request_data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # 对于支持推理模式的模型（如 Qwen），尝试禁用推理模式
            # 方法1: 设置 reasoning_effort 为 none
            # 方法2: 在 system prompt 中明确要求不要输出思考过程
            if "qwen" in self.model.lower():
                # 尝试添加系统提示，要求直接输出答案
                if messages and messages[0].get("role") != "system":
                    messages.insert(0, {
                        "role": "system",
                        "content": "直接输出最终答案，不要包含思考过程、推理步骤或分析过程。"
                    })
                elif messages and messages[0].get("role") == "system":
                    # 如果已有系统提示，追加要求
                    messages[0]["content"] += "\n\n重要：直接输出最终答案，不要包含思考过程、推理步骤或分析过程。"

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=request_data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=self.timeout
            )

            # 如果是400错误，打印详细信息
            if response.status_code == 400:
                print(f"[ERROR] 400 Bad Request")
                print(f"[ERROR] Request data: {request_data}")
                print(f"[ERROR] Response: {response.text}")

            response.raise_for_status()
            response.encoding = 'utf-8'  # 确保响应使用 UTF-8 解码

            result = response.json()

            # 调试：打印响应结构
            if not result.get('choices') or len(result['choices']) == 0:
                print(f"[DEBUG] LLM 响应格式异常: {result}")
                return ""

            message = result['choices'][0]['message']

            # 处理不同的响应格式
            content = message.get('content', '').strip()
            reasoning_content = message.get('reasoning_content', '').strip()

            # 优先使用 content（最终答案）
            if content:
                return content

            # 如果只有 reasoning_content，临时使用它但记录警告
            # TODO: 在 LM Studio 中禁用推理模式是更好的解决方案
            if reasoning_content:
                print(f"[WARNING] 模型返回了 reasoning_content 但没有 content")
                print(f"[WARNING] 这通常意味着模型处于推理模式")
                print(f"[WARNING] 建议在 LM Studio 的模型设置中禁用推理模式")
                print(f"[WARNING] 临时使用 reasoning_content 作为回退")
                return reasoning_content

            # 两者都为空
            print(f"[DEBUG] LLM 返回空内容，完整响应: {result}")
            return ""

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
                        f"{self.base_url}/completions",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "max_tokens": max_tokens,
                            "temperature": 0.7
                        },
                        headers={"Content-Type": "application/json; charset=utf-8"},
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    response.encoding = 'utf-8'

                    result = response.json()

                    # 调试：打印响应结构
                    if not result.get('choices') or len(result['choices']) == 0:
                        print(f"[DEBUG] Completions API 响应格式异常: {result}")
                        return ""

                    text = result['choices'][0]['text']
                    if not text or len(text.strip()) == 0:
                        print(f"[DEBUG] Completions API 返回空内容，完整响应: {result}")

                    return text.strip()
                except requests.RequestException as fallback_error:
                    raise RuntimeError(f"OpenAI API 调用失败 (两种端点都失败): {fallback_error}")
            else:
                raise RuntimeError(f"OpenAI API 调用失败: {e}")
        except requests.Timeout:
            raise RuntimeError(f"OpenAI API 调用超时（{self.timeout}秒）")
        except requests.RequestException as e:
            raise RuntimeError(f"OpenAI API 调用失败: {e}")


class LLMClientFactory:
    """LLM 客户端工厂类 - 集中管理客户端创建逻辑"""

    OPENAI_COMPATIBLE_PROVIDERS = {
        'openai',
        'llmstudio',
        'lmstudio',
        'ollama',
        'vllm',
        'localai',
        'llamacpp',
    }

    @staticmethod
    def create_from_config(config: dict) -> BaseLLMClient:
        """
        从配置字典创建 LLM 客户端

        Args:
            config: 配置字典，包含以下字段：
                - provider: str - 提供商类型 ("mock" 或 "openai")
                - base_url: str - API 服务地址（仅 openai 需要）
                - model: str - 模型名称（仅 openai 需要）
                - max_tokens: int - 最大 token 数（可选）
                - temperature: float - 温度参数（可选）

        Returns:
            BaseLLMClient: LLM 客户端实例

        Raises:
            ValueError: 不支持的提供商或配置缺失必需字段

        Example:
            >>> config = {
            ...     'provider': 'openai',
            ...     'base_url': 'http://127.0.0.1:1234/v1',
            ...     'model': 'qwen3.5-4b'
            ... }
            >>> client = LLMClientFactory.create_from_config(config)
        """
        provider = config.get('provider', 'mock').lower()

        if provider == 'mock':
            return MockLLMClient()

        elif provider in LLMClientFactory.OPENAI_COMPATIBLE_PROVIDERS:
            # 验证必需字段
            base_url = config.get('base_url')
            model = config.get('model')
            timeout = config.get('timeout', 120)

            if not base_url:
                raise ValueError(f"{provider} provider requires 'base_url' in config")
            if not model:
                raise ValueError(f"{provider} provider requires 'model' in config")

            if provider in {'llmstudio', 'lmstudio', 'llamacpp'} and not base_url.rstrip('/').endswith('/v1'):
                base_url = f"{base_url.rstrip('/')}/v1"

            return OpenAIClient(base_url=base_url, model=model, timeout=timeout)

        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")

    @staticmethod
    def create(provider: str = "mock", **kwargs) -> BaseLLMClient:
        """
        直接创建 LLM 客户端（向后兼容）

        Args:
            provider: 提供商类型 ("mock" 或 "openai")
            **kwargs: 传递给客户端的额外参数

        Returns:
            BaseLLMClient: LLM 客户端实例
        """
        provider = provider.lower()
        if provider == "mock":
            return MockLLMClient()
        elif provider in LLMClientFactory.OPENAI_COMPATIBLE_PROVIDERS:
            return OpenAIClient(**kwargs)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")


def create_llm_client(provider: str = "mock", **kwargs) -> BaseLLMClient:
    """
    工厂函数：创建 LLM 客户端（向后兼容，推荐使用 LLMClientFactory）

    Args:
        provider: 提供商类型 ("mock" 或 "openai")
        **kwargs: 传递给客户端的额外参数

    Returns:
        LLM 客户端实例

    Deprecated:
        使用 LLMClientFactory.create() 或 LLMClientFactory.create_from_config() 代替
    """
    return LLMClientFactory.create(provider, **kwargs)
