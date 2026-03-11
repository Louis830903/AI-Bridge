"""
Tests for MCP Prompts module
MCP 提示词模块测试
"""

import pytest
from unittest.mock import MagicMock

from aibridge.core.prompts import (
    PromptArgument, PromptMessage, Prompt,
    BrowserAutomationPrompt, IMMessagePrompt, OfficeDocumentPrompt,
    DesktopAutomationPrompt, CrossPlatformWorkflowPrompt,
    PromptManager,
)


class TestPromptArgument:
    """测试 PromptArgument 数据类"""
    
    def test_create_required_argument(self):
        """测试创建必需参数"""
        arg = PromptArgument(
            name="url",
            description="Target URL",
            required=True
        )
        
        assert arg.name == "url"
        assert arg.required is True
    
    def test_create_optional_argument(self):
        """测试创建可选参数"""
        arg = PromptArgument(
            name="timeout",
            description="Timeout in seconds",
            required=False
        )
        
        assert arg.required is False
    
    def test_argument_to_dict(self):
        """测试参数转字典"""
        arg = PromptArgument(
            name="action",
            description="Action to perform",
            required=True
        )
        
        data = arg.to_dict()
        
        assert data["name"] == "action"
        assert data["description"] == "Action to perform"
        assert data["required"] is True


