#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的集成测试 - 验证过滤器在真实LLM场景中的效果
"""

import sys
import io
import yaml
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from crawler.llm_client import LLMClientFactory


def test_reasoning_filter_integration():
    """测试过滤器在真实LLM调用中的效果"""

    print("=" * 80)
    print("  过滤器集成测试 (真实 LLM)")
    print("=" * 80)
    print()

    # 加载配置
    print("步骤 1: 加载配置")
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    llm_config = config['llm']
    print(f"✓ 配置加载成功")
    print(f"  Provider: {llm_config['provider']}")
    print(f"  Base URL: {llm_config['base_url']}")
    print(f"  Model: {llm_config['model']}")
    print(f"  过滤器启用: {llm_config.get('enable_reasoning_filter', True)}")
    print(f"  过滤策略: {llm_config.get('reasoning_filter_strategy', 'smart')}")
    print()

    # 创建LLM客户端
    print("步骤 2: 创建 LLM 客户端")
    try:
        client = LLMClientFactory.create_from_config(llm_config)
        print(f"✓ LLM 客户端创建成功")
        print(f"  过滤器状态: {'已启用' if client.enable_reasoning_filter else '未启用'}")
        if client.reasoning_filter:
            print(f"  过滤策略: {client.reasoning_filter.strategy}")
        print()
    except Exception as e:
        print(f"❌ 创建客户端失败: {e}")
        return False

    # 测试连接
    print("步骤 3: 测试 LLM 连接")
    try:
        response = client.generate(
            "请用一句话介绍NVMe协议。",
            max_tokens=100,
            temperature=0.7
        )
        print(f"✓ LLM 连接成功")
        print(f"  响应长度: {len(response)} 字符")
        print(f"  响应内容:\n{response}")
        print()

        # 检查响应是否包含思考过程标记
        thinking_markers = ["让我", "首先", "然后", "接下来", "最后"]
        has_thinking = any(marker in response[:50] for marker in thinking_markers)

        if has_thinking:
            print("⚠️  警告: 响应可能仍包含思考过程")
        else:
            print("✓ 响应不包含明显的思考过程标记")
        print()

    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        print()
        print("⚠️  警告: LLM 连接失败")
        print("请检查:")
        print("  1. LM Studio 或 Ollama 是否正在运行")
        print("  2. base_url 是否正确")
        print("  3. 模型是否已加载")
        print()
        return False

    # 测试根因分析场景
    print("步骤 4: 测试根因分析场景")
    try:
        prompt = """分析以下问题的根本原因：

问题描述：在 Sanitize Block Erase 期间下发 NVM Reset，设备重新枚举后无法进行 4K Random Write。

请直接给出根因分析，不要包含思考过程。"""

        response = client.generate(prompt, max_tokens=500, temperature=0.7)
        print(f"✓ 根因分析完成")
        print(f"  响应长度: {len(response)} 字符")
        print(f"  响应内容:\n{response}")
        print()

        # 检查是否包含思考过程
        thinking_markers = ["让我分析", "首先", "然后", "接下来"]
        has_thinking = any(marker in response[:100] for marker in thinking_markers)

        if has_thinking:
            print("⚠️  警告: 响应可能仍包含思考过程")
        else:
            print("✓ 响应不包含明显的思考过程标记")
        print()

    except Exception as e:
        print(f"❌ 根因分析失败: {e}")
        return False

    print("=" * 80)
    print("✓ 集成测试完成")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_reasoning_filter_integration()
    sys.exit(0 if success else 1)
