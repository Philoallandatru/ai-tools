#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试评论智能采样策略
"""

import sys
from crawler.analyzers.comment_analyzer import CommentAnalyzer

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


def create_test_comments(count: int) -> list:
    """创建测试评论"""
    comments = []

    # 前几条：问题发现
    if count >= 1:
        comments.append("[User A] 发现了一个严重的性能问题")
    if count >= 2:
        comments.append("[User B] 已经在3台设备上复现了这个问题")
    if count >= 3:
        comments.append("[User C] 问题影响了客户的生产环境")

    # 中间部分：根因分析和修复
    for i in range(3, min(count - 3, 50)):
        if i % 10 == 5:
            comments.append(f"[Dev {i}] 找到根因了：cache_mgr.c 中的逻辑错误")
        elif i % 10 == 6:
            comments.append(f"[Dev {i}] 已提交修复 patch，commit ID: abc123")
        elif i % 10 == 7:
            comments.append(f"[QA {i}] 修复后测试通过，验证了100台设备")
        elif i % 10 == 8:
            comments.append(f"[PM {i}] 决定将此修复纳入下个版本")
        else:
            comments.append(f"[User {i}] 这是第 {i} 条普通评论，没有特别重要的信息")

    # 最后几条：验证和总结
    if count >= 4:
        comments.append("[QA Lead] 回归测试全部通过")
    if count >= 5:
        comments.append("[PM] 问题已解决，可以关闭了")
    if count >= 6:
        comments.append("[Tech Lead] 总结：这是一个典型的并发问题")

    return comments[:count]


def test_sampling_strategy():
    """测试不同评论数量下的采样策略"""
    analyzer = CommentAnalyzer(llm_client=None)

    test_cases = [
        5,    # ≤10: 全部分析
        10,   # ≤10: 全部分析
        15,   # 11-30: 前5 + 后5
        30,   # 11-30: 前5 + 后5
        40,   # 31-50: 前5 + 关键词5 + 后5
        50,   # 31-50: 前5 + 关键词5 + 后5
        100,  # >50: 前3 + 关键词10 + 后3
    ]

    print("=" * 80)
    print("评论智能采样策略测试")
    print("=" * 80)

    for count in test_cases:
        print(f"\n{'='*80}")
        print(f"测试场景: {count} 条评论")
        print(f"{'='*80}")

        # 创建测试评论
        comments = create_test_comments(count)

        # 执行采样
        selected_comments, selected_indices = analyzer._smart_sample_comments(comments)

        # 打印结果
        print(f"\n总评论数: {count}")
        print(f"选中数量: {len(selected_comments)}")
        print(f"覆盖率: {len(selected_comments)/count*100:.1f}%")
        print(f"选中索引: {selected_indices}")

        # 打印选中的评论预览
        print(f"\n选中的评论:")
        for idx in selected_indices[:5]:  # 只显示前5个
            preview = comments[idx][:60]
            print(f"  [{idx+1}] {preview}...")

        if len(selected_indices) > 5:
            print(f"  ... (还有 {len(selected_indices)-5} 条)")

        # 验证策略
        if count <= 10:
            expected = count
            strategy = "全部分析"
        elif count <= 30:
            expected = 10
            strategy = "前5 + 后5"
        elif count <= 50:
            expected_min = 10
            expected_max = 15
            strategy = f"前5 + 关键词(最多5) + 后5"
        else:
            expected_min = 6
            expected_max = 16
            strategy = f"前3 + 关键词(最多10) + 后3"

        print(f"\n策略: {strategy}")

        if count <= 30:
            status = "✓" if len(selected_comments) == expected else "✗"
            print(f"验证: {status} (期望 {expected}, 实际 {len(selected_comments)})")
        else:
            status = "✓" if expected_min <= len(selected_comments) <= expected_max else "✗"
            print(f"验证: {status} (期望 {expected_min}-{expected_max}, 实际 {len(selected_comments)})")


def test_keyword_matching():
    """测试关键词匹配功能"""
    print("\n" + "=" * 80)
    print("关键词匹配测试")
    print("=" * 80)

    analyzer = CommentAnalyzer(llm_client=None)

    comments = [
        "这是一条普通评论",
        "找到根因了：内存泄漏",
        "已提交修复 patch",
        "测试通过，验证了50台设备",
        "决定采用方案A",
        "这是另一条普通评论",
        "root cause: race condition",
        "fix committed, PR #123",
        "test passed with 100% coverage",
        "decision: rollback to previous version",
    ]

    indices = analyzer._find_keyword_comments(comments, offset=0, max_count=5)

    print(f"\n总评论数: {len(comments)}")
    print(f"匹配数量: {len(indices)}")
    print(f"\n匹配的评论:")
    for idx in indices:
        print(f"  [{idx+1}] {comments[idx]}")


if __name__ == '__main__':
    test_sampling_strategy()
    test_keyword_matching()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
