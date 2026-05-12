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

    def __init__(self, url: str, token: str, error_handler: ErrorHandler, username: Optional[str] = None, is_cloud: bool = True):
        """
        初始化 Confluence 爬虫

        Args:
            url: Confluence 实例 URL
            token: API token (Cloud) 或 Personal Access Token (Server)
            error_handler: 错误处理器
            username: 用户名 (仅 Cloud 需要)
            is_cloud: 是否为 Cloud 版本 (默认 True)
        """
        if is_cloud:
            # Cloud 版本需要 username + API token
            self.client = Confluence(url=url, username=username, password=token, cloud=True)
        else:
            # Server 版本只需要 Personal Access Token
            self.client = Confluence(url=url, token=token, cloud=False)
        self.error_handler = error_handler
        self.base_url = url

    def crawl_space(
        self,
        source_name: str,
        space_key: str,
        storage: StorageManager
    ) -> Dict[str, int]:
        """
        爬取指定 space 的所有页面

        Args:
            source_name: 数据源名称
            space_key: Space key
            storage: 存储管理器

        Returns:
            统计信息字典 {'pages': int, 'attachments': int, 'skipped': int, 'total': int}
        """
        stats = {'pages': 0, 'attachments': 0, 'skipped': 0, 'total': 0}

        try:
            # 第一阶段：获取所有页面的基本信息
            print(f"\n[Confluence] 正在扫描 space {space_key} 的页面...")
            print(f"[Confluence] 模式: {'Cloud' if self.client.cloud else 'Server'}")
            print(f"[Confluence] URL: {self.base_url}")

            # 获取 space 的所有页面（只获取基本信息）
            pages = []
            try:
                # 尝试标准方法
                pages = self.client.get_all_pages_from_space(
                    space_key,
                    expand='version'  # 只获取版本信息用于检测
                )
                print(f"[Confluence] 使用标准方法成功获取页面")
            except Exception as e:
                print(f"[Confluence] 警告: 标准方法失败: {str(e)}")
                print(f"[Confluence] 尝试使用备用方法（手动分页）...")

                # 备用方法：手动分页
                start = 0
                limit = 50
                consecutive_empty = 0

                while consecutive_empty < 2:  # 连续两次空结果才停止
                    try:
                        response = self.client.get_all_pages_from_space_raw(
                            space=space_key,
                            start=start,
                            limit=limit,
                            expand='version'
                        )
                        results = response.get('results', [])

                        if not results:
                            consecutive_empty += 1
                            print(f"[Confluence] 第 {start//limit + 1} 页: 0 个结果 (连续空结果: {consecutive_empty})")
                        else:
                            consecutive_empty = 0
                            pages.extend(results)
                            print(f"[Confluence] 第 {start//limit + 1} 页: {len(results)} 个结果")

                        # 如果返回结果少于 limit，说明已经是最后一页
                        if len(results) < limit:
                            break

                        start += limit

                    except Exception as inner_e:
                        print(f"[Confluence] 备用方法在 start={start} 时失败: {str(inner_e)}")
                        break

            # 调试信息
            print(f"[Confluence] API 返回的页面数量: {len(pages) if pages else 0}")
            if pages and len(pages) > 0:
                print(f"[Confluence] 第一个页面示例: {pages[0].get('id', 'N/A')} - {pages[0].get('title', 'N/A')}")
            elif not pages:
                print(f"[Confluence] 警告: 未找到任何页面，可能的原因:")
                print(f"  1. Space key '{space_key}' 不存在")
                print(f"  2. 没有访问权限")
                print(f"  3. Space 中没有页面")
                print(f"  4. API 认证问题")

            # 获取状态
            state = storage.get_confluence_state(source_name, space_key)

            # 检查哪些页面需要更新
            pages_to_fetch = []
            for page in pages:
                stats['total'] += 1
                page_id = page['id']
                last_version = state.get(page_id, {}).get('version', 0)
                current_version = page['version']['number']

                # 检查是否需要更新
                if current_version > last_version:
                    pages_to_fetch.append(page)
                else:
                    stats['skipped'] += 1

            # 报告扫描结果
            print(f"[Confluence] 扫描完成:")
            print(f"  - 总页面: {stats['total']}")
            print(f"  - 需要拉取: {len(pages_to_fetch)} (新增或已更新)")
            print(f"  - 跳过: {stats['skipped']} (未变化)")

            # 第二阶段：只拉取需要更新的页面
            if pages_to_fetch:
                print(f"\n[Confluence] 开始拉取 {len(pages_to_fetch)} 个页面...")
                for idx, page in enumerate(pages_to_fetch, 1):
                    try:
                        # 获取完整的页面数据（包含内容和历史）
                        page_id = page['id']
                        full_page = self.client.get_page_by_id(
                            page_id,
                            expand='body.storage,version,history'
                        )

                        attachments_count = self._process_page(source_name, space_key, full_page, storage)
                        stats['pages'] += 1
                        stats['attachments'] += attachments_count

                        # 更新状态
                        state[page_id] = {
                            'title': full_page['title'],
                            'last_updated': full_page['version']['when'],
                            'version': full_page['version']['number']
                        }

                        if idx % 10 == 0:
                            print(f"  进度: {idx}/{len(pages_to_fetch)}")

                    except Exception as e:
                        self.error_handler.log_error(
                            'fetch_confluence_page',
                            str(e),
                            (page.get('id'), page.get('title')),
                            {}
                        )

                print(f"[Confluence] 拉取完成: {stats['pages']} 个页面, {stats['attachments']} 个附件")
            else:
                print(f"[Confluence] 无需拉取，所有页面都是最新的")

        except Exception as e:
            self.error_handler.log_error(
                'crawl_confluence_space',
                str(e),
                (source_name, space_key),
                {}
            )

        return stats

    def _process_page(
        self,
        source_name: str,
        space_key: str,
        page: Dict[str, Any],
        storage: StorageManager
    ) -> int:
        """
        处理单个页面：转换 + 下载附件

        Args:
            source_name: 数据源名称
            space_key: Space key
            page: 页面数据
            storage: 存储管理器

        Returns:
            附件数量
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

            return len(attachments)

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
            return 0

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
