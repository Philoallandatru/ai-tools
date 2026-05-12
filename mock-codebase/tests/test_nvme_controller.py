"""
NVMe Controller 测试用例
"""
import pytest
from src.nvme_controller import NVMeController


class TestNVMeReset:
    """测试 NVMe Reset 功能"""

    def test_controller_reset_success(self):
        """测试控制器重置成功场景"""
        controller = NVMeController(controller_id=0)

        # 执行 reset
        result = controller.reset(timeout=30)

        assert result is True
        assert controller.status == "reset"

    def test_controller_reset_with_timeout(self):
        """测试控制器重置超时场景"""
        controller = NVMeController(controller_id=0)

        # 使用较短的超时时间
        result = controller.reset(timeout=1)

        # 应该能够在超时时间内完成
        assert result is True

    def test_cc_enable_cleared_after_reset(self):
        """测试 Reset 后 CC.EN 被清零"""
        controller = NVMeController(controller_id=0)

        # 执行 reset
        controller.reset()

        # 验证 CC.EN 被清零（通过内部状态验证）
        assert controller.status == "reset"

    def test_csts_rdy_polling(self):
        """测试 CSTS.RDY 轮询机制"""
        controller = NVMeController(controller_id=0)

        # 执行 reset，内部会轮询 CSTS.RDY
        result = controller.reset(timeout=30)

        assert result is True


class TestNVMeSanitize:
    """测试 NVMe Sanitize 功能"""

    def test_sanitize_block_erase(self):
        """测试 Sanitize Block Erase 操作"""
        controller = NVMeController(controller_id=0)

        # 执行 block erase
        result = controller.sanitize_block_erase()

        assert result is True
        assert controller.status == "sanitizing"

    def test_sanitize_requires_ready_state(self):
        """测试 Sanitize 需要控制器处于 ready 状态"""
        controller = NVMeController(controller_id=0)
        controller.status = "error"

        # 尝试执行 sanitize
        result = controller.sanitize_block_erase()

        assert result is False

    def test_sanitize_after_reset(self):
        """测试 Reset 后执行 Sanitize"""
        controller = NVMeController(controller_id=0)

        # 先 reset
        controller.reset()

        # reset 后状态不是 ready，sanitize 应该失败
        result = controller.sanitize_block_erase()
        assert result is False


class TestNVMeQueueDepth:
    """测试 NVMe 队列深度配置"""

    def test_default_queue_depth(self):
        """测试默认队列深度"""
        controller = NVMeController(controller_id=0)

        assert controller.queue_depth == 256

    def test_queue_depth_configuration(self):
        """测试队列深度配置"""
        controller = NVMeController(controller_id=0)

        # 修改队列深度
        controller.queue_depth = 512

        assert controller.queue_depth == 512
