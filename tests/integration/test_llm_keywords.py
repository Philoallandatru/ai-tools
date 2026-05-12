"""
测试 LLM 关键词提取功能
"""
import sys
import os

# 设置环境变量强制 UTF-8 输出
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
from crawler.doc_analyzer import DocumentAnalyzer
from crawler.searcher import ContentSearcher

def test_llm_keyword_extraction():
    """测试 LLM 关键词提取"""

    print("=" * 80)
    print("测试 LLM 关键词提取功能")
    print("=" * 80)

    # 创建分析器
    analyzer = DocumentAnalyzer('configs/doc_analysis_config.yaml')

    # 测试文本
    test_texts = [
        {
            "name": "技术规格文档",
            "content": """
## NVMe Reset 流程

执行 NVMe Controller Reset 需要以下步骤：
1. 清零 CC.EN 寄存器
2. 轮询 CSTS.RDY 状态位
3. 等待控制器就绪

超时时间建议设置为 30 秒。
"""
        },
        {
            "name": "自然语言需求",
            "content": """
## 用户登录功能

用户可以通过用户名和密码登录系统。登录成功后，系统应该记住用户的登录状态，
并在用户下次访问时自动登录。如果用户连续3次输入错误密码，账号应该被临时锁定。
"""
        },
        {
            "name": "混合型文档",
            "content": """
## RDMA 传输配置

系统需要支持通过 RDMA 协议进行数据传输。管理员可以配置 Queue Pair 数量和
缓冲区大小。默认情况下，系统会自动选择最优的传输参数。
"""
        }
    ]

    for test in test_texts:
        print(f"\n{'=' * 80}")
        print(f"测试: {test['name']}")
        print(f"{'=' * 80}")
        print(f"文档内容:\n{test['content'].strip()}\n")

        # 提取关键词
        print("[提取关键词]")
        keywords = analyzer._extract_keywords(test['content'])

        print(f"提取到 {len(keywords)} 个关键词:")
        for i, kw in enumerate(keywords, 1):
            print(f"  {i}. {kw}")

        # 测试用这些关键词搜索代码
        print(f"\n[代码搜索测试]")
        searcher = ContentSearcher(source_dir='./mock-codebase')

        total_matches = 0
        for kw in keywords[:5]:  # 只测试前5个关键词
            try:
                matches = searcher.search(
                    query=kw,
                    file_type='all',
                    context_lines=0,
                    use_regex=False,
                    max_results=3
                )
                if matches:
                    print(f"  '{kw}' -> 找到 {len(matches)} 个匹配")
                    total_matches += len(matches)
            except Exception as e:
                print(f"  '{kw}' -> 搜索失败: {e}")

        print(f"\n总计: 前5个关键词共找到 {total_matches} 个代码匹配")


def test_full_analysis_with_llm_keywords():
    """测试完整的文档分析流程（使用 LLM 关键词提取）"""

    print("\n" + "=" * 80)
    print("测试完整文档分析（使用 LLM 关键词提取）")
    print("=" * 80)

    # 创建分析器
    analyzer = DocumentAnalyzer('configs/doc_analysis_config.yaml')

    # 替换 searcher 为指向 mock-codebase 的搜索器
    analyzer.searcher = ContentSearcher(source_dir='./mock-codebase')

    # 禁用 vision 以加快测试
    analyzer.config['vision_llm']['enabled'] = False

    # 分析测试文档
    doc_path = 'test-sources/simple-test.md'

    if not Path(doc_path).exists():
        print(f"[错误] 测试文档不存在: {doc_path}")
        return

    print(f"\n[分析文档] {doc_path}")
    print("-" * 80)

    try:
        report_path = analyzer.analyze_document(doc_path)
        print(f"\n[成功] 分析完成")
        print(f"[报告] {report_path}")

        # 读取报告，查看关键词和代码参考
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取关键词部分
        if '提取的关键词' in content or '关键词' in content:
            print("\n" + "=" * 80)
            print("报告中的关键词")
            print("=" * 80)

            # 简单提取（实际报告格式可能不同）
            lines = content.split('\n')
            in_keywords = False
            for line in lines:
                if '关键词' in line:
                    in_keywords = True
                    print(line)
                elif in_keywords and line.strip():
                    if line.startswith('#'):
                        break
                    print(line)

        # 提取代码参考部分
        if '## 相关代码参考' in content:
            print("\n" + "=" * 80)
            print("报告中的代码参考（前500字符）")
            print("=" * 80)

            start = content.find('## 相关代码参考')
            end = content.find('\n## ', start + 1)
            if end == -1:
                end = start + 500

            code_ref = content[start:end]
            print(code_ref[:500])

            if len(code_ref) > 500:
                print("\n... (更多内容请查看完整报告)")

    except Exception as e:
        print(f"\n[错误] 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 测试1: 单独测试关键词提取
    test_llm_keyword_extraction()

    # 测试2: 完整文档分析流程
    test_full_analysis_with_llm_keywords()
