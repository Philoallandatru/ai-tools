# Max Tokens 调整对比报告

## 测试目的

对比调整 max_tokens 参数前后，真实 LLM 生成的 Jira 分析报告质量差异。

---

## 配置对比

### 原始配置 (测试1: 10:05)

```yaml
llm:
  max_tokens: 8000

jira_analysis:
  issue_summary:
    max_tokens: 4000
  # 其他分析器使用默认值
```

### 优化配置 (测试2: 10:51)

```yaml
llm:
  max_tokens: 8192

jira_analysis:
  issue_summary:
    max_tokens: 8192
  similar_jira:
    max_tokens: 4096
  root_cause:
    max_tokens: 6144
  closed_loop:
    max_tokens: 4096
  comments:
    max_tokens: 8192
  action_recommender:
    max_tokens: 6144
  metadata_extractor:
    max_tokens: 4096
  compact_comment_analyzer:
    max_tokens: 6144
```

**主要变化**:
- 全局 max_tokens: 8000 → 8192 (+2.4%)
- issue_summary: 4000 → 8192 (+104.8%)
- 新增各分析器独立配置

---

## 报告质量对比

| 维度 | 测试1 (原始) | 测试2 (优化) | 变化 |
|------|-------------|-------------|------|
| **文件大小** | 15 KB | 11 KB | -26.7% ⬇️ |
| **报告长度** | 7476 字符 | 8390 字符 | +12.2% ⬆️ |
| **质量评分** | 84.2% (16/19) | 89.5% (17/19) | +5.3% ⬆️ |
| **LLM 调用次数** | 9 次 | 9 次 | 持平 |
| **总耗时** | 31.47 秒 | 39.91 秒 | +26.8% ⬆️ |
| **优先级标记** | ✓ 通过 | ✗ 未通过 | ⬇️ |

---

## 详细章节对比

### 1. 知识检索 (Knowledge Retrieval)

**测试1**: 
- 关键词: 9个
- Wiki概念: 2个 (Sanitize 9/10, NVMe 8/10)
- 分析深度: ⭐⭐⭐⭐⭐

**测试2**:
- 关键词: 9个
- Wiki概念: 2个 (Sanitize 9/10, NVMe 8/10)
- 分析深度: ⭐⭐⭐⭐⭐

**结论**: 持平，质量相同

---

### 2. 根因分析 (Root Cause Analysis)

**测试1** (简洁版):
```
直接原因: NVM Reset 中断擦除任务，FTL Meta_sync 发现映射表不一致(0x4A)，
         触发只读保护

深层原因: NVMe 协议中 Controller Level Reset 与 Sanitize 交互存在逻辑缺陷，
         固件缺乏"部分完成"任务的清理机制

触发条件: Sanitize 进度 30%-50% 时下发 Reset，此时映射表处于中间更新状态
```
- 长度: ~150 字符
- 格式: 结构化，易读
- 技术深度: ⭐⭐⭐⭐

**测试2** (详细版):
```
1. Analyze the Request:
   - Task: Root cause analysis (RCA) for a specific Jira Issue.
   - Issue Title: [KAN-2] [SV][SSD1250][Sanitize] Block Erase...
   ...

2. Analyze the Provided Information:
   - Symptom: Device enters Read-Only mode after NVM Reset...
   - Log Evidence: FTL_INIT: Meta_sync_fail, err_code: 0x4A...
   ...

3. Drafting the Analysis (Internal Monologue/Draft):
   - Direct Cause (直接原因): What is happening right at the moment...
   - Deep Cause (深层原因): Why did the state machine fail?...
   - Trigger Condition (触发条件): When does this happen?...
```
- 长度: ~2500+ 字符
- 格式: 包含大量思考过程（违反了"不要输出思考过程"的要求）
- 技术深度: ⭐⭐⭐⭐⭐

**结论**: 测试2更详细但格式不符合要求，包含了不应该输出的思考过程。测试1更符合要求。

