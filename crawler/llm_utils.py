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
    # 使用循环处理嵌套标签，但限制最大迭代次数防止无限循环
    max_iterations = 10
    iteration = 0
    while '<think>' in text.lower() and iteration < max_iterations:
        prev_text = text
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # 如果文本没有变化，说明正则没有匹配到，跳出循环
        if text == prev_text:
            break
        iteration += 1

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


def extract_json_from_llm(response: str, expected_type: str = 'auto'):
    """
    从 LLM 响应中提取 JSON（对象或数组）

    Args:
        response: LLM 响应文本
        expected_type: 期望的类型 ('object', 'array', 'auto')

    Returns:
        解析后的 JSON 数据，失败返回 None
    """
    import json

    # 尝试提取 JSON 对象
    if expected_type in ('object', 'auto'):
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

    # 尝试提取 JSON 数组
    if expected_type in ('array', 'auto'):
        json_match = re.search(r'\[([^\]]+)\]', response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass

    return None
