/**
 * NVMe JavaScript 测试用例
 */

describe('NVMe Controller Tests', () => {
  describe('Controller Reset', () => {
    it('should reset controller successfully', () => {
      const controller = new NVMeController(0);

      const result = controller.reset(30);

      expect(result).toBe(true);
      expect(controller.status).toBe('reset');
    });

    it('should clear CC.EN register on reset', () => {
      const controller = new NVMeController(0);

      controller.reset();

      // Verify CC.EN is cleared
      expect(controller.ccEnable).toBe(false);
    });

    it('should poll CSTS.RDY after reset', () => {
      const controller = new NVMeController(0);

      const result = controller.reset(30);

      expect(result).toBe(true);
      expect(controller.cstsReady).toBe(true);
    });
  });

  describe('Sanitize Operations', () => {
    it('should perform sanitize block erase', () => {
      const controller = new NVMeController(0);

      const result = controller.sanitizeBlockErase();

      expect(result).toBe(true);
      expect(controller.status).toBe('sanitizing');
    });

    it('should fail sanitize when not ready', () => {
      const controller = new NVMeController(0);
      controller.status = 'error';

      const result = controller.sanitizeBlockErase();

      expect(result).toBe(false);
    });
  });
});

describe('NVMe Transport Tests', () => {
  describe('RDMA Transport', () => {
    it('should connect via RDMA', () => {
      const transport = new RDMATransport();

      const result = transport.connect('192.168.1.100', 4420);

      expect(result).toBe(true);
      expect(transport.connected).toBe(true);
    });

    it('should setup RDMA queue pair', () => {
      const transport = new RDMATransport();

      const result = transport.setupQueuePair();

      expect(result).toBe(true);
      expect(transport.qpNum).toBeGreaterThan(0);
    });

    it('should send command over RDMA fabric', () => {
      const transport = new RDMATransport();
      transport.setupQueuePair();
      transport.connect('nvme-target.local', 4420);

      const response = transport.sendCommand({
        opcode: 0x01,
        nsid: 1,
        slba: 0,
        nlb: 8
      });

      expect(response.status).toBe('success');
    });
  });

  describe('TCP Transport', () => {
    it('should connect via TCP', () => {
      const transport = new TCPTransport();

      const result = transport.connect('192.168.1.100', 8009);

      expect(result).toBe(true);
    });

    it('should enable TLS encryption', () => {
      const transport = new TCPTransport();

      const result = transport.enableTLS();

      expect(result).toBe(true);
    });
  });
});

describe('NVMe Queue Tests', () => {
  describe('Submission Queue', () => {
    it('should create submission queue with correct depth', () => {
      const sq = new NVMeQueue(1, 64);

      expect(sq.queueId).toBe(1);
      expect(sq.queueSize).toBe(64);
    });

    it('should submit command to queue', () => {
      const sq = new NVMeQueue(1, 64);

      const result = sq.submitCommand({ opcode: 0x00, cid: 1 });

      expect(result).toBe(true);
      expect(sq.entries.length).toBe(1);
    });

    it('should handle queue full scenario', () => {
      const sq = new NVMeQueue(1, 2);
      sq.submitCommand({ opcode: 0x00, cid: 1 });
      sq.submitCommand({ opcode: 0x00, cid: 2 });

      const result = sq.submitCommand({ opcode: 0x00, cid: 3 });

      expect(result).toBe(false);
    });
  });

  describe('Completion Queue', () => {
    it('should get completion from queue', () => {
      const cq = new NVMeQueue(1, 64);
      cq.entries.push({ status: 0x00, cid: 1 });

      const completion = cq.getCompletion();

      expect(completion).not.toBeNull();
      expect(completion.cid).toBe(1);
    });

    it('should return null for empty queue', () => {
      const cq = new NVMeQueue(1, 64);

      const completion = cq.getCompletion();

      expect(completion).toBeNull();
    });
  });
});
