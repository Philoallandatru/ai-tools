"""
Prompt 模板系统 - 提供可复用的 prompt 模板和工具函数
"""

from typing import Dict, Any, List, Optional


class PromptTemplate:
    """Prompt 模板基类"""

    @staticmethod
    def format_issue_header(jira_data: Dict[str, Any], include_priority: bool = True) -> str:
        """
        格式化 Issue 头部信息（精简版）

        Args:
            jira_data: Jira 数据
            include_priority: 是否包含优先级

        Returns:
            格式化的头部字符串
        """
        parts = [
            f"Issue: [{jira_data['key']}] {jira_data['title']}",
            f"状态: {jira_data['status']}"
        ]

        if include_priority:
            parts.append(f"优先级: {jira_data['priority']}")

        return "\n".join(parts)

    @staticmethod
    def format_description(jira_data: Dict[str, Any], max_length: int = 1000) -> str:
        """
        格式化描述（带长度限制）

        Args:
            jira_data: Jira 数据
            max_length: 最大长度

        Returns:
            格式化的描述
        """
        description = jira_data.get('description', '无描述')
        if len(description) > max_length:
            return f"描述:\n{description[:max_length]}...(已截断)"
        return f"描述:\n{description}"

    @staticmethod
    def format_comments(jira_data: Dict[str, Any], max_comments: int = 5, max_length: int = 2000) -> str:
        """
        格式化评论（带数量和长度限制）

        Args:
            jira_data: Jira 数据
            max_comments: 最大评论数
            max_length: 最大总长度

        Returns:
            格式化的评论
        """
        comments = jira_data.get('comments', [])
        if not comments:
            return ""

        comments_text = '\n---\n'.join(comments[:max_comments])
        if len(comments_text) > max_length:
            comments_text = comments_text[:max_length] + '\n...(已截断)'

        return f"\n评论 (共 {len(comments)} 条，显示前 {min(max_comments, len(comments))} 条):\n{comments_text}"

    @staticmethod
    def build_output_format_instruction(format_example: str) -> str:
        """
        构建输出格式指令（精简版）

        Args:
            format_example: 格式示例

        Returns:
            格式指令
        """
        return f"\n输出格式:\n{format_example}"

    @staticmethod
    def build_requirements(custom_requirements: Optional[List[str]] = None) -> str:
        """
        构建通用要求（精简版）

        Args:
            custom_requirements: 自定义要求列表

        Returns:
            要求字符串
        """
        base_requirements = [
            "直接输出结果，不要包含思考过程",
            "使用简洁的语言",
            "如果信息不足，标注'未提及'"
        ]

        if custom_requirements:
            base_requirements.extend(custom_requirements)

        return "\n要求:\n" + "\n".join(f"- {req}" for req in base_requirements)


class MetadataPromptTemplate(PromptTemplate):
    """元数据提取 Prompt 模板"""

    @staticmethod
    def build(jira_data: Dict[str, Any], context_info: str = "") -> str:
        """
        构建元数据提取 prompt（优化版 - 更精简）

        Args:
            jira_data: Jira 数据
            context_info: 上下文信息

        Returns:
            Prompt 字符串
        """
        header = PromptTemplate.format_issue_header(jira_data)
        description = PromptTemplate.format_description(jira_data, max_length=800)
        comments = PromptTemplate.format_comments(jira_data, max_comments=5, max_length=1500)

        context_section = f"\n上下文:\n{context_info}" if context_info else ""

        # 更精简的字段列表
        fields = """
提取信息（未提及标"未提及"）：

1. 影响: 客户名/设备数/严重程度
2. 时间: 发现/修复/验证时间，总耗时
3. 修复: 文件/Commit/代码量/Review
4. 测试: 用例/覆盖率/自动化/回归
5. 风险: 不修复后果/修复风险/需升级
6. 成本: 修复/测试/支持（人天）
"""

        format_example = """
## 影响范围
- 客户: ...
- 设备数: ...
- 严重程度: ...

## 时间线
- 发现: ...
- 修复: ...
- 验证: ...
- 耗时: ...

(其他部分类似)
"""

        requirements = PromptTemplate.build_requirements([
            "提取准确数字和时间"
        ])

        return f"""{header}
{context_section}
{description}
{comments}

{fields}
{PromptTemplate.build_output_format_instruction(format_example)}
{requirements}"""


