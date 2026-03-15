"""
协议桥接器

实现 MCP ↔ A2A 双向协议互转：
- MCP → A2A: 将 MCP Tool 暴露为 A2A Agent 能力
- A2A → MCP: 将 A2A Agent 能力映射为 MCP Tool
- 统一的调用接口
- 追踪集成
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from .mcp_registry import MCPRegistry, ToolSchema
from .a2a_gateway import (
    A2AGateway, 
    AgentCard, 
    AgentCapability, 
    A2ATask, 
    TaskStatus
)

if TYPE_CHECKING:
    from ..enterprise.tracing import Tracer, TracingMiddleware

logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    """桥接配置"""
    # MCP → A2A 配置
    auto_expose_mcp_as_a2a: bool = True  # 自动将 MCP Tool 暴露为 A2A 能力
    mcp_agent_prefix: str = "mcp-"       # MCP 转 A2A 时的 Agent ID 前缀
    
    # A2A → MCP 配置
    auto_expose_a2a_as_mcp: bool = True  # 自动将 A2A Agent 暴露为 MCP Tool
    a2a_tool_prefix: str = "a2a-"        # A2A 转 MCP 时的 Tool 前缀
    
    # 追踪配置
    enable_tracing: bool = True          # 启用追踪


class ProtocolBridge:
    """
    协议桥接器
    
    连接 MCP 和 A2A 两个协议世界，实现双向互操作：
    
    1. MCP → A2A: 将 MCP Server 的 Tool 暴露为 A2A Agent 的能力
       - 每个 MCP Server 对应一个虚拟 A2A Agent
       - MCP Tool 对应 A2A Capability
       
    2. A2A → MCP: 将 A2A Agent 的能力暴露为 MCP Tool
       - 每个 A2A Agent 对应一组虚拟 MCP Tool
       - A2A Capability 对应 MCP Tool
    
    使用示例：
    ```python
    mcp_registry = MCPRegistry()
    a2a_gateway = A2AGateway()
    bridge = ProtocolBridge(mcp_registry, a2a_gateway)
    
    # 双向暴露
    await bridge.expose_all_mcp_as_a2a()
    await bridge.expose_all_a2a_as_mcp()
    
    # MCP → A2A: 通过 A2A 协议调用 MCP Tool
    task = A2ATask(
        from_agent="orchestrator",
        to_agent="mcp-browser-use",
        capability="navigate",
        input_data={"url": "https://example.com"}
    )
    
    # A2A → MCP: 通过 MCP 协议调用 A2A Agent
    result = await bridge.call_a2a_via_mcp(
        "a2a-search-agent",
        "search",
        {"query": "AI news"}
    )
    ```
    """
    
    def __init__(
        self, 
        mcp_registry: MCPRegistry, 
        a2a_gateway: A2AGateway,
        config: Optional[BridgeConfig] = None,
        tracer: Optional["Tracer"] = None,
    ):
        self._mcp = mcp_registry
        self._a2a = a2a_gateway
        self._config = config or BridgeConfig()
        self._tracer = tracer
        
        # 映射关系
        self._mcp_agents: Dict[str, str] = {}  # mcp_server_name -> a2a_agent_id
        self._a2a_tools: Dict[str, str] = {}   # a2a_agent_id -> mcp_tool_prefix
        
        # 统计
        self._stats = {
            "mcp_to_a2a_calls": 0,
            "a2a_to_mcp_calls": 0,
            "errors": 0,
        }
    
    def mcp_to_a2a_capability(self, tool: ToolSchema) -> AgentCapability:
        """
        将 MCP Tool 转换为 A2A 能力描述
        
        Args:
            tool: MCP Tool Schema
            
        Returns:
            AgentCapability: A2A 能力描述
        """
        return AgentCapability(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            output_schema=None,  # MCP 通常不定义输出 schema
        )
    
    def mcp_server_to_a2a_agent(self, server_name: str, tools: List[ToolSchema]) -> AgentCard:
        """
        将 MCP Server 转换为 A2A Agent
        
        Args:
            server_name: MCP Server 名称
            tools: Server 提供的工具列表
            
        Returns:
            AgentCard: A2A Agent 名片
        """
        agent_id = f"{self._config.mcp_agent_prefix}{server_name}"
        
        return AgentCard(
            agent_id=agent_id,
            name=f"MCP: {server_name}",
            description=f"A2A Agent bridged from MCP Server '{server_name}'",
            capabilities=[self.mcp_to_a2a_capability(tool) for tool in tools],
            metadata={
                "bridge_type": "mcp_to_a2a",
                "mcp_server": server_name,
            }
        )
    
    async def expose_mcp_as_a2a(self, server_name: str) -> Optional[AgentCard]:
        """
        将指定 MCP Server 暴露为 A2A Agent
        
        Args:
            server_name: MCP Server 名称
            
        Returns:
            创建的 AgentCard，如果 Server 不存在则返回 None
        """
        proxy = await self._mcp.get(server_name)
        if not proxy:
            logger.warning(f"MCP Server {server_name} not found")
            return None
        
        if not proxy.is_connected:
            logger.warning(f"MCP Server {server_name} is not connected")
            return None
        
        # 获取工具列表
        tools = await proxy.list_tools()
        
        # 创建虚拟 Agent
        agent_card = self.mcp_server_to_a2a_agent(server_name, tools)
        
        # 注册到 A2A Gateway
        await self._a2a.register_agent(agent_card)
        
        # 记录映射
        self._mcp_agents[server_name] = agent_card.agent_id
        
        logger.info(f"Exposed MCP Server {server_name} as A2A Agent {agent_card.agent_id}")
        return agent_card
    
    async def expose_all_mcp_as_a2a(self) -> List[AgentCard]:
        """
        将所有 MCP Server 暴露为 A2A Agent
        
        Returns:
            创建的 AgentCard 列表
        """
        cards = []
        for server_name in await self._mcp.list_servers():
            card = await self.expose_mcp_as_a2a(server_name)
            if card:
                cards.append(card)
        return cards
    
    def a2a_task_to_mcp_call(self, task: A2ATask) -> Dict[str, Any]:
        """
        将 A2A 任务转换为 MCP 调用参数
        
        Args:
            task: A2A 任务
            
        Returns:
            MCP 调用参数 {"server": str, "tool": str, "params": dict}
        """
        # 检查是否是 MCP 桥接的 Agent
        agent_id = task.to_agent
        if not agent_id.startswith(self._config.mcp_agent_prefix):
            raise ValueError(f"Agent {agent_id} is not a bridged MCP agent")
        
        # 提取 MCP Server 名称
        server_name = agent_id[len(self._config.mcp_agent_prefix):]
        
        return {
            "server": server_name,
            "tool": task.capability,
            "params": task.input_data,
        }
    
    async def route_a2a_to_mcp(self, task: A2ATask) -> Any:
        """
        将 A2A 任务路由到 MCP Server 执行
        
        Args:
            task: A2A 任务
            
        Returns:
            执行结果
        """
        # 转换参数
        mcp_call = self.a2a_task_to_mcp_call(task)
        
        # 调用 MCP Tool
        result = await self._mcp.call_tool(
            mcp_call["server"],
            mcp_call["tool"],
            mcp_call["params"]
        )
        
        return result
    
    async def execute_task(self, task: A2ATask) -> Any:
        """
        执行任务（自动判断路由）
        
        Args:
            task: A2A 任务
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        try:
            # 检查目标 Agent 是否是 MCP 桥接的
            if task.to_agent.startswith(self._config.mcp_agent_prefix):
                # 路由到 MCP
                self._stats["mcp_to_a2a_calls"] += 1
                return await self.route_a2a_to_mcp(task)
            else:
                # 原生 A2A Agent，使用 A2A Gateway
                handle = await self._a2a.send_task(task)
                return await handle.wait_for_completion()
        except Exception as e:
            self._stats["errors"] += 1
            raise
    
    # ===== A2A → MCP 双向转换 =====
    
    def a2a_capability_to_mcp_tool(self, agent_id: str, cap: AgentCapability) -> ToolSchema:
        """
        将 A2A 能力转换为 MCP Tool Schema
        
        Args:
            agent_id: A2A Agent ID
            cap: A2A 能力
            
        Returns:
            ToolSchema: MCP Tool 描述
        """
        tool_name = f"{self._config.a2a_tool_prefix}{agent_id}/{cap.name}"
        
        return ToolSchema(
            name=tool_name,
            description=f"[A2A Bridge] {cap.description or cap.name}",
            input_schema=cap.input_schema or {"type": "object", "properties": {}},
        )
    
    def a2a_agent_to_mcp_tools(self, agent_card: AgentCard) -> List[ToolSchema]:
        """
        将 A2A Agent 转换为 MCP Tool 列表
        
        Args:
            agent_card: A2A Agent 名片
            
        Returns:
            MCP Tool 列表
        """
        return [
            self.a2a_capability_to_mcp_tool(agent_card.agent_id, cap)
            for cap in agent_card.capabilities
        ]
    
    async def expose_a2a_as_mcp(self, agent_id: str) -> List[ToolSchema]:
        """
        将指定 A2A Agent 暴露为 MCP Tool
        
        Args:
            agent_id: A2A Agent ID
            
        Returns:
            创建的 MCP Tool 列表
        """
        agent_card = await self._a2a.get_agent(agent_id)
        if not agent_card:
            logger.warning(f"A2A Agent {agent_id} not found")
            return []
        
        # 创建虚拟 MCP Tools
        tools = self.a2a_agent_to_mcp_tools(agent_card)
        
        # 记录映射
        self._a2a_tools[agent_id] = self._config.a2a_tool_prefix
        
        logger.info(f"Exposed A2A Agent {agent_id} as {len(tools)} MCP tools")
        return tools
    
    async def expose_all_a2a_as_mcp(self) -> List[ToolSchema]:
        """
        将所有 A2A Agent 暴露为 MCP Tool
        
        Returns:
            创建的 MCP Tool 列表
        """
        all_tools = []
        for agent_id in await self._a2a.list_agents():
            tools = await self.expose_a2a_as_mcp(agent_id)
            all_tools.extend(tools)
        return all_tools
    
    def mcp_tool_to_a2a_task(self, tool_name: str, params: Dict[str, Any]) -> A2ATask:
        """
        将 MCP Tool 调用转换为 A2A 任务
        
        Args:
            tool_name: MCP Tool 名称 (a2a-agent_id/capability)
            params: 调用参数
            
        Returns:
            A2ATask
        """
        if not tool_name.startswith(self._config.a2a_tool_prefix):
            raise ValueError(f"Tool {tool_name} is not an A2A bridged tool")
        
        # 解析 tool_name: a2a-agent_id/capability
        remainder = tool_name[len(self._config.a2a_tool_prefix):]
        parts = remainder.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid A2A tool name format: {tool_name}")
        
        agent_id, capability = parts
        
        return A2ATask(
            from_agent="mcp-bridge",
            to_agent=agent_id,
            capability=capability,
            input_data=params,
        )
    
    async def call_a2a_via_mcp(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Any:
        """
        通过 MCP 协议调用 A2A Agent
        
        Args:
            tool_name: MCP Tool 名称
            params: 调用参数
            
        Returns:
            执行结果
        """
        self._stats["a2a_to_mcp_calls"] += 1
        
        try:
            # 转换为 A2A 任务
            task = self.mcp_tool_to_a2a_task(tool_name, params)
            
            # 发送并等待结果
            handle = await self._a2a.send_task(task)
            return await handle.wait_for_completion()
            
        except Exception as e:
            self._stats["errors"] += 1
            raise
    
    def is_bridged_tool(self, tool_name: str) -> bool:
        """检查是否是桥接的 Tool"""
        return tool_name.startswith(self._config.a2a_tool_prefix)
    
    def is_bridged_agent(self, agent_id: str) -> bool:
        """检查是否是桥接的 Agent"""
        return agent_id.startswith(self._config.mcp_agent_prefix)
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """获取桥接状态"""
        return {
            "mcp_agents": self._mcp_agents,
            "a2a_tools": self._a2a_tools,
            "stats": self._stats,
            "config": {
                "mcp_to_a2a": {
                    "auto_expose": self._config.auto_expose_mcp_as_a2a,
                    "prefix": self._config.mcp_agent_prefix,
                },
                "a2a_to_mcp": {
                    "auto_expose": self._config.auto_expose_a2a_as_mcp,
                    "prefix": self._config.a2a_tool_prefix,
                },
                "tracing": self._config.enable_tracing,
            }
        }
