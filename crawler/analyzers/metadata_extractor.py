"""
元数据提取器 - 提取 Jira Issue 的关键元数据信息

提取以下信息：
1. 影响范围：受影响客户、设备数、产品型号
2. 时间线：问题发现/修复/验证时间、总耗时
3. 修复详情：修改文件、Commit ID、代码变更、Code Review
4. 测试信息：测试用例、覆盖率、自动化测试、回归测试
5. 风险评估：不修复后果、修复风险、升级需求
6. 成本分析：修复成本、测试成本、支持成本
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.prompt_templates import MetadataPromptTemplate


class MetadataExtractor(ConfigurableAnalyzer):
    """元数据提取器 - 提取 Issue 的关键元数据信息"""

    def get_name(self) -> str:
        return "metadata"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        提取元数据信息

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含元数据的字典
        """
        # 构建提示词
        prompt = self._build_prompt(jira_data, context)

        # 调用 LLM
        response = self.call_llm(prompt, context, default_max_tokens=1500)

        # 解析响应
        result = self._parse_response(response)

        # 补充从 Jira 字段直接提取的信息
        result['impact']['affected_products'] = self._extract_affected_products(jira_data)
        result['timeline']['created'] = jira_data.get('created', '未知')
        result['timeline']['updated'] = jira_data.get('updated', '未知')
        result['timeline']['resolved'] = jira_data.get('resolved', '未知')

        return result

    def _build_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建元数据提取提示词（使用优化的模板）

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 获取相关分析结果
        root_cause = context.get_result('root_cause')
        code_coverage = context.get_result('code_coverage')

        # 构建上下文信息（精简版）
        context_info = []

        if root_cause:
            direct_cause = root_cause.get('direct_cause', '')
            if direct_cause:
                context_info.append(f"根因: {direct_cause}")

        if code_coverage:
            files = code_coverage.get('code_references', {}).get('files', [])
            if files:
                context_info.append(f"涉及文件: {', '.join(files[:5])}")

        context_text = "\n".join(context_info) if context_info else ""

        # 使用优化的模板
        return MetadataPromptTemplate.build(jira_data, context_text)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        result = {
            'impact': {
                'affected_customers': '未提及',
                'affected_devices': '未提及',
                'severity': '未提及',
                'affected_products': []
            },
            'timeline': {
                'discovered': '未提及',
                'fixed': '未提及',
                'verified': '未提及',
                'total_time': '未提及',
                'created': '未知',
                'updated': '未知',
                'resolved': '未知'
            },
            'fix_details': {
                'modified_files': '未提及',
                'commit_id': '未提及',
                'code_changes': '未提及',
                'code_review': '未提及'
            },
            'test_info': {
                'test_cases': '未提及',
                'coverage': '未提及',
                'automation': '未提及',
                'regression': '未提及',
                'large_scale': '未提及'
            },
            'risk_assessment': {
                'no_fix_consequence': '未提及',
                'fix_risk': '未提及',
                'upgrade_required': '未提及'
            },
            'cost_analysis': {
                'fix_cost': '未提及',
                'test_cost': '未提及',
                'support_cost': '未提及'
            },
            'raw_response': response
        }

        # 提取影响范围
        impact_section = self._extract_section(response, '影响范围')
        if impact_section:
            result['impact']['affected_customers'] = self._extract_field(impact_section, '受影响客户')
            result['impact']['affected_devices'] = self._extract_field(impact_section, '受影响设备数')
            result['impact']['severity'] = self._extract_field(impact_section, '严重程度')

        # 提取时间线
        timeline_section = self._extract_section(response, '时间线')
        if timeline_section:
            result['timeline']['discovered'] = self._extract_field(timeline_section, '问题发现时间')
            result['timeline']['fixed'] = self._extract_field(timeline_section, '修复完成时间')
            result['timeline']['verified'] = self._extract_field(timeline_section, '验证完成时间')
            result['timeline']['total_time'] = self._extract_field(timeline_section, '总耗时')

        # 提取修复详情
        fix_section = self._extract_section(response, '修复详情')
        if fix_section:
            result['fix_details']['modified_files'] = self._extract_field(fix_section, '修改文件')
            result['fix_details']['commit_id'] = self._extract_field(fix_section, 'Commit ID')
            result['fix_details']['code_changes'] = self._extract_field(fix_section, '代码变更量')
            result['fix_details']['code_review'] = self._extract_field(fix_section, 'Code Review')

        # 提取测试信息
        test_section = self._extract_section(response, '测试信息')
        if test_section:
            result['test_info']['test_cases'] = self._extract_field(test_section, '测试用例')
            result['test_info']['coverage'] = self._extract_field(test_section, '测试覆盖率')
            result['test_info']['automation'] = self._extract_field(test_section, '自动化测试')
            result['test_info']['regression'] = self._extract_field(test_section, '回归测试')
            result['test_info']['large_scale'] = self._extract_field(test_section, '大规模验证')

        # 提取风险评估
        risk_section = self._extract_section(response, '风险评估')
        if risk_section:
            result['risk_assessment']['no_fix_consequence'] = self._extract_field(risk_section, '不修复后果')
            result['risk_assessment']['fix_risk'] = self._extract_field(risk_section, '修复风险')
            result['risk_assessment']['upgrade_required'] = self._extract_field(risk_section, '需要升级')

        # 提取成本分析
        cost_section = self._extract_section(response, '成本分析')
        if cost_section:
            result['cost_analysis']['fix_cost'] = self._extract_field(cost_section, '修复成本')
            result['cost_analysis']['test_cost'] = self._extract_field(cost_section, '测试成本')
            result['cost_analysis']['support_cost'] = self._extract_field(cost_section, '客户支持成本')

        return result

    def _extract_section(self, text: str, section_name: str) -> Optional[str]:
        """
        提取指定章节的内容

        Args:
            text: 文本
            section_name: 章节名称

        Returns:
            章节内容，如果未找到返回 None
        """
        # 匹配 ## 章节名称 到下一个 ## 或文本结尾
        pattern = rf'##\s*{re.escape(section_name)}\s*\n(.+?)(?=\n##|\Z)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_field(self, section: str, field_name: str) -> str:
        """
        从章节中提取字段值

        Args:
            section: 章节内容
            field_name: 字段名称

        Returns:
            字段值，如果未找到返回"未提及"
        """
        # 匹配 - 字段名: 值
        pattern = rf'-\s*{re.escape(field_name)}\s*[：:]\s*(.+?)(?=\n-|\Z)'
        match = re.search(pattern, section, re.DOTALL)
        if match:
            value = match.group(1).strip()
            # 清理多余的换行和空格
            value = re.sub(r'\s+', ' ', value)
            return value if value else '未提及'
        return '未提及'

    def _extract_affected_products(self, jira_data: Dict[str, Any]) -> List[str]:
        """
        从标题和标签中提取受影响的产品

        Args:
            jira_data: Jira 数据

        Returns:
            产品列表
        """
        products = set()

        # 从标题提取
        title = jira_data.get('title', '')
        # 匹配产品型号模式（如 SSD1420, SSD1700）
        product_pattern = r'\b(SSD\d{4}|[A-Z]{2,}\d{3,})\b'
        matches = re.findall(product_pattern, title)
        products.update(matches)

        # 从标签提取
        labels = jira_data.get('labels', [])
        for label in labels:
            matches = re.findall(product_pattern, label)
            products.update(matches)

        # 从组件提取
        components = jira_data.get('components', [])
        for component in components:
            matches = re.findall(product_pattern, component)
            products.update(matches)

        return sorted(list(products))
