"""
LLM 输出清理工具
"""

import re


def clean_llm_output(text: str) -> str:
    """
    清理 LLM 输出，移除思考过程标签和冗余内容

    Args:
        text: 原始 LLM 输出

    Returns:
        清理后的文本
    """
    if not text:
        return text

    # 1. 移除 <think>...</think> 标签及其内容（支持多行和嵌套）
    while '<think>' in text.lower():
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 2. 移除单独的 </think> 或 <think> 标签
    text = re.sub(r'</think>|<think>', '', text, flags=re.IGNORECASE)

    # 3. 移除 JSON 代码块（如果不是预期格式）
    text = re.sub(r'```json\s*\{[^}]*\}\s*```', '', text, flags=re.DOTALL)

    # 4. 移除重复的提示词（更强力的匹配）
    text = re.sub(r'(请从以下.*?维度分析.*?\n)+', '', text, flags=re.MULTILINE)
    text = re.sub(r'(请.*?分析.*?：\n)+', '', text, flags=re.MULTILINE)
    text = re.sub(r'(1\.\s*时间线位置.*?\n2\.\s*关键决策.*?\n3\.\s*合理性评估.*?\n)+', '', text, flags=re.MULTILINE)

    # 5. 移除 "Thinking Process:" 及其后续内容
    text = re.sub(r'Thinking Process:.*?(?=\n\n[^T]|\Z)', '', text, flags=re.DOTALL | re.MULTILINE)

    # 6. 移除格式说明
    text = re.sub(r'请.*?格式.*?输出.*?\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'请仅使用.*?回答.*?\n', '', text, flags=re.MULTILINE)

    # 7. 移除多余的空行（超过2个连续空行）
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # 8. 移除开头和结尾的空白
    text = text.strip()

    return text


def extract_structured_response(text: str, keys: list) -> dict:
    """
    从 LLM 输出中提取结构化信息

    Args:
        text: LLM 输出文本
        keys: 要提取的键列表

    Returns:
        提取的结构化数据字典
    """
    result = {}

    for key in keys:
        # 尝试匹配 "键: 值" 或 "**键**: 值" 格式
        pattern = rf'(?:\*\*)?{re.escape(key)}(?:\*\*)?[：:]\s*(.+?)(?=\n(?:\*\*)?(?:{"|".join(map(re.escape, keys))})|$)'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            result[key] = match.group(1).strip()

    return result
