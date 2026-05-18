"""
Confluence 连接诊断工具
用于诊断 Confluence Server/Cloud 连接和 API 问题
"""

import sys
import yaml
from pathlib import Path
from atlassian import Confluence

# 强制使用 UTF-8 编码（Windows 兼容性）
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def diagnose_confluence(config_path: str = "config.yaml"):
    """诊断 Confluence 连接"""

    # 加载配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    confluence_sources = config.get('sources', {}).get('confluence', [])

    if not confluence_sources:
        print("❌ 配置文件中没有找到 Confluence 数据源")
        return

    for source in confluence_sources:
        print(f"\n{'='*60}")
        print(f"诊断数据源: {source['name']}")
        print(f"{'='*60}")

        # 基本信息
        url = source['url']
        is_cloud = source.get('type', 'cloud').lower() == 'cloud'

        print(f"URL: {url}")
        print(f"类型: {'Cloud' if is_cloud else 'Server'}")

        # 创建客户端
        try:
            if is_cloud:
                username = source.get('username')
                token = source['api_token']
                print(f"用户名: {username}")
                client = Confluence(url=url, username=username, password=token, cloud=True)
            else:
                token = source['api_token']
                print(f"认证: Personal Access Token")
                client = Confluence(url=url, token=token, cloud=False)

            print("✓ 客户端创建成功")
        except Exception as e:
            print(f"❌ 客户端创建失败: {str(e)}")
            continue

        # 测试连接
        print("\n测试 1: 获取当前用户信息")
        try:
            user = client.get_current_user_details()
            print(f"✓ 连接成功")
            print(f"  用户: {user.get('displayName', 'N/A')}")
            print(f"  邮箱: {user.get('email', 'N/A')}")
        except Exception as e:
            print(f"⚠️  无法获取用户信息: {str(e)}")
            print(f"  尝试其他测试...")

        # 测试每个 space
        for space_config in source.get('spaces', []):
            space_key = space_config['key']
            print(f"\n测试 2: 获取 Space '{space_key}' 信息")

            try:
                space = client.get_space(space_key)
                print(f"✓ Space 存在")
                print(f"  名称: {space.get('name', 'N/A')}")
                print(f"  类型: {space.get('type', 'N/A')}")
            except Exception as e:
                print(f"❌ 无法获取 Space: {str(e)}")
                print(f"  可能的原因:")
                print(f"    1. Space key '{space_key}' 不存在")
                print(f"    2. 没有访问权限")
                continue

            print(f"\n测试 3: 获取 Space '{space_key}' 的页面")

            # 方法 1: get_all_pages_from_space
            try:
                pages = client.get_all_pages_from_space(space_key, expand='version')
                print(f"✓ 方法 1 (get_all_pages_from_space) 成功")
                print(f"  页面数量: {len(pages)}")
                if pages:
                    print(f"  第一个页面: {pages[0].get('title', 'N/A')}")
            except Exception as e:
                print(f"❌ 方法 1 失败: {str(e)}")

            # 方法 2: get_all_pages_from_space_raw (手动分页)
            print(f"\n测试 4: 使用原始 API 获取页面")
            try:
                response = client.get_all_pages_from_space_raw(
                    space=space_key,
                    start=0,
                    limit=10,
                    expand='version'
                )
                results = response.get('results', [])
                print(f"✓ 方法 2 (get_all_pages_from_space_raw) 成功")
                print(f"  第一页结果数: {len(results)}")
                print(f"  总数 (size): {response.get('size', 'N/A')}")

                if results:
                    print(f"  第一个页面:")
                    print(f"    ID: {results[0].get('id', 'N/A')}")
                    print(f"    标题: {results[0].get('title', 'N/A')}")
                    print(f"    版本: {results[0].get('version', {}).get('number', 'N/A')}")
                else:
                    print(f"  ⚠️  返回 0 个结果")
                    print(f"  响应内容: {response}")

            except Exception as e:
                print(f"❌ 方法 2 失败: {str(e)}")
                import traceback
                print(f"  详细错误:")
                traceback.print_exc()

        print(f"\n{'='*60}")
        print(f"诊断完成: {source['name']}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Confluence 连接诊断工具")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )

    args = parser.parse_args()
    diagnose_confluence(args.config)
