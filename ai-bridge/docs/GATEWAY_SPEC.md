# AI-Bridge v3.0 开发规范文档

> **战略定位**：AI Agent 生态的统一入口 —— MCP + A2A 双协议网关

---

## 1. 项目愿景

### 1.1 核心价值主张

```
"一次接入，调用所有工具"
"One Integration, Access Everything"
```

### 1.2 战略转型

| 维度 | 旧定位 (v2.x) | 新定位 (v3.0) |
|------|---------------|---------------|
| 核心能力 | 自研各类自动化实现 | 协议网关 + 生态整合 |
| 浏览器 | 自研 Playwright 封装 | 接入 Browser Use / Chrome DevTools MCP |
| 协议 | 仅 MCP | MCP + A2A 双协议 |
| 资产 | 代码实现 | 连接器生态 + CLI 工具库 |
| 护城河 | 技术实现（易被超越） | 生态粘性（难以复制） |

### 1.3 差异化定位

- **唯一双协议**：同时支持 MCP + A2A
- **最全工具库**：100+ MCP Server + CLI 工具
- **零自研负担**：底层能力来自成熟方案
- **企业级网关**：统一鉴权、审计、限流

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      AI Agents                               │
│         (Claude, GPT, Qwen, Gemini, Local LLMs)             │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   MCP Protocol  │     │   A2A Protocol  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI-Bridge Gateway                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Protocol Layer                       │   │
│  │   ┌─────────────┐   ┌─────────────┐   ┌───────────┐  │   │
│  │   │MCP Registry │   │ A2A Gateway │   │ Protocol  │  │   │
│  │   │             │   │             │   │  Bridge   │  │   │
│  │   └─────────────┘   └─────────────┘   └───────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Connector Layer                       │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │   │ Browser │  │Database │  │  Code   │  │  File   │ │   │
│  │   │Connector│  │Connector│  │Connector│  │Connector│ │   │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Adapter Layer (Native)                │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │   │
│  │   │  CLI    │  │ Office  │  │   IM    │  │ Desktop │ │   │
│  │   │Adapters │  │Adapters │  │Adapters │  │Adapters │ │   │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │Browser  │  │Postgres │  │ GitHub  │  │ Local CLI Tools │ │
│  │Use MCP  │  │  MCP    │  │  MCP    │  │ (FFmpeg, etc.)  │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
aibridge/
├── gateway/                    # 🆕 协议网关核心
│   ├── __init__.py
│   ├── mcp_registry.py        # MCP Server 注册中心
│   ├── a2a_gateway.py         # A2A 协议网关
│   ├── protocol_bridge.py     # MCP ↔ A2A 协议桥接
│   └── discovery.py           # 服务发现
│
├── connectors/                 # 🆕 外部服务连接器
│   ├── __init__.py
│   ├── base.py                # 连接器基类
│   └── mcp/                   # MCP Server 连接器
│       ├── __init__.py
│       ├── browser.py         # 浏览器 (Browser Use/DevTools)
│       ├── database.py        # 数据库 (Postgres/SQLite)
│       ├── filesystem.py      # 文件系统
│       ├── github.py          # GitHub
│       └── ...
│
├── adapters/                   # ✅ 保留：原生适配器
│   ├── cli/                   # ✅ 核心资产，继续扩展
│   │   ├── ffmpeg.py
│   │   ├── imagemagick.py
│   │   ├── pandoc.py
│   │   └── ...
│   ├── office/                # ✅ 保留，本地COM
│   ├── browser/               # ⚠️ Deprecated
│   ├── im/                    # ✅ 保留，降优先级
│   └── desktop/               # ✅ 保留
│
├── core/                      # ✅ 保留
├── server/                    # ✅ 保留并扩展
├── automation/                # ⚠️ 冻结，暂停开发
└── utils/                     # ✅ 保留
```

---

## 3. 核心模块设计

### 3.1 Gateway Layer

#### 3.1.1 MCPRegistry

```python
# gateway/mcp_registry.py
"""
MCP Server 注册中心
- 管理所有可用的 MCP Server
- 支持本地和远程 MCP Server
- 提供服务发现和健康检查
"""

