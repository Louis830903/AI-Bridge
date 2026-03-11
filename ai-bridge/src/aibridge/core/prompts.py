"""
MCP Prompts - Prompts support for MCP protocol
MCP 提示词模块 - 提供预定义提示词模板
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ArgumentType(str, Enum):
    """参数类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


@dataclass
class PromptArgument:
    """提示词参数"""
    name: str
    description: str = ""
    required: bool = True
    type: ArgumentType = ArgumentType.STRING
    default: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class PromptMessage:
    """提示词消息"""
    role: str  # "user" or "assistant"
    content: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": {"type": "text", "text": self.content}
        }


@dataclass
class Prompt:
    """
    MCP 提示词定义
    
    提示词是预定义的对话模板，帮助 AI 理解特定任务。
    """
    name: str
    description: str = ""
    arguments: List[PromptArgument] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [arg.to_dict() for arg in self.arguments],
        }
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        """
        生成消息（子类应覆盖此方法）
        
        Args:
            args: 参数字典
            
        Returns:
            消息列表
        """
        raise NotImplementedError("Subclasses must implement generate_messages")


class BrowserAutomationPrompt(Prompt):
    """浏览器自动化提示词"""
    
    def __init__(self):
        super().__init__(
            name="browser_automation",
            description="Automate browser tasks like navigation, clicking, and form filling",
            arguments=[
                PromptArgument(
                    name="task",
                    description="The task to perform in the browser",
                    required=True,
                ),
                PromptArgument(
                    name="url",
                    description="The URL to start with (optional)",
                    required=False,
                ),
            ],
        )
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        task = args.get("task", "")
        url = args.get("url", "")
        
        user_content = f"""Please help me automate the following browser task:

Task: {task}
"""
        if url:
            user_content += f"Starting URL: {url}\n"
        
        user_content += """
Use the aibridge_interact tool with app="chrome" to:
1. Navigate to the appropriate page
2. Interact with elements as needed
3. Return the results

Always take screenshots after important actions to verify the state."""
        
        return [
            PromptMessage(role="user", content=user_content)
        ]


class IMMessagePrompt(Prompt):
    """IM 消息发送提示词"""
    
    def __init__(self):
        super().__init__(
            name="im_message",
            description="Send messages to IM platforms like Feishu, Slack, or Telegram",
            arguments=[
                PromptArgument(
                    name="platform",
                    description="The IM platform (feishu, slack, telegram, etc.)",
                    required=True,
                ),
                PromptArgument(
                    name="recipient",
                    description="The chat/channel ID or name",
                    required=True,
                ),
                PromptArgument(
                    name="message",
                    description="The message to send",
                    required=True,
                ),
            ],
        )
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        platform = args.get("platform", "")
        recipient = args.get("recipient", "")
        message = args.get("message", "")
        
        user_content = f"""Please send the following message:

Platform: {platform}
Recipient: {recipient}
Message: {message}

Use the aibridge_interact tool with:
- app="{platform}"
- action="send_message" or "send"
- target containing the recipient info
- value containing the message

Confirm when the message has been sent successfully."""
        
        return [
            PromptMessage(role="user", content=user_content)
        ]


class OfficeDocumentPrompt(Prompt):
    """Office 文档操作提示词"""
    
    def __init__(self):
        super().__init__(
            name="office_document",
            description="Create or modify Office documents (Word, Excel, PowerPoint)",
            arguments=[
                PromptArgument(
                    name="app",
                    description="The Office app (word, excel, powerpoint)",
                    required=True,
                ),
                PromptArgument(
                    name="action",
                    description="The action (create, open, edit, export)",
                    required=True,
                ),
                PromptArgument(
                    name="file_path",
                    description="The file path",
                    required=True,
                ),
                PromptArgument(
                    name="content",
                    description="The content to write (for create/edit)",
                    required=False,
                ),
            ],
        )
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        app = args.get("app", "word")
        action = args.get("action", "create")
        file_path = args.get("file_path", "")
        content = args.get("content", "")
        
        user_content = f"""Please help me with the following Office document task:

Application: {app}
Action: {action}
File: {file_path}
"""
        if content:
            user_content += f"Content: {content}\n"
        
        user_content += f"""
Use the aibridge_interact tool with app="{app}" to:
1. {action.capitalize()} the document at the specified path
2. Apply any required content or modifications
3. Save the document

Report the results when complete."""
        
        return [
            PromptMessage(role="user", content=user_content)
        ]


