<div align="center">

```
     _    ___      ____       _     _            
    / \  |_ _|    | __ ) _ __(_) __| | __ _  ___ 
   / _ \  | |_____|  _ \| '__| |/ _` |/ _` |/ _ \
  / ___ \ | |_____| |_) | |  | | (_| | (_| |  __/
 /_/   \_\___|    |____/|_|  |_|\__,_|\__, |\___|
                                      |___/      
```

# 🌉 AI-Bridge

### **MCP + A2A 双协议网关**
### **MCP + A2A Dual Protocol Gateway**

<br/>

[![License](https://img.shields.io/badge/许可证-Apache%202.0-blue.svg?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-兼容-00D084?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-欢迎-brightgreen?style=for-the-badge)](CONTRIBUTING.md)

<br/>

<!-- 🔥 新功能横幅 -->
<table>
<tr>
<td>

```diff
🚀 v5.0.0 协议扩展与企业级可观测性！
+ Agent Card - A2A 标准 Agent 发现与注册
+ Prometheus 指标 - /metrics 端点导出工具/Agent/系统统计
+ Agent Registry - 集中式 Agent 管理与负载均衡
+ A2A Streaming - SSE/WebSocket 实时流式通信
+ 审计日志持久化 - SQLite/文件/内存多后端存储
+ MCP Server 动态发现 - 自动检测 Claude Desktop 服务器
+ 647+ 测试 - 企业级测试覆盖
+ 安全加固 - 通过全面安全审计

🎉 v4.0.0 企业管理层！
+ 策略引擎 - 工具级访问控制 (PBAC)
+ 计量系统 - 使用跟踪与成本估算
+ 分布式追踪 - OpenTelemetry 兼容
+ 多 Agent 编排 - DAG 任务调度

🔧 v3.0.0 协议网关架构发布！
+ MCP + A2A 双协议网关 - 统一 AI 工具入口
+ Browser Connector - 代理 Browser Use, Chrome DevTools, Playwright
+ 企业级特性 - 认证、审计、限流、健康检查
```

</td>
</tr>
</table>

<br/>

**🚀 一个网关，双协议支持，无限可能**

<br/>

[📖 English](README.md) • [🎯 功能特性](#-核心能力) • [🏗️ 系统架构](#️-系统架构) • [🚀 快速开始](#-快速开始)

---

</div>

<br/>

## 🔥 为什么选择 AI-Bridge？

<table>
<tr>
<td width="50%">

### ❌ 传统方案

```
每个 AI 工具 → 不同协议 → 不同集成方式
        ↓
   🐢 集成慢
   💥 生态碎片化
   🎯 API 不一致
   🌍 无法互通
```

</td>
<td width="50%">

### ✅ AI-Bridge 方案

```
任意 AI 工具 → AI-Bridge 网关 → MCP 或 A2A 协议
        ↓
   ⚡ 统一入口
   🔒 协议互通
   🎯 一致体验
   🌍 企业就绪
```

</td>
</tr>
</table>

<br/>

## ⚡ 核心能力

<div align="center">

| 🔗 **协议网关** | 🤖 **全 AI 兼容** | 🌐 **浏览器连接器** | 🛠️ **CLI 工具** | 📊 **办公套件** | 🔐 **企业特性** | 🎯 **Agent注册** |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| MCP + A2A 双协议支持，统一入口 | Claude、GPT、千问、Gemini 等 | 代理 Browser Use、Chrome DevTools、Playwright | FFmpeg、Pandoc、yt-dlp、SoX、Prettier、Docker | Word、Excel、PPT、WPS | 认证、审计、限流 | Prometheus、流式通信 |

</div>

<br/>

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       🤖 AI 助手                             │
│           (Claude, GPT, 千问, Gemini, etc.)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP / A2A 协议
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              AI-Bridge v5.0 协议网关                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            协议扩展层 (v5.0)                             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │  Agent   │ │Prometheus│ │   A2A    │ │   MCP    │ │  │
│  │  │ 注册中心  │ │  指标导出 │ │ 流式通信  │ │ 动态发现  │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            企业管理层 (v4.0)                             │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │  策略    │ │   计量   │ │   追踪   │ │  编排器  │ │  │
│  │  │  引擎    │ │  采集器  │ │  (OTel)  │ │   (DAG)  │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MCP 注册中心 │  │ A2A 网关    │  │  协议桥接器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  认证中间件  │  │   审计日志   │  │   请求限流   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬───────────────┐
         ▼               ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Browser │     │  Office │     │   CLI   │     │   MCP   │
    │  连接器  │     │  适配器  │     │  适配器  │     │  生态   │
    └─────────┘     └─────────┘     └─────────┘     └─────────┘
```

<br/>

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install ai-bridge

# 完整安装（所有功能）
pip install ai-bridge[all]

# Docker 一键部署（推荐生产环境）
docker run -p 9090:9090 aibridge/server:v5.0
```

### 环境检查

```bash
# 运行环境诊断
python -m aibridge doctor

# 交互式配置向导
python -m aibridge init
```

### 作为 MCP Server（Claude Desktop 集成）

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "ai-bridge": {
      "command": "python",
      "args": ["-m", "aibridge"],
      "env": {
        "AIBRIDGE_CHROME_ENABLED": "true"
      }
    }
  }
}
```

### v3.0 协议网关使用

```python
import asyncio
from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
from aibridge.connectors.mcp.browser import BrowserBackend

async def main():
    # 1. 创建浏览器连接器（自动选择可用后端）
    config = BrowserConnectorConfig(
        name="browser",
        backend=BrowserBackend.AUTO,  # Browser Use, Chrome DevTools, 或 Playwright
        headless=True,
    )
    connector = BrowserConnector(config)
    
    async with connector:
        # 2. 导航到网站
        await connector.navigate("https://www.baidu.com")
        
        # 3. 在搜索框输入
        await connector.type("#kw", "AI-Bridge MCP 协议网关")
        
        # 4. 点击搜索按钮
        await connector.click("#su")
        
        # 5. 截图
        await connector.screenshot("result.png")

asyncio.run(main())
```

### 直接使用适配器

```python
import asyncio
from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.core.protocol import Target

async def main():
    adapter = ChromeAdapter({"headless": True})
    await adapter.connect()
    
    await adapter.execute(action="goto", value="https://github.com")
    await adapter.execute(action="screenshot", options={"path": "result.png"})
    
    await adapter.disconnect()

asyncio.run(main())
```

<br/>

## 🛠️ 支持的工具

### 浏览器自动化
- **Chrome** - 通过 Playwright 完全控制浏览器
- **Edge** - Microsoft Edge 自动化

### 办公套件
- **Word** - 文档创建和编辑
- **Excel** - 电子表格自动化
- **PowerPoint** - 演示文稿管理
- **WPS Office** - 国产办公套件支持

### CLI 工具适配器
- **FFmpeg** - 音视频处理
- **Pandoc** - 文档格式转换
- **yt-dlp** - 视频下载
- **ImageMagick** - 图片处理
- **Blender** - 3D 渲染
- **Playwright** - 浏览器自动化 CLI
- **SoX** - 音频处理（转换、剪辑、拼接、特效）
- **Prettier** - 代码格式化（多语言支持）
- **Docker** - 容器操作（镜像、容器、卷）

### MCP 生态连接器
- **Browser** - 代理到 Browser Use、Chrome DevTools MCP、Playwright MCP
- **Database** - PostgreSQL、MySQL、SQLite（通过 MCP）
- **Filesystem** - 文件操作（通过 MCP）
- **GitHub** - 仓库操作（通过 MCP）
- **SQLite** - 轻量数据库（查询、执行、表管理）
- **Firecrawl** - 网页抓取（抓取、爬取、搜索、提取）
- **Notion** - 团队协作（页面、数据库、内容块）
- **Slack** - 通讯集成（消息、频道、文件）

<br/>

## 🔐 企业级特性

```python
from aibridge.enterprise import AuthMiddleware, AuditLogger, RateLimiter

# 认证中间件（API Key + JWT）
auth = AuthMiddleware(secret_key="your-secret")
context = await auth.authenticate({"api_key": "key123"})

# 操作审计日志
audit = AuditLogger()
await audit.log("execute_tool", user_id="user1", data={"tool": "browser"})

# 请求限流
limiter = RateLimiter(default_limit=100, window_seconds=60)
await limiter.check("user1")  # 超限抛出 RateLimitExceeded
```

<br/>

## ⚙️ 命令行工具

```bash
# 查看版本
python -m aibridge --version

# 列出可用适配器
python -m aibridge --list-adapters

# 指定配置文件启动
python -m aibridge --config config.yaml

# 设置日志级别
python -m aibridge --log-level DEBUG
```

<br/>

## 📖 文档

| 资源 | 链接 |
|------|------|
| 📚 快速入门示例 | [examples/basic_usage.py](examples/basic_usage.py) |
| 🏗️ 网关演示 | [examples/gateway_demo.py](examples/gateway_demo.py) |
| 🤝 参与贡献 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 📝 更新日志 | [CHANGELOG.md](CHANGELOG.md) |

<br/>

## 🤝 参与贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
# 克隆仓库
git clone https://github.com/Louis830903/AI-Bridge.git
cd AI-Bridge/ai-bridge

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 提交 PR
```

<br/>

## 📜 许可证

Apache 2.0 — 详见 [LICENSE](LICENSE)

<br/>

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 浏览器自动化
- [MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [A2A](https://google.github.io/a2a-spec/) - Agent-to-Agent Protocol
- 所有 [贡献者](https://github.com/Louis830903/AI-Bridge/graphs/contributors) ❤️

<br/>

---

<div align="center">

### 🌟 给我们点个 Star 吧！

<br/>

**为 AI 自动化社区倾心打造 ❤️**

```
 █████╗ ██╗      ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
██╔══██╗██║      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
███████║██║█████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗  
██╔══██║██║╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝  
██║  ██║██║      ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝
                                                              
           一个网关，双协议支持，无限可能
```

</div>
