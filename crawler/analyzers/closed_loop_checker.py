"""
闭环检查器 - 检查问题是否已闭环
"""

from typing import Dict, Any, Optional
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.llm_utils import clean_llm_output


class ClosedLoopChecker(BaseAnalyzer):
    """闭环检查器 - 检查根因识别、修复方案和验证测试"""

    def __init__(self, llm_client: BaseLLMClient, config: Optional[Dict[str, Any]] = None):
        """
        初始化闭环检查器

        Args:
            llm_client: LLM 客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}

    def get_name(self) -> str:
        return "closed_loop"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行闭环检查

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含闭环检查结果的字典
        """
        import sys

        # 1. 基础检查（基于状态）
        print("   [closed_loop] 检查状态...", flush=True)
        status = jira_data.get('status', '').lower()
        is_closed_by_status = status in ['完成', 'done', '已解决', 'resolved', 'closed']

        # 2. 内容检查（使用 LLM）
        print("   [closed_loop] 构建提示词...", flush=True)
        prompt = self._build_prompt(jira_data, context)
        print("   [closed_loop] 调用 LLM...", flush=True)
        context.increment_llm_calls()
        max_tokens = self.config.get('max_tokens', 3000)
        response = self.llm_client.generate(prompt, max_tokens=max_tokens)
        print("   [closed_loop] LLM 响应完成", flush=True)

        # 清理输出
        print("   [closed_loop] 清理输出...", flush=True)
        response = clean_llm_output(response)

        # 3. 解析响应
        print("   [closed_loop] 解析响应...", flush=True)
        result = self._parse_response(response)
        result['is_closed_by_status'] = is_closed_by_status

        # 4. 综合判断
        print("   [closed_loop] 综合判断...", flush=True)
        result['is_closed'] = (
            is_closed_by_status and
            result.get('has_root_cause', False) and
            result.get('has_fix', False) and
            result.get('has_verification', False)
        )

        print("   [closed_loop] 分析完成", flush=True)
        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建闭环检查提示词

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 获取根因分析结果
        root_cause = context.get_result('root_cause')
        root_cause_summary = ""
        if root_cause:
            root_cause_summary = f"\n已识别的根因:\n{root_cause.get('direct_cause', 'N/A')}\n"

        # 获取评论内容
        comments_text = ""
        if jira_data.get('comments'):
            comments_text = "\n评论内容:\n" + "\n---\n".join(jira_data['comments'][:5])

        prompt = f"""请检查以下 Jira Issue 是否已形成闭环：

Issue: [{jira_data['key']}] {jira_data['title']}
状态: {jira_data['status']}

描述:
{jira_data['description'][:800]}

{root_cause_summary}

{comments_text}

请检查以下三个方面：
1. 根因识别：是否明确识别了问题的根本原因？
2. 修复方案：是否提出并实施了修复方案？
3. 验证测试：是否进行了验证测试并通过？

要求：
- 必须用中文回答
- 直接输出分析结果，不要输出思考过程
- 不要使用 <think> 标签
- 按照以下格式回答：

- 根因识别：是/否，说明
- 修复方案：是/否，说明
- 验证测试：是/否，说明
- 结论：已闭环/未闭环
"""
        return prompt

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        import re

        result = {
            'has_root_cause': False,
            'has_fix': False,
            'has_verification': False,
            'root_cause_note': '',
            'fix_note': '',
            'verification_note': '',
            'conclusion': '',
            'raw_response': response
        }

        # 提取各项检查结果
        root_cause_match = re.search(r'根因识别[：:]\s*(是|否)[，,]?\s*(.+?)(?=\n|修复方案|$)', response, re.DOTALL)
        fix_match = re.search(r'修复方案[：:]\s*(是|否)[，,]?\s*(.+?)(?=\n|验证测试|$)', response, re.DOTALL)
        verification_match = re.search(r'验证测试[：:]\s*(是|否)[，,]?\s*(.+?)(?=\n|结论|$)', response, re.DOTALL)
        conclusion_match = re.search(r'结论[：:]\s*(.+?)(?=\n|$)', response, re.DOTALL)

        if root_cause_match:
            result['has_root_cause'] = root_cause_match.group(1) == '是'
            result['root_cause_note'] = root_cause_match.group(2).strip()

        if fix_match:
            result['has_fix'] = fix_match.group(1) == '是'
            result['fix_note'] = fix_match.group(2).strip()

        if verification_match:
            result['has_verification'] = verification_match.group(1) == '是'
            result['verification_note'] = verification_match.group(2).strip()

        if conclusion_match:
            result['conclusion'] = conclusion_match.group(1).strip()

        return result