class DesktopAutomationPrompt(Prompt):
    """桌面应用自动化提示词"""
    
    def __init__(self):
        super().__init__(
            name="desktop_automation",
            description="Automate Windows desktop applications",
            arguments=[
                PromptArgument(
                    name="app_name",
                    description="The application name or window title",
                    required=True,
                ),
                PromptArgument(
                    name="task",
                    description="The task to perform",
                    required=True,
                ),
            ],
        )
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        app_name = args.get("app_name", "")
        task = args.get("task", "")
        
        user_content = f"""Please automate the following desktop application task:

Application: {app_name}
Task: {task}

Use the aibridge_interact tool with app="desktop" to:
1. Connect to the application using action="connect" with target={{"title": "{app_name}"}}
2. List available elements with action="list_elements" to understand the UI
3. Perform the required operations
4. Take a screenshot to verify the result

Be careful with click coordinates and element selection."""
        
        return [
            PromptMessage(role="user", content=user_content)
        ]


class CrossPlatformWorkflowPrompt(Prompt):
    """跨平台工作流提示词"""
    
    def __init__(self):
        super().__init__(
            name="cross_platform_workflow",
            description="Execute workflows across multiple platforms and applications",
            arguments=[
                PromptArgument(
                    name="workflow_description",
                    description="Description of the workflow to execute",
                    required=True,
                ),
            ],
        )
    
    def generate_messages(self, args: Dict[str, Any]) -> List[PromptMessage]:
        workflow = args.get("workflow_description", "")
        
        user_content = f"""Please execute the following cross-platform workflow:

{workflow}

Available tools:
- aibridge_interact: Execute actions on applications
- aibridge_list_apps: See available applications
- aibridge_app_status: Check application status
- aibridge_health: Check system health

Steps:
1. First, list available apps to understand what's connected
2. Plan the workflow steps
3. Execute each step, verifying results
4. Handle any errors and retry if needed
5. Report the final outcome

Please proceed step by step."""
        
        return [
            PromptMessage(role="user", content=user_content)
        ]


class PromptManager:
    """
    提示词管理器
    
    管理所有预定义提示词。
    """
    
    def __init__(self):
        self._prompts: Dict[str, Prompt] = {}
        self._register_default_prompts()
    
    def _register_default_prompts(self):
        """注册默认提示词"""
        self.register(BrowserAutomationPrompt())
        self.register(IMMessagePrompt())
        self.register(OfficeDocumentPrompt())
        self.register(DesktopAutomationPrompt())
        self.register(CrossPlatformWorkflowPrompt())
    
    def register(self, prompt: Prompt):
        """注册提示词"""
        self._prompts[prompt.name] = prompt
    
    def unregister(self, name: str):
        """注销提示词"""
        if name in self._prompts:
            del self._prompts[name]
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """列出所有提示词"""
        return [prompt.to_dict() for prompt in self._prompts.values()]
    
    def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        获取提示词并生成消息
        
        Args:
            name: 提示词名称
            arguments: 参数
            
        Returns:
            包含 description 和 messages 的字典
        """
        prompt = self._prompts.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")
        
        # 验证必需参数
        args = arguments or {}
        for arg in prompt.arguments:
            if arg.required and arg.name not in args:
                raise ValueError(f"Missing required argument: {arg.name}")
        
        # 生成消息
        messages = prompt.generate_messages(args)
        
        return {
            "description": prompt.description,
            "messages": [msg.to_dict() for msg in messages],
        }
