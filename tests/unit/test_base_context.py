"""
Unit tests for BaseContext
"""

import pytest
from datetime import datetime
from crawler.base_context import BaseContext


class ConcreteContext(BaseContext):
    """具体的上下文实现用于测试"""

    def get_summary(self):
        """实现抽象方法"""
        return {
            'identifier': self.identifier,
            'results': self.results,
            'warnings': self.warnings,
            'errors': self.errors,
            'metadata': self.metadata
        }


class TestBaseContext:
    """测试 BaseContext 基类"""

    def test_initialization(self):
        """测试初始化"""
        ctx = ConcreteContext("test-id")

        assert ctx.identifier == "test-id"
        assert ctx.results == {}
        assert ctx.warnings == []
        assert ctx.errors == []
        assert isinstance(ctx.metadata, dict)
        assert 'created_at' in ctx.metadata
        assert ctx.metadata['identifier'] == "test-id"

    def test_set_and_get_result(self):
        """测试设置和获取结果"""
        ctx = ConcreteContext("test-id")

        ctx.set_result("analyzer1", {"key": "value"})
        result = ctx.get_result("analyzer1")

        assert result == {"key": "value"}

    def test_get_result_nonexistent(self):
        """测试获取不存在的结果时返回None"""
        ctx = ConcreteContext("test-id")

        result = ctx.get_result("nonexistent")

        assert result is None

    def test_add_warning(self):
        """测试添加警告"""
        ctx = ConcreteContext("test-id")

        ctx.add_warning("Warning message 1")
        ctx.add_warning("Warning message 2")

        assert len(ctx.warnings) == 2
        assert ctx.warnings[0] == "Warning message 1"
        assert ctx.warnings[1] == "Warning message 2"

    def test_add_error(self):
        """测试添加错误"""
        ctx = ConcreteContext("test-id")

        ctx.add_error("Error message 1")
        ctx.add_error("Error message 2")

        assert len(ctx.errors) == 2
        assert ctx.errors[0] == "Error message 1"
        assert ctx.errors[1] == "Error message 2"

    def test_record_timing(self):
        """测试记录时间"""
        ctx = ConcreteContext("test-id")

        ctx.record_timing("analyzer1", 100.5)
        ctx.record_timing("analyzer2", 250.3)

        assert ctx.timing["analyzer1"] == 100.5
        assert ctx.timing["analyzer2"] == 250.3

    def test_get_total_time(self):
        """测试获取总时间"""
        ctx = ConcreteContext("test-id")

        ctx.record_timing("analyzer1", 100.0)
        ctx.record_timing("analyzer2", 200.0)
        ctx.record_timing("analyzer3", 150.0)

        total = ctx.get_total_time()

        assert total == 450.0

    def test_get_total_time_empty(self):
        """测试空计时的总时间"""
        ctx = ConcreteContext("test-id")

        total = ctx.get_total_time()

        assert total == 0.0

    def test_has_errors(self):
        """测试检查是否有错误"""
        ctx = ConcreteContext("test-id")

        assert not ctx.has_errors()

        ctx.add_error("Error message")

        assert ctx.has_errors()

    def test_has_warnings(self):
        """测试检查是否有警告"""
        ctx = ConcreteContext("test-id")

        assert not ctx.has_warnings()

        ctx.add_warning("Warning message")

        assert ctx.has_warnings()
