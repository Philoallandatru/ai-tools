"""
测试代码搜索功能
"""
from pathlib import Path
from crawler.doc_analyzer import DocumentAnalyzer
from crawler.searcher import ContentSearcher

def test_code_search():
    """测试在模拟代码库中搜索"""

    # 创建搜索器，指向 mock-codebase
    searcher = ContentSearcher(source_dir='./mock-codebase')

    # 测试关键词
    test_keywords = [
        'NVMe',
        'reset',
        'CSTS',
        'sanitize',
        'transport',
        'RDMA',
        'queue',
        'fabric'
    ]

    print("=" * 80)
    print("测试代码搜索功能")
    print("=" * 80)

    for keyword in test_keywords:
        print(f"\n[搜索] 关键词: {keyword}")
        print("-" * 80)

        try:
            matches = searcher.search(
                query=keyword,
                file_type='all',
                context_lines=2,
                use_regex=False,
                max_results=5
            )

            if matches:
                print(f"[成功] 找到 {len(matches)} 个匹配")
                for i, match in enumerate(matches[:3], 1):  # 只显示前3个
                    print(f"\n  [{i}] {match.file_path}")
                    print(f"      行 {match.line_number}: {match.line_content.strip()}")
            else:
                print(f"[失败] 未找到匹配")

        except Exception as e:
            print(f"[错误] 搜索失败: {e}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def test_analyzer_with_mock_codebase():
    """测试文档分析器使用模拟代码库"""

    print("\n" + "=" * 80)
    print("测试文档分析器（使用模拟代码库）")
    print("=" * 80)

    # 创建分析器
    analyzer = DocumentAnalyzer('configs/doc_analysis_config.yaml')

    # 替换 searcher 为指向 mock-codebase 的搜索器
    analyzer.searcher = ContentSearcher(source_dir='./mock-codebase')

    # 分析测试文档
    doc_path = 'test-sources/simple-test.md'

    if not Path(doc_path).exists():
        print(f"[错误] 测试文档不存在: {doc_path}")
        return

    print(f"\n[文档] 分析文档: {doc_path}")
    print("-" * 80)

    try:
        # 禁用 vision 以加快测试
        analyzer.config['vision_llm']['enabled'] = False

        report_path = analyzer.analyze_document(doc_path)
        print(f"\n[成功] 分析完成")
        print(f"[报告] 报告路径: {report_path}")

        # 读取并显示报告中的代码参考部分
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取代码参考部分
        if '## 相关代码参考' in content:
            print("\n" + "=" * 80)
            print("报告中的代码参考")
            print("=" * 80)

            # 找到代码参考部分
            start = content.find('## 相关代码参考')
            end = content.find('\n## ', start + 1)
            if end == -1:
                end = len(content)

            code_ref_section = content[start:end]
            print(code_ref_section[:1000])  # 显示前1000字符

            if len(code_ref_section) > 1000:
                print("\n... (更多内容请查看完整报告)")

    except Exception as e:
        print(f"\n[错误] 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 测试1: 直接测试搜索功能
    test_code_search()

    # 测试2: 测试文档分析器
    test_analyzer_with_mock_codebase()
