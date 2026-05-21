# 测试文档 - 检索日志演示

## NVMe 控制器重置

NVMe 控制器重置是一个关键的错误恢复机制。当控制器遇到严重错误时，需要执行重置操作来恢复正常状态。

重置过程包括以下步骤：
1. 设置 CC.EN 为 0 禁用控制器
2. 等待 CSTS.RDY 变为 0
3. 重新初始化控制器
4. 设置 CC.EN 为 1 启用控制器

## Write Cache 状态切换

Write Cache 功能允许 SSD 在内存中缓存写入数据，提高写入性能。状态切换需要确保数据一致性。

关键 API：
- `nvme_set_features()` - 设置 Write Cache 状态
- `flush_cache()` - 刷新缓存数据到持久化存储
