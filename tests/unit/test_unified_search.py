"""
测试统一搜索引擎
"""

import pytest
from pathlib import Path
from crawler.utils.unified_search import UnifiedSearchEngine, SearchResult
from crawler.llm_client import MockLLMClient


class TestUnifiedSearchEngine:
    """测试统一搜索引擎"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM 客户端"""
        llm = MockLLMClient()
        llm.set_response('{"score": 8, "reason": "高度相关"}')
        return llm

    @pytest.fixture
    def search_engine(self, tmp_path, mock_llm):
        """创建测试用搜索引擎"""
        # 创建测试源文件
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("""
int spdk_nvme_ctrlr_reset(struct spdk_nvme_ctrlr *ctrlr)
{
    // Reset NVMe controller
    return 0;
}

int nvme_init_controller(void)
{
    // Initialize NVMe controller
    return 0;
}
""")

        cache_dir = tmp_path / "cache"
        return UnifiedSearchEngine(
            source_dir=str(source_dir),
            llm_client=mock_llm,
            cache_dir=str(cache_dir)
        )

    def test_basic_search_without_llm(self, tmp_path):
        """测试不使用 LLM 的基础搜索"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("int nvme_reset() { return 0; }")

        engine = UnifiedSearchEngine(source_dir=str(source_dir))
        results = engine.search("nvme_reset", use_llm_ranking=False)

        assert len(results) > 0
        assert any("nvme_reset" in r.snippet for r in results)

    def test_search_with_llm_ranking(self, search_engine):
        """测试使用 LLM 排序的搜索"""
        results = search_engine.search(
            query="NVMe controller reset implementation",
            use_llm_ranking=True,
            max_results=5
        )

        assert len(results) > 0
        # 结果应该按相关性排序
        for i in range(len(results) - 1):
            assert results[i].relevance_score >= results[i + 1].relevance_score

    def test_search_with_keywords(self, search_engine):
        """测试使用关键词列表搜索"""
        results = search_engine.search(
            query="NVMe reset",
            keywords=["nvme", "reset", "controller"],
            max_results=10
        )

        assert len(results) > 0

    def test_search_filters_by_min_relevance(self, tmp_path):
        """测试最低相关性过滤"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("int nvme_reset() { return 0; }")

        mock_llm = MockLLMClient()
        mock_llm.set_response('{"score": 2, "reason": "弱相关"}')  # 低分

        engine = UnifiedSearchEngine(
            source_dir=str(source_dir),
            llm_client=mock_llm,
            min_relevance_score=5.0  # 高阈值
        )

        results = engine.search("nvme", use_llm_ranking=True)

        # 低分结果应该被过滤
        assert all(r.relevance_score >= 5.0 for r in results)

    def test_search_deduplicates_results(self, tmp_path):
        """测试结果去重"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("""
