"""
Confluence 爬取模块 - 从 Confluence 获取页面和附件
"""

from atlassian import Confluence
from markdownify import markdownify as md
from typing import Dict, Any, List, Optional
from .storage import StorageManager
from .error_handler import ErrorHandler


class ConfluenceCrawler:
    """Confluence 爬虫 - 爬取 Confluence 页面和附件"""

    def __init__(self, url: str, username: str, token: str, error_handler: ErrorHandler):
        """
        初始化 Confluence 爬虫

        Args:
            url: Confluence 实例 URL
            username: 用户名
            token: API token
            error_handler: 错误处理器
        """
        self.client = Confluence(url=url, username=username, password=token, cloud=True)
        self.error_handler = error_handler
        self.base_url = url

    def crawl_space(
        self,
        source_name: str,
        space_key: str,
        storage: StorageManager
    ):
        """
        爬取指定 space 的所有页面

        Args:
            source_name: 数据源名称
            space_key: Space key
            storage: 存储管理器
        """
        try:
            # 获取 space 的所有页面
            pages = self.client.get_all_pages_from_space(
                space_key,
                expand='body.storage,version,history'
            )

            # 获取状态
            state = storage.get_confluence_state(source_name, space_key)

            # 处理每个页面
            for page in pages:
                page_id = page['id']
                last_version = state.get(page_id, {}).get('version', 0)
                current_version = page['version']['number']

                # 检查是否需要更新
                if current_version > last_version:
                    self._process_page(source_name, space_key, page, storage)

                    # 更新状态
                    state[page_id] = {
                        'title': page['title'],
                        'last_updated': page['version']['when'],
                        'version': current_version
                    }

        except Exception as e:
            self.error_handler.log_error(
                'crawl_confluence_space',
                str(e),
                (source_name, space_key),
                {}
            )

    def _process_page(
        self,
        source_name: str,
        space_key: str,
        page: Dict[str, Any],
        storage: StorageManager
    ):
        """
        处理单个页面：转换 + 下载附件

        Args:
            source_name: 数据源名称
            space_key: Space key
            page: 页面数据
            storage: 存储管理器
        """
        try:
            # 转换 HTML → Markdown
            html_content = page['body']['storage']['value']
            markdown_content = md(html_content)

            # 构建元数据
            metadata = self._build_metadata(source_name, space_key, page)

            # 组合完整内容
            full_content = f"{metadata}\n\n{markdown_content}"

            # 下载附件
            attachments = self._download_attachments(page['id'])

            # 保存页面
            storage.save_confluence_page(
                source_name=source_name,
                space_key=space_key,
                page_id=page['id'],
                title=page['title'],
                content=full_content,
                attachments=attachments
            )

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.error_handler.log_error(
                'process_confluence_page',
                str(e),
                (page.get('id'), page.get('title')),
                {},
                tb
            )

    def _build_metadata(
        self,
        source_name: str,
        space_key: str,
        page: Dict[str, Any]
    ) -> str:
        """
        构建页面元数据

        Args:
            source_name: 数据源名称
            space_key: Space key
            page: 页面数据

        Returns:
            元数据字符串
        """
        page_url = f"{self.base_url}/wiki/spaces/{space_key}/pages/{page['id']}"
        author = page.get('history', {}).get('createdBy', {}).get('displayName', 'Unknown')
        created = page.get('history', {}).get('createdDate', 'Unknown')
        updated = page['version']['when']

        metadata = f"""# {page['title']}

> 来源: {page_url}
> 作者: {author}
> 创建时间: {created}
> 更新时间: {updated}
> Space: {space_key}
> 数据源: {source_name}"""

        return metadata

    def _download_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """
        下载页面的所有附件

        Args:
            page_id: 页面 ID

        Returns:
            附件列表
        """
        attachments = []

        try:
            # 获取附件列表
            att_list = self.client.get_attachments_from_content(page_id)

            if not att_list or 'results' not in att_list:
                return attachments

            # 下载每个附件
            for att in att_list['results']:
                att_data = self._download_single_attachment(att)
                if att_data:
                    attachments.append(att_data)

        except Exception as e:
            self.error_handler.log_error(
                'download_attachments',
                str(e),
                (page_id,),
                {}
            )

        return attachments

    def _download_single_attachment(self, attachment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        下载单个附件（带重试）

        Args:
            attachment: 附件信息

        Returns:
            附件数据字典，包含 filename 和 content
        """
        @self.error_handler.retry_on_failure
        def download():
            download_link = attachment['_links']['download']
            response = self.client.get(download_link, not_json_response=True)
            return {
                'filename': attachment['title'],
                'content': response
            }

        return download()
