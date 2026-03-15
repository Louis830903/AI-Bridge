"""AI-Bridge 配置向导

交互式引导用户生成配置文件。
"""

import sys
from typing import Dict, Any

# 尝试导入 yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def run_init_wizard(output: str = "config.yaml") -> int:
    """运行配置向导"""
    print()
    print("🚀 AI-Bridge 配置向导")
    print("=" * 50)
    print()
    
    config: Dict[str, Any] = {
        "server": {
            "log_level": "INFO",
        },
        "adapters": {}
    }
    
    # 场景选择
    print("📋 请选择您的使用场景:")
    print("  1. 浏览器自动化 (网页操作、爬虫、测试)")
    print("  2. 办公自动化 (Word/Excel/PPT)")
    print("  3. 多 Agent 协作 (A2A 协议)")
    print("  4. 全部功能")
    print()
    
    try:
        choice = input("请选择 [1-4，默认 4]: ").strip() or "4"
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return 1
    
    # 验证输入
    if choice not in ["1", "2", "3", "4"]:
        print(f"  ⚠️  无效选择 '{choice}'，使用默认值 4")
        choice = "4"
    
    if choice in ["1", "4"]:
        config["adapters"]["chrome"] = {
            "enabled": True,
            "headless": False,
        }
        print("  ✅ 已启用浏览器自动化")
    
    if choice in ["2", "4"]:
        config["adapters"]["office"] = {
            "enabled": True,
            "visible": True,
        }
        print("  ✅ 已启用办公自动化")
    
    if choice in ["3", "4"]:
        config["enterprise"] = {
            "a2a_enabled": True,
            "agent_registry": True,
        }
        print("  ✅ 已启用 Agent 协作")
    
    print()
    
    # 企业特性
    print("🔐 是否启用企业级特性？")
    print("  (认证、审计日志、Prometheus 指标)")
    print()
    
    try:
        enterprise = input("启用企业特性? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return 1
    
    if enterprise != "n":
        config.setdefault("enterprise", {})
        config["enterprise"]["auth_enabled"] = True
        config["enterprise"]["audit_enabled"] = True
        config["enterprise"]["metrics_enabled"] = True
        config["enterprise"]["metrics_port"] = 9090
        print("  ✅ 已启用企业级特性")
        print("     - 认证中间件")
        print("     - 审计日志 (SQLite)")
        print("     - Prometheus 指标 (:9090/metrics)")
    else:
        print("  ⏭️  跳过企业特性")
    
    print()
    
    # 生成配置文件
    if HAS_YAML:
        yaml_content = yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    else:
        # 手动生成 YAML
        yaml_content = _generate_yaml(config)
    
    # 写入文件
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write(f"# AI-Bridge v5.0 配置文件\n")
            f.write(f"# 由配置向导生成\n\n")
            f.write(yaml_content)
        print(f"✅ 配置已保存到: {output}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return 1
    
    print()
    print("=" * 50)
    print("📖 下一步:")
    print()
    print("  1. 启动服务:")
    print(f"     python -m aibridge --config {output}")
    print()
    print("  2. 添加到 Claude Desktop:")
    print("     参考: examples/claude_desktop_config.json")
    print()
    print("  3. 查看文档:")
    print("     https://github.com/Louis830903/AI-Bridge")
    print()
    
    return 0


def _generate_yaml(config: Dict[str, Any], indent: int = 0) -> str:
    """手动生成 YAML 格式"""
    lines = []
    prefix = "  " * indent
    
    for key, value in config.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_generate_yaml(value, indent + 1))
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            lines.append(f"{prefix}{key}: {value}")
        else:
            lines.append(f"{prefix}{key}: \"{value}\"")
    
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(run_init_wizard())
