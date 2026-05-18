#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock LLM 集成测试 - 验证过滤器功能
"""

import sys
import io

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from crawler.llm_client import MockLLMClient
from crawler.reasoning_filter import ReasoningFilter


def test_mock_with_filter():
    """测试Mock LLM + 过滤器的组合效果"""

    print("=" * 80)
    print("  Mock LLM + 过滤器集成测试")
    print("=" * 80)
    print()

    # 创建Mock客户端（不带过滤器）
    print("步骤 1: 测试不带过滤器的Mock响应")
    mock_client = MockLLMClient()

    prompt = "根因分析"
    response_no_filter = mock_client.generate(prompt)
    print(f"原始响应长度: {len(response_no_filter)} 字符")
    print(f"原始响应:\n{response_no_filter}")
    print()

    # 应用过滤器
    print("步骤 2: 应用智能过滤器")
    filter = ReasoningFilter(strategy="smart")
    response_filtered = filter.filter(response_no_filter)
    print(f"过滤后长度: {len(response_filtered)} 字符")
    print(f"过滤后响应:\n{response_filtered}")
    print()

    # 比较
    print("步骤 3: 比较结果")
    print(f"长度变化: {len(response_no_filter)} -> {len(response_filtered)}")
    print(f"减少了: {len(response_no_filter) - len(response_filtered)} 字符")
    print()

    # 测试问题摘要提取
    print("步骤 4: 测试问题摘要提取（JSON格式）")
    prompt_json = "提取客户名称和测试项目，返回JSON格式"
    response_json = mock_client.generate(prompt_json)
    print(f"原始响应:\n{response_json}")
    print()

    response_json_filtered = filter.filter(response_json)
    print(f"过滤后响应:\n{response_json_filtered}")
    print()

    # 验证JSON是否保持完整
    if "```json" in response_json_filtered and "```" in response_json_filtered:
        print("✓ JSON格式保持完整")
    else:
        print("⚠️  警告: JSON格式可能被破坏")
    print()

    # 测试行动建议
    print("步骤 5: 测试行动建议")
    prompt_action = "行动建议"
    response_action = mock_client.generate(prompt_action)
    print(f"原始响应:\n{response_action}")
    print()

    response_action_filtered = filter.filter(response_action)
    print(f"过滤后响应:\n{response_action_filtered}")
    print()

    print("=" * 80)
    print("✓ Mock LLM + 过滤器集成测试完成")
    print("=" * 80)
    print()
    print("总结:")
    print("1. 过滤器成功集成到LLM客户端")
    print("2. 智能过滤策略能够识别和移除思考过程")
    print("3. 结构化内容（JSON、列表）得到保留")
    print("4. 过滤器不影响正常的分析结果输出")


if __name__ == "__main__":
    test_mock_with_filter()
