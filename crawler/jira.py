"""
Jira 爬取模块 - 从 Jira 获取 issues 和附件
"""

import json
from atlassian import Jira
from typing import Dict, Any, List, Optional
from .storage import StorageManager
from .error_handler import ErrorHandler


class JiraCrawler:
    """Jira 爬虫 - 爬取 Jira issues 和附件"""

    def __init__(self, url: str, token: str, error_handler: ErrorHandler, username: Optional[str] = None, is_cloud: bool = True, max_results_per_page: int = 50):
        """
        初始化 Jira 爬虫

        Args:
            url: Jira 实例 URL
            token: API token (Cloud) 或 Personal Access Token (Server)
            error_handler: 错误处理器
            username: 用户名 (仅 Cloud 需要)
            is_cloud: 是否为 Cloud 版本 (默认 True)
            max_results_per_page: 每页获取的最大结果数 (默认 50)
        """
        if is_cloud:
            # Cloud 版本需要 username + API token
            self.client = Jira(url=url, username=username, password=token, cloud=True)
        else:
            # Server 版本只需要 Personal Access Token
            self.client = Jira(url=url, token=token, cloud=False)
        self.error_handler = error_handler
        self.base_url = url
        self.max_results_per_page = max_results_per_page

    def crawl_project(
        self,
        source_name: str,
        project_key: str,
        storage: StorageManager
    ) -> Dict[str, int]:
        """
        爬取指定 project 的所有 issues

        Args:
            source_name: 数据源名称
            project_key: Project key
            storage: 存储管理器

        Returns:
            统计信息字典 {'issues': int, 'attachments': int, 'skipped': int, 'total': int}
        """
        stats = {'issues': 0, 'attachments': 0, 'skipped': 0, 'total': 0}

        try:
            # 使用 JQL 查询所有 issues，获取所有字段
            jql = f'project = {project_key} ORDER BY updated DESC'
            start_at = 0
            max_results = self.max_results_per_page

            # 获取状态
            state = storage.get_jira_state(source_name, project_key)

            # 第一阶段：扫描所有 issues，统计需要更新的数量
            print(f"\n[Jira] 正在扫描 project {project_key} 的 issues...")
            issues_to_fetch = []
            total_issues = 0

            while True:
                # 分页获取 issues - 使用 API v3
                result = self.client.jql(
                    jql,
                    start=start_at,
                    limit=max_results,
                    fields='key,updated,summary'  # 只获取必要字段用于检测
                )

                issues = result.get('issues', [])
                if not issues:
                    break

                # 检查每个 issue 是否需要更新
                for issue in issues:
                    total_issues += 1
                    issue_key = issue['key']
                    last_updated_local = state.get(issue_key, {}).get('last_updated', '')
                    current_updated = issue['fields']['updated']

                    # 检查是否需要更新
                    if current_updated > last_updated_local:
                        issues_to_fetch.append(issue_key)
                    else:
                        stats['skipped'] += 1

                # 检查是否还有更多数据
                if len(issues) < max_results:
                    break

                start_at += max_results

            stats['total'] = total_issues

            # 报告扫描结果
            print(f"[Jira] 扫描完成:")
            print(f"  - 总 issues: {total_issues}")
            print(f"  - 需要拉取: {len(issues_to_fetch)} (新增或已更新)")
            print(f"  - 跳过: {stats['skipped']} (未变化)")

            # 第二阶段：只拉取需要更新的 issues
            if issues_to_fetch:
                print(f"\n[Jira] 开始拉取 {len(issues_to_fetch)} 个 issues...")
                for idx, issue_key in enumerate(issues_to_fetch, 1):
                    try:
                        # 获取完整的 issue 数据
                        issue = self.client.issue(issue_key, fields='*all')

                        attachments_count = self._process_issue(source_name, project_key, issue, storage)
                        stats['issues'] += 1
                        stats['attachments'] += attachments_count

                        # 更新状态
                        state[issue_key] = {
                            'summary': issue['fields']['summary'],
                            'last_updated': issue['fields']['updated']
                        }

                        if idx % 10 == 0:
                            print(f"  进度: {idx}/{len(issues_to_fetch)}")

                    except Exception as e:
                        self.error_handler.log_error(
                            'fetch_jira_issue',
                            str(e),
                            (issue_key,),
                            {}
                        )

                print(f"[Jira] 拉取完成: {stats['issues']} 个 issues, {stats['attachments']} 个附件")
            else:
                print(f"[Jira] 无需拉取，所有 issues 都是最新的")

        except Exception as e:
            self.error_handler.log_error(
                'crawl_jira_project',
                str(e),
                (source_name, project_key),
                {}
            )

        return stats

    def _process_issue(
        self,
        source_name: str,
        project_key: str,
        issue: Dict[str, Any],
        storage: StorageManager
    ) -> int:
        """
        处理单个 issue：构建 markdown + 下载附件

        Args:
            source_name: 数据源名称
            project_key: Project key
            issue: Issue 数据
            storage: 存储管理器

        Returns:
            附件数量
        """
        try:
            # 构建完整的 markdown 内容
            markdown_content = self._build_complete_issue_markdown(source_name, issue)

            # 下载附件
            attachments = self._download_attachments(issue)

            # 获取 issue type
            issue_type = issue['fields']['issuetype']['name']

            # 保存 issue
            storage.save_jira_issue(
                source_name=source_name,
                project_key=project_key,
                issue_key=issue['key'],
                issue_type=issue_type,
                content=markdown_content,
                attachments=attachments
            )

            return len(attachments)

        except Exception as e:
            self.error_handler.log_error(
                'process_jira_issue',
                str(e),
                (issue.get('key'), issue.get('fields', {}).get('summary')),
                {}
            )
            return 0

    def _build_complete_issue_markdown(
        self,
        source_name: str,
        issue: Dict[str, Any]
    ) -> str:
        """
        构建包含所有字段的 markdown

        Args:
            source_name: 数据源名称
            issue: Issue 数据

        Returns:
            完整的 markdown 内容
        """
        fields = issue['fields']
        issue_key = issue['key']
        issue_url = f"{self.base_url}/browse/{issue_key}"

        # 标题和基本元数据
        summary = fields.get('summary', 'No Summary')
        markdown = f"""# [{issue_key}] {summary}

> 来源: {issue_url}
> Project: {fields.get('project', {}).get('name', 'Unknown')} ({fields.get('project', {}).get('key', 'Unknown')})
> 数据源: {source_name}
> 创建时间: {fields.get('created', 'Unknown')}
> 更新时间: {fields.get('updated', 'Unknown')}

## 基本信息

"""

        # 标准字段
        standard_fields = {
            'issuetype': ('类型', lambda x: x.get('name', 'Unknown')),
            'status': ('状态', lambda x: x.get('name', 'Unknown')),
            'priority': ('优先级', lambda x: x.get('name', 'Unknown') if x else 'None'),
            'reporter': ('报告人', lambda x: x.get('displayName', 'Unknown') if x else 'None'),
            'assignee': ('经办人', lambda x: x.get('displayName', 'Unassigned') if x else 'Unassigned'),
            'labels': ('标签', lambda x: ', '.join(x) if x else 'None'),
            'components': ('组件', lambda x: ', '.join([c.get('name', '') for c in x]) if x else 'None'),
            'versions': ('影响版本', lambda x: ', '.join([v.get('name', '') for v in x]) if x else 'None'),
            'fixVersions': ('修复版本', lambda x: ', '.join([v.get('name', '') for v in x]) if x else 'None'),
        }

        for field_key, (label, formatter) in standard_fields.items():
            value = fields.get(field_key)
            try:
                formatted_value = formatter(value)
                markdown += f"- **{label}**: {formatted_value}\n"
            except:
                markdown += f"- **{label}**: N/A\n"

        # 自定义字段
        markdown += "\n## 自定义字段\n\n"
        custom_fields = {k: v for k, v in fields.items() if k.startswith('customfield_')}

        if custom_fields:
            for field_key, value in custom_fields.items():
                if value is not None:
                    # 尝试获取字段名称
                    field_name = field_key
                    # 格式化值
                    if isinstance(value, dict):
                        value_str = value.get('value', str(value))
                    elif isinstance(value, list):
                        value_str = ', '.join([str(v) for v in value])
                    else:
                        value_str = str(value)

                    markdown += f"- **{field_name}**: {value_str}\n"
        else:
            markdown += "无自定义字段\n"

        # 描述
        markdown += "\n## 描述\n\n"
        description = fields.get('description')
        if description:
            markdown += f"{description}\n"
        else:
            markdown += "无描述\n"

        # 评论
        markdown += "\n## 评论\n\n"
        comments = self._get_comments(issue_key)
        if comments:
            for comment in comments:
                author = comment.get('author', {}).get('displayName', 'Unknown')
                created = comment.get('created', 'Unknown')
                body = comment.get('body', '')
                markdown += f"### {author} - {created}\n\n{body}\n\n"
        else:
            markdown += "无评论\n"

        # 关联 Issues
        markdown += "\n## 关联 Issues\n\n"
        issue_links = fields.get('issuelinks', [])
        if issue_links:
            for link in issue_links:
                link_type = link.get('type', {}).get('name', 'Related')
                if 'outwardIssue' in link:
                    linked_issue = link['outwardIssue']
                    markdown += f"- {link_type}: {linked_issue['key']}\n"
                elif 'inwardIssue' in link:
                    linked_issue = link['inwardIssue']
                    markdown += f"- {link_type}: {linked_issue['key']}\n"
        else:
            markdown += "无关联 issues\n"

        # 附件列表
        markdown += "\n## 附件\n\n"
        attachments = fields.get('attachment', [])
        if attachments:
            for att in attachments:
                filename = att.get('filename', 'unknown')
                markdown += f"- [{filename}](./attachments/{filename})\n"
        else:
            markdown += "无附件\n"

        # 工作日志
        markdown += "\n## 工作日志\n\n"
        worklogs = self._get_worklogs(issue_key)
        if worklogs:
            for worklog in worklogs:
                author = worklog.get('author', {}).get('displayName', 'Unknown')
                started = worklog.get('started', 'Unknown')
                time_spent = worklog.get('timeSpent', 'Unknown')
                comment = worklog.get('comment', '')
                markdown += f"- {time_spent} - {author} - {started[:10]} - {comment}\n"
        else:
            markdown += "无工作日志\n"

        # 原始数据（JSON）
        markdown += "\n## 原始数据（JSON）\n\n"
        markdown += "<details>\n<summary>完整字段数据</summary>\n\n```json\n"
        markdown += json.dumps(fields, indent=2, ensure_ascii=False)
        markdown += "\n```\n\n</details>\n"

        return markdown

    def _get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        获取 issue 的评论

        Args:
            issue_key: Issue key

        Returns:
            评论列表
        """
        try:
            comments_data = self.client.issue_get_comments(issue_key)
            if isinstance(comments_data, dict):
                return comments_data.get('comments', [])
            else:
                # 如果返回的不是字典，记录错误
                self.error_handler.log_error(
                    'get_jira_comments',
                    f'Unexpected response type: {type(comments_data)}',
                    (issue_key,),
                    {}
                )
                return []
        except json.JSONDecodeError as e:
            self.error_handler.log_error(
                'get_jira_comments',
                f'JSON decode error: {str(e)}',
                (issue_key,),
                {}
            )
            return []
        except Exception as e:
            self.error_handler.log_error(
                'get_jira_comments',
                str(e),
                (issue_key,),
                {}
            )
            return []

    def _get_worklogs(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        获取 issue 的工作日志

        Args:
            issue_key: Issue key

        Returns:
            工作日志列表
        """
        try:
            worklogs_data = self.client.issue_get_worklog(issue_key)
            return worklogs_data.get('worklogs', [])
        except Exception as e:
            self.error_handler.log_error(
                'get_jira_worklogs',
                str(e),
                (issue_key,),
                {}
            )
            return []

    def _download_attachments(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        下载 issue 的所有附件

        Args:
            issue: Issue 数据

        Returns:
            附件列表
        """
        attachments = []
        att_list = issue['fields'].get('attachment', [])

        for att in att_list:
            att_data = self._download_single_attachment(att)
            if att_data:
                attachments.append(att_data)

        return attachments

    def _download_single_attachment(self, attachment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        下载单个附件（带重试）

        Args:
            attachment: 附件信息

        Returns:
            附件数据字典，包含 filename 和 content (bytes)
        """
        @self.error_handler.retry_on_failure
        def download():
            content_url = attachment['content']
            response = self.client.get(content_url)

            # 确保返回字节内容
            if isinstance(response, bytes):
                content = response
            elif isinstance(response, str):
                content = response.encode('utf-8')
            elif hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response).encode('utf-8')

            return {
                'filename': attachment['filename'],
                'content': content
            }

        return download()
