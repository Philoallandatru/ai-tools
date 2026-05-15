"""
Jira 附件下载降级方案单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from crawler.jira import JiraCrawler


class TestJiraAttachmentDownload(unittest.TestCase):
    """测试 Jira 附件下载的三重降级方案"""

    def setUp(self):
        """设置测试环境"""
        # 创建 mock 的 Jira client
        self.mock_client = Mock()
        self.mock_client.username = 'test@example.com'
        self.mock_client.password = 'test-token'

        # 创建 mock 的 error handler
        self.mock_error_handler = Mock()
        self.mock_error_handler.retry_on_failure = lambda func: func

        # 创建 JiraCrawler 实例
        with patch('crawler.jira.Jira', return_value=self.mock_client):
            self.crawler = JiraCrawler(
                url='https://test.atlassian.net',
                token='test-token',
                error_handler=self.mock_error_handler,
                username='test@example.com',
                is_cloud=True
            )
            self.crawler.client = self.mock_client

    def test_method1_success(self):
        """测试方法1成功：get_attachment_content"""
        # 准备测试数据
        attachment = {
            'filename': 'test.png',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10000'
        }
        expected_content = b'fake image content'

        # Mock 方法1成功
        self.mock_client.get_attachment_content = Mock(return_value=expected_content)

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.png')
        self.assertEqual(result['content'], expected_content)
        self.mock_client.get_attachment_content.assert_called_once_with('10000')

    def test_method2_fallback(self):
        """测试方法2降级：client.get"""
        # 准备测试数据
        attachment = {
            'filename': 'test.docx',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10001'
        }
        expected_content = b'fake docx content'

        # Mock 方法1失败，方法2成功
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(return_value=expected_content)

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.docx')
        self.assertEqual(result['content'], expected_content)
        self.mock_client.get.assert_called_once()

    def test_method2_string_to_bytes(self):
        """测试方法2将字符串转换为 bytes"""
        # 准备测试数据
        attachment = {
            'filename': 'test.pdf',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10002'
        }

        # Mock 方法1失败，方法2返回字符串
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(return_value='string content')

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.pdf')
        self.assertIsInstance(result['content'], bytes)
        self.assertEqual(result['content'], b'string content')

    @patch('requests.get')
    def test_method3_with_basic_auth(self, mock_requests_get):
        """测试方法3使用 basic auth"""
        # 准备测试数据
        attachment = {
            'filename': 'test.jpg',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10003'
        }
        expected_content = b'fake jpg content'

        # 确保使用 basic auth（移除 token 如果存在）
        if hasattr(self.mock_client, 'token'):
            delattr(self.mock_client, 'token')
        self.mock_client.username = 'test@example.com'
        self.mock_client.password = 'test-token'

        # Mock 方法1和2失败
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(side_effect=Exception("Method 2 failed"))

        # Mock requests 成功
        mock_response = Mock()
        mock_response.content = expected_content
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.jpg')
        self.assertEqual(result['content'], expected_content)

        # 验证使用了 basic auth
        mock_requests_get.assert_called_once()
        call_kwargs = mock_requests_get.call_args[1]
        self.assertIn('auth', call_kwargs)
        self.assertEqual(call_kwargs['auth'], ('test@example.com', 'test-token'))

    @patch('requests.get')
    def test_method3_with_token(self, mock_requests_get):
        """测试方法3使用 token"""
        # 准备测试数据
        attachment = {
            'filename': 'test.xlsx',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10004'
        }
        expected_content = b'fake xlsx content'

        # 设置 client 使用 token
        self.mock_client.token = 'bearer-token-123'
        delattr(self.mock_client, 'username')
        delattr(self.mock_client, 'password')

        # Mock 方法1和2失败
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(side_effect=Exception("Method 2 failed"))

        # Mock requests 成功
        mock_response = Mock()
        mock_response.content = expected_content
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.xlsx')
        self.assertEqual(result['content'], expected_content)

        # 验证使用了 token header
        mock_requests_get.assert_called_once()
        call_kwargs = mock_requests_get.call_args[1]
        self.assertIn('headers', call_kwargs)
        self.assertEqual(call_kwargs['headers']['Authorization'], 'Bearer bearer-token-123')

    @patch('requests.get')
    def test_method3_no_auth(self, mock_requests_get):
        """测试方法3无认证信息"""
        # 准备测试数据
        attachment = {
            'filename': 'test.gif',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10005'
        }
        expected_content = b'fake gif content'

        # 移除所有认证信息
        if hasattr(self.mock_client, 'username'):
            delattr(self.mock_client, 'username')
        if hasattr(self.mock_client, 'password'):
            delattr(self.mock_client, 'password')
        if hasattr(self.mock_client, 'token'):
            delattr(self.mock_client, 'token')

        # Mock 方法1和2失败
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(side_effect=Exception("Method 2 failed"))

        # Mock requests 成功
        mock_response = Mock()
        mock_response.content = expected_content
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.gif')
        self.assertEqual(result['content'], expected_content)

        # 验证没有使用认证
        mock_requests_get.assert_called_once()
        call_kwargs = mock_requests_get.call_args[1]
        self.assertNotIn('auth', call_kwargs)
        self.assertNotIn('headers', call_kwargs)

    @patch('requests.get')
    def test_all_methods_fail(self, mock_requests_get):
        """测试所有方法都失败"""
        # 准备测试数据
        attachment = {
            'filename': 'test.bmp',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10006'
        }

        # Mock 所有方法失败
        self.mock_client.get_attachment_content = Mock(side_effect=Exception("Method 1 failed"))
        self.mock_client.get = Mock(side_effect=Exception("Method 2 failed"))

        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=Exception("Method 3 failed"))
        mock_requests_get.return_value = mock_response

        # 执行下载，应该抛出异常
        with self.assertRaises(Exception) as context:
            self.crawler._download_single_attachment(attachment)

        # 验证异常信息
        self.assertIn("所有下载方法都失败", str(context.exception))

    def test_method1_returns_none(self):
        """测试方法1返回 None 时降级到方法2"""
        # 准备测试数据
        attachment = {
            'filename': 'test.png',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10007'
        }
        expected_content = b'fake content from method 2'

        # Mock 方法1返回 None，方法2成功
        self.mock_client.get_attachment_content = Mock(return_value=None)
        self.mock_client.get = Mock(return_value=expected_content)

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.png')
        self.assertEqual(result['content'], expected_content)

    def test_method1_returns_empty_bytes(self):
        """测试方法1返回空 bytes 时降级到方法2"""
        # 准备测试数据
        attachment = {
            'filename': 'test.png',
            'content': 'https://test.atlassian.net/rest/api/2/attachment/content/10008'
        }
        expected_content = b'fake content from method 2'

        # Mock 方法1返回空 bytes，方法2成功
        self.mock_client.get_attachment_content = Mock(return_value=b'')
        self.mock_client.get = Mock(return_value=expected_content)

        # 执行下载
        result = self.crawler._download_single_attachment(attachment)

        # 验证结果
        self.assertIsNotNone(result)
        self.assertEqual(result['filename'], 'test.png')
        self.assertEqual(result['content'], expected_content)


if __name__ == '__main__':
    unittest.main()
