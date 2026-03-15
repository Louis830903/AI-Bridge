"""
Playwright Adapter for AI-Bridge

Wraps Playwright CLI and Python API to provide browser automation capabilities.

Requires: Playwright installed: pip install playwright && playwright install

Usage:
    adapter = PlaywrightAdapter()
    await adapter.initialize()
    
    # Screenshot
    result = await adapter.execute(Action(
        name="screenshot",
        params={"url": "https://example.com", "output": "screenshot.png"}
    ))
"""

import asyncio
import tempfile
import os
from typing import Any, Callable, Dict, List, Optional
from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult


class PlaywrightAdapter(CLIAdapter):
    """AI-Bridge adapter for Playwright browser automation."""
    
    cli_name = "playwright"
    cli_module = "playwright"
    auto_install_cli = True
    default_timeout = 120
    
    ALLOWED_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.pdf',
        '.html', '.txt', '.json'
    }
    
    SUPPORTED_ACTIONS = [
        # Screenshot
        "screenshot", "capture", "full_page_screenshot", "element_screenshot",
        # PDF
        "pdf", "print_to_pdf",
        # Navigation
        "navigate", "goto", "click", "fill", "type", "scroll",
        # Testing
        "test", "run_tests", "codegen",
        # Inspector
        "inspect", "open",
        # Info
        "version", "info",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        return {
            # Screenshot
            "screenshot": self._handle_screenshot,
            "capture": self._handle_screenshot,
            "full_page_screenshot": self._handle_full_page_screenshot,
            "element_screenshot": self._handle_element_screenshot,
            # PDF
            "pdf": self._handle_pdf,
            "print_to_pdf": self._handle_pdf,
            # Navigation
            "navigate": self._handle_navigate,
            "goto": self._handle_navigate,
            "click": self._handle_click,
            "fill": self._handle_fill,
            "type": self._handle_type,
            "scroll": self._handle_scroll,
            # Testing
            "test": self._handle_test,
            "run_tests": self._handle_test,
            "codegen": self._handle_codegen,
            # Inspector
            "inspect": self._handle_inspect,
            "open": self._handle_inspect,
            # Info
            "version": self._handle_version,
            "info": self._handle_version,
        }
    
    async def _handle_screenshot(self, action: Action) -> Response:
        """Take screenshot of a webpage."""
        params = action.params
        url = params.get("url") or params.get("link") or params.get("website")
        output_file = params.get("output") or params.get("path") or "screenshot.png"
        viewport = params.get("viewport") or params.get("size", "1280x720")
        
        if not url:
            return Response(success=False, error="url is required")
        
        # Validate URL
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        is_valid, error = self._validate_path(output_file, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid output: {error}")
        
        # Build Python script for screenshot
        vp_parts = viewport.split("x")
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": {vp_parts[0]}, "height": {vp_parts[1]}}})
        await page.goto("{url}")
        await page.screenshot(path="{output_file}", full_page=False)
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_full_page_screenshot(self, action: Action) -> Response:
        """Take full page screenshot."""
        params = action.params
        url = params.get("url") or params.get("link")
        output_file = params.get("output") or params.get("path") or "fullpage.png"
        viewport = params.get("viewport") or params.get("size", "1280x720")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        is_valid, error = self._validate_path(output_file, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid output: {error}")
        
        vp_parts = viewport.split("x")
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": {vp_parts[0]}, "height": {vp_parts[1]}}})
        await page.goto("{url}")
        await page.screenshot(path="{output_file}", full_page=True)
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_element_screenshot(self, action: Action) -> Response:
        """Take screenshot of specific element."""
        params = action.params
        url = params.get("url") or params.get("link")
        selector = params.get("selector") or params.get("element")
        output_file = params.get("output") or params.get("path") or "element.png"
        
        if not url or not selector:
            return Response(success=False, error="url and selector are required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        is_valid, error = self._validate_path(output_file, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid output: {error}")
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        element = await page.query_selector("{selector}")
        if element:
            await element.screenshot(path="{output_file}")
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_pdf(self, action: Action) -> Response:
        """Generate PDF from webpage."""
        params = action.params
        url = params.get("url") or params.get("link")
        output_file = params.get("output") or params.get("path") or "page.pdf"
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        is_valid, error = self._validate_path(output_file, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid output: {error}")
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        await page.pdf(path="{output_file}", format="A4")
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_navigate(self, action: Action) -> Response:
        """Navigate to URL and return page info."""
        params = action.params
        url = params.get("url") or params.get("link")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        response = await page.goto("{url}")
        title = await page.title()
        result = {{
            "url": "{url}",
            "title": title,
            "status": response.status if response else None
        }}
        print(json.dumps(result))
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_click(self, action: Action) -> Response:
        """Click element on page."""
        params = action.params
        url = params.get("url") or params.get("link")
        selector = params.get("selector") or params.get("element")
        
        if not url or not selector:
            return Response(success=False, error="url and selector are required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        await page.click("{selector}")
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_fill(self, action: Action) -> Response:
        """Fill form field."""
        params = action.params
        url = params.get("url") or params.get("link")
        selector = params.get("selector") or params.get("element")
        value = params.get("value") or params.get("text", "")
        
        if not url or not selector:
            return Response(success=False, error="url and selector are required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        # Escape quotes in value
        value = value.replace('"', '\\"')
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        await page.fill("{selector}", "{value}")
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_type(self, action: Action) -> Response:
        """Type text with delay (simulates keyboard)."""
        params = action.params
        url = params.get("url") or params.get("link")
        selector = params.get("selector") or params.get("element")
        value = params.get("value") or params.get("text", "")
        delay = params.get("delay", 50)
        
        if not url or not selector:
            return Response(success=False, error="url and selector are required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        value = value.replace('"', '\\"')
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        await page.type("{selector}", "{value}", delay={delay})
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_scroll(self, action: Action) -> Response:
        """Scroll page."""
        params = action.params
        url = params.get("url") or params.get("link")
        x = params.get("x", 0)
        y = params.get("y", 1000)
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        script = f'''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("{url}")
        await page.evaluate("window.scrollTo({x}, {y})")
        await browser.close()

asyncio.run(main())
'''
        result = await self._run_python_script(script)
        return self._cli_result_to_response(result)
    
    async def _handle_test(self, action: Action) -> Response:
        """Run Playwright tests."""
        params = action.params
        test_path = params.get("path") or params.get("test_path", ".")
        browser = params.get("browser", "chromium")
        headed = params.get("headed", False)
        
        cmd_args = ["test", test_path]
        
        if browser:
            cmd_args.extend(["--project", browser])
        
        if headed:
            cmd_args.append("--headed")
        
        result = await self._run_cli("", args=cmd_args, timeout=300)
        return self._cli_result_to_response(result)
    
    async def _handle_codegen(self, action: Action) -> Response:
        """Generate test code from browser actions."""
        params = action.params
        url = params.get("url") or params.get("link")
        output_file = params.get("output") or "tests/generated.spec.js"
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = ["codegen", url, "-o", output_file]
        
        result = await self._run_cli("", args=cmd_args, timeout=300)
        return self._cli_result_to_response(result)
    
    async def _handle_inspect(self, action: Action) -> Response:
        """Open Playwright inspector."""
        params = action.params
        url = params.get("url") or params.get("link")
        
        cmd_args = ["open"]
        
        if url:
            if not url.startswith(("http://", "https://")):
                return Response(success=False, error="invalid URL format")
            cmd_args.append(url)
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_version(self, action: Action) -> Response:
        """Get Playwright version."""
        result = await self._run_cli("--version")
        return self._cli_result_to_response(result)
    
    async def _run_python_script(self, script: str) -> CLIResult:
        """Run a Python script using the Playwright API."""
        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.default_timeout
            )
            
            return CLIResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                error=stderr.decode('utf-8', errors='replace') if proc.returncode != 0 else None
            )
        
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=f"Script timed out after {self.default_timeout}s"
            )
        
        except Exception as e:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e)
            )
        
        finally:
            os.unlink(script_path)
