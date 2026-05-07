#!/usr/bin/env python3
"""性能回归检测脚本 — Phase IV v1.0.0

读取 pytest --perf 基准测试结果，与历史阈值对比，
输出通过/告警/失败状态。

用法:
    python scripts/check_benchmark_regression.py              # 运行基准 + 检测
    python scripts/check_benchmark_regression.py --load-json  # 从已有 JSON 加载
    python scripts/check_benchmark_regression.py --thresholds my_thresholds.json
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── 阈值定义 ──
# 每种指标定义: name, unit, warn_threshold, fail_threshold, direction
# direction: "lower" 表示值越低越好, "higher" 表示越高越好

@dataclass
class Threshold:
    name: str
    unit: str
    warn: float          # 告警阈值
    fail: float          # 失败阈值
    direction: str = "lower"  # lower / higher

    def evaluate(self, value: float) -> str:
        """评估测量值: pass / warn / fail"""
        if self.direction == "lower":
            if value < self.warn:
                return "pass"
            elif value < self.fail:
                return "warn"
            else:
                return "fail"
        else:  # higher
            if value > self.warn:
                return "pass"
            elif value > self.fail:
                return "warn"
            else:
                return "fail"


# 默认阈值配置 (Phase IV v1.0.0)
DEFAULT_THRESHOLDS: dict[str, Threshold] = {
    "l1_match_latency_ms": Threshold(
        name="L1 意图匹配延时",
        unit="ms",
        warn=80.0,
        fail=100.0,
        direction="lower",
    ),
    "l1_no_match_latency_ms": Threshold(
        name="L1 无匹配遍历延时",
        unit="ms",
        warn=150.0,
        fail=200.0,
        direction="lower",
    ),
    "adapter_cold_start_ms": Threshold(
        name="适配器冷启动延时",
        unit="ms",
        warn=1500.0,
        fail=2000.0,
        direction="lower",
    ),
    "batch_registration_patterns": Threshold(
        name="批量注册模式数",
        unit="patterns",
        warn=50,
        fail=10,
        direction="higher",
    ),
    "total_tests_passed": Threshold(
        name="全量测试通过数",
        unit="tests",
        warn=900,
        fail=500,
        direction="higher",
    ),
}


@dataclass
class BenchmarkResult:
    metric: str
    value: float
    unit: str
    status: str  # pass / warn / fail
    threshold: Optional[Threshold] = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "threshold_warn": self.threshold.warn if self.threshold else None,
            "threshold_fail": self.threshold.fail if self.threshold else None,
            "message": self.message,
        }


def load_thresholds(path: Optional[str] = None) -> dict[str, Threshold]:
    """加载阈值配置"""
    if path:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        thresholds = {}
        for key, cfg in data.items():
            thresholds[key] = Threshold(**cfg)
        return thresholds
    return dict(DEFAULT_THRESHOLDS)


def run_perf_tests(project_root: Path) -> dict[str, float]:
    """运行性能测试并解析结果"""
    test_file = project_root / "tests" / "e2e" / "test_performance.py"

    if not test_file.exists():
        print(f"⚠️  性能测试文件不存在: {test_file}")
        return {}

    start = time.perf_counter()
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(test_file),
            "--perf", "-v", "--tb=short", "-q",
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
        timeout=300,
    )
    elapsed = time.perf_counter() - start

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # 解析测试结果
    metrics: dict[str, float] = {
        "perf_test_duration_sec": elapsed,
    }

    if "passed" in result.stdout:
        import re
        passed_match = re.search(r"(\d+)\s+passed", result.stdout)
        if passed_match:
            metrics["total_tests_passed"] = int(passed_match.group(1))

    return metrics


def run_manual_benchmarks() -> dict[str, float]:
    """运行手动微基准测试（不依赖 pytest）"""
    import time as _time
    from aibridge.core.domain_registry import DomainIntentRegistry
    from aibridge.core.intent_pattern import IntentPattern

    metrics: dict[str, float] = {}

    # 构建 60 模式注册中心
    reg = DomainIntentRegistry()
    domains = ["media", "office", "browser", "git", "docker", "ffmpeg"]
    for domain in domains:
        patterns = []
        for i in range(10):
            patterns.append(IntentPattern(
                id=f"{domain}.action{i}",
                domain=domain,
                patterns=[f"执行{domain}操作{i}", f"{domain}任务{i}"],
                description=f"{domain} action {i}",
            ))
        reg.register(f"adapter-{domain}", patterns)

    # L1 匹配延时
    for _ in range(10):
        reg.match("执行media操作5")
    start = _time.perf_counter()
    for _ in range(100):
        reg.match("执行media操作5")
    elapsed = _time.perf_counter() - start
    metrics["l1_match_latency_ms"] = (elapsed / 100) * 1000

    # L1 无匹配遍历延时
    start = _time.perf_counter()
    for _ in range(100):
        reg.match("完全无关的输入xyz")
    elapsed = _time.perf_counter() - start
    metrics["l1_no_match_latency_ms"] = (elapsed / 100) * 1000

    # 冷启动延时
    try:
        from aibridge.adapters.office.factory import create_word_adapter
        start = _time.perf_counter()
        adapter = create_word_adapter(backend="openxml")
        elapsed = (_time.perf_counter() - start) * 1000
        metrics["adapter_cold_start_ms"] = elapsed
    except Exception as e:
        print(f"⚠️  冷启动测试跳过: {e}")

    # 批量注册
    metrics["batch_registration_patterns"] = float(reg.total_patterns)

    return metrics


def evaluate_metrics(
    metrics: dict[str, float],
    thresholds: dict[str, Threshold],
) -> list[BenchmarkResult]:
    """评估所有指标"""
    results = []
    for key, threshold in thresholds.items():
        if key in metrics:
            value = metrics[key]
            status = threshold.evaluate(value)

            if status == "pass":
                message = f"✅ {threshold.name}: {value:.1f}{threshold.unit} ({status})"
            elif status == "warn":
                message = f"⚠️  {threshold.name}: {value:.1f}{threshold.unit} 超过告警阈值 {threshold.warn}{threshold.unit} ({status})"
            else:
                message = f"❌ {threshold.name}: {value:.1f}{threshold.unit} 超过失败阈值 {threshold.fail}{threshold.unit} ({status})"

            results.append(BenchmarkResult(
                metric=key,
                value=value,
                unit=threshold.unit,
                status=status,
                threshold=threshold,
                message=message,
            ))
        else:
            results.append(BenchmarkResult(
                metric=key,
                value=0,
                unit=threshold.unit,
                status="unknown",
                threshold=threshold,
                message=f"❓ {threshold.name}: 未获取到数据",
            ))

    return results


def print_report(results: list[BenchmarkResult]) -> int:
    """打印报告，返回退出码"""
    print("\n" + "=" * 60)
    print("  铁幕 · 性能回归检测报告")
    print("=" * 60)

    has_failure = False
    has_warning = False

    for r in results:
        print(f"  {r.message}")
        if r.status == "fail":
            has_failure = True
        elif r.status == "warn":
            has_warning = True

    print("-" * 60)
    status_counts = {
        "pass": sum(1 for r in results if r.status == "pass"),
        "warn": sum(1 for r in results if r.status == "warn"),
        "fail": sum(1 for r in results if r.status == "fail"),
        "unknown": sum(1 for r in results if r.status == "unknown"),
    }
    print(f"  通过: {status_counts['pass']} | 告警: {status_counts['warn']} | 失败: {status_counts['fail']} | 未知: {status_counts['unknown']}")

    if has_failure:
        print("\n❌ 性能回归检测失败 — 存在超过失败阈值的指标")
        return 1
    elif has_warning:
        print("\n⚠️  性能回归检测通过（有告警） — 部分指标超过告警阈值")
        return 0
    else:
        print("\n✅ 性能回归检测通过")
        return 0


def save_results(results: list[BenchmarkResult], output_path: Path):
    """保存结果到 JSON"""
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": [r.to_dict() for r in results],
        "summary": {
            "pass": sum(1 for r in results if r.status == "pass"),
            "warn": sum(1 for r in results if r.status == "warn"),
            "fail": sum(1 for r in results if r.status == "fail"),
            "unknown": sum(1 for r in results if r.status == "unknown"),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 结果已保存到: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="铁幕 · 性能回归检测 (Phase IV v1.0.0)"
    )
    parser.add_argument(
        "--load-json",
        type=str,
        help="从已有 JSON 结果文件加载（跳过运行基准测试）",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        help="自定义阈值 JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmark-results.json",
        help="结果输出路径 (默认: benchmark-results.json)",
    )
    parser.add_argument(
        "--skip-perf-tests",
        action="store_true",
        help="跳过 pytest --perf 测试，仅运行手动微基准",
    )

    args = parser.parse_args()

    # 项目根目录
    project_root = Path(__file__).resolve().parent.parent

    # 加载阈值
    thresholds = load_thresholds(args.thresholds)

    # 获取指标
    metrics: dict[str, float] = {}

    if args.load_json:
        with open(args.load_json, encoding="utf-8") as f:
            data = json.load(f)
            for r in data.get("results", []):
                metrics[r["metric"]] = r["value"]
        print(f"📂 从 {args.load_json} 加载了 {len(metrics)} 个指标")
    else:
        # 运行手动微基准测试
        print("🔬 运行微基准测试...")
        metrics.update(run_manual_benchmarks())

        # 运行 pytest 性能测试
        if not args.skip_perf_tests:
            print("\n🧪 运行 pytest --perf 测试...")
            pytest_metrics = run_perf_tests(project_root)
            metrics.update(pytest_metrics)

    if not metrics:
        print("❌ 没有获取到任何性能数据")
        return 2

    # 评估
    results = evaluate_metrics(metrics, thresholds)

    # 打印报告
    exit_code = print_report(results)

    # 保存结果
    output_path = project_root / args.output
    save_results(results, output_path)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
