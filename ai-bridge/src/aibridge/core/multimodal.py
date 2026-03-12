"""
MultiModal Support - 多模态输入/输出

支持通过图像、描述等多种方式定位元素，
以及返回页面理解和结构化分析。

使用示例:
```python
# 通过图像定位元素
await adapter.execute(
    "click",
    target={"image": base64_encoded_image}
)

# 通过自然语言描述定位
await adapter.execute(
    "click",
    target={"description": "红色的提交按钮"}
)

# 分析页面并返回理解
result = await adapter.execute("analyze_page")
# 返回:
# {
#     "page_type": "search_results",
#     "main_content": "这是一个搜索结果页面...",
#     "interactive_elements": [...],
#     "suggested_actions": [...]
# }
```
"""

import base64
import io
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ElementDescription:
    """元素描述"""
    text: Optional[str] = None
    color: Optional[str] = None
    shape: Optional[str] = None
    position: Optional[str] = None  # "top", "bottom", "left", "right", "center"
    size: Optional[str] = None      # "large", "small", "medium"
    tag: Optional[str] = None       # "button", "link", "input"


@dataclass
class PageAnalysis:
    """页面分析结果"""
    page_type: str
    title: str
    url: str
    main_content: str
    interactive_elements: List[Dict] = field(default_factory=list)
    forms: List[Dict] = field(default_factory=list)
    links: List[Dict] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    accessibility_summary: str = ""


