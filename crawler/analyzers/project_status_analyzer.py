"""
项目状态分析器 - 判断项目状态并提供建议
"""

from typing import Dict, Any
from crawler.analyzers.base import BaseAnalyzer
from crawler.report_context import ReportContext
from crawler.llm_client import BaseLLMClient


class ProjectStatusAnalyzer(BaseAnalyzer):
    """判断项目当前状态并提供可执行的建议"""

    def __init__(self, llm_client: BaseLLMClient, config: Dict[str, Any]):
        """
        初始化项目状态分析器

        Args:
            llm_client: LLM 客户端
            config: 分析器配置
        """
        self.llm_client = llm_client
        self.config = config
        self.max_tokens = config.get('max_tokens', 10000)

    def analyze(self, report_data: Dict[str, Any], context: ReportContext) -> Dict[str, Any]:
        """
        分析项目状态并生成建议

        Args:
            report_data: 报告数据
            context: 报告分析上下文

        Returns:
            包含状态判断、主要问题和行动建议的字典
        """
        # 检查是否启用
        if not self.config.get('enabled', True):
            return {'status': '', 'problems': [], 'recommendations': []}

        # 获取健康度数据（如果有）
        health_data = report_data.get('analysis', {}).get('project_health', {})

        # 构建 prompt
        prompt = self._build_prompt(report_data, health_data)

        # 调用 LLM
        try:
            context.increment_llm_calls()
            response = self.llm_client.generate(prompt, max_tokens=self.max_tokens)

            # 解析响应
            parsed = self._parse_response(response)

            return {
                'status_description': parsed.get('status', ''),
                'main_problems': parsed.get('problems', []),
                'action_recommendations': parsed.get('recommendations', []),
                'raw_response': response,
                'success': True
            }

        except Exception as e:
            context.add_warning(f"项目状态分析失败: {str(e)}")
            return {
                'status_description': '',
                'main_problems': [],
                'action_recommendations': [],
                'success': False,
                'error': str(e)
            }

    def _build_prompt(self, report_data: Dict[str, Any], health_data: Dict[str, Any]) -> str:
        """
        构建 LLM prompt

        Args:
            report_data: 报告数据
            health_data: 健康度数据

        Returns:
            Prompt 字符串
        """
        jira = report_data.get('jira', {})
        report_type = report_data.get('type', '报告')
        start_date = report_data.get('start_date', 'N/A')
        end_date = report_data.get('end_date', 'N/A')

        # 基础统计
        total = jira.get('total', 0)
        new = jira.get('new', 0)
        updated = jira.get('updated', 0)
        by_status = jira.get('by_status', {})
        by_priority = jira.get('by_priority', {})
        by_assignee = jira.get('by_assignee', {})

        # 计算关键指标
        done_count = sum(len(issues) for status, issues in by_status.items()
                        if any(keyword in status.lower() for keyword in ['done', 'closed', 'resolved', '已完成', '已关闭']))
        in_progress_count = sum(len(issues) for status, issues in by_status.items()
                               if any(keyword in status.lower() for keyword in ['progress', 'doing', '进行中']))

        done_ratio = (done_count / total * 100) if total > 0 else 0
        in_progress_ratio = (in_progress_count / total * 100) if total > 0 else 0

        # 高优先级统计
        high_priority_count = sum(len(issues) for priority, issues in by_priority.items()
                                 if priority in ['Highest', 'High', '最高', '高'])

        # 团队统计
        active_members = len([a for a in by_assignee.keys()
                            if a.lower() not in ['unassigned', '未分配', 'none']])
        unassigned_count = sum(len(issues) for assignee, issues in by_assignee.items()
                              if assignee.lower() in ['unassigned', '未分配', 'none'])

        # 负载统计
        assignee_loads = []
        overloaded_members = []
        for assignee, issues in by_assignee.items():
            if assignee.lower() not in ['unassigned', '未分配', 'none']:
                count = len(issues) if isinstance(issues, list) else issues
                assignee_loads.append((assignee, count))
                if count >= 8:
                    overloaded_members.append(f"{assignee}({count}个)")

        assignee_loads.sort(key=lambda x: x[1], reverse=True)
        top_assignees = ', '.join([f"{a}:{c}" for a, c in assignee_loads[:5]])

        # 健康度信息
        health_score = health_data.get('total_score', 'N/A')
        health_level = health_data.get('health_level', 'N/A')

        # 时间范围天数
        from datetime import datetime
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            days = (end - start).days + 1
            new_per_day = round(new / days, 1) if days > 0 else 0
            closed_per_day = round(done_count / days, 1) if days > 0 else 0
        except:
            days = 7
            new_per_day = 0
            closed_per_day = 0

        prompt = f"""基于以下数据，评估项目当前状态并提供建议：

报告类型: {report_type}
时间范围: {start_date} 至 {end_date} ({days}天)
项目健康度: {health_score}/100 ({health_level})

关键指标:
- 总 issues: {total}
- 进行中: {in_progress_count} ({in_progress_ratio:.1f}%)
- 已完成: {done_count} ({done_ratio:.1f}%)
- 新增: {new} ({new_per_day}/天)
- 完成速度: {closed_per_day}/天
- 高优先级未完成: {high_priority_count}

按状态分布: {self._format_dict(by_status)}
按优先级分布: {self._format_dict(by_priority)}

团队状况:
- 活跃成员: {active_members}
- 负载分布: {top_assignees}
- 负载过重 (≥8个): {', '.join(overloaded_members) if overloaded_members else '无'}
- 未分配 issues: {unassigned_count}

请提供:

1. **项目状态判断** (2-3句话)
   - 当前处于什么阶段？(启动期/稳定期/冲刺期/维护期)
   - 整体趋势如何？(加速/稳定/放缓/停滞)
   - 关键特征是什么？

2. **主要问题** (Top 3，每个1句话)
   - 最需要关注的问题
   - 按影响程度排序

3. **行动建议** (3-5条，具体可执行)
   - 优先级排序（高/中/低）
   - 每条建议包含：做什么、为什么、预期效果
   - 建议要具体、可执行、有明确责任人

输出格式:
### 项目状态
[状态判断，2-3句话]

### 主要问题
1. [问题1]
2. [问题2]
3. [问题3]

### 行动建议
#### 高优先级
1. **[建议标题]**: [具体行动] - 预期: [效果]
2. ...

#### 中优先级
1. **[建议标题]**: [具体行动] - 预期: [效果]

#### 低优先级
1. **[建议标题]**: [具体行动] - 预期: [效果]

要求:
- 直接输出评估结果，不要输出思考过程
- 建议要具体，避免泛泛而谈
- 每条建议控制在1-2句话"""

        return prompt

    def _format_dict(self, d: dict) -> str:
        """格式化字典为字符串"""
        if not d:
            return "无"
        # 只显示数量，不显示详细列表
        return ', '.join([f"{k}:{len(v) if isinstance(v, list) else v}" for k, v in d.items()])

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典
        """
        import re

        result = {
            'status': '',
            'problems': [],
            'recommendations': []
        }

        # 分割各个部分
        sections = re.split(r'###\s+', response)

        for section in sections:
            if not section.strip():
                continue

            lines = section.strip().split('\n')
            header = lines[0].strip()

            if '项目状态' in header or 'Project Status' in header:
                # 提取状态描述（去掉标题行）
                status_lines = [line.strip() for line in lines[1:] if line.strip()]
                result['status'] = '\n'.join(status_lines)

            elif '主要问题' in header or 'Main Problems' in header:
                # 提取问题列表
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                    # 移除列表标记
                    if re.match(r'^\d+\.\s*', line):
                        problem = re.sub(r'^\d+\.\s*', '', line)
                        result['problems'].append(problem)

            elif '行动建议' in header or 'Action' in header or 'Recommendation' in header:
                # 提取建议列表
                current_priority = 'medium'
                for line in lines[1:]:
                    line = line.strip()
                    if not line:
                        continue

                    # 检测优先级标题
                    if '高优先级' in line or 'High Priority' in line:
                        current_priority = 'high'
                        continue
                    elif '中优先级' in line or 'Medium Priority' in line:
                        current_priority = 'medium'
                        continue
                    elif '低优先级' in line or 'Low Priority' in line:
                        current_priority = 'low'
                        continue

                    # 提取建议
                    if re.match(r'^\d+\.\s*', line):
                        recommendation = re.sub(r'^\d+\.\s*', '', line)
                        result['recommendations'].append({
                            'priority': current_priority,
                            'text': recommendation
                        })

        return result

    def get_name(self) -> str:
        """获取分析器名称"""
        return "project_status"
