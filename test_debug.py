import sys
from pathlib import Path
from crawler.doc_analyzer import DocumentAnalyzer

# 让用户指定文档路径
if len(sys.argv) < 2:
    print("用法: python test_debug.py <文档路径>")
    sys.exit(1)

doc_path = sys.argv[1]
analyzer = DocumentAnalyzer('config.yaml')

try:
    # 先测试切分
    print("=== 测试文档切分 ===")
    sections = analyzer._split_document(Path(doc_path))
    print(f"切分结果: {len(sections)} 个小节")
    for i, s in enumerate(sections[:10], 1):
        print(f"  {i}. {s.title} ({len(s.content)} 字符)")
    if len(sections) > 10:
        print(f"  ... 还有 {len(sections) - 10} 个小节")
    
    # 测试过滤和分组
    print("\n=== 测试智能处理 ===")
    section_groups = analyzer.doc_processor.process_sections(sections)
    print(f"处理结果: {len(section_groups)} 个小节组")
    for i, g in enumerate(section_groups[:10], 1):
        print(f"  {i}. {g.title} ({len(g.sections)} 个小节, {g.total_chars} 字符)")
    if len(section_groups) > 10:
        print(f"  ... 还有 {len(section_groups) - 10} 个小节组")
        
except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