class MCPRegistry:
    """MCP Server 注册与管理"""
    
    def register(self, name: str, config: MCPServerConfig) -> None:
        """注册 MCP Server"""
        
    def unregister(self, name: str) -> None:
        """注销 MCP Server"""
        
    def get(self, name: str) -> MCPServerProxy:
        """获取 MCP Server 代理"""
        
    def list_tools(self) -> List[ToolSchema]:
        """列出所有可用工具"""
        
    def call_tool(self, server: str, tool: str, params: dict) -> Any:
        """调用指定 Server 的工具"""
```

#### 3.1.2 A2AGateway

```python
# gateway/a2a_gateway.py
"""
A2A (Agent-to-Agent) 协议网关
- 实现 Google A2A 协议规范
- 支持 Agent 间任务委派和协作
- 提供任务状态同步和结果聚合
"""

class A2AGateway:
    """Agent-to-Agent 协议网关"""
    
    def register_agent(self, agent_id: str, agent_card: AgentCard) -> None:
        """注册 Agent 及其能力"""
        
    def discover_agents(self, capability: str) -> List[AgentCard]:
        """发现具备特定能力的 Agent"""
        
    def send_task(self, task: A2ATask) -> TaskHandle:
        """发送任务到目标 Agent"""
        
    def get_task_status(self, task_id: str) -> TaskStatus:
        """获取任务状态"""
        
    def subscribe_events(self, task_id: str) -> AsyncIterator[TaskEvent]:
        """订阅任务事件流"""
```

#### 3.1.3 ProtocolBridge

```python
# gateway/protocol_bridge.py
"""
协议桥接器
- MCP Tool 暴露为 A2A 能力
- A2A Agent 可调用 MCP Tool
"""

class ProtocolBridge:
    """MCP ↔ A2A 协议桥接"""
    
    def mcp_to_a2a_capability(self, tool: ToolSchema) -> AgentCapability:
        """将 MCP Tool 转换为 A2A 能力描述"""
        
    def a2a_task_to_mcp_call(self, task: A2ATask) -> MCPToolCall:
        """将 A2A 任务转换为 MCP 调用"""
```

### 3.2 Connector Layer

#### 3.2.1 连接器基类

```python
# connectors/base.py
"""
MCP 连接器基类
- 定义统一的连接器接口
- 处理 MCP Server 生命周期
- 提供错误处理和重试机制
"""

class MCPConnector(ABC):
    """MCP Server 连接器基类"""
    
    @abstractmethod
    async def start(self) -> None:
        """启动 MCP Server"""
        
    @abstractmethod
    async def stop(self) -> None:
        """停止 MCP Server"""
        
    @abstractmethod
    async def list_tools(self) -> List[ToolSchema]:
        """获取工具列表"""
        
    @abstractmethod
    async def call_tool(self, name: str, params: dict) -> Any:
        """调用工具"""
```

#### 3.2.2 浏览器连接器

```python
# connectors/mcp/browser.py
"""
浏览器连接器
- 优先级：Browser Use > Chrome DevTools MCP > Playwright MCP
- 自动选择可用后端
- 提供统一的浏览器操作接口
"""

class BrowserConnector(MCPConnector):
    """浏览器 MCP 连接器"""
    
    BACKENDS = [
        ("browser-use", "npx @anthropic/browser-use-mcp"),
        ("chrome-devtools", "npx @anthropic/chrome-devtools-mcp"),
        ("playwright", "npx @anthropic/playwright-mcp"),
    ]
    
    async def navigate(self, url: str) -> None:
        """导航到 URL"""
        
    async def click(self, selector: str) -> None:
        """点击元素"""
        
    async def type(self, selector: str, text: str) -> None:
        """输入文本"""
        
    async def screenshot(self, path: str = None) -> bytes:
        """截图"""
