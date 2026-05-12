"""
问题摘要分析器 - 提取 Jira Issue 的结构化摘要信息
"""

import re
import json
from typing import Dict, Any, List, Optional
from crawler.analyzers.base import BaseAnalyzer
from crawler.analysis_context import AnalysisContext
from crawler.llm_client import BaseLLMClient


class IssueSummaryAnalyzer(BaseAnalyzer):
    """问题摘要分析器 - 提取客户名称、测试项目、测试平台、测试步骤、根因、修复方案、代码覆盖检查"""

    def __init__(self, llm_client: BaseLLMClient, config: Optional[Dict[str, Any]] = None):
        """
        初始化问题摘要分析器

        Args:
            llm_client: LLM 客户端
            config: 配置字典
        """
        self.llm_client = llm_client
        self.config = config or {}
        self.use_llm = self.config.get('use_llm', True)  # 默认使用 LLM

    def get_name(self) -> str:
        return "issue_summary"

    def analyze(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Dict[str, Any]:
        """
        执行问题摘要分析

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            包含摘要信息的字典
        """
        # 优先使用 LLM 综合提取
        if self.use_llm:
            llm_result = self._extract_with_llm(jira_data, context)
            if llm_result:
                # LLM 提取成功，补充代码覆盖检查
                llm_result['code_coverage'] = self._extract_code_coverage(context)
                return llm_result

        # LLM 失败或禁用，使用 regex fallback
        result = {
            'customer': self._extract_customer(jira_data, context),
            'test_project': self._extract_test_project(jira_data),
            'test_platform': self._extract_test_platform(jira_data),
            'test_steps': self._extract_test_steps(jira_data),
            'root_cause': self._extract_root_cause(jira_data, context),
            'fix_solution': self._extract_fix_solution(jira_data, context),
            'code_coverage': self._extract_code_coverage(context)
        }

        return result

    def _extract_with_llm(self, jira_data: Dict[str, Any], context: AnalysisContext) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 综合提取所有字段

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            提取结果字典，失败返回 None
        """
        # 构建 prompt
        prompt = self._build_extraction_prompt(jira_data, context)

        try:
            # 调用 LLM
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=self.config.get('max_tokens', 1000),
                temperature=0.3  # 使用较低温度保证稳定性
            )

            if not response:
                return None

            # 解析 JSON 响应
            result = self._parse_llm_response(response)
            return result

        except Exception as e:
            print(f"LLM 提取失败: {e}")
            return None

    def _build_extraction_prompt(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        构建 LLM 提取 prompt

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            prompt 字符串
        """
        # 获取已有分析结果
        root_cause_result = context.get_result('root_cause')

        # 构建上下文信息
        title = jira_data.get('title', '')
        description = jira_data.get('description', '')
        comments = jira_data.get('comments', [])
        labels = jira_data.get('labels', [])

        # 限制评论长度
        comments_text = '\n\n'.join(comments[:10])  # 最多 10 条评论
        if len(comments_text) > 3000:
            comments_text = comments_text[:3000] + '...'

        prompt = f"""请从以下 Jira Issue 中提取结构化信息。

**Issue 标题**: {title}

**Issue 描述**:
{description[:2000]}

**评论** (共 {len(comments)} 条):
{comments_text}

**标签**: {', '.join(labels)}

请提取以下字段（如果某个字段找不到信息，返回"无"）：

1. **客户名称**: 从评论中提取客户公司名称（如 Micron, Dell, Samsung 等）
2. **测试项目**: 从标题和标签中提取产品型号和测试类型（如 SSD1250, Sanitize）
3. **测试平台**: 从描述的"测试环境"部分提取平台信息（Platform, OS, Form Factor）
4. **测试步骤**: 从描述的"复现步骤"或"测试步骤"部分提取步骤列表
5. **根因**: 从描述的"根因分析"部分或评论中提取根本原因
6. **修复方案**: 从描述的"修复方案"或评论中提取修复方法

**要求**:
- 直接输出 JSON 格式，不要包含任何其他文字
- 测试步骤以数组形式返回
- 所有输出必须为中文
- 如果某个字段找不到，返回"无"

**JSON 格式**:
```json
{{
  "customer": "客户名称或无",
  "test_project": "测试项目或无",
  "test_platform": "测试平台或无",
  "test_steps": ["步骤1", "步骤2"] 或 [],
  "root_cause": "根因或无",
  "fix_solution": "修复方案或无"
}}
```

请输出 JSON:"""

        return prompt

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 返回的 JSON 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典，失败返回 None
        """
        try:
            # 尝试提取 JSON（可能包含在 markdown 代码块中）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response.strip()

            # 解析 JSON
            result = json.loads(json_str)

            # 验证必需字段
            required_fields = ['customer', 'test_project', 'test_platform', 'test_steps', 'root_cause', 'fix_solution']
            for field in required_fields:
                if field not in result:
                    result[field] = '无' if field != 'test_steps' else []

            # 确保 test_steps 是列表
            if not isinstance(result['test_steps'], list):
                result['test_steps'] = []

            return result

        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"响应内容: {response[:500]}")
            return None
        except Exception as e:
            print(f"解析响应失败: {e}")
            return None

    def _extract_customer(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        从评论中提取客户名称

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            客户名称，如果未找到返回"无"
        """
        comments = jira_data.get('comments', [])

        # 客户名称匹配模式
        customer_patterns = [
            r'客户\s+([A-Z][a-zA-Z]+)',  # "客户 Micron"
            r'([A-Z][a-zA-Z]+)\s*客户',  # "Dell 客户"
            r'客户[:：]\s*([A-Z][a-zA-Z]+)',  # "客户: Dell"
            r'\[FAE[^\]]*\].*?客户\s+([A-Z][a-zA-Z]+)',  # "[FAE - Sun Yan] 客户 Dell"
            r'([A-Z][a-zA-Z]+)\s+[Cc]ustomer',  # "Dell customer"
            r'[Cc]ustomer[:：]\s*([A-Z][a-zA-Z]+)',  # "Customer: Dell"
        ]

        customers = set()

        for comment in comments:
            for pattern in customer_patterns:
                matches = re.findall(pattern, comment)
                for match in matches:
                    if match and len(match) > 2:  # 过滤太短的匹配
                        customers.add(match)

        if customers:
            return ', '.join(sorted(customers))

        return "无"

    def _extract_test_project(self, jira_data: Dict[str, Any]) -> str:
        """
        从标题和标签中提取测试项目

        Args:
            jira_data: Jira 数据

        Returns:
            测试项目，如果未找到返回"无"
        """
        title = jira_data.get('title', '')
        labels = jira_data.get('labels', [])

        # 从标题中提取方括号标签
        # 格式: [KAN-3] [SV][SSD1300][QoS] PCMark 10 性能衰减
        # 提取: SSD1300, QoS
        tag_pattern = r'\[([^\]]+)\]'
        tags = re.findall(tag_pattern, title)

        # 过滤掉 Issue Key 和团队标识
        filtered_tags = []
        exclude_patterns = [
            r'^[A-Z]+-\d+$',  # Issue Key (KAN-3)
            r'^[A-Z]{2,3}$',  # 团队标识 (SV, FW, FAE, DV)
        ]

        for tag in tags:
            is_excluded = False
            for exclude_pattern in exclude_patterns:
                if re.match(exclude_pattern, tag):
                    is_excluded = True
                    break
            if not is_excluded:
                filtered_tags.append(tag)

        # 合并标签和 labels
        all_tags = filtered_tags + labels

        if all_tags:
            return ', '.join(all_tags)

        return "无"

    def _extract_test_platform(self, jira_data: Dict[str, Any]) -> str:
        """
        从描述的测试环境部分提取测试平台

        Args:
            jira_data: Jira 数据

        Returns:
            测试平台，如果未找到返回"无"
        """
        description = jira_data.get('description', '')

        # 提取测试环境部分
        # 格式:
        # **测试环境**:
        # * Platform: Intel Alder Lake Notebook
        # * OS: Windows 11 23H2
        # * Form Factor: M.2 2230

        platform_info = []

        # 提取 Platform
        platform_match = re.search(r'[Pp]latform[:：]\s*([^\n*]+)', description)
        if platform_match:
            platform_info.append(f"Platform: {platform_match.group(1).strip()}")

        # 提取 OS
        os_match = re.search(r'OS[:：]\s*([^\n*]+)', description)
        if os_match:
            platform_info.append(f"OS: {os_match.group(1).strip()}")

        # 提取 Form Factor
        form_factor_match = re.search(r'Form Factor[:：]\s*([^\n*]+)', description)
        if form_factor_match:
            platform_info.append(f"Form Factor: {form_factor_match.group(1).strip()}")

        if platform_info:
            return ', '.join(platform_info)

        return "无"

    def _extract_test_steps(self, jira_data: Dict[str, Any]) -> List[str]:
        """
        从描述的复现步骤部分提取测试步骤

        Args:
            jira_data: Jira 数据

        Returns:
            测试步骤列表，如果未找到返回空列表
        """
        description = jira_data.get('description', '')

        # 提取复现步骤部分
        # 支持格式:
        # 1. Markdown: **复现步骤**: * 步骤1 * 步骤2
        # 2. Jira wiki: h3. 复现步骤 * 步骤1 * 步骤2

        # 查找复现步骤部分（Jira wiki 标记）
        steps_match = re.search(
            r'h3\.\s*(?:复现步骤|测试步骤|重现步骤)\s*\n+((?:\*[^\n]+\n?)+)',
            description,
            re.MULTILINE
        )

        if not steps_match:
            # 尝试 Markdown 格式
            steps_match = re.search(
                r'(?:\*\*)?(?:复现步骤|测试步骤|重现步骤)(?:\*\*)?[:：]\s*\n((?:\*[^\n]+\n?)+)',
                description,
                re.MULTILINE
            )

        if not steps_match:
            # 尝试英文
            steps_match = re.search(
                r'(?:h3\.\s*)?(?:\*\*)?[Rr]eproduction [Ss]teps(?:\*\*)?[:：]?\s*\n((?:\*[^\n]+\n?)+)',
                description,
                re.MULTILINE
            )

        if steps_match:
            steps_text = steps_match.group(1)
            # 提取每个步骤（以 * 开头）
            steps = re.findall(r'\*\s*(.+)', steps_text)
            # 清理步骤文本
            steps = [step.strip() for step in steps if step.strip()]
            return steps

        return []

    def _extract_root_cause(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        从 RootCauseAnalyzer 结果或描述中提取根因

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            根因，如果未找到返回"无"
        """
        # 优先从 RootCauseAnalyzer 结果提取
        root_cause_result = context.get_result('root_cause')
        if root_cause_result:
            # 优先使用深层原因
            deep_cause = root_cause_result.get('deep_cause', '').strip()
            if deep_cause:
                return deep_cause

            # 其次使用直接原因
            direct_cause = root_cause_result.get('direct_cause', '').strip()
            if direct_cause:
                return direct_cause

            # 最后使用摘要
            summary = root_cause_result.get('summary', '').strip()
            if summary:
                return summary

        # 从描述中提取根因分析部分
        description = jira_data.get('description', '')
        root_cause_match = re.search(
            r'(?:\*\*)?根因分析(?:\*\*)?[:：]\s*\n?(.+?)(?=\n\*\*|\n##|\Z)',
            description,
            re.DOTALL
        )

        if root_cause_match:
            root_cause = root_cause_match.group(1).strip()
            # 限制长度
            if len(root_cause) > 200:
                root_cause = root_cause[:200] + '...'
            return root_cause

        return "无"

    def _extract_fix_solution(self, jira_data: Dict[str, Any], context: AnalysisContext) -> str:
        """
        从评论或描述中提取修复方案

        Args:
            jira_data: Jira 数据
            context: 分析上下文

        Returns:
            修复方案，如果未找到返回"无"
        """
        # 从描述中提取建议修复方案
        description = jira_data.get('description', '')
        fix_match = re.search(
            r'(?:\*\*)?(?:建议)?修复方案(?:\*\*)?[:：]\s*\n?(.+?)(?=\n\*\*|\n##|\Z)',
            description,
            re.DOTALL
        )

        if fix_match:
            fix_solution = fix_match.group(1).strip()
            # 限制长度
            if len(fix_solution) > 200:
                fix_solution = fix_solution[:200] + '...'
            return fix_solution

        # 从评论中提取修复方案
        comments = jira_data.get('comments', [])
        fix_patterns = [
            r'修复方案[:：]\s*(.+?)(?=\n\n|\Z)',
            r'建议[:：]\s*(.+?)(?=\n\n|\Z)',
            r'Hotfix.*?方案[:：]\s*(.+?)(?=\n\n|\Z)',
            r'\[FW[^\]]*\].*?(?:修复|方案).*?[:：]\s*(.+?)(?=\n\n|\Z)',
            r'[Ff]ix[:：]\s*(.+?)(?=\n\n|\Z)',
            r'[Ss]olution[:：]\s*(.+?)(?=\n\n|\Z)',
        ]

        for comment in comments:
            for pattern in fix_patterns:
                match = re.search(pattern, comment, re.DOTALL)
                if match:
                    fix_solution = match.group(1).strip()
                    # 限制长度
                    if len(fix_solution) > 200:
                        fix_solution = fix_solution[:200] + '...'
                    return fix_solution

        return "无"

    def _extract_code_coverage(self, context: AnalysisContext) -> Dict[str, Any]:
        """
        从 KnowledgeRetriever 结果中提取代码覆盖检查信息

        Args:
            context: 分析上下文

        Returns:
            代码覆盖信息字典
        """
        # 检查配置是否启用代码覆盖检查
        config = self.config.get('code_coverage', {})
        enabled = config.get('enabled', True)

        if not enabled:
            return {'enabled': False}

        # 从 KnowledgeRetriever 结果提取
        knowledge_result = context.get_result('knowledge')
        if not knowledge_result:
            return {'enabled': True, 'matches': 0}

        # 统计代码文件匹配数量
        related_sources = knowledge_result.get('related_sources', [])

        # 计算总匹配数
        total_matches = 0
        code_files = []

        for source in related_sources:
            matches = source.get('matches', [])
            for match in matches:
                file_path = match.get('file', '')
                # 判断是否为代码文件
                if self._is_code_file(file_path):
                    total_matches += 1
                    if file_path not in code_files:
                        code_files.append(file_path)

        return {
            'enabled': True,
            'matches': len(code_files),
            'files': code_files[:5]  # 最多返回5个文件
        }

    def _is_code_file(self, file_path: str) -> bool:
        """
        判断是否为代码文件

        Args:
            file_path: 文件路径

        Returns:
            是否为代码文件
        """
        code_extensions = [
            '.py', '.js', '.ts', '.tsx', '.jsx',
            '.java', '.c', '.cpp', '.h', '.hpp',
            '.go', '.rs', '.rb', '.php',
            '.cs', '.swift', '.kt', '.scala'
        ]

        return any(file_path.endswith(ext) for ext in code_extensions)
