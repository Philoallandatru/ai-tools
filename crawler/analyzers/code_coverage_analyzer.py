"""
代码覆盖率分析器 - 分析问题涉及的代码路径和覆盖范围
"""

from typing import Dict, Any, List
from crawler.analyzers.configurable_base import ConfigurableAnalyzer
from crawler.analysis_context import AnalysisContext


class CodeCoverageAnalyzer(ConfigurableAnalyzer):
    """代码覆盖率分析器 - 识别问题涉及的代码模块、文件和函数"""

    def get_name(self) -> str:
        return "code_coverage"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行代码覆盖率分析

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含代码覆盖率分析结果的字典
        """
        self.log_progress("开始分析代码覆盖率...")

        # 1. 提取代码相关信息
        self.log_progress("提取代码引用...")
        code_references = self._extract_code_references(jira_data)

        if not code_references['has_code_info']:
            return {
                'has_code_coverage': False,
                'message': '该 Issue 未包含明确的代码路径信息'
            }

        # 2. 使用 LLM 分析代码覆盖范围
        self.log_progress("分析代码覆盖范围...")
        prompt = self._build_prompt(jira_data, code_references, context)
        response = self.call_llm(prompt, context, default_max_tokens=3000)

        # 3. 解析响应
        self.log_progress("解析分析结果...")
        result = self._parse_response(response, code_references)

        self.log_progress("分析完成")
        return result

    def _extract_code_references(self, jira_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 Issue 描述和评论中提取代码引用

        Args:
            jira_data: Jira 数据

        Returns:
            代码引用信息字典
        """
        import re

        # 合并描述和评论
        text = jira_data.get('description', '')
        for comment in jira_data.get('comments', []):
            text += '\n' + comment

        # 提取代码路径模式
        patterns = {
            'file_paths': r'(?:src/|include/|lib/|drivers/|kernel/|firmware/)[\w/]+\.(?:c|cpp|h|hpp|py|java|js|ts)',
            'functions': r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\([^\)]*\)',
            'modules': r'(?:module|组件|模块)s?[：:]\s*([A-Za-z0-9_\-\s,]+)',
            'classes': r'class\s+([A-Za-z_][a-zA-Z0-9_]*)',
            'commits': r'\b[0-9a-f]{7,40}\b',
        }

        references = {
            'file_paths': [],
            'functions': [],
            'modules': [],
            'classes': [],
            'commits': [],
        }

        for key, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # 去重并限制数量
                references[key] = list(set(matches))[:10]

        has_code_info = any(len(v) > 0 for v in references.values())

        return {
            'has_code_info': has_code_info,
            'references': references,
            'text_preview': text[:500]
        }

    def _build_prompt(
        self,
        jira_data: Dict[str, Any],
        code_references: Dict[str, Any],
        context: AnalysisContext
    ) -> str:
        """
        构建代码覆盖率分析提示词

        Args:
            jira_data: Jira 数据
            code_references: 代码引用信息
            context: 分析上下文

        Returns:
            提示词字符串
        """
        # 格式化代码引用
        refs = code_references['references']
        refs_text = []

        if refs['file_paths']:
            refs_text.append(f"文件路径: {', '.join(refs['file_paths'][:5])}")
        if refs['functions']:
            refs_text.append(f"函数: {', '.join(refs['functions'][:5])}")
        if refs['modules']:
            refs_text.append(f"模块: {', '.join(refs['modules'][:5])}")
        if refs['classes']:
            refs_text.append(f"类: {', '.join(refs['classes'][:5])}")
        if refs['commits']:
            refs_text.append(f"提交: {', '.join(refs['commits'][:3])}")

        refs_summary = '\n'.join(refs_text) if refs_text else '未找到明确的代码引用'

        # 获取根因上下文
        root_cause_summary = self.format_root_cause_context(context)

        prompt = f"""请分析以下 Jira Issue 涉及的代码覆盖范围：

Issue: [{jira_data['key']}] {jira_data['title']}

描述:
{jira_data['description'][:800]}

{root_cause_summary}

已识别的代码引用:
{refs_summary}

请从以下维度分析代码覆盖范围：

1. 核心模块：问题主要涉及哪些核心模块或子系统？
2. 关键文件：哪些源代码文件是问题的核心？
3. 影响范围：问题可能影响哪些相关模块或功能？
4. 测试覆盖：应该测试哪些代码路径以验证修复？

{self.build_chinese_requirements()}
- 按照以下格式回答：

核心模块：[列出 1-3 个核心模块]

关键文件：[列出 1-5 个关键文件，如果有的话]

影响范围：[描述可能受影响的其他模块或功能]

测试覆盖：[列出应该测试的关键代码路径]
"""
        return prompt

    def _parse_response(self, response: str, code_references: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本
            code_references: 代码引用信息

        Returns:
            解析后的结果字典
        """
        import re

        result = {
            'has_code_coverage': True,
            'core_modules': [],
            'key_files': [],
            'impact_scope': '',
            'test_coverage': '',
            'extracted_references': code_references['references'],
            'raw_response': response
        }

        # 提取核心模块
        modules_match = re.search(r'核心模块[：:]\s*(.+?)(?=\n\n|关键文件|$)', response, re.DOTALL)
        if modules_match:
            modules_text = modules_match.group(1).strip()
            # 提取列表项
            modules = re.findall(r'[-•]\s*(.+?)(?=\n|$)', modules_text)
            if not modules:
                # 如果没有列表项，按逗号分割
                modules = [m.strip() for m in modules_text.split('、') if m.strip()]
            result['core_modules'] = modules[:5]

        # 提取关键文件
        files_match = re.search(r'关键文件[：:]\s*(.+?)(?=\n\n|影响范围|$)', response, re.DOTALL)
        if files_match:
            files_text = files_match.group(1).strip()
            files = re.findall(r'[-•]\s*(.+?)(?=\n|$)', files_text)
            if not files:
                files = [f.strip() for f in files_text.split('、') if f.strip()]
            result['key_files'] = files[:10]

        # 提取影响范围
        impact_match = re.search(r'影响范围[：:]\s*(.+?)(?=\n\n|测试覆盖|$)', response, re.DOTALL)
        if impact_match:
            result['impact_scope'] = impact_match.group(1).strip()

        # 提取测试覆盖
        test_match = re.search(r'测试覆盖[：:]\s*(.+?)(?=\n\n|$)', response, re.DOTALL)
        if test_match:
            result['test_coverage'] = test_match.group(1).strip()

        return result
