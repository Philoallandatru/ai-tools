import sys
from pathlib import Path
from crawler.doc_analyzer import DocumentAnalyzer
import logging

# 启用详细日志
logging.basicConfig(level=logging.INFO, format='%(message)s')

if len(sys.argv) < 2:
    print("用法: python test_filter_debug.py <文档路径>")
    sys.exit(1)

doc_path = sys.argv[1]
analyzer = DocumentAnalyzer('config.yaml')

# 1. 切分文档
print("=== 步骤 1: 切分文档 ===")
sections = analyzer._split_document(Path(doc_path))
print(f"切分结果: {len(sections)} 个小节\n")

# 2. 测试过滤器
print("=== 步骤 2: 过滤小节 ===")
filter_obj = analyzer.doc_processor.filter
total_chars = sum(len(s.content) for s in sections)
print(f"总字符数: {total_chars}")
print(f"过滤配置:")
print(f"  skip_empty: {filter_obj.skip_empty}")
print(f"  min_section_chars: {filter_obj.min_section_chars}")
print(f"  min_content_ratio: {filter_obj.min_content_ratio}")
print(f"  exclude_patterns: {filter_obj.exclude_patterns}\n")

# 逐个检查小节
skipped = 0
kept = 0
for i, section in enumerate(sections[:20], 1):  # 只检查前20个
    should_skip = filter_obj._should_skip(section, total_chars)
    status = "❌ 跳过" if should_skip else "✅ 保留"
    print(f"{i}. {status} - {section.title} ({len(section.content)} 字符)")
    if should_skip:
        skipped += 1
        reason = filter_obj._get_skip_reason(section, total_chars)
        print(f"   原因: {reason}")
    else:
        kept += 1

if len(sections) > 20:
    print(f"\n... 还有 {len(sections) - 20} 个小节未显示")

print(f"\n统计: 保留 {kept} 个, 跳过 {skipped} 个 (前20个)")

# 3. 完整处理
print("\n=== 步骤 3: 完整处理 ===")
section_groups = analyzer.doc_processor.process_sections(sections)
print(f"最终结果: {len(section_groups)} 个小节组")
