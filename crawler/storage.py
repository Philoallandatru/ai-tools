"""
存储管理模块 - 管理文件系统操作和增量更新状态
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class StorageManager:
    """存储管理器 - 管理文件保存和状态跟踪"""

    def __init__(self, base_dir: str, state_file: str):
        """
        初始化存储管理器

        Args:
            base_dir: 输出基础目录
            state_file: 状态文件路径
        """
        self.base_dir = Path(base_dir)
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载增量更新状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_sync": None,
            "confluence": {},
            "jira": {}
        }

    def save_state(self):
        """保存状态文件"""
        self.state["last_sync"] = datetime.utcnow().isoformat() + 'Z'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, indent=2, fp=f)

    def get_confluence_state(self, source_name: str, space_key: str) -> Dict[str, Any]:
        """
        获取 Confluence space 的状态

        Args:
            source_name: 数据源名称
            space_key: Space key

        Returns:
            该 space 的状态字典
        """
        if source_name not in self.state["confluence"]:
            self.state["confluence"][source_name] = {}
        if space_key not in self.state["confluence"][source_name]:
            self.state["confluence"][source_name][space_key] = {"pages": {}}
        return self.state["confluence"][source_name][space_key]["pages"]

    def get_jira_state(self, source_name: str, project_key: str) -> Dict[str, Any]:
        """
        获取 Jira project 的状态

        Args:
            source_name: 数据源名称
            project_key: Project key

        Returns:
            该 project 的状态字典
        """
        if source_name not in self.state["jira"]:
            self.state["jira"][source_name] = {}
        if project_key not in self.state["jira"][source_name]:
            self.state["jira"][source_name][project_key] = {"issues": {}}
        return self.state["jira"][source_name][project_key]["issues"]

    def save_confluence_page(
        self,
        source_name: str,
        space_key: str,
        page_id: str,
        title: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ):
        """
        保存 Confluence 页面

        Args:
            source_name: 数据源名称
            space_key: Space key
            page_id: 页面 ID
            title: 页面标题
            content: Markdown 内容
            attachments: 附件列表
        """
        # 创建目录结构
        space_dir = self.base_dir / "confluence" / source_name / space_key
        space_dir.mkdir(parents=True, exist_ok=True)

        # 保存 markdown 文件（使用安全的文件名）
        safe_filename = self._sanitize_filename(title)
        md_file = space_dir / f"{safe_filename}.md"

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存附件
        if attachments:
            att_dir = space_dir / "attachments"
            att_dir.mkdir(exist_ok=True)
            self._save_attachments(attachments, att_dir)

    def save_jira_issue(
        self,
        source_name: str,
        project_key: str,
        issue_key: str,
        issue_type: str,
        content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ):
        """
        保存 Jira issue 到 sources 根目录

        Args:
            source_name: 数据源名称
            project_key: Project key
            issue_key: Issue key (如 PROJ-123)
            issue_type: Issue 类型 (如 Bug, Story, Task)
            content: Markdown 内容
            attachments: 附件列表
        """
        # 直接保存到 sources 根目录，使用 issue_key 作为文件名
        self.base_dir.mkdir(parents=True, exist_ok=True)
        md_file = self.base_dir / f"{issue_key}.md"

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 保存附件到 attachments 子目录
        if attachments:
            att_dir = self.base_dir / "attachments" / issue_key
            att_dir.mkdir(parents=True, exist_ok=True)
            self._save_attachments(attachments, att_dir)

    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 移除或替换非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '-')

        # 限制长度
        return filename[:200]

    def _save_attachments(self, attachments: List[Dict[str, Any]], att_dir: Path):
        """
        保存附件到指定目录

        Args:
            attachments: 附件列表，每个附件包含 'filename' 和 'content' (bytes)
            att_dir: 附件目录
        """
        for attachment in attachments:
            filename = self._sanitize_filename(attachment['filename'])
            file_path = att_dir / filename

            with open(file_path, 'wb') as f:
                f.write(attachment['content'])
