#!/usr/bin/env python
"""
批量文档分析脚本 - 分析指定目录下的所有Markdown文档
"""

import sys
import time
from pathlib import Path
from datetime import datetime


def batch_analyze_documents(input_dir: str, config_path: str, max_docs: int = None):
    """
    批量分析文档

    Args:
        input_dir: 输入文档目录
        config_path: 配置文件路径
        max_docs: 最大分析文档数（None表示全部）
    """
    from crawler.doc_analyzer import DocumentAnalyzer

    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"错误: 目录不存在 {input_dir}")
        return

    # 获取所有Markdown文件
    md_files = sorted(input_path.glob("*.md"))

    if not md_files:
        print(f"错误: 目录中没有找到Markdown文件 {input_dir}")
        return

    # 限制文档数量
    if max_docs:
        md_files = md_files[:max_docs]

    print(f"\n{'='*80}")
    print(f"批量文档分析")
    print(f"{'='*80}")
    print(f"输入目录: {input_dir}")
    print(f"配置文件: {config_path}")
    print(f"文档总数: {len(md_files)}")
    print(f"{'='*80}\n")

    # 初始化分析器
    analyzer = DocumentAnalyzer(config_path=config_path)

    # 统计信息
    total = len(md_files)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    start_time = time.time()

    results = []

    for i, md_file in enumerate(md_files, 1):
        # 安全处理文件名中的特殊字符（Windows 控制台兼容）
        safe_filename = md_file.name.encode('ascii', errors='replace').decode('ascii')
        print(f"\n[{i}/{total}] 分析: {safe_filename}")
        print("-" * 80)

        try:
            # 跳过某些文件（如目录、版权声明等）
            if should_skip(md_file.name):
                print(f"   [跳过] 非技术内容文档")
                skipped_count += 1
                continue

            # 分析文档
            report_path = analyzer.analyze_document(str(md_file), dry_run=False)

            results.append({
                'file': md_file.name,
                'status': 'success',
                'report': report_path
            })
            success_count += 1

            print(f"   [成功] 报告: {report_path}")

        except Exception as e:
            print(f"   [失败] 错误: {str(e)}")
            results.append({
                'file': md_file.name,
                'status': 'failed',
                'error': str(e)
            })
            failed_count += 1

        # 显示进度
        elapsed = time.time() - start_time
        avg_time = elapsed / i
        remaining = (total - i) * avg_time
        print(f"   进度: {i}/{total} ({i/total*100:.1f}%), "
              f"已用时: {elapsed/60:.1f}分钟, "
              f"预计剩余: {remaining/60:.1f}分钟")

    # 生成汇总报告
    total_time = time.time() - start_time
    generate_summary_report(results, total_time, input_dir)

    # 打印统计
    print(f"\n{'='*80}")
    print(f"批量分析完成")
    print(f"{'='*80}")
    print(f"总文档数: {total}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"跳过: {skipped_count}")
    print(f"总耗时: {total_time/60:.1f} 分钟")
    print(f"平均耗时: {total_time/total:.1f} 秒/文档")
    print(f"{'='*80}\n")


def should_skip(filename: str) -> bool:
    """判断是否应该跳过该文件"""
    skip_keywords = [
        'Table-of-Contents',
        'Table-of-Figures',
        'LEGAL',
        'Copyright',
        'DISCLAIMER',
        'SPECIFICATION-DISCLAIMER',
    ]

    for keyword in skip_keywords:
        if keyword in filename:
            return True

    return False


def generate_summary_report(results: list, total_time: float, input_dir: str):
    """生成汇总报告"""
    from pathlib import Path

    output_dir = Path("reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"batch_analysis_summary_{timestamp}.md"

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"# 批量文档分析汇总报告\n\n")
        f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**输入目录**: {input_dir}\n")
        f.write(f"**总文档数**: {len(results)}\n")
        f.write(f"**总耗时**: {total_time/60:.1f} 分钟\n\n")
        f.write(f"---\n\n")

        # 成功的文档
        success_results = [r for r in results if r['status'] == 'success']
        if success_results:
            f.write(f"## 成功分析 ({len(success_results)} 个)\n\n")
            for r in success_results:
                f.write(f"- [{r['file']}]({r['report']})\n")
            f.write(f"\n")

        # 失败的文档
        failed_results = [r for r in results if r['status'] == 'failed']
        if failed_results:
            f.write(f"## 失败文档 ({len(failed_results)} 个)\n\n")
            for r in failed_results:
                f.write(f"- {r['file']}: {r['error']}\n")
            f.write(f"\n")

    print(f"\n汇总报告已保存: {summary_file}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python batch_analyze.py <input_dir> [config_path] [max_docs]")
        print("示例: python batch_analyze.py test_output/nvme_full_split configs/doc_analysis_config.yaml 10")
        sys.exit(1)

    input_dir = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else "configs/doc_analysis_config.yaml"
    max_docs = int(sys.argv[3]) if len(sys.argv) > 3 else None

    batch_analyze_documents(input_dir, config_path, max_docs)