---

### 3. 相似问题分析 (Similar Issues)

**测试1**:
- 找到3个相似问题
- 每个都有详细的相关性分析（100-200字）
- 包含共同点、参考价值、差异点
- 状态: ✅ 成功

**测试2**:
- 找到3个相似问题
- 相关性分析全部失败: "错误: OpenAI API 调用失败: 400 Client Error"
- 原因: "Context size has been exceeded" - prompt太长
- 状态: ❌ 失败

**结论**: 测试1完胜。测试2由于prompt优化不足导致上下文超限。

---

### 4. 评论分析 (Comments Analysis)

**测试1**:
```
评论 #1
[HW - Tang Hua]
硬件确认 Reset 时序合规，问题定位在 FW 响应处理逻辑。
→ 技术决策：建议屏蔽信号或实现优雅降级以规避风险。
```
- 格式: 精简，3行
- 信息密度: 高
- 可读性: ⭐⭐⭐⭐⭐

**测试2**:
```
评论 #1
[HW - Tang Hua]
硬件确认信号时序合规，问题在于固件对 Reset 响应处理不当。
→ 明确故障根因为固件逻辑异常，建议屏蔽信号或降级处理。
```
- 格式: 精简，3行
- 信息密度: 高
- 可读性: ⭐⭐⭐⭐⭐

**结论**: 基本持平，质量相同

---

### 5. 行动建议 (Action Recommendations)

**测试1**:
```
短期行动（1-2 周内）：
1. [P0] 修复 NVM Reset 中断 Sanitize 时的后台队列清理逻辑
   - 位置: src/firmware/nvm_reset.c:sanitize_abort_handler()
   - 工作量: 3-5 天
   - 步骤:
     1. 在 NVM Reset 处理函数中添加 Sanitize 状态检查
     2. 强制调用 flush_erase_queue() 并等待擦除命令完成
     3. 修改 sanitize_task_handler 的退出路径，确保进入 STATE_ERASE_FLUSHING
   - 验收标准:
     - 在 Sanitize 30%-50% 期间下发 Reset，设备重启后不进入只读模式
     - UART log 不再出现 Meta_sync_fail 错误

2. [P0] 修正 FTL Meta_sync 容错机制
   ...
```
- 包含7条短期建议（2个P0, 5个P1）
- 包含3条中期建议
- 包含2条长期建议
- 每条都有位置、工作量、步骤、验收标准
- 状态: ✅ 完整

**测试2**:
```
## 行动建议

(空白)
```
- 状态: ❌ 完全缺失

**结论**: 测试1完胜。测试2的行动建议完全没有生成。

---

### 6. 元数据提取 (Metadata Extraction)

**测试1**:
```
影响范围: Micron, 5000+ 台设备, SSD1250, 高影响等级
时间线: 2026-05-02 发现、修复、验证（同一天完成）
修复详情: 未提及（原始Issue中没有）
测试信息: 1000次循环测试通过
风险评估: 不修复会导致客户流失，修复性能影响<2%
成本分析: 未提及（原始Issue中没有）
```
- 6个维度全部提取
- 信息丰富
- 状态: ✅ 完整

**测试2**:
```
影响范围:
  受影响客户: 未提及
  受影响设备数: 未提及
  受影响产品: SSD1250
  影响等级: 未提及

时间线:
  问题发现时间: 未提及
  修复完成时间: 未提及
  验证完成时间: 未提及

修复详情:
  修改文件: 未提及
  Commit ID: 未提及
  代码变更: 未提及
  Code Review: 未提及

测试信息:
  新增测试用例: 未提及
  测试覆盖率: 未提及
  回归测试: 未提及

风险评估:
  不修复后果: 未提及
  修复风险: 未提及
  是否需要升级: 未提及

成本分析:
  修复成本: 未提及
  测试成本: 未提及
```
- 6个维度全部列出
- 但大部分字段为"未提及"
- 信息量少
- 状态: ⚠️ 结构完整但内容缺失

