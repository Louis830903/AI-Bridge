"""
Tests for core protocol module
协议模块单元测试
"""

import pytest
from aibridge.core.protocol import (
    Action, ElementRole, Target, RequestOptions,
    Request, Response
)


class TestAction:
    """Test Action enum."""
    
    def test_action_values(self):
        """Test action enum values."""
        assert Action.CLICK == "click"
        assert Action.TYPE == "type"
        assert Action.READ == "read"
        assert Action.SCREENSHOT == "screenshot"
    
    def test_action_is_string(self):
        """Test action is string subclass."""
        assert isinstance(Action.CLICK.value, str)


class TestTarget:
    """Test Target dataclass."""
    
    def test_create_empty_target(self):
        """Test creating empty target."""
        target = Target()
        assert target.name is None
        assert target.role is None
        assert target.index == 0
    
    def test_create_target_with_name(self):
        """Test creating target with name."""
        target = Target(name="Submit Button")
        assert target.name == "Submit Button"
    
    def test_create_target_with_css(self):
        """Test creating target with CSS selector."""
        target = Target(css="button.submit")
        assert target.css == "button.submit"
    
    def test_to_dict(self):
        """Test converting target to dict."""
        target = Target(name="test", role="button", index=1)
        d = target.to_dict()
        
        assert d["name"] == "test"
        assert d["role"] == "button"
        assert d["index"] == 1
        assert "xpath" not in d  # None values should be excluded
    
    def test_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        target = Target(name="test")
        d = target.to_dict()
        
        assert "name" in d
        assert "xpath" not in d
        assert "css" not in d
    
    def test_from_dict(self):
        """Test creating target from dict."""
        data = {"name": "test", "css": ".class", "index": 2}
        target = Target.from_dict(data)
        
        assert target.name == "test"
        assert target.css == ".class"
        assert target.index == 2
    
    def test_from_dict_with_nested(self):
        """Test creating target with nested target."""
        data = {
            "name": "child",
            "inside": {"name": "parent", "role": "dialog"}
        }
        target = Target.from_dict(data)
        
        assert target.name == "child"
        assert target.inside is not None
        assert target.inside.name == "parent"
        assert target.inside.role == "dialog"
    
    def test_from_dict_none(self):
        """Test from_dict with None."""
        target = Target.from_dict(None)
        assert target is None


class TestRequestOptions:
    """Test RequestOptions dataclass."""
    
    def test_default_values(self):
        """Test default option values."""
        options = RequestOptions()
        
        assert options.timeout == 10000
        assert options.wait_after == 500
        assert options.retry == 0
        assert options.screenshot is False
    
    def test_custom_values(self):
        """Test custom option values."""
        options = RequestOptions(timeout=5000, retry=3)
        
        assert options.timeout == 5000
        assert options.retry == 3
    
    def test_to_dict(self):
        """Test converting options to dict."""
        options = RequestOptions(timeout=3000)
        d = options.to_dict()
        
        assert d["timeout"] == 3000
        assert "wait_after" in d
    
    def test_from_dict(self):
        """Test creating options from dict."""
        data = {"timeout": 5000, "screenshot": True}
        options = RequestOptions.from_dict(data)
        
        assert options.timeout == 5000
        assert options.screenshot is True


class TestRequest:
    """Test Request dataclass."""
    
    def test_create_simple_request(self):
        """Test creating simple request."""
        request = Request(app="chrome", action="click")
        
        assert request.app == "chrome"
        assert request.action == "click"
        assert request.target is None
    
    def test_create_request_with_target(self):
        """Test creating request with target."""
        target = Target(name="Submit")
        request = Request(app="chrome", action="click", target=target)
        
        assert request.target.name == "Submit"
    
    def test_to_dict(self):
        """Test converting request to dict."""
        request = Request(
            app="feishu",
            action="send",
            value="Hello",
        )
        d = request.to_dict()
        
        assert d["app"] == "feishu"
        assert d["action"] == "send"
        assert d["value"] == "Hello"
        assert "options" in d
    
    def test_from_dict(self):
        """Test creating request from dict."""
        data = {
            "app": "chrome",
            "action": "goto",
            "value": "https://example.com",
            "options": {"timeout": 5000}
        }
        request = Request.from_dict(data)
        
        assert request.app == "chrome"
        assert request.action == "goto"
        assert request.value == "https://example.com"
        assert request.options.timeout == 5000


class TestResponse:
    """Test Response dataclass."""
    
    def test_success_response(self):
        """Test creating success response."""
        response = Response.success_response(data="result")
        
        assert response.success is True
        assert response.data == "result"
        assert response.error is None
    
    def test_error_response(self):
        """Test creating error response."""
        response = Response.error_response(error="Something went wrong")
        
        assert response.success is False
        assert response.error == "Something went wrong"
    
    def test_to_dict(self):
        """Test converting response to dict."""
        response = Response(
            success=True,
            data={"key": "value"},
            duration=150
        )
        d = response.to_dict()
        
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["duration"] == 150
        assert "error" not in d  # Should exclude None/empty
    
    def test_to_dict_excludes_empty(self):
        """Test that to_dict excludes empty values."""
        response = Response(success=True)
        d = response.to_dict()
        
        assert "success" in d
        assert "error" not in d
        assert "screenshot" not in d


class TestElementRole:
    """Test ElementRole enum."""
    
    def test_role_values(self):
        """Test role enum values."""
        assert ElementRole.BUTTON == "button"
        assert ElementRole.INPUT == "input"
        assert ElementRole.LINK == "link"
    
    def test_common_roles_exist(self):
        """Test common roles are defined."""
        roles = [r.value for r in ElementRole]
        
        assert "button" in roles
        assert "input" in roles
        assert "text" in roles
        assert "checkbox" in roles
        assert "dialog" in roles
