"""
LLM 响应后处理过滤器 - 移除思考过程，保留最终答案
"""

import re
from typing import Optional


class ReasoningFilter:
    """过滤 LLM 响应中的思考过程，提取最终答案"""

    # 思考过程的常见开头标记
    THINKING_MARKERS = [
        r'^让我.*?[分析|思考|考虑|看看|想想|理解|检查|评估]',
        r'^首先.*?[，|,|：|:]',
        r'^好的.*?[，|,|：|:]',
        r'^根据.*?[，|,|：|:]',
        r'^从.*?来看',
        r'^这个问题',
        r'^我[需要|应该|可以|会|将]',
        r'^要[分析|理解|解决]',
    ]

    # 最终答案的标记
    ANSWER_MARKERS = [
        r'(?:最终|综合|总结|结论).*?[:：]',
        r'(?:答案|结果|输出).*?[:：]',
        r'(?:因此|所以|综上所述)',
        r'^---+\s*$',  # 分隔线
    ]

    # 需要保留的结构化内容标记
    STRUCTURED_MARKERS = [
        r'```',  # 代码块
        r'^\s*[\-\*\+]\s',  # 列表
        r'^\s*\d+\.\s',  # 编号列表
        r'^\s*[#]+\s',  # 标题
        r'^\s*\|',  # 表格
        r'^\s*{',  # JSON对象
        r'^\s*\[',  # JSON数组
    ]

    def __init__(self, strategy: str = "smart"):
        """
        初始化过滤器

        Args:
            strategy: 过滤策略
                - "smart": 智能检测，尝试识别思考过程和最终答案
                - "aggressive": 激进模式，移除所有可能的思考过程
                - "conservative": 保守模式，只移除明确的思考标记
                - "none": 不过滤
        """
        self.strategy = strategy

    def filter(self, text: str) -> str:
        """
        过滤文本，移除思考过程

        Args:
            text: 原始文本

        Returns:
            过滤后的文本
        """
        if not text or self.strategy == "none":
            return text

        text = text.strip()

        # 如果文本很短（<50字符），可能不包含思考过程
        if len(text) < 50:
            return text

        # 如果文本以结构化内容开始，直接返回
        if self._starts_with_structured_content(text):
            return text

        if self.strategy == "smart":
            return self._smart_filter(text)
        elif self.strategy == "aggressive":
            return self._aggressive_filter(text)
        elif self.strategy == "conservative":
            return self._conservative_filter(text)
        else:
            return text

    def _starts_with_structured_content(self, text: str) -> bool:
        """检查文本是否以结构化内容开始"""
        for pattern in self.STRUCTURED_MARKERS:
            if re.match(pattern, text, re.MULTILINE):
                return True
        return False

    def _smart_filter(self, text: str) -> str:
        """
        智能过滤：尝试识别思考过程和最终答案的边界

        策略：
        1. 查找最终答案标记，提取标记后的内容
        2. 如果没有找到标记，检查是否有明显的思考过程开头
        3. 如果有思考过程，尝试找到第一个结构化内容或段落
        """
        lines = text.split('\n')

        # 策略1: 查找最终答案标记
        for i, line in enumerate(lines):
            for pattern in self.ANSWER_MARKERS:
                if re.search(pattern, line, re.IGNORECASE):
                    # 找到答案标记，返回此行及之后的内容
                    remaining = '\n'.join(lines[i:]).strip()
                    # 移除标记行本身（如果它只是标记）
                    if len(line.strip()) < 20 and ':' in line:
                        remaining = '\n'.join(lines[i+1:]).strip()
                    if remaining:
                        return remaining

        # 策略2: 检查开头是否有思考过程标记
        first_line = lines[0] if lines else ""
        has_thinking_marker = False
        for pattern in self.THINKING_MARKERS:
            if re.match(pattern, first_line):
                has_thinking_marker = True
                break

        if has_thinking_marker:
            # 找到第一个结构化内容或非思考过程的段落
            for i, line in enumerate(lines[1:], 1):
                # 跳过空行
                if not line.strip():
                    continue

                # 如果遇到结构化内容，从这里开始返回
                for pattern in self.STRUCTURED_MARKERS:
                    if re.match(pattern, line):
                        return '\n'.join(lines[i:]).strip()

                # 如果遇到不像思考过程的行，从这里开始返回
                is_thinking = False
                for pattern in self.THINKING_MARKERS:
                    if re.match(pattern, line):
                        is_thinking = True
                        break

                if not is_thinking and len(line.strip()) > 10:
                    return '\n'.join(lines[i:]).strip()

        # 策略3: 如果没有明显的思考过程，返回原文
        return text

    def _aggressive_filter(self, text: str) -> str:
        """
        激进过滤：移除所有可能的思考过程

        策略：
        1. 移除所有思考标记开头的段落
        2. 只保留结构化内容和明确的答案
        """
        lines = text.split('\n')
        filtered_lines = []
        skip_until_structured = False

        for line in lines:
            # 如果遇到思考标记，开始跳过
            if not skip_until_structured:
                for pattern in self.THINKING_MARKERS:
                    if re.match(pattern, line):
                        skip_until_structured = True
                        break

            # 如果遇到结构化内容或答案标记，停止跳过
            if skip_until_structured:
                for pattern in self.STRUCTURED_MARKERS + self.ANSWER_MARKERS:
                    if re.match(pattern, line):
                        skip_until_structured = False
                        break

            # 如果不在跳过状态，保留这行
            if not skip_until_structured:
                filtered_lines.append(line)

        result = '\n'.join(filtered_lines).strip()
        return result if result else text

    def _conservative_filter(self, text: str) -> str:
        """
        保守过滤：只移除明确的思考标记行

        策略：
        只移除单独一行的思考标记（如"让我分析一下："）
        """
        lines = text.split('\n')
        filtered_lines = []

        for line in lines:
            # 检查是否是单独的思考标记行
            is_thinking_marker = False
            if len(line.strip()) < 30:  # 短行更可能是标记
                for pattern in self.THINKING_MARKERS:
                    if re.match(pattern, line.strip()):
                        is_thinking_marker = True
                        break

            if not is_thinking_marker:
                filtered_lines.append(line)

        result = '\n'.join(filtered_lines).strip()
        return result if result else text


def create_filter(strategy: str = "smart") -> ReasoningFilter:
    """
    工厂函数：创建过滤器实例

    Args:
        strategy: 过滤策略 ("smart", "aggressive", "conservative", "none")

    Returns:
        ReasoningFilter 实例
    """
    return ReasoningFilter(strategy=strategy)
