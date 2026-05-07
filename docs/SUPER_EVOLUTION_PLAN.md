# 🚀 AI-Bridge 超级进化计划：《从混沌到星辰》— 开发规格说明书

> **文档类型**: Technical Specification (技术规格说明书)
> **版本**: v2.0
> **最后更新**: 2026-05-07
> **状态**: Draft → 待评审
> **关联文档**: [README_CN.md](../README_CN.md) | [CHANGELOG.md](../ai-bridge/CHANGELOG.md) | [pyproject.toml](../ai-bridge/pyproject.toml)

---

## 目录

1. [计划总览](#1-计划总览)
2. [Phase Ⅰ 涅槃·秩序重生](#2-phase-ⅰ-涅槃秩序重生)
3. [Phase Ⅱ 觉醒·万物有灵](#3-phase-ⅱ-觉醒万物有灵)
4. [Phase Ⅲ 破界·全平台征服](#4-phase-ⅲ-破界全平台征服)
5. [Phase Ⅳ 铸盾·生产就绪](#5-phase-ⅳ-铸盾生产就绪)
6. [Phase Ⅴ 锻剑·适配器淬炼](#6-phase-ⅴ-锻剑适配器淬炼)
7. [Phase Ⅵ 星火·生态燎原](#6-phase-ⅵ-星火生态燎原)
8. [风险矩阵与依赖图](#7-风险矩阵与依赖图)
9. [附录](#8-附录)

---

## 1. 计划总览

### 1.1 版本路线图

| 阶段 | 代号 | 版本输出 | 周期 | 核心交付物 | 前置依赖 |
|------|------|----------|------|-----------|----------|
| Ⅰ | **涅槃·秩序重生** | v0.9.0-rc1 | 2周 (W1-W2) | 版本校准、统一异常体系、代码规范 | 无 |
| Ⅱ | **觉醒·万物有灵** | v0.10.0 | 4周 (W3-W6) | 通用意图引擎、6大领域网络、三级流水线 | Phase Ⅰ |
| Ⅲ | **破界·全平台征服** | v0.11.0 | 4周 (W7-W10) | 跨平台 Office、CLI 工具发现、多平台 CI | Phase Ⅱ |
| Ⅳ | **铸盾·生产就绪** | v1.0.0 🎉 | 3周 (W11-W13) | 集成测试铁幕、性能基准、正式发布 | Phase Ⅲ |
| Ⅴ | **锻剑·适配器淬炼** | v1.1.0 | 3周 (W14-W16) | 6 大适配器深度重构为 L3 AI 原生 | Phase Ⅳ |
| Ⅵ | **星火·生态燎原** | v1.2.0+ | 6周+ (W17+) | 插件系统、市场、社区引擎 | Phase Ⅴ |

### 1.2 项目规模基线

| 指标 | 当前值 (v0.9.0 基线) | Phase Ⅳ 目标 | Phase Ⅵ 目标 |
|------|:--:|:--:|:--:|
| Python 源文件 | 94 | ~120 | ~150+ |
| 代码行数 | ~33,600 | ~45,000 | ~55,000+ |
| 单元测试数 | 647 | 700+ | 800+ |
| 集成测试数 | 0 | 30+ | 50+ |
| 适配器数量 | 20+ | 22 | 30+ (含社区) |
| 跨平台支持 | Windows only | Win/Mac/Linux | Win/Mac/Linux |
| 测试覆盖率 | ~85% | >90% | >90% |

### 1.3 命名约定

本文档中所有任务编号遵循 `P{Phase}-{序号}` 格式（例：P1-3 表示 Phase Ⅰ 第 3 号任务）。每个任务包含：
- **文件清单**：新增/修改/删除的文件
- **API 规格**：公开接口签名与行为契约
- **数据模型**：涉及的核心数据结构
- **测试规格**：最少测试场景与断言
- **验收标准**：可量化的完成条件
- **风险等级**：🟢低 / 🟡中 / 🔴高

---

## 2. Phase Ⅰ 涅槃·秩序重生

> **目标版本**: v0.9.0-rc1 | **周期**: 2周 (W1-W2) | **风险等级**: 🟢低
> **核心命题**: 版本号与代码能力对标，双轨错误体系统一到结构化异常，技术债清偿。

### 2.1 P1-1: 版本校准工程

**优先级**: P0 | **预估工时**: 3d | **负责人**: TBD

#### 2.1.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|:--:|------|
| `ai-bridge/pyproject.toml` | ✏️ 修改 | 版本号、分类器、可选依赖 |
| `ai-bridge/src/aibridge/version.py` | ✏️ 修改 | `__version__` 同步 |
| `README.md` | ✏️ 修改 | 补充架构图、路线图、版本号 |
| `README_CN.md` | ✏️ 修改 | 同步英文版变更 |
| `ai-bridge/CHANGELOG.md` | ✏️ 重写 | 回溯 v1.0→v5.0 变更 |
| `ai-bridge/CONTRIBUTING.md` | ✏️ 修改 | 开发者指南更新 |

#### 2.1.2 pyproject.toml 变更规格

```toml
[project]
name = "ai-bridge"
# 变更前
version = "0.1.0-alpha"
# 变更后
version = "0.9.0-rc1"
description = "Universal AI-to-Tool bridge: MCP+A2A dual protocol gateway for CLI, Office, and Browser adapters"

# 变更前
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Operating System :: Microsoft :: Windows",
]
# 变更后
classifiers = [
    "Development Status :: 4 - Beta",
    "Operating System :: OS Independent",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: MacOS",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Intended Audience :: Developers",
]

[project.optional-dependencies]
# 🆕 新增可选依赖分组
office-win = ["pywin32>=305"]
office-cross = ["python-docx>=1.0", "openpyxl>=3.1"]
browser = ["playwright>=1.40"]
media = ["ffmpeg-python>=0.2"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.3", "mypy>=1.8"]
all = ["ai-bridge[office-cross,browser,media,dev]"]
```

#### 2.1.3 CHANGELOG.md 回溯规格

按以下格式从 Git 历史逆向生成：

```markdown
## [v0.9.0-rc1] - 2026-05-??

### 史诗回溯
本版本合并了 v1.0 → v5.0 的历史演进，以下是里程碑摘要：

#### v5.0 企业级能力 (2026 Q1)
- **新增**: PBAC 策略引擎 (policy.py, ~400行)
- **新增**: Metering 计量系统 (metering.py, metering_prometheus.py)
- **新增**: Audit 审计日志 (audit.py, audit_log.py)
- **新增**: Rate Limiting (rate_limit.py)
- **新增**: OpenTelemetry 全链路追踪 (tracing.py)
- **新增**: Health Check 端点 (health.py)

#### v4.0 协议扩展 (2025 Q4)
- **新增**: A2A Gateway (a2a_gateway.py, protocol_bridge.py)
- **新增**: Agent Card 发布与发现 (agent_card.py, card_publisher.py, card_discovery.py)
- **新增**: MCP Registry (mcp_registry.py, mcp_discovery.py)
- **新增**: Prometheus 指标导出 (prometheus.py)
- **新增**: A2A Streaming (a2a_streaming.py)

#### v3.0 核心重构 (2025 Q3)
- **新增**: IntentEngine 意图引擎 (intent_engine.py)
- **新增**: Batch Executor (batch_executor.py)
- **新增**: Smart Wait (smart_wait.py)
- **新增**: Multi-modal 支持 (multimodal.py)

#### v2.0 适配器扩展 (2025 Q2)
- **新增**: CLI 适配器体系 (aider, blender, docker, ffmpeg, gimp, imagemagick, libreoffice, pandoc, playwright, prettier, shotcut)
- **新增**: Browser 适配器 (chrome.py, edge.py)
- **新增**: Office 适配器 (word, excel, ppt)

#### v1.0 基础框架 (2025 Q1)
- **新增**: MCP Server (mcp_server.py, mcp_tools.py)
- **新增**: 核心配置系统 (config.py, adapter_config.py)
- **新增**: Session Manager (session_manager.py)
- **新增**: 安全模块 (security.py)
```

#### 2.1.4 Git Tag 打标

```bash
# 在现有历史提交上打里程碑 tag
git tag -a v0.1.0-base <最早提交> -m "v1.0 基础框架"
git tag -a v0.2.0-adapters <适配器首次提交> -m "v2.0 适配器扩展"
git tag -a v0.3.0-core <核心重构提交> -m "v3.0 核心重构"
git tag -a v0.4.0-protocol <协议扩展提交> -m "v4.0 协议扩展"
git tag -a v0.5.0-enterprise <企业级提交> -m "v5.0 企业级能力"
git tag -a v0.9.0-rc1 HEAD -m "涅槃: 秩序重生"
```

#### 2.1.5 验收标准

- [ ] `pyproject.toml` 版本为 `0.9.0-rc1`，分类器覆盖三大平台
- [ ] `pip install -e .` 成功且 `ai-bridge --version` 输出 `0.9.0-rc1`
- [ ] CHANGELOG.md 包含 v1.0→v5.0 完整回溯
- [ ] 5 个里程碑 Git Tag 已推送
- [ ] README.md 包含分层架构图 (Mermaid) 和路线图

---

### 2.2 P1-2: 错误处理大统一

**优先级**: P1 | **预估工时**: 5d | **负责人**: TBD | **风险**: 🔴高 (涉及全项目文件)

#### 2.2.1 统一异常层次结构

```python
# src/aibridge/core/exceptions.py (扩展)

class AIBridgeError(Exception):
    """所有 AI-Bridge 异常的根类"""
    def __init__(self, message: str, code: str, details: dict = None,
                 cause: Exception = None):
        self.code = code          # 机器可读错误码: "ADAPTER_TIMEOUT"
        self.details = details or {}
        self.cause = cause        # 异常链
        super().__init__(message)

# --- 适配器异常 (2xx) ---
class AdapterError(AIBridgeError):
    """适配器层异常 (2xx)"""
    def __init__(self, message, code, adapter_id=None, **kwargs):
        super().__init__(message, code,
                        details={"adapter_id": adapter_id, **kwargs})

class AdapterConnectionError(AdapterError):
    code = "ADAPTER_CONNECTION_ERROR"      # 201

class AdapterTimeoutError(AdapterError):
    code = "ADAPTER_TIMEOUT"               # 202

class AdapterExecutionError(AdapterError):
    code = "ADAPTER_EXECUTION_ERROR"       # 203

class AdapterNotFoundError(AdapterError):
    code = "ADAPTER_NOT_FOUND"             # 204

class AdapterConfigError(AdapterError):
    code = "ADAPTER_CONFIG_ERROR"          # 205

# --- 协议异常 (3xx) ---
class ProtocolError(AIBridgeError):
    """协议层异常 (3xx)"""
    pass

class MCPProtocolError(ProtocolError):
    code = "MCP_PROTOCOL_ERROR"            # 301

class A2AProtocolError(ProtocolError):
    code = "A2A_PROTOCOL_ERROR"            # 302

class ProtocolBridgeError(ProtocolError):
    code = "PROTOCOL_BRIDGE_ERROR"         # 303

# --- 意图引擎异常 (4xx) ---  🆕
class IntentError(AIBridgeError):
    """意图引擎异常 (4xx)"""
    pass

class IntentParseError(IntentError):
    code = "INTENT_PARSE_ERROR"            # 401

class IntentRouteError(IntentError):
    code = "INTENT_ROUTE_ERROR"            # 402

class IntentRegistrationError(IntentError):
    code = "INTENT_REGISTRATION_ERROR"     # 403

# --- 企业级异常 (5xx) ---
class EnterpriseError(AIBridgeError):
    """企业级异常 (5xx)"""
    pass

class PolicyDeniedError(EnterpriseError):
    code = "POLICY_DENIED"                 # 501

class RateLimitExceededError(EnterpriseError):
    code = "RATE_LIMIT_EXCEEDED"           # 502

class AuditWriteError(EnterpriseError):
    code = "AUDIT_WRITE_ERROR"             # 503

# --- 安全异常 (6xx) ---  🆕
class SecurityError(AIBridgeError):
    """安全异常 (6xx)"""
    pass

class SSRFBlockedError(SecurityError):
    code = "SSRF_BLOCKED"                  # 601

class InputValidationError(SecurityError):
    code = "INPUT_VALIDATION_ERROR"        # 602
```

#### 2.2.2 旧字典模式迁移策略

**Step 1: 创建兼容层** (`src/aibridge/core/legacy_error_wrapper.py`)

```python
"""旧字典错误模式兼容层 — v1.0 时移除"""
from __future__ import annotations
import warnings
from typing import Any, Callable
from functools import wraps
from aibridge.core.exceptions import (
    AIBridgeError, AdapterError, AdapterExecutionError
)

def migrate_dict_error(result: dict[str, Any]) -> AIBridgeError:
    """将旧字典错误转为结构化异常，同时发出 DeprecationWarning"""
    if not result.get("success", True):
        warnings.warn(
            "字典错误模式已弃用，请使用 raise AIBridgeError",
            DeprecationWarning, stacklevel=3
        )
        return AdapterExecutionError(
            message=result.get("error", "Unknown error"),
            details={"legacy_result": result}
        )
    return None

def bridge_legacy(func: Callable) -> Callable:
    """装饰器：自动将旧字典错误转为异常"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, dict):
            error = migrate_dict_error(result)
            if error:
                raise error
        return result
    return wrapper
```

**Step 2: 逐模块迁移清单**

| 优先级 | 模块路径 | 文件数 | 预估字典错误数 | 策略 |
|:--:|------|:--:|:--:|------|
| 1 | `src/aibridge/adapters/` | 20+ | ~60 | 适配器 execute() 直接 raise |
| 2 | `src/aibridge/core/orchestrator.py` | 1 | ~10 | 中间层转换 |
| 3 | `src/aibridge/gateway/` | 8 | ~15 | 协议层统一处理 |
| 4 | `src/aibridge/server/` | 5 | ~8 | 入口层捕获 |
| 5 | `src/aibridge/connectors/` | 3 | ~5 | 连接器迁移 |

**Step 3: 回归护栏**

```python
# tests/test_error_migration.py (新增)
class TestErrorMigration:
    """错误迁移回归测试"""

    def test_legacy_dict_still_works_with_warning(self):
        """确保旧字典模式在 v0.9.x 仍可用但发出警告"""
        with pytest.warns(DeprecationWarning):
            # 模拟旧适配器返回
            ...

    def test_new_exception_propagates_correctly(self):
        """确保新异常在调用链中正确传播"""
        with pytest.raises(AdapterExecutionError) as exc:
            raise AdapterExecutionError("test", adapter_id="chrome")
        assert exc.value.code == "ADAPTER_EXECUTION_ERROR"
        assert exc.value.details["adapter_id"] == "chrome"

    @pytest.mark.parametrize("old_return,expected_code", [
        ({"success": False, "error": "timeout"}, "ADAPTER_EXECUTION_ERROR"),
        ({"success": True, "data": "ok"}, None),  # 成功不抛异常
    ])
    def test_migrate_dict_error(self, old_return, expected_code):
        ...

    def test_bridge_legacy_decorator(self):
        """装饰器自动转换"""
        @bridge_legacy
        async def old_style():
            return {"success": False, "error": "boom"}
        
        with pytest.raises(AdapterExecutionError):
            await old_style()
```

#### 2.2.3 验收标准

- [ ] `src/aibridge/core/exceptions.py` 包含完整 6 类 17 个异常子类
- [ ] `legacy_error_wrapper.py` 已创建且 `bridge_legacy` 装饰器通过测试
- [ ] Adapter 层 100% 使用结构化异常（已完成迁移清单前 2 级）
- [ ] 647 现有测试全部通过（兼容层保证）
- [ ] 新增 15+ 异常专项测试
- [ ] `ruff check` 检测不到旧字典错误模式

---

### 2.3 P1-3: 代码债务清偿

**优先级**: P2 | **预估工时**: 3d | **负责人**: TBD | **风险**: 🟡中

#### 2.3.1 Import 规范化配置

**文件**: `ai-bridge/pyproject.toml` 追加

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E", "W",    # pycodestyle
    "F",         # pyflakes
    "I",         # isort
    "N",         # pep8-naming
    "B",         # flake8-bugbear
    "C4",        # flake8-comprehensions
    "SIM",       # flake8-simplify
    "TCH",       # flake8-type-checking-imports
]

[tool.ruff.lint.isort]
force-single-line = false
lines-between-types = 1
known-first-party = ["aibridge"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # 渐进式类型化
exclude = ["tests/", "demos/", "examples/"]
```

#### 2.3.2 TODO/FIXME 清理清单

使用 `rg -n "TODO|FIXME|HACK|XXX" --type py` 全项目扫描后按以下策略处理：

| 状态 | 数量 (预估) | 处理策略 |
|------|:--:|------|
| 🔴 必须修 | ~15 | 立即修复或转为 P0 Issue |
| 🟡 应该修 | ~30 | 转为 Issue，分配 Phase |
| 🟢 可保留 | ~10 | 加 `NOTE:` 前缀，写清楚原因 |

#### 2.3.3 Docstring 补充优先级

| 优先级 | 模块 | 文件 | 当前状态 | 目标 |
|:--:|------|------|------|------|
| P0 | IntentEngine | `core/intent_engine.py` | 部分有 | 完全覆盖 |
| P0 | ProtocolBridge | `gateway/protocol_bridge.py` | 无 | 完整 API 文档 |
| P0 | AdapterBase | `adapters/base.py` | 无 | 抽象方法文档 |
| P1 | A2AGateway | `gateway/a2a_gateway.py` | 少 | 完整覆盖 |
| P1 | MCPRegistry | `gateway/mcp_registry.py` | 少 | 完整覆盖 |
| P1 | PolicyEngine | `enterprise/policy.py` | 部分有 | 策略语法文档 |
| P2 | Orchestrator | `core/orchestrator.py` | 部分有 | 编排流程文档 |

Docstring 格式规范：

```python
def some_function(param1: str, param2: int = 42) -> Result:
    """简短的一句话摘要。

    详细的描述可以跨多行，解释函数的行为、边界条件、
    以及调用者需要注意的事项。

    Args:
        param1: 参数说明，包含类型信息。
        param2: 参数说明，注明默认值 42。

    Returns:
        返回值说明，包括可能的异常情况。

    Raises:
        ValueError: 当 param1 为空字符串时。
        AdapterTimeoutError: 当操作超时时。

    Example:
        >>> result = some_function("hello", 99)
        >>> result.status
        'ok'
    """
```

#### 2.3.4 CODEOWNERS 建立

```
# .github/CODEOWNERS
# 核心模块
src/aibridge/core/          @ai-bridge/core-team
src/aibridge/adapters/      @ai-bridge/adapter-team
src/aibridge/gateway/       @ai-bridge/gateway-team
src/aibridge/enterprise/    @ai-bridge/enterprise-team
# 文档
docs/                       @ai-bridge/docs-team
*.md                        @ai-bridge/docs-team
# CI/CD
.github/workflows/          @ai-bridge/devops-team
```

#### 2.3.5 审查发现：具体代码债务清单

> 来源：[IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md) 2026-05-07 全面审计。以下问题纳入本 Phase 的代码清偿任务一并修复。

| 审查编号 | 问题 | 文件 | 严重程度 | 修复要点 |
|:--:|------|------|:--:|------|
| **P1-3** | `config.py` `from_dict` 修改输入参数（`pop` → `get`） | `core/config.py:44` | 🔴 High | 避免副作用，使用 `get` + 字典推导 |
| **P1-4** | `chrome.py` 类定义中存在游离 docstring | `adapters/browser/chrome.py:104-122` | 🔴 High | 移动至类定义下方作为类 docstring |
| **P1-5** | `mcp_server.py` 重复属性定义 | `server/mcp_server.py:208-209` | 🔴 High | 删除重复的 `_shutdown_event` 声明 |
| **P2-1** | `manager.py` 异常吞噬且无日志 | `core/manager.py:111-135` | 🟡 Medium | `except` 块添加 `logger.warning()` |
| **P2-2** | `manager.py` 缺少重复注册检查 | `core/manager.py:21-28` | 🟡 Medium | `register()` 检测已存在 ID 并警告 |
| **P2-3** | `session_manager.py` 破坏封装（直接访问 `_page`） | `core/session_manager.py:100-101` | 🟡 Medium | 浏览器适配器添加 `page`/`has_page` property，SessionManager 用 duck-typing |
| **P2-4** | 缺少统一错误类型体系 | 全项目 | 🟡 Medium | 创建 `core/exceptions.py`（与 P1-2 错误统一任务协同） |
| **P3-3** | `security_auditor.py` 使用 `logger` 替代 `print` | `tools/security_auditor.py` | 🟢 Low | 全局替换 `print()` → `logger.info()` |
| **P3-4** | 补充类型注解（`get_any_adapter`） | `core/manager.py:65-67` | 🟢 Low | 添加 `Optional[Union[BaseAdapter, SyncBaseAdapter]]` |

**详细修复方案**: 参见 [IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md) 各对应章节。

#### 2.3.6 验收标准

- [ ] `ruff check` 零错误零警告
- [ ] `mypy src/aibridge/core/` 通过（核心模块）
- [ ] 所有 TODO/FIXME 已转为 Issue 或已修复
- [ ] P0/P1 模块 docstring 覆盖率 >80%
- [ ] `.github/CODEOWNERS` 已创建
- [ ] **🆕 审查问题**: 上表 9 项全部修复，回归测试通过

---

### 2.4 Phase Ⅰ 里程碑总结

| 任务 | 状态 | 新增文件 | 修改文件 | 删除 |
|------|:--:|------|------|:--:|
| P1-1 版本校准 | ⬜ | 0 | 6 | 0 |
| P1-2 错误统一 | ⬜ | 1 | ~45 | 0 |
| P1-3 代码清偿 | ⬜ | 1 | ~94 | 0 |
| 🆕 审查修复 (P1-3/4/5, P2-1/2/3/4, P3-3/4) | ⬜ | 0 | ~8 | 0 |
| **合计** | | **2** | **~153** | **0** |

> **说明**: 审查修复项为 P1-3（代码清偿）的子任务，共享同一批次。P2-4（统一错误类型体系）与 P1-2（错误处理大统一）协同推进。

---

## 3. Phase Ⅱ 觉醒·万物有灵

> **目标版本**: v0.10.0 | **周期**: 4周 (W3-W6) | **风险等级**: 🔴高
> **核心命题**: 意图引擎通用化，让 20+ 适配器获得自然语言理解能力。

### 3.1 架构总览

```
┌─────────────────────────────────────────────────────┐
│                 IntentEngine (v2.0)                   │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ L1 Exact    │→│ L2 Semant│→│ L3 LLM Fallback│  │
│  │ Pattern     │  │ ic Route │  │ + Auto-        │  │
│  │ Match       │  │          │  │ Registration   │  │
│  └─────────────┘  └──────────┘  └────────────────┘  │
│         ↑               ↑               ↑           │
│  ┌──────┴───────────────┴───────────────┴──────┐    │
│  │        DomainIntentRegistry (联合体)         │    │
│  │  🌐Browser │ 📄Office │ 🎬Media │ 🛠DevOps  │    │
│  │  💬Collab  │ 🌍WebTools │ 🆕Custom...       │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         ↑ register()           ↑ register()
┌────────┴───────┐     ┌────────┴──────────┐
│ ChromeAdapter  │     │ FFmpegAdapter     │
│ 🧠 patterns:6  │     │ 🧠 patterns:18    │
└────────────────┘     └───────────────────┘
```

### 3.2 P2-1: IntentPattern 协议与 DomainIntentRegistry

**优先级**: P0 | **预估工时**: 5d | **负责人**: TBD

#### 3.2.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|:--:|------|
| `src/aibridge/core/intent_pattern.py` | 🆕 新建 | IntentPattern 协议 + Slot 类型 |
| `src/aibridge/core/domain_registry.py` | 🆕 新建 | DomainIntentRegistry 实现 |
| `src/aibridge/core/intent_engine.py` | ✏️ 重构 | 集成新流水线 |
| `src/aibridge/adapters/base.py` | ✏️ 修改 | AdapterBase 增加 `register_intents()` |
| `tests/test_intent_pattern.py` | 🆕 新建 | 意图模式单元测试 |
| `tests/test_domain_registry.py` | 🆕 新建 | 注册中心测试 |

#### 3.2.2 API 规格

```python
# src/aibridge/core/intent_pattern.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, Type, runtime_checkable
from pathlib import Path


class SlotType(Enum):
    """槽位值类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    PATH = "path"          # 文件路径
    URL = "url"            # URL
    FORMAT = "format"      # 媒体/文档格式
    DURATION = "duration"  # 时间长度
    BOOLEAN = "boolean"


@dataclass
class Slot:
    """意图中的参数槽位"""
    name: str                     # 槽位名: "输入格式"
    type: SlotType                # 值类型
    required: bool = True         # 是否必填
    default: Any = None           # 默认值
    description: str = ""         # 语义说明
    enum_values: list[str] = field(default_factory=list)  # FORMAT 等枚举值


@dataclass
class IntentPattern:
    """单个意图模式——适配器向引擎注册的能力声明"""
    id: str                       # 唯一标识: "ffmpeg.convert"
    domain: str                   # 领域: "media"
    patterns: list[str]           # 自然语言模式模板
    description: str              # 人类可读描述
    confidence_threshold: float = 0.6
    slots: list[Slot] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    adapter_id: str = ""          # 回填：关联的适配器
    tags: list[str] = field(default_factory=list)

    # 模式模板示例:
    # "把{输入文件:path}转成{目标格式:format}"
    # "压缩{输入文件:path}到{目标大小:integer}MB以内"


@dataclass
class IntentMatch:
    """意图匹配结果"""
    pattern: IntentPattern        # 命中的意图模式
    confidence: float             # 置信度 0.0-1.0
    matched_text: str             # 匹配到的原始文本片段
    resolved_slots: dict[str, Any] # 解析后的槽位值: {"输入文件": Path("a.mp4"), ...}
    route: str                    # "exact" | "semantic" | "llm"
    alternatives: list[IntentMatch] = field(default_factory=list)  # 备选


@dataclass
class CompositeIntent:
    """复合意图——跨多适配器的组合任务"""
    sub_intents: list[IntentMatch] # 子意图列表
    dag: dict[str, list[str]]     # 执行 DAG: {"ffmpeg": ["office"], "office": []}
    original_text: str            # 原始用户输入
```

#### 3.2.3 DomainIntentRegistry API

```python
# src/aibridge/core/domain_registry.py

class DomainIntentRegistry:
    """领域意图注册中心——所有适配器意图模式的统一索引"""

    def __init__(self):
        self._patterns: dict[str, list[IntentPattern]] = {}  # domain → patterns
        self._by_adapter: dict[str, list[str]] = {}           # adapter_id → pattern_ids
        self._pattern_index: dict[str, IntentPattern] = {}    # id → pattern
        self._slot_parsers: dict[SlotType, Callable] = {}     # 槽位类型解析器

    def register(self, adapter_id: str, patterns: list[IntentPattern]) -> int:
        """注册一组意图模式，返回注册数量。
        
        Args:
            adapter_id: 适配器 ID (如 "ffmpeg")
            patterns: 该适配器的意图模式列表
        
        Returns:
            成功注册的模式数量
        
        Raises:
            IntentRegistrationError: 模式 ID 冲突时
        """
        ...

    def unregister_adapter(self, adapter_id: str) -> int:
        """注销某适配器的所有模式，返回移除数量"""
        ...

    def match(self, user_input: str, domain: str = None,
              min_confidence: float = 0.0) -> list[IntentMatch]:
        """L1 精确匹配——用注册的模式模板匹配用户输入。
        
        Args:
            user_input: 用户自然语言输入
            domain: 限定的领域 (None = 全领域)
            min_confidence: 最低置信度阈值
        
        Returns:
            匹配结果列表，按置信度降序排列
        """
        ...

    def semantic_search(self, user_input: str,
                        top_k: int = 5) -> list[IntentMatch]:
        """L2 语义搜索——跨领域模糊匹配。
        
        使用 embedding 计算 user_input 与所有 pattern.description 的相似度。
        """
        ...

    def merge(self, other: "DomainIntentRegistry") -> "DomainIntentRegistry":
        """合并另一个注册中心，返回新的联合注册中心。
        
        用于组合多个适配器的意图空间，形成"组合爆炸"效应。
        """
        ...

    def get_domain_stats(self) -> dict[str, int]:
        """获取各领域注册模式数量统计"""
        ...

    def export_patterns(self) -> list[dict]:
        """导出所有模式为可序列化格式（用于 Agent Card 发布）"""
        ...

    def to_prompt_context(self) -> str:
        """生成 LLM 可用的意图模式上下文（用于 L3 LLM Fallback）"""
        ...
```

#### 3.2.4 数据流图

```
Adapter.__init__()
    │
    ▼
self.register_intents(registry)   ←── 适配器向注册中心声明能力
    │
    │  registry.register("ffmpeg", [
    │      IntentPattern(id="ffmpeg.convert", domain="media",
    │          patterns=["把{输入:path}转成{目标:format}"],
    │          slots=[Slot("输入", SlotType.PATH), Slot("目标", SlotType.FORMAT)])
    │  ])
    ▼
IntentEngine.resolve("把视频转成gif")
    │
    ├── L1: DomainIntentRegistry.match() → 精确命中 "ffmpeg.convert"
    │      返回: IntentMatch(pattern=..., confidence=0.95, slots={...})
    │
    ├── L2: (L1 未命中时) DomainIntentRegistry.semantic_search()
    │      返回: [IntentMatch(confidence=0.72), IntentMatch(confidence=0.45)]
    │
    └── L3: (L1+L2 均未命中) LLM 解析 → 自动建议新 IntentPattern
           返回: IntentMatch(route="llm", ...)
           + 触发: registry.propose_pattern(new_pattern)  # 可选
```

#### 3.2.5 测试规格

```python
# tests/test_intent_pattern.py

class TestIntentPattern:
    def test_slot_parsing_string(self): ...
    def test_slot_parsing_path_with_spaces(self): ...
    def test_slot_parsing_format_enum(self): ...
    def test_missing_required_slot_returns_none(self): ...
    def test_pattern_matching_exact(self): ...
    def test_pattern_matching_fuzzy_whitespace(self): ...

class TestDomainIntentRegistry:
    def test_register_and_match_single_pattern(self): ...
    def test_match_returns_highest_confidence_first(self): ...
    def test_match_with_domain_filter(self): ...
    def test_match_below_threshold_returns_empty(self): ...
    def test_register_duplicate_id_raises(self): ...
    def test_unregister_removes_all_patterns(self): ...
    def test_merge_two_registries(self): ...
    def test_merge_preserves_original(self): ...
    def test_semantic_search_finds_related(self): ...
    def test_to_prompt_context_format(self): ...
    def test_export_patterns_serializable(self): ...
```

#### 3.2.6 验收标准

- [ ] `IntentPattern` 支持 7 种 SlotType，含枚举值约束
- [ ] `DomainIntentRegistry.match()` 精确匹配延迟 P99 < 10ms
- [ ] `DomainIntentRegistry.semantic_search()` 语义搜索 P99 < 200ms
- [ ] 单元测试覆盖率 >95%
- [ ] `AdapterBase.register_intents()` 抽象方法已定义
- [ ] 所有现有测试仍然通过

---

### 3.3 P2-2: 六大领域意图网络

**优先级**: P1 | **预估工时**: 8d | **负责人**: TBD

#### 3.3.1 各领域意图模式详细规格

##### 🌐 Browser 领域 (已有基础，扩展)

```python
BROWSER_PATTERNS = [
    IntentPattern(id="browser.navigate", domain="browser",
        patterns=["打开{网址:url}", "访问{网址:url}", "去{网址:url}"],
        slots=[Slot("网址", SlotType.URL)], confidence_threshold=0.8,
        examples=["打开百度", "访问 github.com"]),
    IntentPattern(id="browser.click", domain="browser",
        patterns=["点击{元素:string}", "按下{按钮:string}"],
        slots=[Slot("元素", SlotType.STRING)], confidence_threshold=0.6),
    IntentPattern(id="browser.fill", domain="browser",
        patterns=["在{字段:string}输入{内容:string}", "填写{字段:string}为{内容:string}"],
        slots=[Slot("字段", SlotType.STRING), Slot("内容", SlotType.STRING)]),
    IntentPattern(id="browser.screenshot", domain="browser",
        patterns=["截屏", "截图保存到{路径:path}", "给当前页面截图"],
        slots=[Slot("路径", SlotType.PATH, required=False)]),
    IntentPattern(id="browser.scroll", domain="browser",
        patterns=["向下滚动", "滚动到{位置:string}", "翻到{方向:string}"],
        slots=[Slot("位置", SlotType.STRING), Slot("方向", SlotType.STRING)]),
    IntentPattern(id="browser.extract", domain="browser",        # 🆕
        patterns=["提取{页面:string}中的{数据:string}", "从{页面:string}抓取{数据:string}"],
        slots=[Slot("页面", SlotType.URL), Slot("数据", SlotType.STRING)]),
]
```

##### 📄 Office 领域 (全新)

```python
OFFICE_PATTERNS = [
    # Word
    IntentPattern(id="office.create_doc", domain="office",
        patterns=["创建一个文档", "新建{类型:string}文档"],
        slots=[Slot("类型", SlotType.STRING, default="word")]),
    IntentPattern(id="office.open_doc", domain="office",
        patterns=["打开{文件:path}", "编辑{文件:path}"],
        slots=[Slot("文件", SlotType.PATH)]),
    IntentPattern(id="office.export_pdf", domain="office",
        patterns=["把{文件:path}导出为PDF", "{文件:path}转PDF"],
        slots=[Slot("文件", SlotType.PATH)]),
    # Excel
    IntentPattern(id="office.excel_sum", domain="office",
        patterns=["求{范围:string}的和", "计算{范围:string}总和"],
        slots=[Slot("范围", SlotType.STRING)]),
    IntentPattern(id="office.excel_chart", domain="office",
        patterns=["用{范围:string}生成{图表类型:string}图",
                 "根据{范围:string}画{图表类型:string}"],
        slots=[Slot("范围", SlotType.STRING), Slot("图表类型", SlotType.STRING,
              enum_values=["柱状", "折线", "饼", "散点"])]),
    IntentPattern(id="office.excel_pivot", domain="office",
        patterns=["以{行:string}为行{值:string}为值创建数据透视表"],
        slots=[Slot("行", SlotType.STRING), Slot("值", SlotType.STRING)]),
    # PPT
    IntentPattern(id="office.ppt_create", domain="office",
        patterns=["生成{主题:string}的PPT", "创建关于{主题:string}的演示文稿"],
        slots=[Slot("主题", SlotType.STRING)]),
    IntentPattern(id="office.ppt_add_slide", domain="office",
        patterns=["添加一张{布局:string}幻灯片"],
        slots=[Slot("布局", SlotType.STRING, enum_values=["标题", "内容", "空白", "两栏"])]),
    # 通用
    IntentPattern(id="office.extract_tables", domain="office",
        patterns=["提取{文件:path}中的表格", "从{文件:path}导出表格数据"],
        slots=[Slot("文件", SlotType.PATH)]),
    IntentPattern(id="office.format", domain="office",
        patterns=["格式化{文件:path}", "美化{文件:path}的排版"],
        slots=[Slot("文件", SlotType.PATH)]),
    IntentPattern(id="office.merge", domain="office",
        patterns=["合并{文件列表:string}到{目标:string}"],
        description="合并多个文档/表格到一个文件"),
    IntentPattern(id="office.mail_merge", domain="office",
        patterns=["用{数据源:path}填充{模板:path}", "邮件合并"],
        slots=[Slot("数据源", SlotType.PATH), Slot("模板", SlotType.PATH)]),
]
```

##### 🎬 Media 领域 (全新)

```python
MEDIA_PATTERNS = [
    IntentPattern(id="media.convert", domain="media",
        patterns=["把{输入:path}转成{格式:format}", "{输入:path}转换为{格式:format}"],
        slots=[Slot("输入", SlotType.PATH), Slot("格式", SlotType.FORMAT,
              enum_values=["mp4","avi","mkv","mov","gif","webm","mp3","wav"])]),
    IntentPattern(id="media.compress", domain="media",
        patterns=["压缩{文件:path}到{大小:integer}MB以内",
                 "把{文件:path}压到{大小:integer}M"],
        slots=[Slot("文件", SlotType.PATH), Slot("大小", SlotType.INTEGER)]),
    IntentPattern(id="media.trim", domain="media",
        patterns=["裁剪{文件:path}从{开始:duration}到{结束:duration}",
                 "截取{文件:path}的{开始:duration}到{结束:duration}"],
        slots=[Slot("文件", SlotType.PATH), Slot("开始", SlotType.DURATION),
               Slot("结束", SlotType.DURATION)]),
    IntentPattern(id="media.extract_audio", domain="media",
        patterns=["提取{视频:path}的音频", "从{视频:path}分离音轨"],
        slots=[Slot("视频", SlotType.PATH)]),
    IntentPattern(id="media.watermark", domain="media",
        patterns=["给{文件:path}加水印{水印:string}"],
        slots=[Slot("文件", SlotType.PATH), Slot("水印", SlotType.STRING)]),
    IntentPattern(id="media.concat", domain="media",
        patterns=["拼接{文件列表:string}", "合并{文件列表:string}为一个视频"],
        description="拼接多个视频文件"),
    IntentPattern(id="media.resize", domain="media",
        patterns=["调整{文件:path}分辨率为{宽:integer}x{高:integer}"],
        slots=[Slot("文件", SlotType.PATH), Slot("宽", SlotType.INTEGER),
               Slot("高", SlotType.INTEGER)]),
    IntentPattern(id="media.fps_change", domain="media",
        patterns=["把{文件:path}帧率改为{fps:integer}"],
        slots=[Slot("文件", SlotType.PATH), Slot("fps", SlotType.INTEGER)]),
    IntentPattern(id="media.extract_frame", domain="media",
        patterns=["从{文件:path}提取第{帧号:integer}帧",
                 "截取{文件:path}的{时间:duration}处画面"],
        slots=[Slot("文件", SlotType.PATH), Slot("帧号", SlotType.INTEGER, required=False),
               Slot("时间", SlotType.DURATION, required=False)]),
    IntentPattern(id="media.gif_from_video", domain="media",
        patterns=["把{视频:path}做成GIF", "{视频:path}转gif",
                 "制作{视频:path}的动态图"],
        slots=[Slot("视频", SlotType.PATH)]),
    IntentPattern(id="media.add_subtitle", domain="media",
        patterns=["给{视频:path}加字幕{字幕:string}"],
        slots=[Slot("视频", SlotType.PATH), Slot("字幕", SlotType.STRING)]),
    IntentPattern(id="media.record_screen", domain="media",
        patterns=["录屏{时长:duration}", "录制屏幕{时长:duration}"],
        slots=[Slot("时长", SlotType.DURATION)]),
    IntentPattern(id="media.screenshot_video", domain="media",
        patterns=["视频{文件:path}截图", "{文件:path}缩略图"],
        slots=[Slot("文件", SlotType.PATH)]),
    IntentPattern(id="media.change_speed", domain="media",
        patterns=["{文件:path}{速度:float}倍速", "把{文件:path}加速{速度:float}倍"],
        slots=[Slot("文件", SlotType.PATH), Slot("速度", SlotType.FLOAT)]),
    IntentPattern(id="media.rotate", domain="media",
        patterns=["旋转{文件:path}{角度:integer}度"],
        slots=[Slot("文件", SlotType.PATH), Slot("角度", SlotType.INTEGER,
              enum_values=["90","180","270"])]),
    IntentPattern(id="media.denoise", domain="media",
        patterns=["{文件:path}降噪", "给{文件:path}去噪"]),
    IntentPattern(id="media.stabilize", domain="media",
        patterns=["稳定{文件:path}", "{文件:path}防抖"]),
    IntentPattern(id="media.batch_convert", domain="media",
        patterns=["批量把{目录:path}转成{格式:format}",
                 "把{目录:path}下所有文件转为{格式:format}"],
        slots=[Slot("目录", SlotType.PATH), Slot("格式", SlotType.FORMAT)]),
]
```

##### 🛠 DevOps 领域 (全新)

```python
DEVOPS_PATTERNS = [
    # Docker
    IntentPattern(id="devops.docker_list", domain="devops",
        patterns=["列出容器", "查看所有容器", "显示{状态:string}的容器"],
        slots=[Slot("状态", SlotType.STRING, required=False,
              enum_values=["运行中","已停止","全部"])]),
    IntentPattern(id="devops.docker_start", domain="devops",
        patterns=["启动容器{名称:string}", "运行{名称:string}"],
        slots=[Slot("名称", SlotType.STRING)]),
    IntentPattern(id="devops.docker_stop", domain="devops",
        patterns=["停止{名称:string}", "关闭容器{名称:string}"]),
    IntentPattern(id="devops.docker_logs", domain="devops",
        patterns=["查看{名称:string}日志", "{名称:string}的日志"]),
    IntentPattern(id="devops.docker_compose", domain="devops",
        patterns=["启动{文件:path}的docker-compose",
                 "用{文件:path}编排容器"]),
    # Git
    IntentPattern(id="devops.git_status", domain="devops",
        patterns=["查看git状态", "git状态"]),
    IntentPattern(id="devops.git_commit", domain="devops",
        patterns=["提交代码", "git commit -m {信息:string}"],
        slots=[Slot("信息", SlotType.STRING)]),
    IntentPattern(id="devops.git_push", domain="devops",
        patterns=["推送代码", "git push"]),
    IntentPattern(id="devops.git_branch", domain="devops",
        patterns=["创建分支{名称:string}", "切换到{名称:string}分支"]),
]
```

##### 💬 Collab 领域 (全新)

```python
COLLAB_PATTERNS = [
    IntentPattern(id="collab.slack_send", domain="collab",
        patterns=["发Slack消息到{频道:string}", "在Slack{频道:string}发{消息:string}"],
        slots=[Slot("频道", SlotType.STRING), Slot("消息", SlotType.STRING)]),
    IntentPattern(id="collab.notion_sync", domain="collab",
        patterns=["同步到Notion", "把{内容:string}存到Notion{页面:string}"],
        slots=[Slot("内容", SlotType.STRING), Slot("页面", SlotType.STRING)]),
    IntentPattern(id="collab.github_issue", domain="collab",
        patterns=["在{仓库:string}创建Issue", "给{仓库:string}提Bug"],
        slots=[Slot("仓库", SlotType.STRING)]),
    IntentPattern(id="collab.email_send", domain="collab",
        patterns=["发邮件给{收件人:string}", "发送{主题:string}到{收件人:string}"],
        slots=[Slot("收件人", SlotType.STRING), Slot("主题", SlotType.STRING)]),
]
```

##### 🌍 WebTools 领域 (全新)

```python
WEBTOOLS_PATTERNS = [
    IntentPattern(id="webtools.scrape", domain="webtools",
        patterns=["抓取{网址:url}", "爬{网址:url}的内容"],
        slots=[Slot("网址", SlotType.URL)]),
    IntentPattern(id="webtools.extract_table", domain="webtools",
        patterns=["提取{网址:url}的表格", "从{网址:url}导出表格数据"]),
    IntentPattern(id="webtools.search", domain="webtools",
        patterns=["搜索{关键词:string}", "在{平台:string}搜{关键词:string}"],
        slots=[Slot("关键词", SlotType.STRING), Slot("平台", SlotType.STRING, required=False)]),
    IntentPattern(id="webtools.markdown", domain="webtools",
        patterns=["把{网址:url}转成Markdown", "{网址:url}转md"]),
]
```

#### 3.3.2 适配器注册模式

每个适配器在 `__init__` 中调用：

```python
# src/aibridge/adapters/cli/ffmpeg.py

class FFmpegAdapter(BaseCLIAdapter):
    def register_intents(self, registry: DomainIntentRegistry) -> None:
        registry.register(self.adapter_id, MEDIA_PATTERNS)
```

#### 3.3.3 验收标准

- [ ] 6 大领域共 54+ 意图模式已定义
- [ ] 每个 IntentPattern 有 ≥2 个 `examples`
- [ ] 每个 Slot 有明确的 `description`
- [ ] 所有现有适配器调用 `register_intents()` 无异常
- [ ] 领域统计 API 返回正确数量

---

### 3.4 P2-3: 三级意图解析流水线

**优先级**: P0 | **预估工时**: 5d | **负责人**: TBD

#### 3.4.1 重构 IntentEngine

```python
# src/aibridge/core/intent_engine.py (重构后)

from __future__ import annotations
import asyncio
import time
from typing import Optional

from aibridge.core.intent_pattern import IntentMatch, CompositeIntent, IntentPattern
from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.exceptions import IntentParseError, IntentRouteError
from aibridge.core.llm_provider import LLMProvider
from aibridge.core.logger import get_logger

logger = get_logger(__name__)


class IntentPipelineConfig:
    """流水线配置"""
    l1_timeout_ms: int = 50        # L1 精确匹配超时
    l2_timeout_ms: int = 500       # L2 语义搜索超时
    l3_timeout_ms: int = 5000      # L3 LLM 超时
    l2_top_k: int = 5              # 语义搜索返回数量
    l2_min_confidence: float = 0.5 # L2 最低置信度
    l3_auto_register: bool = False # 是否自动注册新模式
    l3_register_threshold: float = 0.8  # 自动注册置信阈值


class IntentEngine:
    """三级意图解析流水线 (v2.0)"""

    def __init__(
        self,
        registry: DomainIntentRegistry,
        llm_provider: Optional[LLMProvider] = None,
        config: Optional[IntentPipelineConfig] = None,
    ):
        self.registry = registry
        self.llm_provider = llm_provider
        self.config = config or IntentPipelineConfig()
        self._stats = {"l1_hits": 0, "l2_hits": 0, "l3_hits": 0, "misses": 0}

    async def resolve(
        self, user_input: str, domain: str = None
    ) -> IntentMatch | CompositeIntent | None:
        """三级流水线解析用户意图。
        
        Args:
            user_input: 自然语言输入
            domain: 限定的领域 (可选)
        
        Returns:
            IntentMatch (单意图), CompositeIntent (复合意图), 或 None
            
        Raises:
            IntentRouteError: 所有级别都失败时
        """
        # L1: 精确模式匹配
        result = await self._resolve_l1(user_input, domain)
        if result:
            self._stats["l1_hits"] += 1
            return result

        # L2: 语义路由
        result = await self._resolve_l2(user_input)
        if result:
            self._stats["l2_hits"] += 1
            return result

        # L3: LLM 回退
        if self.llm_provider:
            result = await self._resolve_l3(user_input)
            if result:
                self._stats["l3_hits"] += 1
                return result

        self._stats["misses"] += 1
        return None

    async def _resolve_l1(self, user_input: str, domain: str = None) -> Optional[IntentMatch]:
        """L1: 精确模式匹配——基于注册的模板"""
        try:
            matches = await asyncio.wait_for(
                asyncio.to_thread(self.registry.match, user_input, domain),
                timeout=self.config.l1_timeout_ms / 1000
            )
            if matches and matches[0].confidence >= matches[0].pattern.confidence_threshold:
                logger.debug(f"L1 hit: {matches[0].pattern.id} (conf={matches[0].confidence:.2f})")
                return matches[0]
        except asyncio.TimeoutError:
            logger.warning("L1 match timeout")
        return None

    async def _resolve_l2(self, user_input: str) -> Optional[IntentMatch | CompositeIntent]:
        """L2: 语义搜索 + 组合意图检测"""
        try:
            matches = await asyncio.wait_for(
                asyncio.to_thread(
                    self.registry.semantic_search, user_input, self.config.l2_top_k
                ),
                timeout=self.config.l2_timeout_ms / 1000
            )
            if not matches or matches[0].confidence < self.config.l2_min_confidence:
                return None

            # 检测是否为复合意图（多个高置信度匹配）
            high_conf = [m for m in matches if m.confidence > 0.6]
            if len(high_conf) >= 2:
                return CompositeIntent(
                    sub_intents=high_conf,
                    dag={m.pattern.id: [] for m in high_conf},  # 简单情况：并行
                    original_text=user_input,
                )

            logger.debug(f"L2 hit: {matches[0].pattern.id} (conf={matches[0].confidence:.2f})")
            return matches[0]
        except asyncio.TimeoutError:
            logger.warning("L2 semantic search timeout")
        return None

    async def _resolve_l3(self, user_input: str) -> Optional[IntentMatch]:
        """L3: LLM 理解 + 自动注册候选"""
        try:
            context = self.registry.to_prompt_context()
            result = await asyncio.wait_for(
                self.llm_provider.parse_intent(user_input, context),
                timeout=self.config.l3_timeout_ms / 1000
            )
            if result and result.confidence >= 0.5:
                logger.info(f"L3 LLM resolved: {result.pattern.id}")

                # 自动注册候选
                if (self.config.l3_auto_register and
                        result.confidence >= self.config.l3_register_threshold):
                    logger.info(f"Auto-registering new pattern: {result.pattern.id}")
                    self.registry.register(result.pattern.adapter_id, [result.pattern])

                return result
        except asyncio.TimeoutError:
            logger.error("L3 LLM timeout")
        except Exception as e:
            logger.error(f"L3 LLM error: {e}")
        return None

    def get_stats(self) -> dict:
        """获取流水线统计"""
        total = sum(self._stats.values())
        return {
            **self._stats,
            "total": total,
            "l1_rate": self._stats["l1_hits"] / max(total, 1),
            "l2_rate": self._stats["l2_hits"] / max(total, 1),
            "l3_rate": self._stats["l3_hits"] / max(total, 1),
            "miss_rate": self._stats["misses"] / max(total, 1),
        }
```

#### 3.4.2 验收标准

- [ ] L1 延迟 P99 < 50ms
- [ ] L2 延迟 P99 < 500ms
- [ ] L3 延迟 P99 < 5s（含 LLM 调用）
- [ ] 复合意图正确检测（≥2 高置信度匹配时）
- [ ] `get_stats()` 统计准确
- [ ] L1/L2/L3 超时不阻塞主流程
- [ ] 40+ 单元测试覆盖所有分支

---

### 3.5 P2-4: 意图自进化系统

**优先级**: P2 | **预估工时**: 3d | **负责人**: TBD

#### 3.5.1 自动注册提案机制

```python
# src/aibridge/core/intent_evolution.py (新增)

@dataclass
class IntentProposal:
    """L3 LLM 解析成功后生成的意图注册提案"""
    pattern: IntentPattern
    source_input: str           # 触发提案的原始输入
    confidence: float
    frequency: int = 1          # 累计出现次数
    proposed_at: float = field(default_factory=time.time)
    status: str = "pending"     # pending | approved | rejected


class IntentEvolutionEngine:
    """意图自进化引擎——从 L3 成功案例中学习"""

    def __init__(self, registry: DomainIntentRegistry,
                 storage_path: Optional[Path] = None):
        self.registry = registry
        self.storage_path = storage_path or Path("data/intent_evolution.json")
        self._proposals: dict[str, IntentProposal] = {}
        self._load()

    def observe(self, user_input: str, match: IntentMatch) -> None:
        """观察 L3 解析结果，生成或更新提案"""
        if match.route != "llm":
            return
        key = self._normalize(user_input)
        if key in self._proposals:
            self._proposals[key].frequency += 1
        else:
            self._proposals[key] = IntentProposal(
                pattern=match.pattern,
                source_input=user_input,
                confidence=match.confidence,
            )
        self._save()

    def get_pending_proposals(self, min_frequency: int = 3) -> list[IntentProposal]:
        """获取达到频率阈值的待审核提案"""
        return [p for p in self._proposals.values()
                if p.status == "pending" and p.frequency >= min_frequency]

    def approve(self, key: str) -> None:
        """审核通过，注册到 L1"""
        proposal = self._proposals[key]
        proposal.status = "approved"
        self.registry.register(proposal.pattern.adapter_id, [proposal.pattern])
        self._save()

    def reject(self, key: str) -> None:
        """审核拒绝"""
        self._proposals[key].status = "rejected"
        self._save()
```

#### 3.5.2 验收标准

- [ ] 相同意图出现 ≥3 次时自动提升为待审核提案
- [ ] 提案审核通过后自动注册到 L1
- [ ] 提案持久化到 JSON 文件，重启不丢失
- [ ] 审批 API `approve()` / `reject()` 正常工作

---

### 3.6 审查发现：意图引擎加固

> 来源：[IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md) 2026-05-07 审计。以下问题在 Phase Ⅱ 意图引擎重构时一并修复。

#### 3.6.1 P1-6: intent_engine 与 ChromeAdapter 紧耦合（审查）

**严重程度**: 🔴 High | **预计工时**: 3h | **文件**: `core/intent_engine.py`

**问题**:
1. 第22行直接导入 `ChromeAdapter`
2. 所有 handler 函数签名硬编码 `ChromeAdapter` 类型
3. `handle_search` 硬编码百度选择器

**修复方案**（与 P2-1/P2-3 协同）:

- **Step 1**: 使用 `TYPE_CHECKING` 延迟导入，消除运行时对 `ChromeAdapter` 的硬依赖
- **Step 2**: 所有 handler 签名改为 `BaseAdapter`（P2-1 已定义 `AdapterBase.register_intents()`）
- **Step 3**: `IntentEngine.__init__` 接受 `BaseAdapter` 而非 `ChromeAdapter`
- **Step 4**: `handle_search` 抽取 `SEARCH_ENGINES` 字典配置，消除硬编码百度选择器

**关联任务**: 本修复与 P2-1（IntentPattern 协议）、P2-3（三级流水线重构）共享同一批次，handler 两参数签名 `(match, adapter)` 在重构后保持不变。

#### 3.6.2 P2-9: intent_engine 缺少全局执行超时（审查）

**严重程度**: 🟡 Medium | **预计工时**: 0.5h | **文件**: `core/intent_engine.py`

**修复方案**（与 P2-3 流水线配置协同）:

在 `IntentEngine` 中添加可配置超时机制，与 P2-3 的 `IntentPipelineConfig` 统一：

```python
class IntentEngine:
    DEFAULT_EXECUTE_TIMEOUT = 120.0  # 意图解析+执行总超时
    DEFAULT_STEP_TIMEOUT = 30.0      # 单步操作超时
    
    async def execute(self, intent_text: str, context=None,
                      timeout: Optional[float] = None) -> Dict:
        effective_timeout = timeout or self._execute_timeout
        try:
            return await asyncio.wait_for(
                self._execute_internal(intent_text, context),
                timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            return {"success": False, "error": f"意图执行超时（{effective_timeout}秒）"}
```

**设计说明**: 超时配置与 P2-3 的 `IntentPipelineConfig` (L1/L2/L3 各自超时) 互补——P2-3 控制解析流水线各级超时，P2-9 控制整体执行超时。两者互不冲突。

**详细修复方案**: 参见 [IMPROVEMENT_PLAN.md P2-9 章节](../../IMPROVEMENT_PLAN.md#p2-9-intent_engine-缺少全局执行超时)。

---

### 3.7 Phase Ⅱ 里程碑总结

| 任务 | 状态 | 新增文件 | 修改文件 | 新增测试 |
|------|:--:|------|------|:--:|
| P2-1 协议与注册中心 | ⬜ | 3 | 2 | ~25 |
| P2-2 六大领域网络 | ⬜ | 6 | 20+ | ~30 |
| P2-3 三级流水线 | ⬜ | 0 | 1 | ~40 |
| P2-4 自进化系统 | ⬜ | 1 | 0 | ~10 |
| 🆕 审查修复 (P1-6 解耦) | ✅ | 0 | 1 | ~5 |
| 🆕 审查修复 (P2-9 超时) | ✅ | 0 | 1 | ~3 |
| **合计** | | **10** | **25+** | **~113** |

---

## 4. Phase Ⅲ 破界·全平台征服

> **目标版本**: v0.11.0 | **周期**: 4周 (W7-W10) | **风险等级**: 🔴高
> **核心命题**: Windows → Win/Mac/Linux 三位一体，Office 适配器策略模式重构。

### 4.1 P3-1: Office 适配器跨平台架构

**优先级**: P0 | **预估工时**: 8d | **负责人**: TBD

#### 4.1.1 文件变更清单

| 文件 | 操作 | 说明 |
|------|:--:|------|
| `src/aibridge/adapters/office/base.py` | 🆕 新建 | OfficeAdapter 抽象基类 |
| `src/aibridge/adapters/office/win32_backend.py` | 🆕 新建 | Win32OfficeAdapter (pywin32) |
| `src/aibridge/adapters/office/openxml_backend.py` | 🆕 新建 | OpenXMLOfficeAdapter (python-docx/openpyxl) |
| `src/aibridge/adapters/office/libreoffice_backend.py` | 🆕 新建 | LibreOfficeAdapter (unolib/subprocess) |
| `src/aibridge/adapters/office/factory.py` | 🆕 新建 | `create_office_adapter()` 工厂 |
| `src/aibridge/adapters/office/word.py` | ✏️ 重构 | 改为使用后端代理 |
| `src/aibridge/adapters/office/excel.py` | ✏️ 重构 | 改为使用后端代理 |
| `src/aibridge/adapters/office/ppt.py` | ✏️ 重构 | 改为使用后端代理 |
| `src/aibridge/adapters/office/__init__.py` | ✏️ 修改 | 导出工厂函数 |
| `tests/test_office_cross_platform.py` | 🆕 新建 | 跨平台 Office 测试 |

#### 4.1.2 API 规格

```python
# src/aibridge/adapters/office/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class DocumentHandle:
    """文档操作句柄"""
    path: Path
    backend_type: str           # "win32" | "openxml" | "libreoffice"
    metadata: dict = None


class OfficeAdapter(ABC):
    """Office 适配器抽象——跨平台统一接口"""

    @abstractmethod
    def open_document(self, path: Path) -> DocumentHandle:
        """打开文档并返回操作句柄"""
        ...

    @abstractmethod
    def save_as(self, doc: DocumentHandle, target_path: Path,
                format: str = None) -> DocumentHandle:
        """另存为指定格式"""
        ...

    @abstractmethod
    def export_pdf(self, doc: DocumentHandle, output_path: Path = None) -> Path:
        """导出为 PDF，返回输出路径"""
        ...

    @abstractmethod
    def extract_text(self, doc: DocumentHandle) -> str:
        """提取纯文本内容"""
        ...

    @abstractmethod
    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        """提取所有表格"""
        ...

    @abstractmethod
    def close(self, doc: DocumentHandle) -> None:
        """关闭文档并释放资源"""
        ...

    # -- 便捷方法 (非抽象，有默认实现) --

    def convert_to(self, input_path: Path, output_format: str,
                   output_path: Path = None) -> Path:
        """一键转换：打开 → 另存 → 关闭"""
        doc = self.open_document(input_path)
        try:
            output_path = output_path or input_path.with_suffix(f".{output_format}")
            result = self.save_as(doc, output_path, output_format)
            return result.path
        finally:
            self.close(doc)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass  # 子类实现资源清理


class WordAdapter(OfficeAdapter):
    """Word 适配器专用接口"""
    @abstractmethod
    def insert_text(self, doc: DocumentHandle, text: str,
                    position: str = "end") -> None: ...
    @abstractmethod
    def replace_text(self, doc: DocumentHandle, old: str, new: str) -> int: ...
    @abstractmethod
    def add_table(self, doc: DocumentHandle, rows: int, cols: int,
                  data: list[list] = None) -> int: ...
    @abstractmethod
    def get_comments(self, doc: DocumentHandle) -> list[dict]: ...


class ExcelAdapter(OfficeAdapter):
    """Excel 适配器专用接口"""
    @abstractmethod
    def read_range(self, doc: DocumentHandle, range_str: str) -> pd.DataFrame: ...
    @abstractmethod
    def write_range(self, doc: DocumentHandle, range_str: str,
                    data: pd.DataFrame) -> None: ...
    @abstractmethod
    def add_chart(self, doc: DocumentHandle, data_range: str,
                  chart_type: str, position: str) -> None: ...
    @abstractmethod
    def create_pivot(self, doc: DocumentHandle, source_range: str,
                     rows: list[str], values: list[str]) -> None: ...
    @abstractmethod
    def apply_formula(self, doc: DocumentHandle, cell: str,
                      formula: str) -> None: ...


class PPTAdapter(OfficeAdapter):
    """PPT 适配器专用接口"""
    @abstractmethod
    def add_slide(self, doc: DocumentHandle, layout: str = "blank") -> int: ...
    @abstractmethod
    def add_text_box(self, doc: DocumentHandle, slide_index: int,
                     text: str, position: tuple) -> None: ...
    @abstractmethod
    def add_image(self, doc: DocumentHandle, slide_index: int,
                  image_path: Path, position: tuple) -> None: ...
```

#### 4.1.3 工厂函数

```python
# src/aibridge/adapters/office/factory.py

import platform
import shutil
from typing import Optional
from aibridge.adapters.office.base import OfficeAdapter, WordAdapter, ExcelAdapter, PPTAdapter


def _check_pywin32() -> bool:
    try:
        import win32com.client
        return True
    except ImportError:
        return False


def _check_libreoffice() -> bool:
    return shutil.which("libreoffice") is not None or shutil.which("soffice") is not None


def _get_best_backend() -> str:
    """自动选择最佳后端"""
    if platform.system() == "Windows" and _check_pywin32():
        return "win32"
    if _check_libreoffice():
        return "libreoffice"
    return "openxml"  # 纯 Python 兜底


def create_word_adapter(backend: str = None) -> WordAdapter:
    """创建 Word 适配器，自动选择最佳后端"""
    backend = backend or _get_best_backend()
    if backend == "win32":
        from aibridge.adapters.office.win32_backend import Win32WordAdapter
        return Win32WordAdapter()
    elif backend == "libreoffice":
        from aibridge.adapters.office.libreoffice_backend import LibreOfficeWordAdapter
        return LibreOfficeWordAdapter()
    else:
        from aibridge.adapters.office.openxml_backend import OpenXMLWordAdapter
        return OpenXMLWordAdapter()


def create_excel_adapter(backend: str = None) -> ExcelAdapter:
    backend = backend or _get_best_backend()
    ...

def create_ppt_adapter(backend: str = None) -> PPTAdapter:
    backend = backend or _get_best_backend()
    ...
```

#### 4.1.4 跨平台兼容矩阵

| 功能 | Win32 后端 | OpenXML 后端 | LibreOffice 后端 |
|------|:--:|:--:|:--:|
| 打开文档 | ✅ | ✅ | ✅ |
| 导出 PDF | ✅ | ⚠️ 基础 | ✅ |
| 提取文本 | ✅ | ✅ | ✅ |
| 提取表格 | ✅ | ✅ | ✅ |
| 插入文本/图片 | ✅ | ✅ | ⚠️ |
| 邮件合并 | ✅ | ❌ | ⚠️ |
| 修订追踪 | ✅ | ❌ | ❌ |
| 宏执行 | ✅ | ❌ | ❌ |
| 图表操作 | ✅ | ✅ | ⚠️ |

#### 4.1.5 测试规格

```python
# tests/test_office_cross_platform.py

class TestOfficeCrossPlatform:
    """跨平台 Office 适配器测试——使用纯 Python OpenXML 后端（不依赖外部工具）"""

    @pytest.fixture
    def word(self):
        return create_word_adapter(backend="openxml")

    def test_create_and_save_docx(self, word, tmp_path):
        """创建文档 → 写入内容 → 保存 → 重开验证"""
        doc_path = tmp_path / "test.docx"
        doc = word.open_document(doc_path)
        word.insert_text(doc, "Hello AI-Bridge")
        word.save_as(doc, doc_path)
        word.close(doc)
        # 验证
        doc2 = word.open_document(doc_path)
        assert "Hello AI-Bridge" in word.extract_text(doc2)
        word.close(doc2)

    def test_export_pdf(self, word, tmp_path):
        doc = word.open_document(tmp_path / "test.docx")
        word.insert_text(doc, "Export test")
        pdf_path = word.export_pdf(doc, tmp_path / "output.pdf")
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        word.close(doc)

    def test_extract_tables(self, excel, tmp_path):
        """Excel 表格提取"""
        doc = excel.open_document(tmp_path / "test.xlsx")
        excel.write_range(doc, "A1:B2", pd.DataFrame({"A": [1, 2], "B": [3, 4]}))
        tables = excel.extract_tables(doc)
        assert len(tables) == 1
        assert tables[0].iloc[0, 0] == 1

    def test_backend_fallback(self):
        """后端降级策略"""
        adapter = create_word_adapter(backend="openxml")
        assert "OpenXML" in type(adapter).__name__

    def test_context_manager(self, word, tmp_path):
        with word as w:
            doc = w.open_document(tmp_path / "test.docx")
            w.insert_text(doc, "Context test")
            w.close(doc)
```

#### 4.1.6 验收标准

- [x] 三大后端 (Win32/OpenXML/LibreOffice) 实现完整
- [x] 工厂函数自动选择最佳后端
- [x] `backend="openxml"` 在 Windows/Mac/Linux 下全部通过
- [x] `extract_text()` 和 `extract_tables()` 输出一致（跨后端）
- [x] 降级策略：LibreOffice 不可用时 → OpenXML 兜底
- [x] 集成测试 29 场景

---

### 4.2 P3-2: CLI 工具跨平台发现

**优先级**: P1 | **预估工时**: 3d | **负责人**: TBD

#### 4.2.1 文件清单

| 文件 | 操作 | 说明 |
|------|:--:|------|
| `src/aibridge/core/cli_discovery.py` | 🆕 新建 | CLIToolDiscovery |
| `src/aibridge/adapters/cli/base.py` | ✏️ 修改 | 集成发现层 |
| `tests/test_cli_discovery.py` | 🆕 新建 | 发现层测试 |

#### 4.2.2 API 规格

```python
# src/aibridge/core/cli_discovery.py

@dataclass
class ToolInfo:
    name: str                      # "ffmpeg"
    path: str | None               # "/usr/bin/ffmpeg" or None
    version: str | None            # "6.0"
    platform: str                  # "Windows"
    available: bool
    install_hint: str | None       # "brew install ffmpeg"


class CLIToolDiscovery:
    """智能 CLI 工具发现——跨平台第一道防线"""

    # 工具元数据库
    TOOL_DB: dict[str, dict] = {
        "ffmpeg": {
            "install": {
                "Windows": "choco install ffmpeg",
                "Darwin": "brew install ffmpeg",
                "Linux": "apt install ffmpeg",
            },
            "version_flag": "-version",
            "min_version": "4.0",
        },
        "pandoc": {
            "install": {
                "Windows": "choco install pandoc",
                "Darwin": "brew install pandoc",
                "Linux": "apt install pandoc",
            },
            "version_flag": "--version",
        },
        "docker": {
            "install": {
                "Windows": "winget install Docker.DockerDesktop",
                "Darwin": "brew install --cask docker",
                "Linux": "apt install docker.io",
            },
            "version_flag": "--version",
        },
        # ... 覆盖所有 20+ CLI 工具
    }

    def detect(self, tool_name: str) -> ToolInfo:
        """检测工具是否可用，返回完整信息"""
        ...

    def detect_all(self) -> dict[str, ToolInfo]:
        """批量检测所有已知工具"""
        ...

    def suggest_alternative(self, tool_name: str) -> str:
        """工具不可用时给出替代建议"""
        ...

    def warm_up(self) -> dict[str, ToolInfo]:
        """预热——启动时检测所有工具并缓存结果"""
        ...
```

#### 4.2.3 验收标准

- [x] 覆盖全部 15 CLI 工具的跨平台安装指南
- [x] `detect()` 缓存结果，重复调用 < 1ms
- [x] `suggest_alternative()` 给出平台正确的安装命令
- [x] 工具不存在时返回 `available=False` + 安装提示

---

### 4.3 P3-3: 跨平台 CI 矩阵

**优先级**: P1 | **预估工时**: 2d | **负责人**: TBD

#### 4.3.1 GitHub Actions 配置

```yaml
# .github/workflows/cross-platform.yml (新增)

name: Cross-Platform CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-matrix:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Install
        run: |
          pip install -e ".[dev,office-cross]"
      - name: Unit Tests
        run: pytest tests/ -m "not integration" -v --tb=short
      - name: Cross-Platform Office Tests
        run: pytest tests/test_office_cross_platform.py -v --tb=short
```

#### 4.3.2 验收标准

- [x] CI 在 Ubuntu / macOS / Windows + Python 3.10/3.11/3.12 全部通过
- [x] 跨平台 Office 测试在所有 OS 上通过（使用 OpenXML 后端）

---

### 4.4 Phase Ⅲ 里程碑总结

| 任务 | 状态 | 新增文件 | 修改文件 | 新增测试 |
|------|:--:|------|------|:--:|
| P3-1 Office 跨平台 | ✅ | 6 | 1 | ~29 |
| P3-2 CLI 工具发现 | ✅ | 1 | 0 | ~31 |
| P3-3 CI 矩阵 | ✅ | 1 | 0 | 0 |
| **合计** | | **8** | **1** | **~60** |

---



## 5. Phase Ⅳ 铸盾·生产就绪

> **目标版本**: v1.0.0 🎉 | **周期**: 3周 (W11-W13) | **风险等级**: 🟡中
> **核心命题**: 从 Mock 堆砌到真实测试，从 Alpha 到 Production。

### 5.1 P4-1: 分级测试体系建设

**优先级**: P0 | **预估工时**: 10d | **负责人**: TBD

#### 5.1.1 测试金字塔目标

```
        ┌─────────┐
        │  L4 混沌 │  5+  每周
       ┌┴─────────┴┐
       │  L3 E2E   │ 10+  每日
      ┌┴───────────┴┐
      │  L2 集成     │ 30+  每 PR
     ┌┴─────────────┴┐
     │  L1 组件       │ 50+  每 commit
    ┌┴───────────────┴┐
    │  L0 单元 (已有)  │ 700+ 每 commit
    └─────────────────┘
```

#### 5.1.2 文件清单

| 文件 | 操作 | 说明 |
|------|:--:|------|
| `tests/component/__init__.py` | 🆕 | 组件测试入口 |
| `tests/component/test_intent_pipeline.py` | 🆕 | 意图流水线组件测试 |
| `tests/component/test_protocol_bridge.py` | 🆕 | 协议桥组件测试 |
| `tests/component/test_pbac_engine.py` | 🆕 | PBAC 策略引擎组件测试 |
| `tests/component/test_dag_orchestrator.py` | 🆕 | DAG 编排引擎组件测试 |
| `tests/integration/__init__.py` | 🆕 | 集成测试入口 |
| `tests/integration/test_chrome_real.py` | 🆕 | Chrome 真实交互测试 |
| `tests/integration/test_ffmpeg_real.py` | 🆕 | FFmpeg 真实转码测试 |
| `tests/integration/test_office_real.py` | 🆕 | Office 真实文档测试 |
| `tests/integration/test_docker_real.py` | 🆕 | Docker 真实容器测试 |
| `tests/integration/test_git_real.py` | 🆕 | Git 真实仓库测试 |
| `tests/e2e/__init__.py` | 🆕 | E2E 测试入口 |
| `tests/e2e/test_full_chain.py` | 🆕 | 全链路 E2E 测试 |
| `tests/e2e/test_performance.py` | 🆕 | 性能基准测试 |
| `tests/fixtures/e2e_config.yaml` | 🆕 | E2E 测试配置 |
| `.github/workflows/iron-curtain.yml` | 🆕 | 铁幕 CI 管线 |
| `tests/conftest.py` | ✏️ 修改 | 增加 pytest 标记和 CLI 选项 |
| `scripts/check_benchmark_regression.py` | 🆕 | 性能回归检测脚本 |

#### 5.1.3 L1 组件测试规格

```python
# tests/component/test_intent_pipeline.py (新增)
class TestIntentPipeline:
    """意图流水线组件测试——使用真实 Registry 和 Mock LLM"""

    @pytest.fixture
    def engine(self):
        registry = DomainIntentRegistry()
        registry.register("ffmpeg", MEDIA_PATTERNS[:5])
        registry.register("office", OFFICE_PATTERNS[:5])
        return IntentEngine(registry, llm_provider=MockLLMProvider())

    @pytest.mark.asyncio
    async def test_l1_exact_match(self, engine):
        result = await engine.resolve("把视频转成gif")
        assert result is not None
        assert result.route == "exact"
        assert result.pattern.id == "media.gif_from_video"

    @pytest.mark.asyncio
    async def test_l2_semantic_fallback(self, engine):
        result = await engine.resolve("这个视频帮我做成动图")
        assert result is not None
        assert result.route in ("exact", "semantic")

    @pytest.mark.asyncio
    async def test_composite_intent_detection(self, engine):
        result = await engine.resolve("把报表转PDF然后发Slack")
        if result:
            assert isinstance(result, CompositeIntent)

    @pytest.mark.asyncio
    async def test_l3_llm_fallback(self, engine):
        engine.llm_provider.set_mock_response(...)
        result = await engine.resolve("帮我把那个视频搞小一点")
        assert result is not None
        assert result.route == "llm"


# tests/component/test_dag_orchestrator.py (新增)
class TestDAGOrchestrator:
    async def test_sequential_two_node_dag(self): ...
    async def test_parallel_independent_nodes(self): ...
    async def test_dependency_chain_execution_order(self): ...
    async def test_node_failure_short_circuits_dependents(self): ...
```

#### 5.1.4 L2 集成测试规格

```python
# tests/integration/test_chrome_real.py (新增)
@pytest.mark.integration
@pytest.mark.docker
class TestChromeReal:
    @pytest.fixture(scope="class")
    async def chrome(self):
        from aibridge.adapters.browser.chrome import ChromeAdapter
        adapter = ChromeAdapter({"headless": True, "sandbox": False})
        await adapter.connect()
        yield adapter
        await adapter.disconnect()

    async def test_navigate_and_get_title(self, chrome):
        await chrome.navigate("https://httpbin.org/html")
        title = await chrome.get_title()
        assert len(title) > 0

    async def test_screenshot_non_empty(self, chrome, tmp_path):
        await chrome.navigate("https://example.com")
        screenshot = await chrome.screenshot()
        assert screenshot is not None
        assert len(screenshot) > 1000


# tests/integration/test_ffmpeg_real.py (新增)
@pytest.mark.integration
class TestFFmpegReal:
    def test_convert_mp4_to_gif(self, tmp_path):
        adapter = FFmpegAdapter({})
        input_path = self._generate_test_video(tmp_path)
        output = adapter.convert(input_path, tmp_path / "out.gif", format="gif")
        assert output.exists()
        assert output.stat().st_size > 0

    def test_convert_nonexistent_file_raises(self, tmp_path):
        adapter = FFmpegAdapter({})
        with pytest.raises(AdapterExecutionError):
            adapter.convert(tmp_path / "ghost.mp4", tmp_path / "out.mp4")

    def _generate_test_video(self, tmp_path) -> Path:
        output = tmp_path / "test.mp4"
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240",
            "-c:v", "libx264", str(output)
        ], check=True, capture_output=True)
        return output


# tests/integration/test_office_real.py (新增)
@pytest.mark.integration
class TestOfficeReal:
    def test_create_docx_write_and_read(self, tmp_path):
        adapter = create_word_adapter(backend="openxml")
        doc_path = tmp_path / "test.docx"
        doc = adapter.open_document(doc_path)
        adapter.insert_text(doc, "AI-Bridge Integration Test")
        adapter.close(doc)
        doc2 = adapter.open_document(doc_path)
        assert "AI-Bridge" in adapter.extract_text(doc2)
        adapter.close(doc2)

    def test_export_pdf_from_docx(self, tmp_path):
        adapter = create_word_adapter(backend="openxml")
        doc_path = tmp_path / "test.docx"
        doc = adapter.open_document(doc_path)
        adapter.insert_text(doc, "PDF Export")
        adapter.close(doc)
        pdf = adapter.convert_to(doc_path, "pdf")
        assert pdf.suffix == ".pdf"
        assert pdf.stat().st_size > 0


# tests/integration/test_docker_real.py (新增)
@pytest.mark.integration
@pytest.mark.docker
class TestDockerReal:
    async def test_pull_run_stop_alpine(self):
        adapter = DockerAdapter({})
        await adapter.connect()
        cid = await adapter.run("alpine:latest", command="echo hello")
        logs = await adapter.logs(cid)
        assert "hello" in logs
        await adapter.stop(cid)
        await adapter.remove(cid)
```

#### 5.1.5 L3 端到端测试规格

```python
# tests/e2e/test_full_chain.py (新增)
@pytest.mark.e2e
class TestFullChainE2E:
    async def test_natural_language_to_browser_action(self):
        bridge = AIBridge(config_path="tests/fixtures/e2e_config.yaml")
        result = await bridge.do("打开 example.com 并截图")
        assert result.success
        assert result.screenshot is not None

    async def test_multi_adapter_office_workflow(self, tmp_path):
        bridge = AIBridge(config_path="tests/fixtures/e2e_config.yaml")
        result = await bridge.do(
            f"创建一个Word文档保存到{tmp_path}，写入'Hello World'，然后导出PDF"
        )
        assert result.success
        pdf = tmp_path / "output.pdf"
        assert pdf.exists()

    async def test_a2a_streaming_full_chain(self):
        ...


# tests/e2e/test_performance.py (新增)
@pytest.mark.perf
class TestPerformance:
    def test_l1_intent_match_latency(self, benchmark):
        engine = create_test_engine_with_60_patterns()
        result = benchmark(engine.registry.match, "把视频转成gif")
        assert benchmark.stats.stats.mean < 0.05

    def test_adapter_cold_start_latency(self, benchmark):
        benchmark(create_word_adapter, backend="openxml")
        assert benchmark.stats.stats.mean < 2.0
```

#### 5.1.6 pytest 基础设施

```python
# tests/conftest.py 追加部分

def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true",
                     help="运行集成测试 (需要 Docker)")
    parser.addoption("--e2e", action="store_true",
                     help="运行端到端测试 (需要完整环境)")
    parser.addoption("--perf", action="store_true",
                     help="运行性能基准测试")

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "docker: 需要 Docker 守护进程")
    config.addinivalue_line("markers", "e2e: 端到端测试标记")
    config.addinivalue_line("markers", "perf: 性能基准标记")

def pytest_collection_modifyitems(config, items):
    skip_integration = pytest.mark.skip(reason="需要 --integration 标志")
    skip_e2e = pytest.mark.skip(reason="需要 --e2e 标志")
    for item in items:
        if "integration" in item.keywords and not config.getoption("--integration"):
            item.add_marker(skip_integration)
        if "e2e" in item.keywords and not config.getoption("--e2e"):
            item.add_marker(skip_e2e)
```

#### 5.1.7 CI/CD 铁幕管线

```yaml
# .github/workflows/iron-curtain.yml (新增)

name: 铁幕防线

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 2 * * *"

jobs:
  lint-and-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - name: Lint & Type Check
        run: ruff check src/ && mypy src/aibridge/core/
      - name: Unit Tests + Coverage
        run: pytest tests/ -m "not integration and not e2e" -v --cov --cov-report=xml

  integration-docker:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:dind
        options: --privileged
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: |
          sudo apt-get update && sudo apt-get install -y ffmpeg git
          pip install -e ".[all]"
      - name: Integration Tests
        run: pytest tests/integration/ -v --tb=long --timeout=120 --integration

  e2e-nightly:
    if: github.event_name == 'schedule'
    runs-on: [self-hosted, linux]
    steps:
      - uses: actions/checkout@v4
      - name: E2E Suite
        run: pytest tests/e2e/ -v --tb=long --timeout=300 --e2e

  benchmark-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - name: Performance Benchmarks
        run: pytest tests/e2e/test_performance.py --benchmark-only --perf
      - name: Regression Check
        run: python scripts/check_benchmark_regression.py
```

#### 5.1.8 性能基准规格

| 指标 | 目标值 | 测量工具 | 告警阈值 |
|------|--------|----------|:--:|
| L1 意图匹配 P99 | < 50ms | pytest-benchmark | > 100ms |
| L2 语义搜索 P99 | < 500ms | pytest-benchmark | > 800ms |
| L3 LLM 解析 P99 | < 5s | 内置 telemetry | > 8s |
| 适配器冷启动 (OpenXML) | < 2s | pytest-benchmark | > 3s |
| MCP 消息吞吐 | > 1000 msg/s | 压测脚本 | < 800 |
| A2A 流首字节 | < 100ms | e2e tracing | > 200ms |
| 单元测试执行 | < 60s | CI 计时 | > 90s |

#### 5.1.9 验收标准

- [ ] L0 单元测试 700+，覆盖率 >90%
- [ ] L1 组件测试 50+，全部通过
- [ ] L2 集成测试 30+，Chrome/FFmpeg/Docker/Office/Git 各 ≥3 项
- [ ] L3 E2E 测试 10+，覆盖完整自然语言链路
- [ ] 性能基准 6/7 项达标
- [ ] CI 铁幕管线全绿
- [ ] `--integration` 和 `--e2e` 命令行开关正常工作

---

### 5.2 审查发现：安全与健壮性加固

> 来源：[IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md) 2026-05-07 全面安全审计。以下问题纳入 Phase Ⅳ（生产就绪）作为 v1.0.0 发布前的必修安全门禁。

#### 5.2.1 P0 级安全漏洞（发布阻断项）

##### P0-1: SecureAdapterWrapper.__getattr__ 安全完全绕过

**文件**: `core/security.py:414-416` | **CWE-284** | **预计工时**: 1h

**问题**: `__getattr__` 将所有非显式定义的属性直接代理到原始 adapter，攻击者可通过 `secure_wrapper._page.evaluate(恶意JS)` 完全绕过安全策略。

**修复**: 将透传改为白名单模式，仅允许 `info`、`adapter_id`、`adapter_name`、`is_connected`、`get_supported_actions`、`supports_action`、`health_check` 等安全只读属性透传，拒绝所有 `_` 开头的私有属性访问。

##### P0-2: mcp_server.py 三个 handler 缺少初始化检查

**文件**: `server/mcp_server.py:466,491,506` | **预计工时**: 0.5h

**问题**: `handle_screenshot`、`handle_execute_intent`、`handle_execute_task` 三个方法缺少 `_check_initialized()` 调用，未初始化时导致 `AttributeError` 崩溃而非友好错误提示。

**修复**: 在三个方法开头添加 `if error := await self._check_initialized(): return error`。

##### P0-3: mcp_server.py URL 验证存在 SSRF 风险

**文件**: `server/mcp_server.py:255-293` | **CWE-918** | **预计工时**: 2h

**问题**: `_validate_url` 只验证协议和 netloc，未检查内网 IP，存在 SSRF 攻击风险。

**修复**: 
- 添加 `allow_private_ips` 配置开关
- 将 `_validate_url` 改为异步方法，使用 `loop.run_in_executor` 进行异步 DNS 解析
- 检查回环地址、内网地址、本地链路地址、多播地址、未指定地址
- 更新所有同步 `_validate_url(url)` 调用为 `await self._validate_url(url)`

**已知局限**: DNS 重绑定攻击需网络层防火墙配合完全防御；IPv6 特有地址需额外分支。

#### 5.2.2 P1 级安全加固项

##### P1-1: chrome.py JS 注入防护 fields 验证过于宽松

**文件**: `adapters/browser/chrome.py:1165` | **预计工时**: 0.5h

**问题**: `safe_fields = [f for f in fields if f.isalnum() or f.replace('_', '').isalnum()]` 允许 `__proto__`、`constructor`、纯数字等危险字段名。

**修复**: 引入正则 `^[a-zA-Z_][a-zA-Z0-9_]*$` 验证 + 显式黑名单排除 `__proto__`、`constructor`、`prototype`。

##### P1-2: session_manager.py JSON 反序列化缺少结构验证

**文件**: `core/session_manager.py:182-186` | **预计工时**: 0.5h

**问题**: `data = json.load(f)` 后直接 `SessionData(**data)`，不验证 JSON 结构完整性。

**修复**: 验证 `data` 为 dict 且包含必需键 `name`、`created_at`、`updated_at`、`url`、`title`，缺失时返回友好错误而非崩溃。

#### 5.2.3 P2 级健壮性改进项

##### P2-5: chrome.py connect() 失败时资源清理不完整

**文件**: `adapters/browser/chrome.py:217-246` | **预计工时**: 1h

**修复**: 引入集中的 `_cleanup_resources()` 方法，按 `_page → _context → _browser → _playwright` 顺序容错清理，保留原始异常链（`raise ... from e`）。

##### P2-6: manager.py execute() 中的 TOCTOU 竞态

**文件**: `core/manager.py:169-173` | **预计工时**: 0.5h

**修复**: 先执行操作，仅在 `adapter.is_connected == False` 时才重连重试，避免对参数校验错误等非连接错误进行无意义重连。

##### P2-7: chrome.py 快照缓存达到上限后行为不一致

**文件**: `adapters/browser/chrome.py:748-768` | **预计工时**: 1h

**修复**: 引入 `OrderedDict` LRU 淘汰策略，达到 `MAX_SNAPSHOT_CACHE=1000` 上限时淘汰最旧的 20% 条目。

##### P2-8: orchestrator.py asyncio.gather 错误传播

**文件**: `core/orchestrator.py:544` | **预计工时**: 0.5h

**修复**: `asyncio.gather` 添加 `return_exceptions=True`，逐个检查结果并记录异常任务日志。

---

**安全审计验证**: 全部修复完成后运行 `python ai-bridge/tools/security_auditor.py` 确认零新增告警。

**状态: 全部 9 项已完成** (P0-1/2/3, P1-1/2, P2-5/6/7/8) — 已在 Phase I-III 开发过程中实施并验证通过。全量回归 907 测试全部通过，`security_auditor.py` 零新增告警。

**详细修复方案**: 各问题具体代码对比参见 [IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md)。

---

### 5.3 P4-2: v1.0.0 正式发布

**优先级**: P0 | **预估工时**: 3d | **负责人**: TBD

#### 5.2.1 发布检查清单

| # | 检查项 | 通过条件 |
|:--:|------|------|
| 1 | `pyproject.toml` version = `1.0.0` | 文件已更新 |
| 2 | 全平台 CI 矩阵 12 job 全绿 | CI 通过 |
| 3 | 安全审计零高危 | bandit + pip-audit + security_auditor.py 零新增告警 |
| 4 | API 文档完整 | 所有 Public API 已文档化 |
| 5 | 迁移指南就绪 | `MIGRATION_0.x_to_1.0.md` |
| 6 | CHANGELOG v1.0.0 完成 | 包含 Phase Ⅰ-Ⅳ 全部变更 |
| 7 | 性能基准 6/7 达标 | 基准报告 |
| 8 | 依赖许可证全部兼容 MIT | 合规检查 |
| 9 | `python -m build` + `twine check` | 通过 |
| 10 | `docker build -t ai-bridge:1.0.0 .` | 构建成功 |

#### 5.2.2 发布文件清单

| 文件 | 说明 |
|------|------|
| `MIGRATION_0.x_to_1.0.md` | 旧字典模式 → 结构化异常迁移指南 |
| `CHANGELOG.md` (v1.0.0) | 完整变更日志 |
| `docs/api/` | mkdocs 生成 API 文档 |
| `docs/architecture.md` | 分层架构文档 |
| `SECURITY.md` | 安全策略更新 |
| `examples/v1_migration.py` | 迁移代码示例 |

#### 5.2.3 验收标准

- [ ] `pip install ai-bridge==1.0.0` 成功安装
- [ ] Docker 镜像推送至 GitHub Container Registry
- [ ] GitHub Release 含完整 Release Notes
- [ ] 发布博文已发布

---

### 5.4 Phase Ⅳ 里程碑总结

| 任务 | 状态 | 新增文件 | 修改文件 | 新增测试 |
|------|:--:|------|------|:--:|
| P4-1 分级测试体系 | 🔄 | 10 | 1 | ~30 |
| 🆕 安全加固 (P0-1/2/3, P1-1/2) | ✅ | 0 | 0 | 0 |
| 🆕 健壮性改进 (P2-5/6/7/8) | ✅ | 0 | 0 | 0 |
| P4-2 v1.0 正式发布 | ⬜ | 3 | 3 | 0 |
| **合计** | | **13** | **4** | **~30** |

> 注：安全加固与健壮性改进共 9 项已在 Phase I-III 开发过程中全部实现并验证通过。

---

## 6. Phase Ⅴ 锻剑·适配器淬炼

> **目标版本**: v1.1.0 | **周期**: 3周 (W14-W16) | **风险等级**: 🟡中
> **核心命题**: 6 大适配器从 L1 "薄壳" 升级为 L3 "AI 原生"（含 Chrome 审查重构）。

### 6.1 适配器分级标准

| 级别 | 标志 | 特征 | 当前数量 | 目标数量 |
|:--:|------|------|:--:|:--:|
| **L1 命令封装** | `subprocess.run()` 薄壳 | 参数透传，无智能 | 8 | → 0 |
| **L2 智能增强** | + 参数推断 + 错误恢复 + 结果解析 | 半自动，需少量人工干预 | 4 | → 8 |
| **L3 AI 原生** | + 意图感知 + 上下文学习 + 自优化 | 全自动，自然语言驱动 | 2 | → 6 |

### 6.2 P5-1: FFmpeg 适配器深度重构

**优先级**: P1 | **预估工时**: 5d | **源文件**: `src/aibridge/adapters/cli/ffmpeg.py`

#### 6.2.1 重构对比

| 维度 | 当前 (L1) | 目标 (L3) |
|------|------|------|
| 行数 | 192 | ~600 |
| 方法数 | 5 | 18+ |
| 意图模式 | 0 | 18 |
| 智能参数推断 | ❌ | ✅ |
| 错误自愈 | ❌ | ✅ |
| 媒体分析 | ❌ | ✅ (ffprobe + AI) |
| 批量调度 | ❌ | ✅ |

#### 6.2.2 新增核心 API

```python
class FFmpegProAdapter(BaseCLIAdapter):
    """FFmpeg 专业适配器 v2.0 — AI 原生多媒体处理引擎"""

    def smart_convert(self, input_path: Path, intent: str,
                      output_path: Path = None) -> ConversionResult:
        """根据自然语言意图自动推断最佳参数。

        Examples:
            smart_convert("video.mp4", "压缩到10MB以内")
            → 自动计算 target bitrate = (10*8*1024) / duration
            → ffmpeg -i video.mp4 -b:v {calculated}k output.mp4

            smart_convert("video.mp4", "提取前30秒并加水印")
            → ffmpeg -i video.mp4 -t 30 -vf "drawtext=text='BRAND'" output.mp4
        """
        ...

    def probe_analyze(self, file: Path) -> MediaProfile:
        """深度媒体分析——ffprobe + AI 内容理解

        Returns:
            MediaProfile(
                codec="h264", resolution="1920x1080", duration=120.5,
                bitrate="5000k", fps=30, has_audio=True,
                scene_changes=[12.3, 45.6, 89.0],
                content_summary="产品演示视频，包含3个章节",
                optimization_suggestions=["建议使用CRF 23压缩"]
            )
        """
        ...

    async def batch_optimize(self, files: list[Path],
                             target: BatchTarget) -> BatchReport:
        """批量媒体优化——智能并行 + 进度预测 + 失败重试"""
        ...

    def error_heal(self, error: FFmpegError) -> HealingAction:
        """常见错误自动诊断，覆盖 8+ 种错误模式"""
        ...
```

#### 6.2.3 数据模型

```python
@dataclass
class MediaProfile:
    path: Path
    codec: str
    resolution: str
    duration: float
    bitrate: str
    fps: float
    file_size: int
    has_audio: bool
    audio_codec: str | None
    scene_changes: list[float] = field(default_factory=list)
    content_summary: str = ""
    quality_score: float = 0.0
    optimization_suggestions: list[str] = field(default_factory=list)

@dataclass
class ConversionResult:
    success: bool
    input_path: Path
    output_path: Path
    command: str
    duration: float
    input_size: int
    output_size: int
    compression_ratio: float
    warnings: list[str]

@dataclass
class BatchReport:
    success: int
    failed: int
    total_duration: float
    avg_compression_ratio: float
    retry_count: int
    details: list[ConversionResult]
```

#### 6.2.4 测试矩阵

| 编号 | 测试场景 | 类型 | 预期断言 |
|:--:|------|:--:|------|
| FF-01 | mp4 → gif 基本转换 | 集成 | 输出存在且 >0 bytes |
| FF-02 | 压缩到指定大小 | 集成 | 输出 size ≤ target |
| FF-03 | 裁剪起止时间 | 集成 | duration = end-start |
| FF-04 | 提取音频 | 集成 | 输出无视频轨道 |
| FF-05 | 添加文字水印 | 集成 | 滤镜已应用 |
| FF-06 | 拼接多视频 | 集成 | duration = sum |
| FF-07 | 调整分辨率 | 集成 | ffprobe 验证 |
| FF-08 | 修改帧率 | 集成 | ffprobe 验证 |
| FF-09 | 提取第 N 帧 | 集成 | 输出为图片文件 |
| FF-10 | 倍速播放 | 集成 | duration 减半 |
| FF-11 | probe_analyze | 集成 | 必填字段非空 |
| FF-12 | batch_optimize | 集成 | stats 正确 |
| FF-13 | error_heal | 单元 | 返回 HealingAction |
| FF-14 | 18 意图模式全可匹配 | 组件 | L1 匹配率 100% |

---

### 6.3 其他适配器重构规格

#### 6.3.1 P5-2: pandoc (3d)

| 源文件 | 当前 | 目标 |
|------|:--:|:--:|
| `adapters/cli/pandoc.py` | 123行 | ~350行 |

**新增**: `smart_convert()`, `batch_convert()`, `extract_metadata()`, `supported_formats()` | 意图: 8个

#### 6.3.2 P5-3: Docker (3d)

| 源文件 | 当前 | 目标 |
|------|:--:|:--:|
| `adapters/cli/docker.py` | ~200行 | ~500行 |

**新增**: `compose_up/down()`, `health_check()`, `resource_monitor()`, `log_aggregator()`, `cleanup_dangling()`

#### 6.3.3 P5-4: Git (2d)

| 源文件 | 当前 | 目标 |
|------|:--:|:--:|
| `adapters/cli/aider.py` | ~150行 | ~400行 |

**新增**: `smart_commit()`, `conflict_analyze()`, `branch_workflow()`

#### 6.3.4 P5-5: Blender (2d)

| 源文件 | 当前 | 目标 |
|------|:--:|:--:|
| `adapters/cli/blender.py` | ~180行 | ~500行 |

**新增**: `render_optimize()`, `scene_analyze()`, `batch_render()`

#### 6.3.5 P5-6: Chrome 适配器审查重构（审查 P3-1 + P3-2）

> 来源：[IMPROVEMENT_PLAN.md](../../IMPROVEMENT_PLAN.md) P3-1/P3-2

**优先级**: P2 | **预估工时**: 5h | **文件**: `adapters/browser/chrome.py`

##### P3-1: chrome.py execute() 方法过长（~314行）

**问题**: `execute()` 方法（第320-633行）包含 25+ 个 `if/elif` 分支，圈复杂度过高。

**修复**: 策略模式 + 分发字典，将原有 `elif` 分支拆分为独立的 `_handle_xxx` 方法，每个方法 ≤ 50 行。`execute()` 精简为：查表 → 调用 handler → 统一异常处理。

##### P3-2: 提取公共验证逻辑到工具模块

**问题**: CSS 选择器验证逻辑在 `chrome.py` 和 `mcp_server.py` 中重复。

**修复**: 创建 `src/aibridge/utils/security.py`，包含 `validate_css_selector()` 等通用验证函数。`chrome.py` 和 `mcp_server.py` 改为引用此公共函数。

**详细修复方案**: 参见 [IMPROVEMENT_PLAN.md P3-1/P3-2 章节](../../IMPROVEMENT_PLAN.md#p3-1-chromepy-execute-方法过长)。

#### 6.3.6 Phase Ⅴ 验收标准

- [ ] 5 个适配器全部达 L2+ 级别
- [ ] 每个适配器 ≥8 个意图模式
- [ ] 每个适配器新增 ≥5 个集成测试
- [ ] `adapter_info` 正确报告能力级别

---

### 6.4 Phase Ⅴ 里程碑总结

| 任务 | 状态 | 新增代码行 | 修改文件 | 新增测试 |
|------|:--:|:--:|------|:--:|
| P5-1 FFmpeg 重构 | ⬜ | ~600 | 1 | 14 |
| P5-2 pandoc 重构 | ⬜ | ~350 | 1 | 8 |
| P5-3 Docker 重构 | ⬜ | ~500 | 1 | 10 |
| P5-4 Git 重构 | ⬜ | ~400 | 1 | 8 |
| P5-5 Blender 重构 | ⬜ | ~500 | 1 | 8 |
| 🆕 P5-6 Chrome 重构 (审查 P3-1/2) | ⬜ | ~200 | 2 | ~5 |
| **合计** | | **~2,550** | **7** | **~53** |

---

## 7. Phase Ⅵ 星火·生态燎原

> **目标版本**: v1.2.0+ | **周期**: 6周+ (W17+) | **风险等级**: 🟡中
> **核心命题**: 插件市场 + 社区引擎，从项目到生态。

### 7.1 P6-1: 插件系统核心

**优先级**: P0 | **预估工时**: 10d

#### 7.1.1 文件清单

| 文件 | 操作 | 行数 |
|------|:--:|:--:|
| `src/aibridge/plugin/__init__.py` | 🆕 | ~20 |
| `src/aibridge/plugin/protocol.py` | 🆕 | ~200 |
| `src/aibridge/plugin/manager.py` | 🆕 | ~350 |
| `src/aibridge/plugin/discovery.py` | 🆕 | ~200 |
| `src/aibridge/plugin/security.py` | 🆕 | ~250 |
| `src/aibridge/plugin/sandbox.py` | 🆕 | ~150 |
| `src/aibridge/marketplace/__init__.py` | 🆕 | ~20 |
| `src/aibridge/marketplace/index.py` | 🆕 | ~200 |
| `src/aibridge/marketplace/installer.py` | 🆕 | ~250 |
| `src/aibridge/marketplace/publisher.py` | 🆕 | ~200 |
| `src/aibridge/cli/plugin_commands.py` | 🆕 | ~300 |
| `tests/test_plugin_system.py` | 🆕 | ~400 |
| `tests/test_marketplace.py` | 🆕 | ~300 |

#### 7.1.2 核心 API

```python
# src/aibridge/plugin/protocol.py

@dataclass
class PluginManifest:
    name: str                      # "ai-bridge-plugin-ffmpeg"
    display_name: str              # "FFmpeg Pro"
    version: str                   # "1.0.0"
    description: str
    author: str
    license: str = "MIT"
    repository: str = ""
    requires_python: str = ">=3.10"
    requires_bridge: str = ">=1.0.0"
    requires_tools: list[str] = field(default_factory=list)
    provides_adapters: list[str] = field(default_factory=list)
    provides_intents: int = 0
    provides_tools: int = 0
    category: str = "media"
    tags: list[str] = field(default_factory=list)
    icon: str = ""


class AIBridgePlugin(ABC):
    """插件灵魂契约——任何开发者 30 分钟即可实现"""

    manifest: PluginManifest

    async def on_load(self, context: "PluginContext") -> None:
        """加载时注册适配器、意图、MCP 工具"""
        ...

    async def on_unload(self) -> None:
        """卸载时清理资源"""
        ...

    def register_adapters(self, registry: "AdapterRegistry") -> None: pass
    def register_intents(self, registry: "IntentRegistry") -> None: pass
    def register_tools(self, registry: "ToolRegistry") -> None: pass

    async def health_check(self) -> bool:
        return True


@dataclass
class PluginContext:
    bridge: "AIBridge"
    config: dict
    data_dir: Path
    logger: "Logger"


class PluginManager:
    async def discover(self) -> list[PluginManifest]: ...
    async def load(self, plugin_name: str) -> AIBridgePlugin: ...
    async def unload(self, plugin_name: str) -> None: ...
    async def reload(self, plugin_name: str) -> AIBridgePlugin: ...
    def get_plugin(self, name: str) -> AIBridgePlugin | None: ...
    def list_plugins(self) -> list[PluginManifest]: ...
```

#### 7.1.3 entry_points 注册

```toml
# 第三方插件的 pyproject.toml
[project.entry-points."ai_bridge.plugins"]
ffmpeg_pro = "ai_bridge_ffmpeg.plugin:FFmpegProPlugin"
```

#### 7.1.4 CLI 命令

```bash
# 插件管理
bridge plugin list                    # 列出已安装
bridge plugin search ffmpeg           # 市场搜索
bridge plugin install ffmpeg-pro      # 安装
bridge plugin uninstall ffmpeg-pro    # 卸载
bridge plugin update ffmpeg-pro       # 更新
bridge plugin info ffmpeg-pro         # 详情

# 插件开发
bridge dev new my-plugin              # 脚手架生成
bridge dev test my-plugin             # 本地测试
bridge dev publish                    # 发布到市场
```

#### 7.1.5 验收标准

- [ ] `AIBridgePlugin` 协议完整，≤4 个必须实现方法
- [ ] PluginManager 加载/卸载/重载无异常
- [ ] entry_points 自动发现正常
- [ ] 插件沙箱隔离运行
- [ ] 安全审计覆盖权限声明 + 静态扫描
- [ ] CLI 6 管理命令 + 3 开发命令可用
- [ ] 3 个示例插件通过安装测试

---

### 7.2 P6-2: 适配器市场

**优先级**: P1 | **预估工时**: 8d

#### 7.2.1 市场索引格式

```json
{
  "version": "1",
  "updated_at": "2026-09-01T00:00:00Z",
  "plugins": [{
    "name": "ai-bridge-plugin-ffmpeg",
    "display_name": "FFmpeg Pro",
    "version": "2.1.0",
    "description": "AI-native FFmpeg adapter",
    "author": "community",
    "category": "media",
    "downloads": 12000,
    "rating": 4.8,
    "min_bridge_version": "1.0.0",
    "repository": "https://github.com/...",
    "package_url": "https://.../plugin.whl",
    "sha256": "abc123...",
    "tags": ["ffmpeg", "video", "media"]
  }]
}
```

#### 7.2.2 发布流程

```
开发者: bridge dev publish
  ├─ manifest 自动验证
  ├─ bandit 安全扫描
  ├─ 测试运行
  └─ 打包上传
  → PR 提交市场索引
  → 人工审核
  → 沙箱验证
  → 签名 → 上架 ✅
```

#### 7.2.3 验收标准

- [ ] 市场索引 API 通过 GitHub Pages 可访问
- [ ] `bridge plugin search/install` 全流程走通
- [ ] SHA256 校验防止篡改
- [ ] 发布审核流程文档化

---

### 7.3 P6-3: 社区引擎

**优先级**: P2 | **预估工时**: 6d

#### 7.3.1 激励机制设计

| 机制 | 触发条件 | 奖励 |
|------|------|------|
| 🏅 贡献者勋章 | 首次 PR 合并 | GitHub 数字勋章 + README 鸣谢 |
| 🌟 月度之星 | 最佳插件 | 官网首页推荐 + 社媒推广 |
| 💰 赞助计划 | 核心/热门维护者 | GitHub Sponsors / OpenCollective |
| 🎪 季度黑客松 | 48h 造适配器 | 奖金 + 官方集成 + 推荐位 |

#### 7.3.2 文档体系规划

```
docs/
├── getting-started/
│   ├── installation.md, quickstart.md, concepts.md
├── guides/
│   ├── plugin-development.md     # 插件开发指南 (≥3000字)
│   ├── intent-patterns.md        # 意图模式设计指南
│   ├── adapter-guide.md          # 适配器开发最佳实践
│   ├── testing.md                # 测试指南
│   └── publishing.md             # 发布到市场
├── api/
│   ├── core.md, plugin-protocol.md, adapters.md
├── examples/
│   ├── basic-plugin/             # 最简插件
│   ├── ffmpeg-plugin/            # 完整插件示例
│   └── office-plugin/            # Office 插件示例
└── community/
    ├── code-of-conduct.md, contributing.md, roadmap.md
```

#### 7.3.3 验收标准

- [ ] 插件开发指南 ≥3000 字，含中文版
- [ ] 3 个完整示例插件（含注释）
- [ ] `bridge dev new` 一键生成插件骨架
- [ ] CONTRIBUTING.md 含完整 PR 流程
- [ ] CODE_OF_CONDUCT.md 就绪

---

### 7.4 Phase Ⅵ 里程碑总结

| 任务 | 状态 | 新增文件 | 修改文件 | 新增代码行 |
|------|:--:|------|------|:--:|
| P6-1 插件系统 | ⬜ | 11 | 2 | ~2,800 |
| P6-2 适配器市场 | ⬜ | 3 | 0 | ~800 |
| P6-3 社区引擎 | ⬜ | 8 | 0 | ~3,000 (文档) |
| **合计** | | **22** | **2** | **~6,600** |

---

## 8. 风险矩阵与依赖图

### 8.1 风险矩阵

| ID | 风险描述 | 影响 | 概率 | 等级 | 缓解措施 |
|:--:|------|:--:|:--:|:--:|------|
| R1 | 错误体系统一导致大规模回归 | 高 | 中 | 🔴 | 兼容层 + 渐进迁移 + 全量回归测试 |
| R2 | Office 跨平台后端功能矩阵有限 | 高 | 高 | 🔴 | 功能矩阵明确定义，降级路径预置 |
| R3 | LLM 不可用时 L3 完全失效 | 中 | 中 | 🟡 | L1+L2 兜底，超时不阻塞主流程 |
| R4 | 集成测试 Docker 环境搭建复杂 | 中 | 中 | 🟡 | Docker Compose 标准化 + CI 自动化 |
| R5 | 插件市场审核人力不足 | 低 | 高 | 🟡 | 自动化安全扫描 + 社区协作审核 |
| R6 | 性能回归未被及时发现 | 中 | 低 | 🟢 | 基准测试 + CI 自动告警 |
| R7 | 第三方依赖安全漏洞 | 高 | 低 | 🟡 | dependabot + pip-audit 自动扫描 |

### 8.2 阶段依赖图

```
Phase Ⅰ (涅槃·秩序重生)
  │ 产出: 统一异常 + 代码规范 + v0.9.0-rc1
  │
  └──→ Phase Ⅱ (觉醒·万物有灵)
        │ 产出: 意图引擎 + 六大领域网络 + 三级流水线
        │ 依赖: Phase Ⅰ 统一异常体系
        │
        └──→ Phase Ⅲ (破界·全平台征服)
              │ 产出: 跨平台 Office + CLI 发现 + 多平台 CI
              │ 依赖: Phase Ⅱ 意图注册机制
              │
              └──→ Phase Ⅳ (铸盾·生产就绪) 🎉 v1.0.0
                    │ 产出: 集成测试铁幕 + 性能基准 + 正式发布
                    │ 依赖: Phase Ⅲ 稳定跨平台适配器
                    │
                    ├──→ Phase Ⅴ (锻剑·适配器淬炼) v1.1.0
                    │     产出: 5 大适配器 L2→L3 升级
                    │     依赖: Phase Ⅳ 测试基础设施
                    │
                    └──→ Phase Ⅵ (星火·生态燎原) v1.2.0+
                          产出: 插件系统 + 市场 + 社区
                          依赖: Phase Ⅴ 高质量适配器作范例
```

### 8.3 资源估算

| 阶段 | 开发(d) | 测试(d) | 文档(d) | 总计(d) | 建议人力 | 并行策略 |
|------|:--:|:--:|:--:|:--:|:--:|------|
| Ⅰ 涅槃 | 8 | 3 | 2 | 13 | 2人 | 版本校准 + 错误统一可部分并行 |
| Ⅱ 觉醒 | 16 | 5 | 3 | 24 | 2-3人 | 6大领域可并行开发 |
| Ⅲ 破界 | 11 | 4 | 2 | 17 | 2人 | 3个Office后端可并行 |
| Ⅳ 铸盾 | 10 | 7 | 3 | 20 | 2-3人 | 5组集成测试可并行；安全加固与测试并行 |
| Ⅴ 锻剑 | 11 | 4 | 1 | 16 | 2人 | 6个适配器可并行重构 |
| Ⅵ 星火 | 18 | 6 | 6 | 30 | 3人 | 插件+市场+社区多线并行 |
| **总计** | **74** | **29** | **17** | **120** | | |

---

## 9. 附录

### 附录 A: 术语表

| 术语 | 定义 |
|------|------|
| **Adapter (适配器)** | 封装外部工具/服务的统一接口模块 |
| **Intent Pattern (意图模式)** | 自然语言到工具调用的映射规则 |
| **Slot (槽位)** | 意图中的可提取参数（如文件路径、格式） |
| **L1/L2/L3** | 意图解析三级流水线: 精确匹配 / 语义路由 / LLM 回退 |
| **Domain (领域)** | 意图六大分类: browser / office / media / devops / collab / webtools |
| **MCP** | Model Context Protocol — AI 与工具通信的开放协议 |
| **A2A** | Agent-to-Agent — Google 提出的跨 Agent 通信协议 |
| **PBAC** | Policy-Based Access Control — 基于策略的访问控制 |
| **DAG** | Directed Acyclic Graph — 多适配器有向无环图编排 |
| **Plugin (插件)** | 第三方开发的适配器扩展包 |

### 附录 B: 文件变更总索引

| Phase | 新建文件 | 修改文件 | 删除文件 | 新增代码行 (含测试) |
|------|:--:|:--:|:--:|:--:|
| Ⅰ 涅槃 | 2 | ~10 | 0 | ~500 |
| Ⅱ 觉醒 | 10 | ~25 | 0 | ~3,500 |
| Ⅲ 破界 | 8 | 5 | 0 | ~2,200 |
| Ⅳ 铸盾 | 21 | 10 | 0 | ~4,500 |
| Ⅴ 锻剑 | 3 | 7 | 0 | ~3,000 |
| Ⅵ 星火 | 22 | 2 | 0 | ~6,600 |
| **总计** | **66** | **~59** | **0** | **~20,300** |

### 附录 C: 版本兼容性矩阵

| 版本 | Python | OS | 破坏性变更 |
|------|------|------|------|
| v0.9.0-rc1 | 3.10-3.12 | Windows | 无（首个 RC） |
| v0.10.0 | 3.10-3.12 | Windows | 意图引擎 API 重构 |
| v0.11.0 | 3.10-3.12 | Win/Mac/Linux | Office 适配器底层重写 |
| v1.0.0 | 3.10-3.12 | Win/Mac/Linux | ⚠️ 旧字典错误模式移除 |
| v1.1.0 | 3.10-3.12 | Win/Mac/Linux | 适配器方法签名扩展（向后兼容） |
| v1.2.0+ | 3.10-3.13 | Win/Mac/Linux | 插件系统引入 |

### 附录 D: 评审记录

| 日期 | 评审人 | 版本 | 意见摘要 | 状态 |
|------|------|------|------|:--:|
| 2026-05-07 | — | v2.0 | 初始规格说明书发布 | 待评审 |

---

> **文档维护**: 本文档随开发进度持续更新。每个 Phase 完成后，更新对应章节的任务状态（⬜ → ✅ 或 ❌），记录实际工时与偏差原因。
>
> **最后更新**: 2026-05-07 | **下次评审**: Phase Ⅰ 完成后 (预计 W2)
>
> *AI-Bridge 首席架构师 · 2026年5月 · 《从混沌到星辰》开发规格说明书 v2.0*