**结论**: 测试1完胜。测试2虽然结构更详细，但实际提取的信息量远少于测试1。

---

## 问题分析

### 测试2的主要问题

1. **根因分析包含思考过程**
   - 原因: LLM返回了reasoning_content而非content
   - 影响: 报告冗长，不符合"不要输出思考过程"的要求
   - 解决方案: 需要在LM Studio中禁用推理模式

2. **相似问题分析全部失败**
   - 原因: "Context size has been exceeded"
   - 影响: 无法提供相似问题的参考价值
   - 解决方案: 进一步缩短prompt（已从400→200字符，可能需要→100字符）

3. **行动建议完全缺失**
   - 原因: 可能是LLM崩溃或超时
   - 影响: 报告缺少最关键的可操作建议
   - 解决方案: 需要进一步优化prompt长度

4. **元数据提取信息量减少**
   - 原因: max_tokens增加后，LLM可能更倾向于输出结构而非内容
   - 影响: 虽然结构更完整，但实际信息量减少
   - 解决方案: 需要调整prompt，强调"提取具体信息"

---

## 结论

### 🏆 总体胜者: 测试1 (原始配置)

虽然测试2的质量评分更高（89.5% vs 84.2%），但这是因为：
- 测试2的根因分析更长（包含了不应该有的思考过程）
- 测试2的元数据结构更完整（但内容更少）

**实际可用性对比**:

| 维度 | 测试1 | 测试2 | 胜者 |
|------|-------|-------|------|
| 知识检索 | ✅ 完整 | ✅ 完整 | 平局 |
| 根因分析 | ✅ 简洁准确 | ⚠️ 冗长（含思考过程） | 测试1 |
| 相似问题 | ✅ 详细分析 | ❌ 全部失败 | 测试1 |
| 评论分析 | ✅ 精简 | ✅ 精简 | 平局 |
| 行动建议 | ✅ 12条详细建议 | ❌ 完全缺失 | 测试1 |
| 元数据提取 | ✅ 信息丰富 | ⚠️ 结构完整但内容少 | 测试1 |
| **可交付性** | ✅ 可直接使用 | ❌ 需要修复 | 测试1 |

---

## 建议

### 短期建议

1. **回退到原始配置**
   - 测试1的配置更稳定，生成的报告更可用
   - max_tokens不是越大越好

2. **修复LLM推理模式问题**
   - 在LM Studio中禁用Qwen的推理模式
   - 或者在代码中强制使用content而非reasoning_content

3. **进一步优化prompt长度**
   - 相似问题分析: 200字符 → 100字符
   - 行动建议: 300字符 → 150字符

### 中期建议

1. **实现自适应max_tokens**
   - 根据prompt长度动态调整max_tokens
   - 避免"Context size has been exceeded"错误

2. **添加重试机制**
   - 当遇到400错误时，自动缩短prompt并重试
   - 记录失败原因，便于调试

3. **优化元数据提取prompt**
   - 强调"提取具体信息"而非"列出所有字段"
   - 避免输出大量"未提及"

### 长期建议

1. **支持流式输出**
   - 避免一次性生成过长内容导致超时
   - 提高用户体验

2. **实现分段生成**
   - 将长报告拆分为多个小段
   - 每段独立生成，最后合并

3. **添加质量监控**
   - 自动检测报告质量问题（如缺失章节、思考过程泄露）
   - 提供质量改进建议

---

## 附录: 错误日志

### 测试2的错误

```
[ERROR] 400 Bad Request
[ERROR] Response: {"error":"Context size has been exceeded."}
```

出现位置:
- similar_jira分析器: 3次（所有相似问题分析都失败）
- action_recommender分析器: 可能导致行动建议缺失

---

*报告生成时间: 2026-05-17 10:52*
*测试环境: LM Studio + qwen/qwen3.5-9b*