nvme_reset();
nvme_reset();
nvme_reset();
""")

        engine = UnifiedSearchEngine(source_dir=str(source_dir))
        results = engine.search(
            query="nvme_reset",
            keywords=["nvme_reset", "nvme_reset"],  # 重复关键词
            use_llm_ranking=False
        )

        # 同一行不应该出现多次
        seen = set()
        for r in results:
            key = (r.file_path, r.line_number)
            assert key not in seen
            seen.add(key)

    def test_search_respects_max_results(self, tmp_path):
        """测试最大结果数限制"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("\n".join([f"nvme_function_{i}();" for i in range(20)]))

        engine = UnifiedSearchEngine(source_dir=str(source_dir))
        results = engine.search("nvme", max_results=5, use_llm_ranking=False)

        assert len(results) <= 5

    def test_search_caching(self, search_engine):
        """测试搜索缓存"""
        query = "NVMe reset"
        keywords = ["nvme", "reset"]

        # 第一次搜索
        results1 = search_engine.search(query, keywords=keywords)

        # 第二次搜索（应该使用缓存）
        results2 = search_engine.search(query, keywords=keywords)

        # 结果应该相同
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.file_path == r2.file_path
            assert r1.relevance_score == r2.relevance_score

    def test_search_without_cache(self, tmp_path):
        """测试禁用缓存"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("int nvme_reset() { return 0; }")

        engine = UnifiedSearchEngine(
            source_dir=str(source_dir),
            cache_dir=None  # 禁用缓存
        )

        results = engine.search("nvme", use_llm_ranking=False)
        assert len(results) > 0

    def test_search_handles_llm_error_gracefully(self, tmp_path):
        """测试 LLM 错误时的优雅降级"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        test_file = source_dir / "test.c"
        test_file.write_text("int nvme_reset() { return 0; }")

        mock_llm = MockLLMClient()
        mock_llm.set_response("invalid json")  # 无效响应

        engine = UnifiedSearchEngine(
            source_dir=str(source_dir),
            llm_client=mock_llm
        )

        results = engine.search("nvme", use_llm_ranking=True)

        # 应该回退到默认评分
        assert len(results) > 0
        assert all(r.relevance_score > 0 for r in results)

    def test_search_result_contains_context(self, search_engine):
        """测试搜索结果包含上下文"""
        results = search_engine.search("nvme_reset", context_lines=2)

        assert len(results) > 0
        for result in results:
            assert result.context is not None
            assert len(result.context) > 0
            # 上下文应该包含匹配行
            assert ">>>" in result.context

    def test_simple_ranking_by_file_type(self, tmp_path):
        """测试简单排序（按文件类型）"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        # 创建不同类型的文件
        (source_dir / "test.c").write_text("nvme_reset();")
        (source_dir / "test.py").write_text("nvme_reset()")
        (source_dir / "test.md").write_text("nvme_reset")

        engine = UnifiedSearchEngine(source_dir=str(source_dir))
        results = engine.search("nvme_reset", use_llm_ranking=False)

        # C 文件应该得分最高
        c_results = [r for r in results if r.file_path.endswith('.c')]
        py_results = [r for r in results if r.file_path.endswith('.py')]

        if c_results and py_results:
            assert c_results[0].relevance_score > py_results[0].relevance_score


class TestUnifiedSearchEngineIntegration:
    """集成测试"""

    def test_search_real_codebase_structure(self, tmp_path):
        """测试真实代码库结构"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        # 创建类似真实项目的结构
        lib_dir = source_dir / "lib" / "nvme"
        lib_dir.mkdir(parents=True)

        (lib_dir / "nvme_ctrlr.c").write_text("""
int spdk_nvme_ctrlr_reset(struct spdk_nvme_ctrlr *ctrlr)
{
    /* Reset the NVMe controller */
    return nvme_ctrlr_reset_internal(ctrlr);
}
""")

        (lib_dir / "nvme_internal.h").write_text("""
int nvme_ctrlr_reset_internal(struct spdk_nvme_ctrlr *ctrlr);
""")

        engine = UnifiedSearchEngine(source_dir=str(source_dir))
        results = engine.search(
            query="NVMe controller reset implementation",
            use_llm_ranking=False
        )

        assert len(results) > 0
        # 应该找到实现文件
        assert any("nvme_ctrlr.c" in r.file_path for r in results)

    def test_search_quality_comparison(self, tmp_path):
        """测试搜索质量对比（LLM vs 简单排序）"""
        source_dir = tmp_path / "sources"
        source_dir.mkdir()

        # 创建高相关性和低相关性的文件
        (source_dir / "highly_relevant.c").write_text("""
int spdk_nvme_ctrlr_reset(struct spdk_nvme_ctrlr *ctrlr)
{
    // This is the main reset implementation
    return do_reset(ctrlr);
}
""")

        (source_dir / "barely_relevant.c").write_text("""
// Just mentions reset in a comment
int some_other_function(void) { return 0; }
""")

        # 使用 LLM 排序
        mock_llm = MockLLMClient()
        mock_llm.set_response('{"score": 9, "reason": "主要实现"}')

        engine_with_llm = UnifiedSearchEngine(
            source_dir=str(source_dir),
            llm_client=mock_llm
        )

        results_with_llm = engine_with_llm.search(
            query="NVMe controller reset implementation",
            use_llm_ranking=True
        )

        # 不使用 LLM 排序
        engine_without_llm = UnifiedSearchEngine(source_dir=str(source_dir))
        results_without_llm = engine_without_llm.search(
            query="reset",
            use_llm_ranking=False
        )

        # LLM 排序应该更准确
        if results_with_llm:
            assert "highly_relevant" in results_with_llm[0].file_path
