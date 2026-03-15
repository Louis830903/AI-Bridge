"""FFmpeg Adapter for AI-Bridge

Provides video/audio processing capabilities through FFmpeg CLI.
"""

from typing import Any, Callable, Dict

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter


class FFmpegAdapter(CLIAdapter):
    """AI-Bridge adapter for FFmpeg video/audio processing."""
    
    cli_name = "ffmpeg"
    cli_module = None  # FFmpeg is a system binary
    auto_install_cli = False

    SUPPORTED_ACTIONS = [
        "convert", "extract_audio", "trim", "concat", "scale",
        "add_audio", "probe", "thumbnail", "gif", "compress"
    ]

    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Map action names to handler methods."""
        return {
            "convert": self._handle_convert,
            "extract_audio": self._handle_extract_audio,
            "trim": self._handle_trim,
            "scale": self._handle_scale,
            "probe": self._handle_probe,
            "thumbnail": self._handle_thumbnail,
            "compress": self._handle_compress,
        }

    async def _handle_convert(self, action: Action) -> Response:
        """Convert video format."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = ["-i", input_file]
        
        if params.get("codec"):
            args.extend(["-c:v", params["codec"]])
        if params.get("audio_codec"):
            args.extend(["-c:a", params["audio_codec"]])
        
        args.extend(["-y", output_file])
        
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _handle_extract_audio(self, action: Action) -> Response:
        """Extract audio from video."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = ["-i", input_file, "-vn", "-y", output_file]
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _handle_trim(self, action: Action) -> Response:
        """Trim video."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_trimmed.")
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = ["-i", input_file]
        
        if params.get("start"):
            args.extend(["-ss", str(params["start"])])
        if params.get("duration"):
            args.extend(["-t", str(params["duration"])])
        
        args.extend(["-c", "copy", "-y", output_file])
        
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _handle_scale(self, action: Action) -> Response:
        """Scale video."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        width = params.get("width", -1)
        height = params.get("height", -1)
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = ["-i", input_file, "-vf", f"scale={width}:{height}", "-y", output_file]
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _handle_probe(self, action: Action) -> Response:
        """Get media file information."""
        input_file = action.params.get("input")
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        # Use ffprobe instead of ffmpeg
        import subprocess
        import json
        
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", input_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return Response(success=True, data=data)
            else:
                return Response(success=False, error=result.stderr)
        except Exception as e:
            return Response(success=False, error=str(e))

    async def _handle_thumbnail(self, action: Action) -> Response:
        """Generate thumbnail from video."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        time = params.get("time", "00:00:01")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = ["-i", input_file, "-ss", time, "-vframes", "1", "-y", output_file]
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _handle_compress(self, action: Action) -> Response:
        """Compress video."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        crf = params.get("crf", 23)  # Lower = better quality
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = ["-i", input_file, "-c:v", "libx264", "-crf", str(crf), "-y", output_file]
        result = await self._run_cli_raw(args)
        return self._cli_result_to_response(result)

    async def _run_cli_raw(self, args: list) -> 'CLIResult':
        """Run FFmpeg directly with raw arguments."""
        import asyncio
        import subprocess
        from .base import CLIResult
        
        cmd = ["ffmpeg"] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            
            return CLIResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                data=None,
                error=None if proc.returncode == 0 else stderr.decode('utf-8', errors='replace')
            )
        except Exception as e:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e)
            )