```

---

## 4. 实施计划

### 4.1 Phase 1：基础设施 (Week 1-2)

#### 目标
- 创建 gateway/ 和 connectors/ 目录结构
- 实现 MCPRegistry 基础版
- 实现第一个 MCP 连接器 (Browser)

#### 任务清单

| ID | 任务 | 优先级 | 预估时间 |
|----|------|--------|----------|
| P1-01 | 创建 gateway/ 目录及基础文件 | P0 | 2h |
| P1-02 | 创建 connectors/ 目录及基础文件 | P0 | 2h |
| P1-03 | 实现 MCPConnector 基类 | P0 | 4h |
| P1-04 | 实现 MCPRegistry 基础版 | P0 | 8h |
| P1-05 | 实现 BrowserConnector | P0 | 8h |
| P1-06 | 接入 Browser Use MCP 验证 | P0 | 4h |
| P1-07 | 接入 Chrome DevTools MCP | P1 | 4h |
| P1-08 | 单元测试 | P1 | 4h |
| P1-09 | adapters/browser 添加 deprecated 警告 | P2 | 1h |

#### 交付物
- [ ] `gateway/__init__.py`
- [ ] `gateway/mcp_registry.py`
- [ ] `connectors/__init__.py`
- [ ] `connectors/base.py`
- [ ] `connectors/mcp/__init__.py`
- [ ] `connectors/mcp/browser.py`
- [ ] 测试用例

### 4.2 Phase 2：A2A 协议支持 (Week 3-4)

#### 目标
- 实现 A2A 协议基础支持
- 实现 MCP ↔ A2A 协议桥接
- 验证多 Agent 协作场景

#### 任务清单

| ID | 任务 | 优先级 | 预估时间 |
|----|------|--------|----------|
| P2-01 | A2A 协议规范研究 | P0 | 4h |
| P2-02 | 实现 AgentCard 数据结构 | P0 | 2h |
| P2-03 | 实现 A2AGateway 基础版 | P0 | 12h |
| P2-04 | 实现 ProtocolBridge | P0 | 8h |
| P2-05 | A2A 任务委派功能 | P1 | 8h |
| P2-06 | A2A 事件流支持 | P1 | 4h |
| P2-07 | 多 Agent 协作示例 | P1 | 4h |
| P2-08 | 集成测试 | P1 | 4h |

#### 交付物
- [ ] `gateway/a2a_gateway.py`
- [ ] `gateway/protocol_bridge.py`
- [ ] `gateway/models/a2a.py` (数据模型)
- [ ] A2A 集成测试
- [ ] 多 Agent 协作示例

### 4.3 Phase 3：生态扩展 (Week 5-8)

#### 目标
- 扩展 MCP 连接器生态
- 扩展 CLI 适配器
- 完善文档和示例

#### 优先接入的 MCP Server

| 类别 | MCP Server | 优先级 | 价值 |
|------|------------|--------|------|
| 浏览器 | Browser Use MCP | P0 | 最强开源方案 |
| 浏览器 | Chrome DevTools MCP | P0 | 官方支持 |
| 数据库 | PostgreSQL MCP | P1 | 企业刚需 |
| 数据库 | SQLite MCP | P1 | 轻量方案 |
| 开发 | GitHub MCP | P1 | 开发者生态 |
| 文件 | Filesystem MCP | P1 | 基础能力 |
| 搜索 | Firecrawl MCP | P2 | 网页抓取 |
| 协作 | Notion MCP | P2 | 团队协作 |

#### CLI 适配器扩展

| 类别 | 工具 | 优先级 | 当前状态 |
|------|------|--------|----------|
| 视频 | FFmpeg | - | ✅ 已有 |
| 视频 | Shotcut | - | ✅ 已有 |
| 图像 | ImageMagick | - | ✅ 已有 |
| 图像 | GIMP | - | ✅ 已有 |
| 3D | Blender | - | ✅ 已有 |
| 文档 | Pandoc | - | ✅ 已有 |
| 下载 | yt-dlp | - | ✅ 已有 |
| 代码 | Aider | - | ✅ 已有 |
| 音频 | sox | P1 | 🆕 待开发 |
| 格式化 | prettier | P2 | 🆕 待开发 |
| 容器 | docker-cli | P2 | 🆕 待开发 |

### 4.4 Phase 4：企业级特性 (Week 9-12)

#### 目标
- 统一鉴权和权限控制
- 操作审计日志
- 性能监控和限流

#### 任务清单

| ID | 任务 | 优先级 |
|----|------|--------|
| P4-01 | 统一认证中间件 | P1 |
| P4-02 | 细粒度权限控制 | P1 |
| P4-03 | 操作审计日志 | P1 |
| P4-04 | 性能指标收集 | P2 |
| P4-05 | 请求限流 | P2 |
| P4-06 | 健康检查端点 | P2 |

---

## 5. 模块处理决策

### 5.1 保留模块

| 模块 | 原因 | 后续计划 |
|------|------|----------|
| `adapters/cli/` | 核心资产，10个成熟适配器 | 继续扩展 |
| `adapters/office/` | 本地 COM，无替代方案 | 按需维护 |
| `adapters/im/` | 13个平台，有独立价值 | 降优先级维护 |
| `adapters/desktop/` | UI Automation 基础能力 | 按需维护 |
| `core/` | 核心基础设施 | 按需扩展 |
| `server/` | MCP Server 实现 | 集成 gateway |
| `utils/` | 工具函数 | 保持不变 |

### 5.2 Deprecated 模块

| 模块 | 原因 | 迁移路径 |
|------|------|----------|
| `adapters/browser/` | 自研实现有 BUG，成熟方案更好 | → `connectors/mcp/browser.py` |

### 5.3 冻结模块

| 模块 | 原因 | 后续计划 |
|------|------|----------|
| `automation/` | 养号引擎，战略优先级调整 | 待新架构稳定后重新评估 |

---

## 6. 接口兼容性

### 6.1 向后兼容承诺

- `adapters/cli/*` 所有接口保持不变
- `adapters/office/*` 所有接口保持不变
- `server/mcp_server.py` 对外接口保持不变

### 6.2 Deprecated 处理

```python
# adapters/browser/__init__.py
import warnings

def __getattr__(name):
    warnings.warn(
        f"aibridge.adapters.browser.{name} is deprecated since v3.0. "
        f"Use aibridge.connectors.mcp.browser instead. "
        f"This module will be removed in v4.0.",
        DeprecationWarning,
        stacklevel=2
    )
    # 返回兼容层，内部代理到新实现
    from aibridge.connectors.mcp.browser import BrowserConnector
    return BrowserConnector
```

---

## 7. 版本规划

| 版本 | 里程碑 | 预计时间 |
|------|--------|----------|
| v3.0.0-alpha | Phase 1 完成，Browser 连接器可用 | Week 2 |
| v3.0.0-beta | Phase 2 完成，A2A 协议可用 | Week 4 |
| v3.0.0-rc | Phase 3 完成，生态扩展 | Week 8 |
| v3.0.0 | Phase 4 完成，企业级特性 | Week 12 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| MCP Server 不稳定 | 功能不可用 | 多后端备选，自动切换 |
| A2A 协议变更 | 需要重新适配 | 抽象协议层，减少耦合 |
| 生态扩展慢 | 竞争力不足 | 优先接入高价值工具 |
| 旧用户迁移 | 用户流失 | 保持向后兼容，提供迁移指南 |

---

## 9. 成功指标

| 指标 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| MCP 连接器数量 | 2 | 2 | 8+ | 15+ |
| A2A 功能 | - | 基础可用 | 完善 | 生产级 |
| 测试覆盖率 | 70% | 75% | 80% | 85% |
| 文档完整度 | 基础 | 完善 | 完善 | 完善 |

---

## 10. 附录

### 10.1 参考资料

- [MCP Protocol Specification](https://modelcontextprotocol.io/docs)
- [A2A Protocol Specification](https://github.com/a2aproject/A2A)
- [Browser Use GitHub](https://github.com/browser-use/browser-use)
- [Chrome DevTools MCP](https://github.com/anthropics/mcp-chrome-devtools)

### 10.2 相关文档

- [CONTRIBUTING.md](../CONTRIBUTING.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [README.md](../README.md)

---

**文档版本**: v1.0.0  
**创建日期**: 2026-03-15  
**最后更新**: 2026-03-15  
**维护者**: AI-Bridge Team
