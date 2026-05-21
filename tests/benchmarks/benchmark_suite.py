#!/usr/bin/env python3
"""
基准测试套件 - 用于性能监控和回归测试
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import sys

class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, output_dir: str = "./opencode-reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[Dict[str, Any]] = []

    def measure_performance(self, name: str, command: List[str], timeout: int = 300) -> Dict[str, Any]:
        """
        测量命令执行性能

        Args:
            name: 测试名称
            command: 命令列表
            timeout: 超时时间（秒）

        Returns:
            性能指标字典
        """
        print(f"测试: {name}")

        # 执行命令
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
        except subprocess.TimeoutExpired:
            success = False
            output = ""
            error = f"Timeout after {timeout} seconds"
        except Exception as e:
            success = False
            output = ""
            error = str(e)

        end_time = time.time()
        duration = end_time - start_time

        result_data = {
            "name": name,
            "success": success,
            "duration": round(duration, 2),
            "output_size": len(output),
            "error": error if not success else None
        }

        status = "通过" if success else "失败"
        print(f"  {status} (耗时: {duration:.2f}s)")

        return result_data

    def run_benchmark_suite(self):
        """运行完整的基准测试套件"""
        print("=" * 60)
        print("基准测试套件")
        print("=" * 60)

        # 测试 1: 文档分析
        print("\n[1/3] 文档分析测试")
        self.results.append(
            self.measure_performance(
                "doc_analysis",
                ["python", "cli.py", "analyze-doc", "sources/KAN-1.md"],
                timeout=300
            )
        )

        # 测试 2: Jira 分析
        print("\n[2/3] Jira 分析测试")
        self.results.append(
            self.measure_performance(
                "jira_analysis",
                ["python", "cli.py", "analyze-jira", "KAN-10"],
                timeout=300
            )
        )

        # 测试 3: 报告生成
        print("\n[3/3] 报告生成测试")
        self.results.append(
            self.measure_performance(
                "report_generation",
                ["python", "cli.py", "generate-report", "--report-type", "weekly"],
                timeout=180
            )
        )

        # 保存结果
        self.save_results()
        self.print_summary()

    def save_results(self):
        """保存测试结果"""
        output_file = self.output_dir / "benchmark_results.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {output_file}")

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("基准测试摘要")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        total_time = sum(r["duration"] for r in self.results)

        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        print(f"总耗时: {total_time:.2f}s")
        print()

        print("详细结果:")
        print("-" * 60)
        for result in self.results:
            status = "通过" if result["success"] else "失败"
            print(f"{status:<6} {result['name']:<25} {result['duration']:>6.2f}s")

    def compare_with_baseline(self, baseline_file: str):
        """
        与基准结果对比

        Args:
            baseline_file: 基准结果文件路径
        """
        baseline_path = Path(baseline_file)
        if not baseline_path.exists():
            print(f"\n基准文件不存在: {baseline_file}")
            print("使用当前结果作为基准")
            self.save_baseline(baseline_file)
            return

        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)

        baseline_results = {r["name"]: r for r in baseline_data["results"]}

        print("\n" + "=" * 60)
        print("性能对比（当前 vs 基准）")
        print("=" * 60)

        for result in self.results:
            name = result["name"]
            if name not in baseline_results:
                print(f"\n{name}: 无基准数据")
                continue

            baseline = baseline_results[name]

            # 计算变化
            time_delta = result["duration"] - baseline["duration"]
            time_percent = (time_delta / baseline["duration"]) * 100 if baseline["duration"] > 0 else 0

            # 判断趋势
            if abs(time_percent) < 10:
                time_trend = "稳定"
            elif time_delta > 0:
                time_trend = "变慢"
            else:
                time_trend = "变快"

            print(f"\n{name}:")
            print(f"  时间: {result['duration']:.2f}s (基准: {baseline['duration']:.2f}s, {time_delta:+.2f}s, {time_trend} {time_percent:+.1f}%)")

    def save_baseline(self, baseline_file: str):
        """保存当前结果作为基准"""
        baseline_path = Path(baseline_file)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)

        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        print(f"基准已保存到: {baseline_file}")

if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run_benchmark_suite()
    runner.compare_with_baseline("baseline_results.json")
