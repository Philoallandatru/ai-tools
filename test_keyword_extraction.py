"""
对比测试：正则提取 vs LLM 提取关键词
"""
import re
from test_utils import create_test_llm_client

# 测试文本样例
test_texts = [
    # 样例1：技术规格文档（大量技术术语）
    """
    ## NVMe Reset 流程

    执行 NVMe Controller Reset 需要以下步骤：
    1. 清零 CC.EN 寄存器
    2. 轮询 CSTS.RDY 状态位
    3. 等待控制器就绪

    超时时间建议设置为 30 秒。
    """,

    # 样例2：自然语言需求描述
    """
    ## 用户登录功能

    用户可以通过用户名和密码登录系统。登录成功后，系统应该记住用户的登录状态，
    并在用户下次访问时自动登录。如果用户连续3次输入错误密码，账号应该被临时锁定。
    """,

    # 样例3：混合型文档
    """
    ## RDMA 传输配置

    系统需要支持通过 RDMA 协议进行数据传输。管理员可以配置 Queue Pair 数量和
    缓冲区大小。默认情况下，系统会自动选择最优的传输参数。
    """
]


def extract_keywords_regex(text: str) -> list:
    """使用正则表达式提取关键词"""
    keywords = []

    patterns = [
        r'\b[A-Z]{2,}\b',                    # 大写缩写：NVMe, CSTS
        r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b',  # 驼峰命名：ReadyState
        r'\b[a-z_]+_[a-z_]+\b',              # 下划线命名：nvme_reset
        r'[一-龥]{2,4}',                      # 中文词汇
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        keywords.extend(matches)

    # 去重并过滤短词
    keywords = list(set(k for k in keywords if len(k) >= 3))

    return sorted(keywords)


def extract_keywords_llm(text: str, llm_client) -> list:
    """使用 LLM 提取关键词"""
    prompt = f"""请从以下文本中提取关键词，用于代码搜索。

要求：
1. 提取技术术语、API 名称、组件名称等
2. 提取核心概念和功能名称
3. 每个关键词 2-10 个字符
4. 只返回关键词列表，每行一个，不要其他解释

文本：
{text}

关键词："""

    try:
        response = llm_client.generate(prompt, max_tokens=200)
        # 解析响应，提取关键词
        keywords = [line.strip() for line in response.strip().split('\n') if line.strip()]
        # 过滤掉可能的序号
        keywords = [re.sub(r'^\d+[\.\)]\s*', '', k) for k in keywords]
        keywords = [k for k in keywords if k and len(k) >= 2]
        return keywords
    except Exception as e:
        print(f"LLM 提取失败: {e}")
        return []


def main():
    print("=" * 80)
    print("关键词提取方案对比测试")
    print("=" * 80)
    print()

    # 初始化 LLM 客户端（自动降级到 Mock）
    llm_client = create_test_llm_client(
        provider='openai',
        base_url='http://127.0.0.1:1234/v1',
        model='qwen3.5-4b',
        auto_fallback=True
    )
    print()

    for i, text in enumerate(test_texts, 1):
        print(f"\n{'=' * 80}")
        print(f"测试样例 {i}")
        print(f"{'=' * 80}")
        print(text.strip()[:200] + "..." if len(text.strip()) > 200 else text.strip())

        # 方案1：正则提取
        print(f"\n[方案1] 正则表达式提取：")
        regex_keywords = extract_keywords_regex(text)
        print(f"  提取到 {len(regex_keywords)} 个关键词")
        print(f"  {', '.join(regex_keywords)}")

        # 方案2：LLM 提取
        print(f"\n[方案2] LLM 提取：")
        llm_keywords = extract_keywords_llm(text, llm_client)
        print(f"  提取到 {len(llm_keywords)} 个关键词")
        print(f"  {', '.join(llm_keywords)}")

        # 对比分析
        print(f"\n[对比分析]")
        only_regex = set(regex_keywords) - set(llm_keywords)
        only_llm = set(llm_keywords) - set(regex_keywords)
        both = set(regex_keywords) & set(llm_keywords)

        print(f"  共同提取: {len(both)} 个 - {', '.join(sorted(both)) if both else '无'}")
        print(f"  仅正则: {len(only_regex)} 个 - {', '.join(sorted(only_regex)) if only_regex else '无'}")
        print(f"  仅LLM: {len(only_llm)} 个 - {', '.join(sorted(only_llm)) if only_llm else '无'}")

    # 总结建议
    print(f"\n{'=' * 80}")
    print("方案建议")
    print(f"{'=' * 80}")
    print("""
1. 【纯正则方案】- 适用场景：
   - 文档包含大量技术术语（大写缩写、驼峰命名）
   - 需要快速处理，成本敏感
   - 关键词模式明确（如 API 文档、规格文档）

   优点：快速、稳定、成本低
   缺点：可能提取到不相关词，遗漏语义关键词

2. 【纯LLM方案】- 适用场景：
   - 自然语言描述的需求文档
   - 需要理解语义和上下文
   - 关键词不明显，需要概念提取

   优点：理解语义，提取质量高
   缺点：慢、成本高、可能不稳定

3. 【混合方案】（推荐）- 适用场景：
   - 文档类型多样
   - 需要平衡质量和成本

   实现：
   - 先用正则快速提取明显的技术术语
   - 如果提取到的关键词少于阈值（如 < 5 个），再用 LLM 补充
   - 合并去重

   优点：兼顾速度和质量
   缺点：实现稍复杂
    """)


if __name__ == '__main__':
    main()
