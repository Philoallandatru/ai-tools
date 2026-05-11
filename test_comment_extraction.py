"""
测试评论提取正则表达式
"""

import re
from pathlib import Path

# 读取 KAN-13 文件
file_path = Path('sources/KAN-13.md')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取评论
comments = []
comment_pattern = re.compile(r'###\s+(.+?)\s+-\s+(.+?)\n\n(.+?)(?=\n###|\n##|\Z)', re.DOTALL)

print("开始匹配评论...")
print(f"文件长度: {len(content)} 字符")
print("")

for i, match in enumerate(comment_pattern.finditer(content), 1):
    author = match.group(1).strip()
    timestamp = match.group(2).strip()
    comment_text = match.group(3).strip()

    print(f"=== 评论 #{i} ===")
    print(f"作者: {author}")
    print(f"时间: {timestamp}")
    print(f"内容: {comment_text[:100]}...")
    print("")

    comments.append(f"[{author} @ {timestamp}]\n{comment_text}")

print(f"总共找到 {len(comments)} 条评论")

# 显示前 3 条完整评论
print("\n前 3 条完整评论:")
for i, comment in enumerate(comments[:3], 1):
    print(f"\n=== 评论 {i} ===")
    print(comment)
