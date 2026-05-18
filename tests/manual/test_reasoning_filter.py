#!/usr/bin/env python3
"""测试推理过程过滤器"""

from crawler.reasoning_filter import ReasoningFilter


def test_smart_filter():
    """测试智能过滤策略"""
    filter = ReasoningFilter(strategy="smart")

    # 测试用例1: 带有明显思考过程的文本
    text1 = """让我分析一下这个问题。

首先，我们需要理解根本原因。

根因分析：
1. 直接原因：NVMe Reset 期间状态机未正确处理 CC.EN 清零
2. 深层原因：固件未实现 CSTS.RDY 等待机制
3. 触发条件：在 Sanitize Block Erase 期间下发 NVM Reset"""

    result1 = filter.filter(text1)
    print("测试用例1 - 带思考过程:")
    print(f"原文长度: {len(text1)}")
    print(f"过滤后长度: {len(result1)}")
    print(f"过滤后内容:\n{result1}\n")

    # 测试用例2: 带有"最终答案"标记的文本
    text2 = """让我思考一下这个问题的解决方案。

首先需要检查配置，然后验证网络连接。

最终答案：
- 短期：添加 CC.EN 清零后的 CSTS.RDY 轮询机制
- 中期：完善 Reset 状态机的异常处理
- 长期：建立 Reset 场景的自动化测试"""

    result2 = filter.filter(text2)
    print("测试用例2 - 带最终答案标记:")
    print(f"原文长度: {len(text2)}")
    print(f"过滤后长度: {len(result2)}")
    print(f"过滤后内容:\n{result2}\n")

    # 测试用例3: 直接的结构化内容（不应过滤）
    text3 = """```json
{
  "customer": "Micron",
  "test_project": "SSD1250, Sanitize",
  "root_cause": "固件未实现 CSTS.RDY 等待机制"
}
```"""

    result3 = filter.filter(text3)
    print("测试用例3 - 结构化内容:")
    print(f"原文长度: {len(text3)}")
    print(f"过滤后长度: {len(result3)}")
    print(f"内容是否保持不变: {text3.strip() == result3}")
    print(f"过滤后内容:\n{result3}\n")

    # 测试用例4: 列表格式（不应过滤）
    text4 = """- 短期：添加 CC.EN 清零后的 CSTS.RDY 轮询机制
- 中期：完善 Reset 状态机的异常处理
- 长期：建立 Reset 场景的自动化测试"""

    result4 = filter.filter(text4)
    print("测试用例4 - 列表格式:")
    print(f"原文长度: {len(text4)}")
    print(f"过滤后长度: {len(result4)}")
    print(f"内容是否保持不变: {text4.strip() == result4}")
    print(f"过滤后内容:\n{result4}\n")


def test_aggressive_filter():
    """测试激进过滤策略"""
    filter = ReasoningFilter(strategy="aggressive")

    text = """让我分析一下这个问题。

首先，我们需要理解根本原因。

根因分析：
1. 直接原因：NVMe Reset 期间状态机未正确处理 CC.EN 清零
2. 深层原因：固件未实现 CSTS.RDY 等待机制"""

    result = filter.filter(text)
    print("激进过滤测试:")
    print(f"原文长度: {len(text)}")
    print(f"过滤后长度: {len(result)}")
    print(f"过滤后内容:\n{result}\n")


def test_conservative_filter():
    """测试保守过滤策略"""
    filter = ReasoningFilter(strategy="conservative")

    text = """让我分析一下这个问题。

根因分析：
1. 直接原因：NVMe Reset 期间状态机未正确处理 CC.EN 清零
2. 深层原因：固件未实现 CSTS.RDY 等待机制"""

    result = filter.filter(text)
    print("保守过滤测试:")
    print(f"原文长度: {len(text)}")
    print(f"过滤后长度: {len(result)}")
    print(f"过滤后内容:\n{result}\n")


if __name__ == "__main__":
    print("=" * 80)
    print("推理过程过滤器测试")
    print("=" * 80)
    print()

    test_smart_filter()
    print("=" * 80)
    test_aggressive_filter()
    print("=" * 80)
    test_conservative_filter()