class TestPromptMessage:
    """测试 PromptMessage 数据类"""
    
    def test_user_message(self):
        """测试用户消息"""
        msg = PromptMessage(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_assistant_message(self):
        """测试助手消息"""
        msg = PromptMessage(role="assistant", content="How can I help?")
        
        assert msg.role == "assistant"
    
    def test_message_to_dict(self):
        """测试消息转字典"""
        msg = PromptMessage(role="user", content="Test message")
        
        data = msg.to_dict()
        
        assert data["role"] == "user"
        assert data["content"]["type"] == "text"
        assert data["content"]["text"] == "Test message"


class TestPromptManager:
    """测试 PromptManager"""
    
    def test_default_prompts_registered(self):
        """测试默认提示词已注册"""
        manager = PromptManager()
        
        prompts = manager.list_prompts()
        names = [p["name"] for p in prompts]
        
        assert "browser_automation" in names
        assert "im_message" in names
        assert "office_document" in names
        assert "desktop_automation" in names
        assert "cross_platform_workflow" in names
    
    def test_list_prompts(self):
        """测试列出提示词"""
        manager = PromptManager()
        
        prompts = manager.list_prompts()
        
        assert len(prompts) >= 5
        assert all("name" in p for p in prompts)
        assert all("description" in p for p in prompts)
    
    def test_get_prompt_not_found(self):
        """测试获取不存在的提示词"""
        manager = PromptManager()
        
        with pytest.raises(ValueError, match="Prompt not found"):
            manager.get_prompt("nonexistent")
    
    def test_get_prompt_missing_required(self):
        """测试缺少必需参数"""
        manager = PromptManager()
        
        with pytest.raises(ValueError, match="Missing required argument"):
            manager.get_prompt("browser_automation", {})
    
    def test_get_browser_automation_prompt(self):
        """测试获取浏览器自动化提示词"""
        manager = PromptManager()
        
        result = manager.get_prompt("browser_automation", {
            "url": "https://example.com",
            "task": "Click the login button"
        })
        
        assert "description" in result
        assert "messages" in result
        assert len(result["messages"]) > 0
    
    def test_get_im_message_prompt(self):
        """测试获取 IM 消息提示词"""
        manager = PromptManager()
        
        result = manager.get_prompt("im_message", {
            "platform": "slack",
            "recipient": "#general",
            "message": "Hello team!"
        })
        
        assert "description" in result
        assert len(result["messages"]) > 0
    
    def test_get_office_document_prompt(self):
        """测试获取 Office 文档提示词"""
        manager = PromptManager()
        
        result = manager.get_prompt("office_document", {
            "app": "word",
            "action": "create",
            "file_path": "C:/Documents/report.docx"
        })
        
        assert "description" in result
    
    def test_get_desktop_automation_prompt(self):
        """测试获取桌面自动化提示词"""
        manager = PromptManager()
        
        result = manager.get_prompt("desktop_automation", {
            "app_name": "notepad",
            "task": "Type some text"
        })
        
        assert "description" in result
    
    def test_get_cross_platform_workflow_prompt(self):
        """测试获取跨平台工作流提示词"""
        manager = PromptManager()
        
        result = manager.get_prompt("cross_platform_workflow", {
            "workflow_description": "Copy data from Excel to Slack"
        })
        
        assert "description" in result
    
    def test_register_custom_prompt(self):
        """测试注册自定义提示词"""
        manager = PromptManager()
        
        # 创建自定义提示词
        class CustomPrompt(Prompt):
            def __init__(self):
                super().__init__(
                    name="custom_prompt",
                    description="A custom prompt",
                    arguments=[
                        PromptArgument("param", "A parameter", True)
                    ]
                )
            
            def generate_messages(self, args):
                return [PromptMessage("user", f"Param: {args['param']}")]
        
        manager.register(CustomPrompt())
        
        prompts = manager.list_prompts()
        names = [p["name"] for p in prompts]
        
        assert "custom_prompt" in names
    
    def test_unregister_prompt(self):
        """测试注销提示词"""
        manager = PromptManager()
        
        manager.unregister("browser_automation")
        
        prompts = manager.list_prompts()
        names = [p["name"] for p in prompts]
        
        assert "browser_automation" not in names


class TestBrowserAutomationPrompt:
    """测试浏览器自动化提示词"""
    
    def test_prompt_name(self):
        """测试提示词名称"""
        prompt = BrowserAutomationPrompt()
        
        assert prompt.name == "browser_automation"
    
    def test_prompt_arguments(self):
        """测试提示词参数"""
        prompt = BrowserAutomationPrompt()
        
        arg_names = [a.name for a in prompt.arguments]
        
        assert "url" in arg_names
        assert "task" in arg_names
    
    def test_generate_messages(self):
        """测试生成消息"""
        prompt = BrowserAutomationPrompt()
        
        messages = prompt.generate_messages({
            "url": "https://example.com",
            "task": "Click button"
        })
        
        assert len(messages) > 0
        assert any("https://example.com" in m.content for m in messages)


class TestIMMessagePrompt:
    """测试 IM 消息提示词"""
    
    def test_prompt_name(self):
        """测试提示词名称"""
        prompt = IMMessagePrompt()
        
        assert prompt.name == "im_message"
    
    def test_prompt_arguments(self):
        """测试提示词参数"""
        prompt = IMMessagePrompt()
        
        arg_names = [a.name for a in prompt.arguments]
        
        assert "platform" in arg_names
        assert "recipient" in arg_names
        assert "message" in arg_names
    
    def test_generate_messages(self):
        """测试生成消息"""
        prompt = IMMessagePrompt()
        
        messages = prompt.generate_messages({
            "platform": "feishu",
            "recipient": "team-chat",
            "message": "Hello!"
        })
        
        assert len(messages) > 0


class TestOfficeDocumentPrompt:
    """测试 Office 文档提示词"""
    
    def test_prompt_name(self):
        """测试提示词名称"""
        prompt = OfficeDocumentPrompt()
        
        assert prompt.name == "office_document"
    
    def test_prompt_with_file_path(self):
        """测试带文件路径的提示词"""
        prompt = OfficeDocumentPrompt()
        
        messages = prompt.generate_messages({
            "application": "excel",
            "task": "Add formula",
            "file_path": "C:/Documents/report.xlsx"
        })
        
        assert len(messages) > 0


class TestDesktopAutomationPrompt:
    """测试桌面自动化提示词"""
    
    def test_prompt_name(self):
        """测试提示词名称"""
        prompt = DesktopAutomationPrompt()
        
        assert prompt.name == "desktop_automation"


class TestCrossPlatformWorkflowPrompt:
    """测试跨平台工作流提示词"""
    
    def test_prompt_name(self):
        """测试提示词名称"""
        prompt = CrossPlatformWorkflowPrompt()
        
        assert prompt.name == "cross_platform_workflow"
    
    def test_prompt_arguments(self):
        """测试提示词参数"""
        prompt = CrossPlatformWorkflowPrompt()
        
        arg_names = [a.name for a in prompt.arguments]
        
        assert "workflow_description" in arg_names
