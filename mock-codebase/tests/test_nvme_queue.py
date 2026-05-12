"""
NVMe Queue 管理测试用例
"""
import pytest


class NVMeQueue:
    """NVMe 队列类（用于测试）"""

    def __init__(self, queue_id: int, queue_size: int):
        self.queue_id = queue_id
        self.queue_size = queue_size
        self.entries = []

    def submit_command(self, command: dict) -> bool:
        """提交命令到队列"""
        if len(self.entries) >= self.queue_size:
            return False
        self.entries.append(command)
        return True

    def get_completion(self) -> dict:
        """获取完成队列条目"""
        if not self.entries:
            return None
        return self.entries.pop(0)


class TestNVMeSubmissionQueue:
    """测试 NVMe Submission Queue"""

    def test_create_submission_queue(self):
        """测试创建提交队列"""
        sq = NVMeQueue(queue_id=1, queue_size=64)

        assert sq.queue_id == 1
        assert sq.queue_size == 64

    def test_submit_command_to_queue(self):
        """测试向队列提交命令"""
        sq = NVMeQueue(queue_id=1, queue_size=64)

        result = sq.submit_command({"opcode": 0x00, "cid": 1})

        assert result is True
        assert len(sq.entries) == 1

    def test_queue_full_scenario(self):
        """测试队列满的场景"""
        sq = NVMeQueue(queue_id=1, queue_size=2)

        # 填满队列
        sq.submit_command({"opcode": 0x00, "cid": 1})
        sq.submit_command({"opcode": 0x00, "cid": 2})

        # 再次提交应该失败
        result = sq.submit_command({"opcode": 0x00, "cid": 3})

        assert result is False

    def test_submission_queue_depth(self):
        """测试提交队列深度配置"""
        # 测试不同的队列深度
        for depth in [16, 32, 64, 128, 256]:
            sq = NVMeQueue(queue_id=1, queue_size=depth)
            assert sq.queue_size == depth


class TestNVMeCompletionQueue:
    """测试 NVMe Completion Queue"""

    def test_get_completion_from_queue(self):
        """测试从完成队列获取条目"""
        cq = NVMeQueue(queue_id=1, queue_size=64)
        cq.entries.append({"status": 0x00, "cid": 1})

        completion = cq.get_completion()

        assert completion is not None
        assert completion["cid"] == 1

    def test_empty_completion_queue(self):
        """测试空的完成队列"""
        cq = NVMeQueue(queue_id=1, queue_size=64)

        completion = cq.get_completion()

        assert completion is None

    def test_completion_queue_processing(self):
        """测试完成队列处理流程"""
        cq = NVMeQueue(queue_id=1, queue_size=64)

        # 添加多个完成条目
        cq.entries.append({"status": 0x00, "cid": 1})
        cq.entries.append({"status": 0x00, "cid": 2})
        cq.entries.append({"status": 0x00, "cid": 3})

        # 按顺序处理
        completions = []
        while True:
            comp = cq.get_completion()
            if comp is None:
                break
            completions.append(comp)

        assert len(completions) == 3
        assert completions[0]["cid"] == 1
        assert completions[2]["cid"] == 3


class TestNVMeQueuePair:
    """测试 NVMe Queue Pair（SQ + CQ）"""

    def test_queue_pair_creation(self):
        """测试创建队列对"""
        sq = NVMeQueue(queue_id=1, queue_size=64)
        cq = NVMeQueue(queue_id=1, queue_size=64)

        assert sq.queue_id == cq.queue_id

    def test_command_submission_and_completion(self):
        """测试命令提交和完成流程"""
        sq = NVMeQueue(queue_id=1, queue_size=64)
        cq = NVMeQueue(queue_id=1, queue_size=64)

        # 提交命令
        sq.submit_command({"opcode": 0x02, "cid": 100})

        # 模拟命令完成
        cq.entries.append({"status": 0x00, "cid": 100})

        # 获取完成
        completion = cq.get_completion()

        assert completion["cid"] == 100
        assert completion["status"] == 0x00

    def test_multiple_queue_pairs(self):
        """测试多个队列对"""
        queue_pairs = []

        for i in range(4):
            sq = NVMeQueue(queue_id=i, queue_size=32)
            cq = NVMeQueue(queue_id=i, queue_size=32)
            queue_pairs.append((sq, cq))

        assert len(queue_pairs) == 4
        assert queue_pairs[0][0].queue_id == 0
        assert queue_pairs[3][0].queue_id == 3
