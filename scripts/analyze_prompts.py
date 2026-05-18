#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析所有分析器的prompt使用情况
"""

import sys
import io
import re
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def estimate_tokens(text: str) -> int:
    """粗略估算token数量（中文按字符数，英文按单词数）"""
    # 简单估算：中文1字符≈1token，英文1单词≈1.3token
    chinese_chars = len(re.findall(r'[一-鿿]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    return chinese_chars + int(english_words * 1.3)


def analyze_analyzer_file(file_path: Path) -> dict:
    """分析单个分析器文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找所有字符串字面量（可能是prompt）
        # 匹配多行字符串和单行字符串
        multiline_strings = re.findall(r'"""(.*?)"""', content, re.DOTALL)
        singleline_strings = re.findall(r'"([^"]{50,})"', content)

        prompts = []
        for s in multiline_strings + singleline_strings:
            s = s.strip()
            if len(s) > 50:  # 只关注较长的字符串
                tokens = estimate_tokens(s)
                prompts.append({
                    'text': s[:200] + '...' if len(s) > 200 else s,
                    'length': len(s),
                    'tokens': tokens
                })

        return {
            'file': file_path.name,
            'prompts': prompts,
            'total_tokens': sum(p['tokens'] for p in prompts),
            'max_tokens': max((p['tokens'] for p in prompts), default=0)
        }
    except Exception as e:
        return {
            'file': file_path.name,
            'error': str(e)
        }


def main():
    print("=" * 80)
    print("  分析器 Prompt 使用情况分析")
    print("=" * 80)
    print()

    analyzers_dir = Path('crawler/analyzers')
    analyzer_files = [
        f for f in analyzers_dir.glob('*.py')
        if f.name not in ['__init__.py', 'base.py', 'configurable_base.py']
    ]

    results = []
    for file_path in sorted(analyzer_files):
        result = analyze_analyzer_file(file_path)
        results.append(result)

    # 按总token数排序
    results.sort(key=lambda x: x.get('total_tokens', 0), reverse=True)

    print(f"共分析 {len(results)} 个分析器文件\n")

    # 打印详细结果
    for i, result in enumerate(results, 1):
        if 'error' in result:
            print(f"{i}. {result['file']}")
            print(f"   错误: {result['error']}\n")
            continue

        print(f"{i}. {result['file']}")
        print(f"   Prompt数量: {len(result['prompts'])}")
        print(f"   总Token数: {result['total_tokens']}")
        print(f"   最大Token数: {result['max_tokens']}")

        if result['prompts']:
            print(f"   Prompt详情:")
            for j, prompt in enumerate(result['prompts'][:3], 1):  # 只显示前3个
                print(f"     {j}. 长度: {prompt['length']} 字符, Token: {prompt['tokens']}")
                print(f"        内容: {prompt['text'][:100]}...")
        print()

    # 统计总结
    print("=" * 80)
    print("  统计总结")
    print("=" * 80)
    total_tokens = sum(r.get('total_tokens', 0) for r in results)
    total_prompts = sum(len(r.get('prompts', [])) for r in results)

    print(f"总Token数: {total_tokens}")
    print(f"总Prompt数: {total_prompts}")
    print(f"平均每个分析器Token数: {total_tokens // len(results) if results else 0}")
    print()

    # 识别优化机会
    print("=" * 80)
    print("  优化建议")
    print("=" * 80)
    print()

    high_token_analyzers = [r for r in results if r.get('total_tokens', 0) > 500]
    if high_token_analyzers:
        print(f"高Token使用分析器 (>500 tokens):")
        for r in high_token_analyzers:
            print(f"  - {r['file']}: {r['total_tokens']} tokens")
        print()

    print("优化策略:")
    print("1. 简化prompt措辞，去除冗余描述")
    print("2. 使用更简洁的指令格式")
    print("3. 提取公共prompt模板，减少重复")
    print("4. 对于长prompt，考虑分步骤处理")
    print("5. 使用示例代替长篇说明")


if __name__ == "__main__":
    main()
