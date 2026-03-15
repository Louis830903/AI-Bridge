"""
ImageMagick Adapter for AI-Bridge

Wraps ImageMagick CLI to provide advanced image processing capabilities.

Requires:
    ImageMagick installed and in PATH

Usage:
    adapter = ImageMagickAdapter()
    await adapter.initialize()
    
    # Resize image
    result = await adapter.execute(Action(
        name="resize",
        params={"input": "photo.jpg", "output": "thumb.jpg", "size": "200x200"}
    ))
"""

from typing import Any, Callable, Dict, List, Optional

from aibridge.core.protocol import Response
from .base import CLIAdapter, CLIResult


class ImageMagickAdapter(CLIAdapter):
    """
    AI-Bridge adapter for ImageMagick advanced image processing.
    
    Provides:
    - Image format conversion
    - Resizing and scaling
    - Cropping and trimming
    - Filters and effects (blur, sharpen, edge)
    - Color adjustments
    - Composition and overlays
    - Batch processing
    - Metadata extraction
    """
    
    # CLI configuration
    cli_name = "convert"  # ImageMagick's main command
    cli_module = None
    auto_install_cli = False
    default_timeout = 120
    
    # Allowed image extensions
    ALLOWED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
        '.webp', '.svg', '.pdf', '.psd', '.raw', '.cr2', '.nef',
        '.heic', '.avif', '.ico', '.eps', '.ai'
    }
    
    # Supported action types
    SUPPORTED_ACTIONS = [
        # Format conversion
        "convert", "format",
        # Size operations
        "resize", "scale", "crop", "trim", "extent",
        # Filters
        "blur", "sharpen", "edge", "emboss", "noise",
        # Color operations
        "brightness", "contrast", "saturation", "grayscale",
        "sepia", "invert", "modulate",
        # Effects
        "vignette", "polaroid", "charcoal", "paint", "sketch",
        # Composition
        "composite", "watermark", "overlay",
        # Batch operations
        "mogrify", "montage",
        # Info
        "identify", "metadata",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable]:
        """Map action names to handler methods."""
        return {
            # Format
            "convert": self._handle_convert,
            "format": self._handle_convert,
            # Size
            "resize": self._handle_resize,
            "scale": self._handle_resize,
            "crop": self._handle_crop,
            "trim": self._handle_trim,
            # Filters
            "blur": self._handle_blur,
            "sharpen": self._handle_sharpen,
            "edge": self._handle_edge,
            # Color
            "brightness": self._handle_brightness,
            "contrast": self._handle_contrast,
            "grayscale": self._handle_grayscale,
            "sepia": self._handle_sepia,
            "invert": self._handle_invert,
            # Effects
            "vignette": self._handle_vignette,
            "charcoal": self._handle_charcoal,
            "paint": self._handle_paint,
            # Composition
            "composite": self._handle_composite,
            "watermark": self._handle_watermark,
            "overlay": self._handle_composite,
            # Info
            "identify": self._handle_identify,
            "metadata": self._handle_identify,
        }
    
    def _validate_image_path(self, path: str, param_name: str = "path") -> tuple:
        """Validate image file path."""
        if not path:
            return False, f"{param_name} is required"
        return self._validate_path(path, allowed_extensions=self.ALLOWED_EXTENSIONS)
    
    # Format Conversion
    async def _handle_convert(self, action) -> Response:
        """Convert image format."""
        params = action.params
        input_file = params.get("input") or params.get("input_path") or params.get("source")
        output_file = params.get("output") or params.get("output_path") or params.get("target")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        # Validate paths
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        is_valid, error = self._validate_image_path(output_file, "output")
        if not is_valid:
            return Response(success=False, error=error)
        
        # Build command
        cmd_args = [input_file]
        
        # Quality
        quality = params.get("quality")
        if quality:
            cmd_args.extend(["-quality", str(quality)])
        
        # Strip metadata
        if params.get("strip_metadata"):
            cmd_args.append("-strip")
        
        cmd_args.append(output_file)
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Size Operations
    async def _handle_resize(self, action) -> Response:
        """Resize image."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        size = params.get("size") or params.get("geometry") or params.get("dimensions")
        
        if not input_file or not output_file or not size:
            return Response(success=False, error="input, output, and size are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-resize", str(size)]
        
        # Filter
        filter_type = params.get("filter")
        if filter_type:
            cmd_args.extend(["-filter", filter_type])
        
        cmd_args.append(output_file)
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_crop(self, action) -> Response:
        """Crop image."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        width = params.get("width")
        height = params.get("height")
        x = params.get("x", 0)
        y = params.get("y", 0)
        
        if not input_file or not output_file or not width or not height:
            return Response(success=False, error="input, output, width, and height are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        geometry = f"{width}x{height}+{x}+{y}"
        cmd_args = [input_file, "-crop", geometry, "+repage", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_trim(self, action) -> Response:
        """Trim image edges."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        fuzz = params.get("fuzz", 0)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-trim"]
        if fuzz:
            cmd_args.extend(["-fuzz", f"{fuzz}%"])
        cmd_args.extend(["+repage", output_file])
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Filters
    async def _handle_blur(self, action) -> Response:
        """Apply blur."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        radius = params.get("radius") or params.get("sigma", 0)
        sigma = params.get("sigma", radius)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        blur_geom = f"{radius}x{sigma}"
        cmd_args = [input_file, "-blur", blur_geom, output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_sharpen(self, action) -> Response:
        """Apply sharpen."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        radius = params.get("radius", 0)
        sigma = params.get("sigma", 1)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        sharpen_geom = f"{radius}x{sigma}"
        cmd_args = [input_file, "-sharpen", sharpen_geom, output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_edge(self, action) -> Response:
        """Detect edges."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        radius = params.get("radius", 0)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-edge", str(radius), output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Color Operations
    async def _handle_brightness(self, action) -> Response:
        """Adjust brightness."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        brightness = params.get("brightness") or params.get("value", 0)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-brightness-contrast", str(brightness), output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_contrast(self, action) -> Response:
        """Adjust contrast."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        contrast = params.get("contrast") or params.get("value", 0)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-brightness-contrast", f"0x{contrast}", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_grayscale(self, action) -> Response:
        """Convert to grayscale."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-colorspace", "Gray", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_sepia(self, action) -> Response:
        """Apply sepia tone."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        threshold = params.get("threshold", 80)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-sepia-tone", f"{threshold}%", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_invert(self, action) -> Response:
        """Invert colors."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-negate", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Effects
    async def _handle_vignette(self, action) -> Response:
        """Apply vignette effect."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-vignette", "0x50", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_charcoal(self, action) -> Response:
        """Apply charcoal effect."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        radius = params.get("radius", 0)
        sigma = params.get("sigma", 1)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-charcoal", f"{radius}x{sigma}", output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_paint(self, action) -> Response:
        """Apply oil paint effect."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        radius = params.get("radius") or params.get("value", 3)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [input_file, "-paint", str(radius), output_file]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Composition
    async def _handle_composite(self, action) -> Response:
        """Composite images together."""
        params = action.params
        base_image = params.get("base") or params.get("base_image")
        overlay_image = params.get("overlay") or params.get("overlay_image")
        output_file = params.get("output") or params.get("output_path")
        gravity = params.get("gravity", "center")
        geometry = params.get("geometry") or params.get("position", "+0+0")
        compose = params.get("compose") or params.get("mode", "over")
        
        if not base_image or not overlay_image or not output_file:
            return Response(success=False, error="base, overlay, and output are required")
        
        # Validate images
        for img, name in [(base_image, "base"), (overlay_image, "overlay")]:
            is_valid, error = self._validate_image_path(img, name)
            if not is_valid:
                return Response(success=False, error=error)
        
        cmd_args = [
            base_image, overlay_image,
            "-gravity", gravity,
            "-geometry", geometry,
            "-compose", compose,
            "-composite", output_file
        ]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_watermark(self, action) -> Response:
        """Add watermark to image."""
        params = action.params
        input_file = params.get("input") or params.get("input_path")
        output_file = params.get("output") or params.get("output_path")
        text = params.get("text") or params.get("watermark")
        fontsize = params.get("fontsize") or params.get("size", 24)
        color = params.get("color", "white")
        gravity = params.get("gravity", "southeast")
        opacity = params.get("opacity", 50)
        
        if not input_file or not output_file or not text:
            return Response(success=False, error="input, output, and text are required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_args = [
            input_file,
            "-gravity", gravity,
            "-pointsize", str(fontsize),
            "-fill", f"{color}{int(opacity/100*255):02x}",
            "-annotate", "+10+10", text,
            output_file
        ]
        
        result = await self._run_imagemagick(cmd_args)
        return self._cli_result_to_response(result)
    
    # Info Operations
    async def _handle_identify(self, action) -> Response:
        """Get image information."""
        params = action.params
        input_file = params.get("input") or params.get("file") or params.get("path")
        verbose = params.get("verbose", False)
        
        if not input_file:
            return Response(success=False, error="input file is required")
        
        is_valid, error = self._validate_image_path(input_file, "input")
        if not is_valid:
            return Response(success=False, error=error)
        
        cmd_parts = ["identify"]
        if verbose:
            cmd_parts.append("-verbose")
        cmd_parts.append(input_file)
        
        result = await self._run_imagemagick_direct(cmd_parts)
        return self._cli_result_to_response(result)
    
    # Helper methods
    async def _run_imagemagick(self, args: List[str], timeout: Optional[int] = None) -> CLIResult:
        """Run ImageMagick convert command."""
        if not self._cli_executable:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="ImageMagick not initialized",
                error="ImageMagick (convert) not found"
            )
        
        return await self._run_cli("", args=args, timeout=timeout)
    
    async def _run_imagemagick_direct(self, cmd_parts: List[str], timeout: Optional[int] = None) -> CLIResult:
        """Run ImageMagick command directly (for mogrify, montage, identify)."""
        import asyncio
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout or self.default_timeout
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
                error=f"Command timed out after {timeout or self.default_timeout}s"
            )
        except Exception as e:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e)
            )
