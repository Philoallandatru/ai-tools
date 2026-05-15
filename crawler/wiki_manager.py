"""
Wiki Manager - 管理多个 wiki 仓库的初始化、配置和元数据
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config.models import WikiRepositoryConfig, WikiAutoMatchConfig, WikiCompilationConfig


class WikiMetadata:
    """Wiki 元数据管理"""

    def __init__(self, wiki_path: Path):
        self.wiki_path = wiki_path
        self.metadata_file = wiki_path / '.wiki-metadata.json'

    def load(self) -> Dict[str, Any]:
        """加载 wiki 元数据"""
        if not self.metadata_file.exists():
            return {}

        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self, metadata: Dict[str, Any]) -> None:
        """保存 wiki 元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def create(self, name: str, display_name: str, description: str,
               auto_match: Optional[Dict[str, Any]] = None,
               compilation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建新的 wiki 元数据"""
        metadata = {
            'name': name,
            'display_name': display_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'auto_match_rules': auto_match or {
                'jira_projects': [],
                'confluence_spaces': [],
                'keywords': []
            },
            'compilation_config': compilation or {
                'batch_size': 5,
                'auto_compile': True
            }
        }
        self.save(metadata)
        return metadata


class WikiManager:
    """Wiki 仓库管理器"""

    def __init__(self, wikis_root: str = './wikis'):
        self.wikis_root = Path(wikis_root)

    def initialize_wiki(self, config: WikiRepositoryConfig) -> Path:
        """
        初始化一个新的 wiki 仓库

        Args:
            config: Wiki 配置

        Returns:
            Wiki 路径
        """
        wiki_path = Path(config.path)

        # 创建目录结构
        (wiki_path / 'temp').mkdir(parents=True, exist_ok=True)
        (wiki_path / 'sources').mkdir(parents=True, exist_ok=True)
        (wiki_path / 'wiki').mkdir(parents=True, exist_ok=True)
        (wiki_path / '.llmwiki').mkdir(parents=True, exist_ok=True)

        # 创建元数据
        metadata_manager = WikiMetadata(wiki_path)
        metadata_manager.create(
            name=config.name,
            display_name=config.display_name,
            description=config.description,
            auto_match={
                'jira_projects': config.auto_match.jira_projects,
                'confluence_spaces': config.auto_match.confluence_spaces,
                'keywords': config.auto_match.keywords
            },
            compilation={
                'batch_size': config.compilation.batch_size,
                'auto_compile': config.compilation.auto_compile
            }
        )

        print(f"[WikiManager] 初始化 wiki: {config.display_name} at {wiki_path}")
        return wiki_path

    def load_wiki_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        加载所有 wiki 配置

        Returns:
            Wiki 配置字典 {wiki_name: config}
        """
        wikis = {}

        if not self.wikis_root.exists():
            return wikis

        for wiki_dir in self.wikis_root.iterdir():
            if not wiki_dir.is_dir():
                continue

            metadata_file = wiki_dir / '.wiki-metadata.json'
            if metadata_file.exists():
                metadata_manager = WikiMetadata(wiki_dir)
                metadata = metadata_manager.load()
                wikis[wiki_dir.name] = {
                    'path': str(wiki_dir),
                    **metadata
                }

        return wikis

    def get_wiki_path(self, wiki_name: str) -> Optional[Path]:
        """获取 wiki 路径"""
        wiki_path = self.wikis_root / wiki_name
        if wiki_path.exists():
            return wiki_path
        return None

    def wiki_exists(self, wiki_name: str) -> bool:
        """检查 wiki 是否存在"""
        return (self.wikis_root / wiki_name).exists()

    def list_wikis(self) -> List[str]:
        """列出所有 wiki 名称"""
        if not self.wikis_root.exists():
            return []

        return [
            d.name for d in self.wikis_root.iterdir()
            if d.is_dir() and (d / '.wiki-metadata.json').exists()
        ]

    def get_wiki_info(self, wiki_name: str) -> Optional[Dict[str, Any]]:
        """获取 wiki 信息"""
        wiki_path = self.get_wiki_path(wiki_name)
        if not wiki_path:
            return None

        metadata_manager = WikiMetadata(wiki_path)
        return metadata_manager.load()

    def update_wiki_metadata(self, wiki_name: str, updates: Dict[str, Any]) -> bool:
        """更新 wiki 元数据"""
        wiki_path = self.get_wiki_path(wiki_name)
        if not wiki_path:
            return False

        metadata_manager = WikiMetadata(wiki_path)
        metadata = metadata_manager.load()
        metadata.update(updates)
        metadata_manager.save(metadata)
        return True
