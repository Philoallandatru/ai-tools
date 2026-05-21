"""
文档小节分组和过滤模块 - 智能合并相关小节，过滤低价值内容
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class SectionGroup:
    """小节组 - 合并后的小节集合"""
    name: str
    title: str
    sections: List[Any]  # List[DocumentSection]
    total_chars: int

    @property
    def combined_content(self) -> str:
        """获取合并后的内容"""
        return "\n\n".join(s.content for s in self.sections)

    @property
    def section_titles(self) -> List[str]:
        """获取所有小节标题"""
        return [s.title for s in self.sections]


class SectionGrouper:
    """小节分组器 - 智能合并相关小节"""

    # 预定义的小节组规则
    SECTION_GROUPS = {
        "overview": {
            "name": "概览",
            "keywords": ["标题", "基本信息", "描述", "摘要", "summary", "overview", "description"],
            "priority": 1
        },
        "collaboration": {
            "name": "协作信息",
            "keywords": ["评论", "关联", "工作日志", "comment", "link", "worklog", "history"],
            "priority": 2
        },
        "technical": {
            "name": "技术细节",
            "keywords": ["实现", "设计", "架构", "技术", "implementation", "design", "architecture"],
            "priority": 3
        },
        "testing": {
            "name": "测试相关",
            "keywords": ["测试", "验证", "test", "validation", "qa"],
            "priority": 4
        },
        "attachments": {
            "name": "附件",
            "keywords": ["附件", "attachment", "文件", "file"],
            "priority": 5
        }
    }

    def __init__(self, config: Dict[str, Any]):
        """
        初始化分组器

        Args:
            config: 配置字典
        """
        self.config = config
        self.merge_related = config.get('splitting', {}).get('merge_related', True)
        self.min_section_chars = config.get('splitting', {}).get('min_section_chars', 100)

    def group_sections(self, sections: List[Any]) -> List[SectionGroup]:
        """
        将小节分组

        Args:
            sections: 原始小节列表

        Returns:
            分组后的小节组列表
        """
        if not self.merge_related:
            # 不合并，每个小节单独成组
            return [
                SectionGroup(
                    name=f"section_{i}",
                    title=s.title,
                    sections=[s],
                    total_chars=len(s.content)
                )
                for i, s in enumerate(sections, 1)
            ]

        # 智能分组
        groups = []
        assigned = set()

        # 第一轮：按预定义规则分组
        for group_key, group_info in sorted(
            self.SECTION_GROUPS.items(),
            key=lambda x: x[1]['priority']
        ):
            matched_sections = []
            for i, section in enumerate(sections):
                if i in assigned:
                    continue

                # 检查标题是否匹配关键词
                if self._matches_keywords(section.title, group_info['keywords']):
                    matched_sections.append(section)
                    assigned.add(i)

            # 如果有匹配的小节，创建组
            if matched_sections:
                total_chars = sum(len(s.content) for s in matched_sections)
                groups.append(SectionGroup(
                    name=group_key,
                    title=group_info['name'],
                    sections=matched_sections,
                    total_chars=total_chars
                ))

        # 第二轮：未分组的小节单独成组
        for i, section in enumerate(sections):
            if i not in assigned:
                groups.append(SectionGroup(
                    name=f"other_{i}",
                    title=section.title,
                    sections=[section],
                    total_chars=len(section.content)
                ))

        logger.info(f"分组完成: {len(sections)} 个小节 → {len(groups)} 个小节组")
        return groups

    def _matches_keywords(self, title: str, keywords: List[str]) -> bool:
        """
        检查标题是否匹配关键词

        Args:
            title: 小节标题
            keywords: 关键词列表

        Returns:
            是否匹配
        """
        title_lower = title.lower()
        return any(keyword.lower() in title_lower for keyword in keywords)


class SectionFilter:
    """小节过滤器 - 过滤低价值小节"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化过滤器

        Args:
            config: 配置字典
        """
        self.config = config
        filtering_config = config.get('filtering', {})

        self.skip_empty = filtering_config.get('skip_empty', True)
        self.exclude_patterns = filtering_config.get('exclude_patterns', [])
        self.min_content_ratio = filtering_config.get('min_content_ratio', 0.1)
        self.min_section_chars = config.get('splitting', {}).get('min_section_chars', 100)

    def filter_sections(self, sections: List[Any]) -> List[Any]:
        """
        过滤小节

        Args:
            sections: 原始小节列表

        Returns:
            过滤后的小节列表
        """
        if not sections:
            return sections

        # 计算总文档长度
        total_chars = sum(len(s.content) for s in sections)

        filtered = []
        skipped_count = 0

        for section in sections:
            # 检查是否应该跳过
            if self._should_skip(section, total_chars):
                skipped_count += 1
                logger.debug(f"跳过小节: {section.title} (原因: {self._get_skip_reason(section, total_chars)})")
                continue

            filtered.append(section)

        logger.info(f"过滤完成: {len(sections)} 个小节 → {len(filtered)} 个小节 (跳过 {skipped_count} 个)")
        return filtered

    def _should_skip(self, section: Any, total_chars: int) -> bool:
        """
        判断是否应该跳过该小节

        Args:
            section: 小节对象
            total_chars: 总文档字符数

        Returns:
            是否跳过
        """
        content = section.content.strip()

        # 1. 检查是否为空
        if self.skip_empty and len(content) == 0:
            return True

        # 2. 检查是否小于最小字符数
        if len(content) < self.min_section_chars:
            return True

        # 3. 检查是否匹配排除模式
        for pattern in self.exclude_patterns:
            if pattern.lower() in section.title.lower():
                return True

        # 4. 检查内容比例（仅当 min_content_ratio > 0 时生效）
        if self.min_content_ratio > 0 and total_chars > 0 and len(content) > 0:
            content_ratio = len(content) / total_chars
            if content_ratio < self.min_content_ratio:
                return True

        return False

    def _get_skip_reason(self, section: Any, total_chars: int) -> str:
        """获取跳过原因（用于日志）"""
        if len(section.content.strip()) == 0:
            return "空内容"
        if len(section.content) < self.min_section_chars:
            return f"内容太短 ({len(section.content)} < {self.min_section_chars})"
        for pattern in self.exclude_patterns:
            if pattern.lower() in section.title.lower():
                return f"匹配排除模式: {pattern}"
        if total_chars > 0:
            content_ratio = len(section.content) / total_chars
            if content_ratio < self.min_content_ratio:
                return f"内容比例太低 ({content_ratio:.1%} < {self.min_content_ratio:.1%})"
        return "未知原因"

    def filter_groups(self, groups: List[SectionGroup]) -> List[SectionGroup]:
        """
        过滤小节组

        Args:
            groups: 小节组列表

        Returns:
            过滤后的小节组列表
        """
        filtered = []

        for group in groups:
            # 过滤组内的小节
            filtered_sections = [
                s for s in group.sections
                if not self._should_skip(s, sum(len(s.content) for s in group.sections))
            ]

            # 如果组内还有小节，保留该组
            if filtered_sections:
                filtered.append(SectionGroup(
                    name=group.name,
                    title=group.title,
                    sections=filtered_sections,
                    total_chars=sum(len(s.content) for s in filtered_sections)
                ))

        return filtered


class DocumentProcessor:
    """文档处理器 - 整合分组和过滤功能"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化处理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.grouper = SectionGrouper(config)
        self.filter = SectionFilter(config)

        # 获取策略配置
        self.strategy = config.get('splitting', {}).get('strategy', 'smart')

    def process_sections(self, sections: List[Any]) -> List[SectionGroup]:
        """
        处理小节：过滤 + 分组

        Args:
            sections: 原始小节列表

        Returns:
            处理后的小节组列表
        """
        logger.info(f"开始处理文档小节 (策略: {self.strategy})")
        logger.info(f"原始小节数: {len(sections)}")

        # 1. 过滤低价值小节
        filtered_sections = self.filter.filter_sections(sections)

        if not filtered_sections:
            logger.warning("过滤后没有剩余小节")
            return []

        # 2. 分组（如果策略是 smart）
        if self.strategy == 'smart':
            groups = self.grouper.group_sections(filtered_sections)
        else:
            # fixed 策略：每个小节单独成组
            groups = [
                SectionGroup(
                    name=f"section_{i}",
                    title=s.title,
                    sections=[s],
                    total_chars=len(s.content)
                )
                for i, s in enumerate(filtered_sections, 1)
            ]

        logger.info(f"最终小节组数: {len(groups)}")

        # 打印分组摘要
        for i, group in enumerate(groups, 1):
            logger.info(f"  组 {i}: {group.title} ({len(group.sections)} 个小节, {group.total_chars} 字符)")

        return groups