class ClosedLoopPromptTemplate(PromptTemplate):
    """闭环检查 Prompt 模板"""

    @staticmethod
    def build(jira_data: Dict[str, Any], root_cause_summary: str = "") -> str:
        """
        构建闭环检查 prompt（优化版 - 更精简）

        Args:
            jira_data: Jira 数据
            root_cause_summary: 根因摘要

        Returns:
            Prompt 字符串
        """
        header = PromptTemplate.format_issue_header(jira_data, include_priority=False)
        description = PromptTemplate.format_description(jira_data, max_length=600)
        comments = PromptTemplate.format_comments(jira_data, max_comments=8, max_length=2000)

        root_cause_section = f"\n{root_cause_summary}" if root_cause_summary else ""

        check_items = """
检查三项并提供证据：

1. 根因识别：是否明确根本原因？引用具体描述
2. 修复方案：是否实施修复？引用具体内容
3. 验证测试：是否测试通过？引用测试数据（设备数/成功率）
   注意：需明确测试数据才判"是"
"""

        format_example = """
根因识别：是/否
证据：[内容]

修复方案：是/否
证据：[内容]

验证测试：是/否
证据：[内容或"无"]

结论：已闭环/未闭环
"""

        requirements = PromptTemplate.build_requirements([
            "严格按格式输出"
        ])

        return f"""{header}
{description}
{root_cause_section}
{comments}

{check_items}
{PromptTemplate.build_output_format_instruction(format_example)}
{requirements}"""


class ActionRecommenderPromptTemplate(PromptTemplate):
    """行动建议 Prompt 模板"""

    @staticmethod
    def build(jira_data: Dict[str, Any], context_summary: str = "") -> str:
        """
        构建行动建议 prompt（优化版）

        Args:
            jira_data: Jira 数据
            context_summary: 上下文摘要

        Returns:
            Prompt 字符串
        """
        header = PromptTemplate.format_issue_header(jira_data)
        description = PromptTemplate.format_description(jira_data, max_length=800)

        context_section = f"\n分析结果:\n{context_summary}" if context_summary else ""

        instruction = """
基于以上信息，提供3类行动建议：

1. 短期行动（1-2周）：立即可执行的改进
2. 中期行动（1-3月）：流程和工具优化
3. 长期行动（3月+）：系统性改进

每类2-3条，具体可执行。
"""

        format_example = """
## 短期行动
- 建议1: ...
- 建议2: ...

## 中期行动
- 建议1: ...
- 建议2: ...

## 长期行动
- 建议1: ...
- 建议2: ...
"""

        requirements = PromptTemplate.build_requirements([
            "建议具体可执行",
            "避免空泛建议"
        ])

        return f"""{header}
{description}
{context_section}

{instruction}
{PromptTemplate.build_output_format_instruction(format_example)}
{requirements}"""


class RootCausePromptTemplate(PromptTemplate):
    """根因分析 Prompt 模板"""

    @staticmethod
    def build(jira_data: Dict[str, Any], knowledge_context: str = "") -> str:
        """
        构建根因分析 prompt（优化版 - 更精简）

        Args:
            jira_data: Jira 数据
            knowledge_context: 知识库上下文

        Returns:
            Prompt 字符串
        """
        header = PromptTemplate.format_issue_header(jira_data)
        description = PromptTemplate.format_description(jira_data, max_length=800)
        comments = PromptTemplate.format_comments(jira_data, max_comments=6, max_length=2000)

        knowledge_section = f"\n参考:\n{knowledge_context}" if knowledge_context else ""

        instruction = """
分析根本原因：

1. 直接原因：直接导致问题的原因
2. 深层原因：背后的系统性原因
3. 触发条件：问题出现的条件
"""

        format_example = """
## 根因分析
1. 直接原因：...
2. 深层原因：...
3. 触发条件：...
"""

        requirements = PromptTemplate.build_requirements([
            "分析要具体深入"
        ])

        return f"""{header}
{description}
{comments}
{knowledge_section}

{instruction}
{PromptTemplate.build_output_format_instruction(format_example)}
{requirements}"""


# 导出所有模板
__all__ = [
    'PromptTemplate',
    'MetadataPromptTemplate',
    'ClosedLoopPromptTemplate',
    'ActionRecommenderPromptTemplate',
    'RootCausePromptTemplate',
]
