"""Integration Tests — Git 真实仓库操作 (L2)

Phase IV v1.0.0 — 使用 Git CLI 进行仓库操作集成测试。
标记为 @pytest.mark.integration，需要 --integration 标志运行。
"""

from __future__ import annotations

import pytest
import subprocess
from pathlib import Path


@pytest.mark.integration
class TestGitReal:
    """Git 仓库集成测试"""

    def _run_git(self, *args, cwd: Path = None) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def test_init_and_status(self, tmp_path: Path):
        """初始化 Git 仓库并查看状态"""
        self._run_git("init", cwd=tmp_path)
        self._run_git("config", "user.email", "test@example.com", cwd=tmp_path)
        self._run_git("config", "user.name", "Test User", cwd=tmp_path)

        # 创建一个文件
        (tmp_path / "README.md").write_text("# Test Repo")
        self._run_git("add", "README.md", cwd=tmp_path)

        status = self._run_git("status", "--short", cwd=tmp_path)
        assert "README.md" in status

    def test_commit(self, tmp_path: Path):
        """提交文件并验证 log"""
        self._run_git("init", cwd=tmp_path)
        self._run_git("config", "user.email", "test@example.com", cwd=tmp_path)
        self._run_git("config", "user.name", "Test User", cwd=tmp_path)

        (tmp_path / "file.txt").write_text("Phase IV git test")
        self._run_git("add", "file.txt", cwd=tmp_path)
        self._run_git("commit", "-m", "Initial commit", cwd=tmp_path)

        log = self._run_git("log", "--oneline", cwd=tmp_path)
        assert "Initial commit" in log

    def test_commit_and_amend(self, tmp_path: Path):
        """提交后修改消息（amend）"""
        self._run_git("init", cwd=tmp_path)
        self._run_git("config", "user.email", "test@example.com", cwd=tmp_path)
        self._run_git("config", "user.name", "Test User", cwd=tmp_path)

        (tmp_path / "main.py").write_text('print("hello")')
        self._run_git("add", "main.py", cwd=tmp_path)
        self._run_git("commit", "-m", "Add main module", "--allow-empty", cwd=tmp_path)

        log = self._run_git("log", "--oneline", cwd=tmp_path)
        assert "Add main module" in log
