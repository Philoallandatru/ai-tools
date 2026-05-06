"""
错误处理模块 - 提供重试机制、错误日志和错误报告
"""

import logging
import time
import traceback
from functools import wraps
from typing import List, Dict, Any, Callable


class ErrorHandler:
    """错误处理器 - 管理错误日志、重试和报告"""

    def __init__(self, max_retries: int = 3, retry_delay: int = 5, error_log: str = 'sync-errors.log'):
        """
        初始化错误处理器

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            error_log: 错误日志文件路径
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_log = error_log
        self.errors: List[Dict[str, Any]] = []

        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(error_log, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def retry_on_failure(self, func: Callable) -> Callable:
        """
        装饰器：失败时自动重试

        Args:
            func: 要装饰的函数

        Returns:
            装饰后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    self.logger.warning(
                        f"尝试 {attempt + 1}/{self.max_retries} 失败: {func.__name__} - {str(e)}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                    else:
                        # 记录完整堆栈跟踪
                        tb = traceback.format_exc()
                        self.log_error(func.__name__, str(e), args, kwargs, tb)
                        return None
        return wrapper

    def log_error(self, operation: str, error_msg: str, args: tuple, kwargs: dict, traceback_str: str = None):
        """
        记录错误

        Args:
            operation: 操作名称
            error_msg: 错误消息
            args: 函数参数
            kwargs: 函数关键字参数
            traceback_str: 堆栈跟踪字符串
        """
        error_entry = {
            'operation': operation,
            'error': error_msg,
            'args': str(args),
            'kwargs': str(kwargs),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'traceback': traceback_str
        }
        self.errors.append(error_entry)
        self.logger.error(f"操作失败: {operation} - {error_msg}")
        if traceback_str:
            self.logger.error(f"堆栈跟踪:\n{traceback_str}")

    def generate_error_report(self):
        """生成错误报告"""
        if not self.errors:
            self.logger.info("[OK] 同步完成，无错误")
            return

        self.logger.warning(f"\n{'='*60}")
        self.logger.warning(f"错误报告 - 共 {len(self.errors)} 个错误")
        self.logger.warning(f"{'='*60}")

        for i, error in enumerate(self.errors, 1):
            self.logger.warning(f"\n错误 #{i}:")
            self.logger.warning(f"  操作: {error['operation']}")
            self.logger.warning(f"  错误: {error['error']}")
            self.logger.warning(f"  时间: {error['timestamp']}")
            if error.get('traceback'):
                self.logger.warning(f"  堆栈:\n{error['traceback']}")

        self.logger.warning(f"\n详细日志请查看: {self.error_log}")
