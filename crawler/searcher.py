"""
全文搜索模块 - 在 sources 目录中快速搜索内容
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchMatch:
    """搜索匹配结果"""
    file_path: Path
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]
    match_start: int
    match_end: int


class ContentSearcher:
    """内容搜索器"""

    def __init__(self, source_dir: str = './sources'):
        """
        初始化搜索器

        Args:
            source_dir: 源文件目录
        """
        self.source_dir = Path(source_dir)

    def search(
        self,
        query: str,
        file_type: str = 'all',
        context_lines: int = 2,
        use_regex: bool = False,
        case_sensitive: bool = False,
        max_results: int = 100
    ) -> List[SearchMatch]:
        """
        执行搜索

        Args:
            query: 搜索关键词
            file_type: 文件类型过滤 (jira/confluence/all)
            context_lines: 上下文行数
            use_regex: 是否使用正则表达式
            case_sensitive: 是否区分大小写
            max_results: 最大结果数

        Returns:
            搜索匹配结果列表
        """
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        # 编译搜索模式
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            if use_regex:
                pattern = re.compile(query, flags)
            else:
                # 转义特殊字符，支持普通文本搜索
                escaped_query = re.escape(query)
                pattern = re.compile(escaped_query, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # 获取要搜索的文件列表
        files = self._get_files_by_type(file_type)

        # 执行搜索
        matches = []
        for file_path in files:
            file_matches = self._search_in_file(
                file_path, pattern, context_lines
            )
            matches.extend(file_matches)

            # 限制结果数量
            if len(matches) >= max_results:
                matches = matches[:max_results]
                break

        return matches

    def _get_files_by_type(self, file_type: str) -> List[Path]:
        """
        根据类型获取文件列表

        Args:
            file_type: 文件类型 (jira/confluence/all)

        Returns:
            文件路径列表
        """
        files = []

        if file_type == 'jira':
            # Jira 文件格式: PROJECT-123.md
            jira_pattern = re.compile(r'^[A-Z]+-\d+\.md$')
            for md_file in self.source_dir.rglob('*.md'):
                if jira_pattern.match(md_file.name):
                    files.append(md_file)

        elif file_type == 'confluence':
            # Confluence 文件在 confluence 子目录中
            confluence_dir = self.source_dir / 'confluence'
            if confluence_dir.exists():
                files.extend(confluence_dir.rglob('*.md'))

        else:  # all
            # 搜索所有文本文件（包括代码文件）
            extensions = ['*.md', '*.py', '*.js', '*.ts', '*.java', '*.c', '*.cpp', '*.go', '*.rs', '*.txt']
            for ext in extensions:
                files.extend(self.source_dir.rglob(ext))

        return sorted(files)

    def _search_in_file(
        self,
        file_path: Path,
        pattern: re.Pattern,
        context_lines: int
    ) -> List[SearchMatch]:
        """
        在单个文件中搜索

        Args:
            file_path: 文件路径
            pattern: 编译后的正则表达式
            context_lines: 上下文行数

        Returns:
            匹配结果列表
        """
        matches = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                # 搜索匹配
                for match in pattern.finditer(line):
                    # 获取上下文
                    context_before = []
                    for j in range(max(0, i - context_lines), i):
                        context_before.append(lines[j].rstrip('\n'))

                    context_after = []
                    for j in range(i + 1, min(len(lines), i + 1 + context_lines)):
                        context_after.append(lines[j].rstrip('\n'))

                    matches.append(SearchMatch(
                        file_path=file_path,
                        line_number=i + 1,
                        line_content=line.rstrip('\n'),
                        context_before=context_before,
                        context_after=context_after,
                        match_start=match.start(),
                        match_end=match.end()
                    ))

        except Exception as e:
            # 忽略无法读取的文件
            pass

        return matches

    def format_match(
        self,
        match: SearchMatch,
        highlight: bool = True,
        show_context: bool = True
    ) -> str:
        """
        格式化匹配结果

        Args:
            match: 搜索匹配结果
            highlight: 是否高亮显示匹配内容
            show_context: 是否显示上下文

        Returns:
            格式化后的字符串
        """
        lines = []

        # 文件路径和行号
        rel_path = match.file_path.relative_to(self.source_dir)
        lines.append(f"\n📄 {rel_path}:{match.line_number}")
        lines.append("─" * 60)

        if show_context:
            # 上下文（之前）
            for ctx_line in match.context_before:
                lines.append(f"  {ctx_line}")

        # 匹配行（高亮）
        if highlight:
            line = match.line_content
            highlighted = (
                line[:match.match_start] +
                f"\033[1;33m{line[match.match_start:match.match_end]}\033[0m" +
                line[match.match_end:]
            )
            lines.append(f"▶ {highlighted}")
        else:
            lines.append(f"▶ {match.line_content}")

        if show_context:
            # 上下文（之后）
            for ctx_line in match.context_after:
                lines.append(f"  {ctx_line}")

        return '\n'.join(lines)

    def find_jira_by_key(self, issue_key: str) -> Optional[Path]:
        """
        根据 issue key 查找对应的 Jira 文件

        Args:
            issue_key: Jira issue key (如 KAN-10, PROJ-123)

        Returns:
            文件路径，如果找不到返回 None
        """
        # 标准化 issue key（转大写）
        issue_key = issue_key.upper().strip()

        # 验证格式：PROJECT-NUMBER
        if not re.match(r'^[A-Z]+-\d+$', issue_key):
            raise ValueError(f"Invalid issue key format: {issue_key}. Expected format: PROJECT-123")

        # 构建文件名
        filename = f"{issue_key}.md"

        # 在 sources 目录及其子目录中查找
        for md_file in self.source_dir.rglob(filename):
            return md_file

        return None

    def list_all_jira_issues(self) -> List[Dict[str, Any]]:
        """
        列出所有 Jira issue 文件

        Returns:
            包含 issue 信息的字典列表
        """
        issues = []
        jira_pattern = re.compile(r'^([A-Z]+-\d+)\.md$')

        for md_file in self.source_dir.rglob('*.md'):
            match = jira_pattern.match(md_file.name)
            if match:
                issue_key = match.group(1)
                try:
                    # 读取文件获取基本信息
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read(2000)  # 只读前2000字符

                    # 提取状态、优先级、类型
                    status_match = re.search(r'-\s*\*\*状态\*\*:\s*([^\n]+)', content)
                    priority_match = re.search(r'-\s*\*\*优先级\*\*:\s*([^\n]+)', content)
                    type_match = re.search(r'-\s*\*\*类型\*\*:\s*([^\n]+)', content)
                    title_match = re.search(r'^#\s+\[' + issue_key + r'\]\s+(.+)$', content, re.MULTILINE)

                    issues.append({
                        'key': issue_key,
                        'file': md_file,
                        'title': title_match.group(1).strip() if title_match else 'N/A',
                        'status': status_match.group(1).strip() if status_match else 'N/A',
                        'priority': priority_match.group(1).strip() if priority_match else 'N/A',
                        'type': type_match.group(1).strip() if type_match else 'N/A'
                    })
                except Exception:
                    # 如果解析失败，只添加基本信息
                    issues.append({
                        'key': issue_key,
                        'file': md_file,
                        'title': 'N/A',
                        'status': 'N/A',
                        'priority': 'N/A',
                        'type': 'N/A'
                    })

        # 按 issue key 排序
        issues.sort(key=lambda x: x['key'])
        return issues

    def get_statistics(self, matches: List[SearchMatch]) -> Dict[str, Any]:
        """
        获取搜索统计信息

        Args:
            matches: 搜索匹配结果列表

        Returns:
            统计信息字典
        """
        if not matches:
            return {
                'total_matches': 0,
                'total_files': 0,
                'files': []
            }

        # 按文件分组
        files_dict = {}
        for match in matches:
            file_key = str(match.file_path)
            if file_key not in files_dict:
                files_dict[file_key] = {
                    'path': match.file_path,
                    'count': 0
                }
            files_dict[file_key]['count'] += 1

        # 排序（按匹配数量降序）
        sorted_files = sorted(
            files_dict.values(),
            key=lambda x: x['count'],
            reverse=True
        )

        return {
            'total_matches': len(matches),
            'total_files': len(files_dict),
            'files': [
                {
                    'path': str(f['path'].relative_to(self.source_dir)),
                    'count': f['count']
                }
                for f in sorted_files
            ]
        }
