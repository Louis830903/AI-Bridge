"""
Screenshot utilities for AI-Bridge
"""

import base64
from pathlib import Path
from typing import Optional, Union

# Lazy imports
mss = None
PIL_Image = None


def _get_mss():
    global mss
    if mss is None:
        import mss as _mss
        mss = _mss
    return mss


def _get_pil():
    global PIL_Image
    if PIL_Image is None:
        from PIL import Image
        PIL_Image = Image
    return PIL_Image


def take_screenshot(
    region: Optional[dict] = None,
    monitor: int = 0
) -> bytes:
    """
    Take a screenshot.
    
    Args:
        region: Optional region dict with keys: left, top, width, height
        monitor: Monitor number (0 = all monitors, 1+ = specific monitor)
        
    Returns:
        PNG image bytes
    """
    _mss = _get_mss()
    
    with _mss.mss() as sct:
        if region:
            screenshot = sct.grab(region)
        else:
            screenshot = sct.grab(sct.monitors[monitor])
        
        # Convert to PNG bytes
        return _mss.tools.to_png(screenshot.rgb, screenshot.size)


def save_screenshot(
    path: Union[str, Path],
    region: Optional[dict] = None,
    monitor: int = 0
) -> str:
    """
    Take and save a screenshot.
    
    Args:
        path: File path to save the screenshot
        region: Optional region dict
        monitor: Monitor number
        
    Returns:
        Saved file path
    """
    png_bytes = take_screenshot(region, monitor)
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "wb") as f:
        f.write(png_bytes)
    
    return str(path)


def screenshot_to_base64(
    region: Optional[dict] = None,
    monitor: int = 0
) -> str:
    """
    Take a screenshot and return as base64 string.
    
    Args:
        region: Optional region dict
        monitor: Monitor number
        
    Returns:
        Base64 encoded PNG string
    """
    png_bytes = take_screenshot(region, monitor)
    return base64.b64encode(png_bytes).decode()
