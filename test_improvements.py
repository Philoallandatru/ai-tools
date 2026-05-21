"""快速测试代码质量改进"""

from crawler.utils.keyword_extractor import KeywordExtractor
from crawler.utils.unified_search import UnifiedSearchEngine
from crawler.llm_client import MockLLMClient

# 1. 测试关键词提取
print("=" * 50)
print("测试关键词提取器")
print("=" * 50)

extractor = KeywordExtractor()
text = "NVMe Reset功能需要实现spdk_nvme_ctrlr_reset接口"
keywords = extractor.extract_from_text(text)

print(f"输入文本: {text}")
print(f"提取的关键词: {keywords}")
print()

# 2. 测试 Jira 数据提取
jira_data = {
    'title': 'NVMe FFU Download Failure',
    'description': 'The firmware update fails during download. Error in spdk_nvme_ctrlr_update_firmware.'
}

keywords = extractor.extract_from_jira(jira_data)
print(f"Jira 标题: {jira_data['title']}")
print(f"提取的关键词: {keywords}")
print()

# 3. 测试统一搜索（需要真实的源文件目录）
print("=" * 50)
print("测试统一搜索引擎")
print("=" * 50)

# 使用 Mock LLM 进行演示
mock_llm = MockLLMClient()

engine = UnifiedSearchEngine(
    source_dir='./sources',  # 确保这个目录存在
    llm_client=mock_llm
)

try:
    results = engine.search(
        query="NVMe controller reset implementation",
        keywords=["nvme", "reset"],
        max_results=5,
        use_llm_ranking=False  # 先不使用 LLM 排序
    )

    print(f"搜索查询: NVMe controller reset implementation")
    print(f"找到 {len(results)} 个结果")

    for i, result in enumerate(results[:3], 1):
        print(f"\n结果 {i}:")
        print(f"  文件: {result.file_path}")
        print(f"  相关性: {result.relevance_score}/10")
        print(f"  代码片段: {result.snippet[:80]}...")

except Exception as e:
    print(f"搜索失败: {e}")
    print("提示: 确保 ./sources 目录存在并包含一些代码文件")

print("\n" + "=" * 50)
print("测试完成！")
print("=" * 50)
