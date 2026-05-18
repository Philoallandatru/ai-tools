"""
闭环检查器 - 检查问题是否已闭环
"""

from typing import Dict, Any, Optional
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient
from crawler.prompt_templates import ClosedLoopPromptTemplate


class ClosedLoopChecker(ConfigurableAnalyzer):
    """闭环检查器 - 检查根因识别、修复方案和验证测试"""

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
        # 1. 基础检查（基于状态）
        self.log_progress("检查状态...")
        status = jira_data.get('status', '').lower()
        is_closed_by_status = status in ['完成', 'done', '已解决', 'resolved', 'closed']

        # 2. 内容检查（使用 LLM）
        self.log_progress("构建提示词...")
        prompt = self._build_prompt(jira_data, context)

        self.log_progress("调用 LLM...")
        response = self.call_llm(prompt, context, default_max_tokens=3000)

        self.log_progress("解析响应...")
        result = self._parse_response(response)
        result['is_closed_by_status'] = is_closed_by_status

        # 3. 综合判断
        self.log_progress("综合判断...")
        result['is_closed'] = (
            is_closed_by_status and
            result.get('has_root_cause', False) and
            result.get('has_fix', False) and
            result.get('has_verification', False)
        )

        self.log_progress("分析完成")
        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建闭环检查提示词（使用优化的模板）

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 使用基类的根因上下文格式化
        root_cause_summary = self.format_root_cause_context(context)

        # 使用优化的模板
        return ClosedLoopPromptTemplate.build(jira_data, root_cause_summary)

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
            'root_cause_evidence': '',
            'fix_note': '',
            'fix_evidence': '',
            'verification_note': '',
            'verification_evidence': '',
            'conclusion': '',
            'raw_response': response
        }

        # 提取根因识别
        root_cause_match = re.search(r'根因识别[：:]\s*(是|否)\s*\n证据[：:]\s*(.+?)(?=\n\n|修复方案|$)', response, re.DOTALL)
        if root_cause_match:
            result['has_root_cause'] = root_cause_match.group(1) == '是'
            evidence = root_cause_match.group(2).strip()
            result['root_cause_evidence'] = evidence
            result['root_cause_note'] = evidence if len(evidence) < 200 else evidence[:200] + '...'

        # 提取修复方案
        fix_match = re.search(r'修复方案[：:]\s*(是|否)\s*\n证据[：:]\s*(.+?)(?=\n\n|验证测试|$)', response, re.DOTALL)
        if fix_match:
            result['has_fix'] = fix_match.group(1) == '是'
            evidence = fix_match.group(2).strip()
            result['fix_evidence'] = evidence
            result['fix_note'] = evidence if len(evidence) < 200 else evidence[:200] + '...'

        # 提取验证测试
        verification_match = re.search(r'验证测试[：:]\s*(是|否)\s*\n证据[：:]\s*(.+?)(?=\n\n|结论|$)', response, re.DOTALL)
        if verification_match:
            result['has_verification'] = verification_match.group(1) == '是'
            evidence = verification_match.group(2).strip()
            result['verification_evidence'] = evidence

            # 额外验证：如果证据中包含"无"或"没有"等否定词，强制设为 False
            if evidence.lower() in ['无', '无明确测试数据', '没有', '未找到']:
                result['has_verification'] = False
                result['verification_note'] = '未找到明确的测试证据'
            else:
                result['verification_note'] = evidence if len(evidence) < 200 else evidence[:200] + '...'

        # 提取结论
        conclusion_match = re.search(r'结论[：:]\s*(.+?)(?=\n|$)', response, re.DOTALL)
        if conclusion_match:
            result['conclusion'] = conclusion_match.group(1).strip()

        return result
