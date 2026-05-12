"""
NVMe Transport 层测试用例
"""
import pytest
from src.nvme_transport import NVMeTransport, RDMATransport, TCPTransport


class TestNVMeTransportBase:
    """测试 NVMe Transport 基础功能"""

    def test_transport_connect(self):
        """测试传输层连接"""
        transport = NVMeTransport("RDMA")

        result = transport.connect("192.168.1.100", 4420)

        assert result is True
        assert transport.connected is True

    def test_transport_disconnect(self):
        """测试传输层断开连接"""
        transport = NVMeTransport("RDMA")
        transport.connect("192.168.1.100", 4420)

        transport.disconnect()

        assert transport.connected is False

    def test_send_command_without_connection(self):
        """测试未连接时发送命令"""
        transport = NVMeTransport("RDMA")

        with pytest.raises(ConnectionError):
            transport.send_command({"opcode": 0x00})

    def test_send_command_with_connection(self):
        """测试连接后发送命令"""
        transport = NVMeTransport("RDMA")
        transport.connect("192.168.1.100", 4420)

        response = transport.send_command({"opcode": 0x00})

        assert response["status"] == "success"


class TestRDMATransport:
    """测试 RDMA 传输实现"""

    def test_rdma_transport_type(self):
        """测试 RDMA 传输类型"""
        transport = RDMATransport()

        assert transport.transport_type == "RDMA"

    def test_rdma_queue_pair_setup(self):
        """测试 RDMA Queue Pair 设置"""
        transport = RDMATransport()

        result = transport.setup_queue_pair()

        assert result is True
        assert transport.qp_num > 0

    def test_rdma_connect_and_send(self):
        """测试 RDMA 连接并发送命令"""
        transport = RDMATransport()
        transport.setup_queue_pair()
        transport.connect("192.168.1.100", 4420)

        response = transport.send_command({"opcode": 0x02, "nsid": 1})

        assert response["status"] == "success"


class TestTCPTransport:
    """测试 TCP 传输实现"""

    def test_tcp_transport_type(self):
        """测试 TCP 传输类型"""
        transport = TCPTransport()

        assert transport.transport_type == "TCP"

    def test_tcp_tls_enable(self):
        """测试 TCP TLS 加密"""
        transport = TCPTransport()

        result = transport.enable_tls()

        assert result is True

    def test_tcp_connect_with_tls(self):
        """测试启用 TLS 的 TCP 连接"""
        transport = TCPTransport()
        transport.enable_tls()

        result = transport.connect("192.168.1.100", 8009)

        assert result is True
        assert transport.connected is True


class TestNVMeFabrics:
    """测试 NVMe over Fabrics 场景"""

    def test_fabric_rdma_connection(self):
        """测试 Fabric RDMA 连接"""
        transport = RDMATransport()
        transport.setup_queue_pair()

        # 连接到 NVMe target
        result = transport.connect("nvme-target.local", 4420)

        assert result is True

    def test_fabric_tcp_connection(self):
        """测试 Fabric TCP 连接"""
        transport = TCPTransport()
        transport.enable_tls()

        # 连接到 NVMe target
        result = transport.connect("nvme-target.local", 8009)

        assert result is True

    def test_fabric_command_submission(self):
        """测试 Fabric 命令提交"""
        transport = RDMATransport()
        transport.setup_queue_pair()
        transport.connect("nvme-target.local", 4420)

        # 提交 I/O 命令
        response = transport.send_command({
            "opcode": 0x01,  # Write
            "nsid": 1,
            "slba": 0,
            "nlb": 8
        })

        assert response["status"] == "success"
