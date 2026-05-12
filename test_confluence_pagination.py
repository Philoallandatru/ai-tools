"""
测试 Confluence 分页逻辑

模拟场景：
1. Space 有 250 个页面
2. 每页返回 100 个结果
3. 验证是否能正确获取所有 250 个页面
"""

class MockConfluenceClient:
    """模拟 Confluence 客户端"""

    def __init__(self, total_pages=250, page_size=100):
        self.total_pages = total_pages
        self.page_size = page_size
        self.api_calls = []

    def get_all_pages_from_space_raw(self, space, start, limit, expand=None):
        """模拟 API 调用"""
        self.api_calls.append({'start': start, 'limit': limit})

        # 计算这一页应该返回多少结果
        remaining = self.total_pages - start
        results_count = min(limit, remaining)

        # 生成模拟结果
        results = []
        for i in range(results_count):
            page_num = start + i + 1
            results.append({
                'id': str(page_num),
                'title': f'Page {page_num}',
                'version': {'number': 1}
            })

        return {'results': results}


def test_pagination_logic():
    """测试分页逻辑"""

    # 场景 1: 250 个页面，每页 100 个
    print("场景 1: 250 个页面，每页 100 个")
    client = MockConfluenceClient(total_pages=250, page_size=100)

    pages = []
    start = 0
    limit = 100

    while True:
        response = client.get_all_pages_from_space_raw(
            space='TEST',
            start=start,
            limit=limit,
            expand='version'
        )

        results = response.get('results', [])

        if not results:
            print(f"  第 {start//limit + 1} 页: 0 个结果，分页结束")
            break

        pages.extend(results)
        print(f"  第 {start//limit + 1} 页: {len(results)} 个结果 (累计: {len(pages)})")

        # 正确的终止条件：< limit
        if len(results) < limit:
            print(f"  已到达最后一页")
            break

        start += limit

    print(f"  总共获取: {len(pages)} 个页面")
    print(f"  API 调用次数: {len(client.api_calls)}")
    assert len(pages) == 250, f"期望 250 个页面，实际获取 {len(pages)} 个"
    print("  [OK] 测试通过\n")

    # 场景 2: 100 个页面（正好一页）
    print("场景 2: 100 个页面（正好一页）")
    client = MockConfluenceClient(total_pages=100, page_size=100)

    pages = []
    start = 0
    limit = 100

    while True:
        response = client.get_all_pages_from_space_raw(
            space='TEST',
            start=start,
            limit=limit,
            expand='version'
        )

        results = response.get('results', [])

        if not results:
            break

        pages.extend(results)
        print(f"  第 {start//limit + 1} 页: {len(results)} 个结果 (累计: {len(pages)})")

        if len(results) < limit:
            print(f"  已到达最后一页")
            break

        start += limit

    print(f"  总共获取: {len(pages)} 个页面")
    print(f"  API 调用次数: {len(client.api_calls)}")
    assert len(pages) == 100, f"期望 100 个页面，实际获取 {len(pages)} 个"
    print("  [OK] 测试通过\n")

    # 场景 3: 演示错误的终止条件（<= limit）
    print("场景 3: 错误的终止条件（<= limit）- 演示 bug")
    client = MockConfluenceClient(total_pages=250, page_size=100)

    pages = []
    start = 0
    limit = 100

    while True:
        response = client.get_all_pages_from_space_raw(
            space='TEST',
            start=start,
            limit=limit,
            expand='version'
        )

        results = response.get('results', [])

        if not results:
            break

        pages.extend(results)
        print(f"  第 {start//limit + 1} 页: {len(results)} 个结果 (累计: {len(pages)})")

        # 错误的终止条件：<= limit（这是库的 bug）
        if len(results) <= limit:
            print(f"  [BUG] 错误地提前终止（使用了 <= limit）")
            break

        start += limit

    print(f"  总共获取: {len(pages)} 个页面")
    print(f"  [BUG] 应该获取 250 个，但只获取了 {len(pages)} 个\n")


if __name__ == '__main__':
    test_pagination_logic()
