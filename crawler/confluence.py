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

    def get_page_by_title(self, space_key: str, title: str) -> Optional[Dict[str, Any]]:
        """
        通过标题在指定 space 中查找页面

        Args:
            space_key: Space key
            title: 页面标题

        Returns:
            页面信息字典，如果未找到则返回 None
        """
        try:
            # 使用 CQL 查询精确匹配标题
            cql = f'space = "{space_key}" AND title = "{title}"'
            result = self.client.cql(cql, limit=1)

            if result and 'results' in result and len(result['results']) > 0:
                page = result['results'][0]
                return {
                    'id': page['content']['id'],
                    'title': page['content']['title'],
                    'type': page['content']['type'],
                    'space': page['content']['space']['key'] if 'space' in page['content'] else space_key
                }
            return None
        except Exception as e:
            print(f"[Confluence] 查找页面失败: {str(e)}")
            return None

    def crawl_space(
        self,
        source_name: str,
        space_key: str,
        storage: StorageManager,
        max_pages: Optional[int] = None,
        root_page_id: Optional[str] = None,
        root_page_title: Optional[str] = None
    ) -> Dict[str, int]:
        """
        爬取指定 space 的所有页面

        Args:
            source_name: 数据源名称
            space_key: Space key
            storage: 存储管理器
            max_pages: 可选，限制拉取的最大页面数（用于测试）
            root_page_id: 可选，只抓取指定页面及其子页面（通过 ID）
            root_page_title: 可选，只抓取指定页面及其子页面（通过标题）

        Returns:
            统计信息字典 {'pages': int, 'attachments': int, 'skipped': int, 'total': int}
        """
        stats = {'pages': 0, 'attachments': 0, 'skipped': 0, 'total': 0}

        try:
            # 第一阶段：获取所有页面的基本信息
            print(f"\n[Confluence] 正在扫描 space {space_key} 的页面...")
            print(f"[Confluence] 模式: {'Cloud' if self.client.cloud else 'Server'}")
            print(f"[Confluence] URL: {self.base_url}")
            if max_pages:
                print(f"[Confluence] 限制: 最多拉取 {max_pages} 个页面")

            # 如果指定了标题，先通过标题查找页面 ID
            if root_page_title:
                print(f"[Confluence] 通过标题查找根页面: '{root_page_title}'")
                root_page = self.get_page_by_title(space_key, root_page_title)
                if root_page:
                    root_page_id = root_page['id']
                    print(f"[Confluence] 找到页面: {root_page['title']} (ID: {root_page_id})")
                else:
                    print(f"[Confluence] 错误: 未找到标题为 '{root_page_title}' 的页面")
                    return stats

            if root_page_id:
                print(f"[Confluence] 限制: 只抓取页面 {root_page_id} 及其子页面")

            # 根据是否指定根页面选择不同的获取方式
            if root_page_id:
                pages = self._get_page_tree(root_page_id, max_pages)
            else:
                pages = self._get_all_pages_from_space(space_key, max_pages)

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

    def _get_all_pages_from_space(self, space_key: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取 space 的所有页面（使用手动分页确保获取所有页面）

        Args:
            space_key: Space key
            max_pages: 可选，限制获取的最大页面数

        Returns:
            页面列表
        """
        # 注意：直接使用 get_all_pages_from_space_raw 而不是 get_all_pages_from_space
        # 因为后者有一个 bug：使用 <= limit 而不是 < limit 作为终止条件
        pages = []
        start = 0
        limit = 100  # 每页获取 100 个，减少 API 调用次数

        print(f"[Confluence] 开始分页获取所有页面...")

        while True:
            try:
                # 直接调用 raw 方法来绕过库的 bug
                response = self.client.get_all_pages_from_space_raw(
                    space=space_key,
                    start=start,
                    limit=limit,
                    expand='version'
                )

                results = response.get('results', [])

                if not results:
                    print(f"[Confluence] 第 {start//limit + 1} 页: 0 个结果，分页结束")
                    break

                pages.extend(results)
                print(f"[Confluence] 第 {start//limit + 1} 页: {len(results)} 个结果 (累计: {len(pages)})")

                # 检查是否达到最大页面数限制
                if max_pages and len(pages) >= max_pages:
                    pages = pages[:max_pages]
                    print(f"[Confluence] 已达到最大页面数限制 ({max_pages})，停止获取")
                    break

                # 如果返回结果少于 limit，说明已经是最后一页
                if len(results) < limit:
                    print(f"[Confluence] 已到达最后一页")
                    break

                start += limit

            except Exception as e:
                print(f"[Confluence] 分页获取失败 (start={start}): {str(e)}")
                print(f"[Confluence] 已获取 {len(pages)} 个页面，继续处理...")
                break

        return pages

    def _get_page_tree(self, root_page_id: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        递归获取指定页面及其所有子页面

        Args:
            root_page_id: 根页面 ID
            max_pages: 可选，限制获取的最大页面数

        Returns:
            页面列表（包含根页面和所有子页面）
        """
        pages = []
        visited = set()

        print(f"[Confluence] 开始获取页面树 (根页面: {root_page_id})...")

        def fetch_page_and_children(page_id: str):
            """递归获取页面及其子页面"""
            if page_id in visited:
                return
            if max_pages and len(pages) >= max_pages:
                return

            visited.add(page_id)

            try:
                # 获取页面基本信息
                page = self.client.get_page_by_id(page_id, expand='version')
                pages.append(page)
                print(f"[Confluence] 获取页面: {page['title']} (ID: {page_id}) - 累计: {len(pages)}")

                # 获取子页面
                children = self.client.get_page_child_by_type(page_id, type='page', start=0, limit=100)

                if children and isinstance(children, list):
                    child_list = children
                elif children and isinstance(children, dict):
                    child_list = children.get('results', [])
                else:
                    child_list = []

                # 递归处理每个子页面
                for child in child_list:
                    if max_pages and len(pages) >= max_pages:
                        print(f"[Confluence] 已达到最大页面数限制 ({max_pages})，停止获取")
                        return
                    fetch_page_and_children(child['id'])

            except Exception as e:
                print(f"[Confluence] 获取页面 {page_id} 失败: {str(e)}")

        fetch_page_and_children(root_page_id)
        print(f"[Confluence] 页面树获取完成，共 {len(pages)} 个页面")

        return pages