class MultiModalLocator:
    """
    多模态定位器
    
    支持图像、描述等多种定位方式。
    """
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.page = adapter._page
    
    async def locate_by_image(self, image_data: str) -> Optional[Dict]:
        """
        通过图像定位元素
        
        注意：这是一个简化实现，实际图像匹配需要计算机视觉库（如 OpenCV）
        
        Args:
            image_data: base64 编码的图像数据
        
        Returns:
            元素位置信息或 None
        """
        logger.warning("图像定位功能需要额外的计算机视觉库支持（如 OpenCV）")
        
        # 简化实现：返回错误提示
        return {
            "success": False,
            "error": "图像定位功能需要安装 OpenCV 和额外的图像处理库。请安装: pip install opencv-python pillow"
        }
    
    async def locate_by_description(
        self,
        description: str,
        element_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        通过自然语言描述定位元素
        
        Args:
            description: 自然语言描述，如"红色的提交按钮"
            element_type: 元素类型提示，如 "button", "input"
        
        Returns:
            元素选择器或 None
        """
        if not self.page:
            return None
        
        # 解析描述
        desc = self._parse_description(description)
        
        # 根据描述构建选择器策略
        strategies = []
        
        # 策略1: 根据文本内容
        if desc.text:
            strategies.append(f'text="{desc.text}"')
        
        # 策略2: 根据元素类型
        if desc.tag or element_type:
            tag = desc.tag or element_type
            if desc.text:
                strategies.append(f'{tag}:has-text("{desc.text}")')
            else:
                strategies.append(tag)
        
        # 策略3: 根据位置
        if desc.position:
            position_selectors = {
                "top": ":nth-child(-n+5)",  # 前5个元素
                "bottom": ":nth-last-child(-n+5)",  # 后5个元素
                "first": ":first-child",
                "last": ":last-child"
            }
            if desc.position in position_selectors:
                # 需要在更具体的选择器后添加
                pass
        
        # 策略4: 基于常见模式匹配
        common_patterns = {
            "提交": "button[type='submit'], input[type='submit'], button:has-text('提交')",
            "搜索": "button:has-text('搜索'), input[type='search']",
            "登录": "button:has-text('登录'), a:has-text('登录')",
            "注册": "button:has-text('注册'), a:has-text('注册')",
            "确认": "button:has-text('确认'), button:has-text('确定')",
            "取消": "button:has-text('取消'), button:has-text('关闭')",
        }
        
        for keyword, selector in common_patterns.items():
            if keyword in description:
                strategies.append(selector)
                break
        
        # 尝试每个策略
        for strategy in strategies:
            try:
                locator = self.page.locator(strategy)
                count = await locator.count()
                if count > 0:
                    return {
                        "success": True,
                        "selector": strategy,
                        "match_count": count,
                        "strategy": "description_matching"
                    }
            except Exception as e:
                logger.debug(f"策略失败 {strategy}: {e}")
                continue
        
        return {
            "success": False,
            "error": f"无法根据描述 '{description}' 找到元素"
        }
    
    def _parse_description(self, description: str) -> ElementDescription:
        """解析自然语言描述"""
        desc = ElementDescription()
        
        # 提取颜色
        colors = ["红", "蓝", "绿", "黄", "白", "黑", "灰"]
        for color in colors:
            if color in description:
                desc.color = color
                break
        
        # 提取位置
        positions = ["顶部", "底部", "左边", "右边", "中间", "上方", "下方", "第一个", "最后一个"]
        position_map = {
            "顶部": "top", "上方": "top",
            "底部": "bottom", "下方": "bottom",
            "左边": "left", "右边": "right",
            "中间": "center",
            "第一个": "first", "最后一个": "last"
        }
        for pos in positions:
            if pos in description:
                desc.position = position_map.get(pos)
                break
        
        # 提取元素类型
        tags = ["按钮", "链接", "输入框", "下拉框", "复选框", "单选框"]
        tag_map = {
            "按钮": "button",
            "链接": "a",
            "输入框": "input",
            "下拉框": "select",
            "复选框": "input[type='checkbox']",
            "单选框": "input[type='radio']"
        }
        for tag in tags:
            if tag in description:
                desc.tag = tag_map.get(tag)
                break
        
        # 提取大小
        sizes = ["大", "小", "中等"]
        for size in sizes:
            if size in description:
                desc.size = size
                break
        
        return desc
    
    async def resolve_target(self, target: Dict) -> Dict:
        """
        解析多模态目标为具体选择器
        
        Args:
            target: 可能包含 css/image/description 的目标定义
        
        Returns:
            解析后的目标定义
        """
        if not target:
            return target
        
        # 如果已经有 CSS 选择器，直接返回
        if target.get("css") or target.get("xpath") or target.get("uid"):
            return target
        
        # 处理图像定位
        if "image" in target:
            result = await self.locate_by_image(target["image"])
            if result and result.get("success"):
                return {"css": result.get("selector")}
            else:
                # 返回错误
                return {"_error": result.get("error", "图像定位失败")}
        
        # 处理描述定位
        if "description" in target:
            result = await self.locate_by_description(
                target["description"],
                target.get("element_type")
            )
            if result and result.get("success"):
                return {"css": result.get("selector")}
            else:
                return {"_error": result.get("error", "描述定位失败")}
        
        return target


class PageAnalyzer:
    """
    页面分析器
    
    分析页面结构和内容，返回页面理解。
    """
    
    def __init__(self, adapter):
        self.adapter = adapter
        self.page = adapter._page
    
    async def analyze(self) -> PageAnalysis:
        """分析当前页面"""
        if not self.page:
            raise RuntimeError("页面未初始化")
        
        url = self.page.url
        title = await self.page.title()
        
        # 获取交互元素
        interactive = await self._get_interactive_elements()
        
        # 获取表单
        forms = await self._get_forms()
        
        # 获取链接
        links = await self._get_links()
        
        # 判断页面类型
        page_type = self._detect_page_type(url, title, interactive)
        
        # 生成主要内容摘要
        main_content = await self._get_main_content()
        
        # 生成建议操作
        suggested_actions = self._generate_suggestions(page_type, interactive, forms)
        
        # 获取可访问性摘要
        a11y_summary = await self._get_a11y_summary()
        
        return PageAnalysis(
            page_type=page_type,
            title=title,
            url=url,
            main_content=main_content,
            interactive_elements=interactive[:10],  # 只取前10个
            forms=forms,
            links=links[:10],  # 只取前10个
            suggested_actions=suggested_actions,
            accessibility_summary=a11y_summary
        )
    
    async def _get_interactive_elements(self) -> List[Dict]:
        """获取可交互元素"""
        try:
            elements = await self.page.evaluate("""
                () => {
                    const interactive = [];
                    const elements = document.querySelectorAll('button, a, input, select, textarea, [role="button"]');
                    elements.forEach((el, i) => {
                        if (i < 20) {  // 限制数量
                            interactive.push({
                                tag: el.tagName.toLowerCase(),
                                type: el.type || null,
                                text: el.innerText?.slice(0, 50) || el.value?.slice(0, 50) || '',
                                id: el.id || null,
                                class: el.className?.slice(0, 50) || null
                            });
                        }
                    });
                    return interactive;
                }
            """)
            return elements
        except Exception as e:
            logger.warning(f"获取交互元素失败: {e}")
            return []
    
    async def _get_forms(self) -> List[Dict]:
        """获取表单信息"""
        try:
            forms = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('form')).map(form => ({
                        id: form.id || null,
                        action: form.action || null,
                        method: form.method || 'get',
                        inputs: Array.from(form.querySelectorAll('input, select, textarea')).map(input => ({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name || null,
                            placeholder: input.placeholder || null,
                            required: input.required
                        }))
                    }));
                }
            """)
            return forms
        except Exception as e:
            logger.warning(f"获取表单失败: {e}")
            return []
    
    async def _get_links(self) -> List[Dict]:
        """获取链接"""
        try:
            links = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]')).map((a, i) => ({
                        index: i,
                        text: a.innerText?.slice(0, 30) || '',
                        href: a.href
                    }));
                }
            """)
            return links
        except Exception as e:
            logger.warning(f"获取链接失败: {e}")
            return []
    
    def _detect_page_type(self, url: str, title: str, interactive: List) -> str:
        """检测页面类型"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        # 搜索页面
        if any(x in url_lower for x in ['search', 'query', 'find', 's']):
            return "search_results"
        
        # 登录页面
        if any(x in title_lower for x in ['登录', 'login', 'sign in']):
            return "login"
        
        # 商品详情页
        if any(x in url_lower for x in ['product', 'item', 'goods', 'detail']):
            return "product_detail"
        
        # 购物车
        if any(x in url_lower for x in ['cart', 'basket']):
            return "shopping_cart"
        
        # 结账页面
        if any(x in url_lower for x in ['checkout', 'payment', 'order']):
            return "checkout"
        
        # 表单页面
        if len([e for e in interactive if e.get('tag') == 'input']) > 3:
            return "form"
        
        return "generic"
    
    async def _get_main_content(self) -> str:
        """获取主要内容"""
        try:
            # 尝试获取主要文本内容
            text = await self.page.evaluate("""
                () => {
                    // 尝试找主要内容区域
                    const main = document.querySelector('main, article, [role="main"], .content, #content');
                    if (main) {
                        return main.innerText.slice(0, 500);
                    }
                    // 否则取 body 文本
                    return document.body.innerText.slice(0, 500);
                }
            """)
            return text
        except Exception as e:
            logger.warning(f"获取主要内容失败: {e}")
            return ""
    
    def _generate_suggestions(
        self,
        page_type: str,
        interactive: List,
        forms: List
    ) -> List[str]:
        """生成建议操作"""
        suggestions = []
        
        if page_type == "search_results":
            suggestions.append("点击第一个搜索结果")
            suggestions.append("修改搜索词")
            suggestions.append("查看下一页")
        
        elif page_type == "login":
            suggestions.append("输入用户名")
            suggestions.append("输入密码")
            suggestions.append("点击登录按钮")
        
        elif page_type == "product_detail":
            suggestions.append("查看商品详情")
            suggestions.append("添加到购物车")
            suggestions.append("查看评价")
        
        elif forms:
            suggestions.append("填写表单")
            suggestions.append("提交表单")
        
        if any(e.get('tag') == 'a' for e in interactive):
            suggestions.append("点击链接导航")
        
        return suggestions[:5]  # 最多5条建议
    
    async def _get_a11y_summary(self) -> str:
        """获取可访问性摘要"""
        try:
            # 这里可以集成更复杂的 a11y 检查
            # 简化版本：返回元素数量
            count = await self.page.evaluate("""
                () => document.querySelectorAll('button, a, input, [role]').length
            """)
            return f"页面包含 {count} 个可交互元素"
        except Exception as e:
            logger.warning(f"获取 a11y 摘要失败: {e}")
            return ""


# ============ 使用示例 ============

async def demo():
    """演示多模态功能"""
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    adapter = ChromeAdapter()
    await adapter.connect()
    
    # 导航到百度
    await adapter.execute("goto", target={"url": "https://www.baidu.com"})
    
    # 分析页面
    print("\n=== 页面分析 ===")
    analyzer = PageAnalyzer(adapter)
    analysis = await analyzer.analyze()
    
    print(f"页面类型: {analysis.page_type}")
    print(f"标题: {analysis.title}")
    print(f"主要内容: {analysis.main_content[:100]}...")
    print(f"建议操作: {analysis.suggested_actions}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
