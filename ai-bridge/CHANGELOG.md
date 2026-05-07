# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 铸盾·生产就绪 (2026-05-07)

### Phase IV 变更

### Added
- 🧪 **分层测试金字塔**: L0 单元(907) / L1 组件(22) / L2 集成(7) / L3 E2E(8) 四级测试体系
- **pytest 分层标记基础设施** (`tests/conftest.py`): --integration / --e2e / --perf CLI 开关
- **L1 组件测试**: intent_pipeline, dag_orchestrator, protocol_bridge, pbac_engine
- **L2 集成测试**: office_real (docx/pdf/xlsx/ppt), git_real (init/status/commit)
- **L3 E2E 测试**: full_chain (自然语言→适配器), performance (延时/冷启动/批量注册)
- 🛡️ **铁幕 CI 管线** (`.github/workflows/iron-curtain.yml`): L0 lint+unit / L2 docker-integration / L3 nightly E2E / L4 benchmark
- 📊 **性能回归检测**: `scripts/check_benchmark_regression.py` (微基准 + 阈值告警)

### Changed
- 版本号升级至 `1.0.0` (正式发布)
- 安全审查 9/9 项确认为前期已完成
- SUPER_EVOLUTION_PLAN.md 更新至 Phase IV 完成状态

---

## [0.9.0-rc1] — 涅槃·秩序重生 (2026-05-07)

### 史诗回溯

本版本合并了 v1.0 → v5.0 的历史演进，以下是里程碑摘要：

#### v5.0 企业级能力 (2026 Q1)
- **新增**: PBAC 策略引擎 (`enterprise/policy.py`, ~400行)
- **新增**: Metering 计量系统 (`enterprise/metering.py`, `metering_prometheus.py`)
- **新增**: Audit 审计日志 (`enterprise/audit.py`, `audit_log.py`)
- **新增**: Rate Limiting (`enterprise/rate_limit.py`)
- **新增**: OpenTelemetry 全链路追踪 (`enterprise/tracing.py`)
- **新增**: Health Check 端点 (`enterprise/health.py`)
- **新增**: CLI 工具 (`cli/doctor.py`, `cli/init_wizard.py`)
- **新增**: Docker 支持 (Dockerfile, docker-compose.yml)
- **新增**: 全面安全审计与加固 (22 项 P0-P3 修复)
- **新增**: CSS 选择器验证 (42 项安全测试)
- **新增**: 速率限制与密钥管理工具 (`utils/security.py`)

#### v4.0 协议扩展 (2025 Q4)
- **新增**: A2A Gateway (`gateway/a2a_gateway.py`, `protocol_bridge.py`)
- **新增**: Agent Card 发布与发现 (`gateway/agent_card.py`, `card_publisher.py`, `card_discovery.py`)
- **新增**: MCP Registry (`gateway/mcp_registry.py`, `mcp_discovery.py`)
- **新增**: Prometheus 指标导出 (`enterprise/prometheus.py`)
- **新增**: A2A Streaming (`registry/a2a_streaming.py`)
- **新增**: Agent Registry (`registry/agent_registry.py`)

#### v3.0 核心重构 (2025 Q3)
- **新增**: IntentEngine 意图引擎 (`core/intent_engine.py`)
- **新增**: Batch Executor (`core/batch_executor.py`)
- **新增**: Smart Wait (`core/smart_wait.py`)
- **新增**: Multi-modal 支持 (`core/multimodal.py`)
- **新增**: LLM Provider 抽象层 (`core/llm_provider.py`)
- **新增**: 统一异常体系 (`core/exceptions.py`)

#### v2.0 适配器扩展 (2025 Q2)
- **新增**: CLI 适配器体系 (aider, blender, docker, ffmpeg, gimp, imagemagick, libreoffice, pandoc, playwright, prettier, shotcut)
- **新增**: Browser 适配器 (chrome.py, edge.py)
- **新增**: Office 适配器 (word, excel, ppt)
- **新增**: MCP 连接器 (HTTP/SSE/stdio)

#### v1.0 基础框架 (2025 Q1)
- **新增**: MCP Server (`server/mcp_server.py`, `mcp_tools.py`)
- **新增**: 核心配置系统 (`core/config.py`, `adapter_config.py`)
- **新增**: Session Manager (`core/session_manager.py`)
- **新增**: 安全模块 (`core/security.py`)

### Phase I 变更

### Changed
- 版本号从 `0.1.0-alpha` 校准为 `0.9.0-rc1`
- Python 最低版本提升至 3.10
- 依赖分组重构：`office-win`、`office-cross`、`browser`、`media`、`dev`、`all`
- 统一异常体系扩展为 6 类 17 子类，含结构化错误码
- ruff 配置升级，新增 SIM/TCH 规则 + isort/format 配置

### Added
- 旧字典错误兼容层 (`core/legacy_error_wrapper.py`)
- 错误迁移回归测试 (`tests/test_error_migration.py`)
- CODEOWNERS 模块归属声明 (`.github/CODEOWNERS`)

### Fixed
- `core/config.py` `from_dict` 方法副作用修复 (pop → get)
- `server/mcp_server.py` 重复属性定义清理
- `core/manager.py` 异常吞噬添加日志、重复注册检查
- `core/session_manager.py` 封装破坏修复

---

## Release Notes Format

### Added — New features
### Changed — Changes in existing functionality
### Deprecated — Soon-to-be removed features
### Removed — Now removed features
### Fixed — Bug fixes
### Security — Security improvements
