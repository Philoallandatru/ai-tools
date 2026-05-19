"""
Wiki Batch Compiler - 批量编译 wiki 源文件
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class BatchCompilationConfig:
    """批量编译配置"""
    batch_size: int = 5
    compile_timeout: int = 300  # seconds
    stop_on_failure: bool = True
    auto_cleanup_temp: bool = False


@dataclass
class BatchStatus:
    """批次状态"""
    batch_number: int
    total_batches: int
    files: List[str]
    status: str  # 'pending', 'compiling', 'completed', 'failed'
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WikiBatchCompiler:
    """Wiki 批量编译管理器"""

    def __init__(self, wiki_path: Path, config: BatchCompilationConfig, llm_config: Optional[Dict[str, Any]] = None):
        self.wiki_path = wiki_path
        self.config = config
        self.llm_config = llm_config or {}
        self.temp_dir = wiki_path / "temp"
        self.sources_dir = wiki_path / "sources"
        self.state_file = wiki_path / ".batch-state.json"

    def start_batch_compilation(self, resume: bool = False) -> Dict[str, Any]:
        """
        启动批量编译流程

        Args:
            resume: 是否从上次失败处继续

        Returns:
            编译摘要
        """
        # 1. 扫描 temp 目录
        temp_files = self._scan_temp_files()
        if not temp_files:
            return {"status": "no_files", "message": "No files in temp directory"}

        # 2. 初始化或恢复状态
        if resume and self.state_file.exists():
            state = self._load_state()
            # 过滤掉已完成的文件
            completed_set = set(state.get('completed_files', []))
            temp_files = [f for f in temp_files if f.name not in completed_set]
            if not temp_files:
                return {"status": "already_completed", "message": "All files already compiled"}
        else:
            total_batches = (len(temp_files) + self.config.batch_size - 1) // self.config.batch_size
            state = self._init_state(temp_files, total_batches)

        # 3. 处理批次
        results = []
        total_batches = (len(temp_files) + self.config.batch_size - 1) // self.config.batch_size

        for batch_num in range(1, total_batches + 1):
            batch_result = self._process_batch(batch_num, temp_files, state)
            results.append(batch_result)

            if batch_result.status == 'failed' and self.config.stop_on_failure:
                print(f"[WikiBatchCompiler] 批次 {batch_num} 失败，停止编译")
                break

        # 4. 清理和返回摘要
        if self.config.auto_cleanup_temp and all(r.status == 'completed' for r in results):
            self._cleanup_temp()

        return self._generate_summary(results)

    def _process_batch(self, batch_num: int, all_files: List[Path],
                       state: Dict) -> BatchStatus:
        """处理单个批次"""
        start_idx = (batch_num - 1) * self.config.batch_size
        end_idx = min(start_idx + self.config.batch_size, len(all_files))
        batch_files = all_files[start_idx:end_idx]

        batch_status = BatchStatus(
            batch_number=batch_num,
            total_batches=state['total_batches'],
            files=[f.name for f in batch_files],
            status='compiling',
            started_at=datetime.now().isoformat()
        )

        print(f"[WikiBatchCompiler] 处理批次 {batch_num}/{state['total_batches']}: {len(batch_files)} 个文件")

        try:
            # 1. 移动文件从 temp/ 到 sources/
            self._move_files_to_sources(batch_files)

            # 2. 运行编译
            self._run_compilation()

            # 3. 更新状态
            batch_status.status = 'completed'
            batch_status.completed_at = datetime.now().isoformat()

            # 4. 更新状态文件
            self._update_state(state, batch_status)

            print(f"[WikiBatchCompiler] 批次 {batch_num} 完成")

        except Exception as e:
            batch_status.status = 'failed'
            batch_status.error = str(e)
            batch_status.completed_at = datetime.now().isoformat()
            print(f"[WikiBatchCompiler] 批次 {batch_num} 失败: {str(e)}")

            # 更新状态文件
            self._update_state(state, batch_status)

        return batch_status

    def _move_files_to_sources(self, files: List[Path]) -> None:
        """移动文件从 temp/ 到 sources/ 保留结构"""
        for file_path in files:
            # 确定目标路径（保留 Jira/Confluence 结构）
            relative_path = file_path.relative_to(self.temp_dir)
            target_path = self.sources_dir / relative_path

            # 创建父目录
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # 移动文件
            shutil.move(str(file_path), str(target_path))
            print(f"  移动: {file_path.name} → sources/{relative_path}")

    def _run_compilation(self) -> None:
        """运行 npx llm-wiki-compiler compile"""
        import os

        cmd = ["npx", "llm-wiki-compiler", "compile"]

        # 设置环境变量（如果提供了 LLM 配置）
        env = os.environ.copy()
        if self.llm_config:
            if 'base_url' in self.llm_config:
                env['OPENAI_BASE_URL'] = self.llm_config['base_url']
            if 'api_key' in self.llm_config:
                env['OPENAI_API_KEY'] = self.llm_config['api_key']
            elif 'OPENAI_API_KEY' not in env:
                env['OPENAI_API_KEY'] = 'dummy'  # 本地 LLM 不需要真实 key
            if 'model' in self.llm_config:
                env['OPENAI_MODEL'] = self.llm_config['model']

        print(f"  运行编译: {' '.join(cmd)}")
        print(f"  工作目录: {self.wiki_path}")
        if 'OPENAI_BASE_URL' in env:
            print(f"  LLM Base URL: {env['OPENAI_BASE_URL']}")

        result = subprocess.run(
            cmd,
            cwd=str(self.wiki_path),
            capture_output=True,
            text=True,
            timeout=self.config.compile_timeout,
            shell=True,  # Windows 需要 shell=True
            env=env
        )

        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed: {result.stderr}")

        print(f"  编译成功")

    def _scan_temp_files(self) -> List[Path]:
        """扫描 temp 目录中的文件"""
        if not self.temp_dir.exists():
            return []

        # 递归查找所有 .md 文件
        return sorted(self.temp_dir.glob("**/*.md"))

    def _init_state(self, files: List[Path], total_batches: int) -> Dict:
        """初始化批次状态"""
        state = {
            "total_batches": total_batches,
            "current_batch": 0,
            "completed_files": [],
            "pending_files": [f.name for f in files],
            "failed_files": [],
            "started_at": datetime.now().isoformat(),
            "status": "in_progress"
        }
        self._save_state(state)
        return state

    def _update_state(self, state: Dict, batch_status: BatchStatus) -> None:
        """更新状态"""
        state['current_batch'] = batch_status.batch_number

        if batch_status.status == 'completed':
            state['completed_files'].extend(batch_status.files)
            for f in batch_status.files:
                if f in state['pending_files']:
                    state['pending_files'].remove(f)
        elif batch_status.status == 'failed':
            state['failed_files'].extend(batch_status.files)

        if batch_status.batch_number == state['total_batches']:
            state['status'] = 'completed' if not state['failed_files'] else 'partial'
            state['completed_at'] = datetime.now().isoformat()

        self._save_state(state)

    def _save_state(self, state: Dict) -> None:
        """保存状态到文件"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _load_state(self) -> Dict:
        """加载状态"""
        with open(self.state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _cleanup_temp(self) -> None:
        """清理 temp 目录"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"[WikiBatchCompiler] 清理 temp 目录")

    def _generate_summary(self, results: List[BatchStatus]) -> Dict[str, Any]:
        """生成编译摘要"""
        completed = sum(1 for r in results if r.status == 'completed')
        failed = sum(1 for r in results if r.status == 'failed')

        return {
            "status": "success" if failed == 0 else "partial",
            "total_batches": len(results),
            "completed_batches": completed,
            "failed_batches": failed,
            "batches": [
                {
                    "batch": r.batch_number,
                    "status": r.status,
                    "files": r.files,
                    "error": r.error
                }
                for r in results
            ]
        }
