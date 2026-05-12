"""
Shared test fixtures and utilities
"""

import pytest
from typing import Dict, Any
from crawler.llm_client import MockLLMClient, BaseLLMClient


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """提供 Mock LLM 客户端"""
    return MockLLMClient()


@pytest.fixture
def sample_jira_data() -> Dict[str, Any]:
    """提供示例 Jira 数据"""
    return {
        'key': 'TEST-1',
        'title': 'Test Issue',
        'status': 'In Progress',
        'priority': 'High',
        'type': 'Task',
        'assignee': 'John Doe',
        'description': 'This is a test issue description.',
        'comments': [
            '[Alice @ 2026-05-01 10:00]\nFirst comment',
            '[Bob @ 2026-05-02 14:30]\nSecond comment'
        ]
    }


@pytest.fixture
def sample_report_data() -> Dict[str, Any]:
    """提供示例报告数据"""
    return {
        'type': 'weekly',
        'start_date': '2026-05-05',
        'end_date': '2026-05-12',
        'jira': {
            'total_issues': 21,
            'by_status': {
                'To Do': 5,
                'In Progress': 10,
                'Done': 6
            },
            'by_priority': {
                'High': 3,
                'Medium': 12,
                'Low': 6
            },
            'new_issues': ['TEST-1', 'TEST-2'],
            'updated_issues': ['TEST-3', 'TEST-4']
        },
        'confluence': {
            'total_pages': 36,
            'new_pages': 2,
            'updated_pages': 5
        },
        'summary': {
            'fixed_issues': ['TEST-5', 'TEST-6']
        }
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """提供示例配置"""
    return {
        'llm': {
            'provider': 'mock',
            'max_tokens': 2000,
            'temperature': 0.7
        },
        'report_analysis': {
            'enabled': True,
            'analyzers': {
                'report_summary': {'max_tokens': 500},
                'key_insights': {'max_tokens': 800},
                'risk_analysis': {'max_tokens': 600}
            }
        },
        'knowledge': {
            'retriever': {
                'enabled': True,
                'top_k': 5,
                'min_score': 0.3
            }
        }
    }
