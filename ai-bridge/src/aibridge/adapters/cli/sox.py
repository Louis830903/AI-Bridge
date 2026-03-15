"""SoX Adapter for AI-Bridge

Provides audio processing capabilities through SoX (Sound eXchange) CLI.
SoX is the Swiss Army knife of audio manipulation.

Installation: 
- macOS: brew install sox
- Ubuntu: apt install sox libsox-fmt-all
- Windows: Download from https://sourceforge.net/projects/sox/

Usage example:
```python
from aibridge.adapters.cli import SoXAdapter
from aibridge.core.protocol import Action

adapter = SoXAdapter()
await adapter.initialize()

# Convert audio format
result = await adapter.execute(Action(
    name="convert",
    params={"input": "input.wav", "output": "output.mp3"}
))

# Trim audio
result = await adapter.execute(Action(
    name="trim",
    params={"input": "audio.wav", "start": "0:00", "end": "0:30"}
))

# Mix/merge audio files
result = await adapter.execute(Action(
    name="mix",
    params={"inputs": ["track1.wav", "track2.wav"], "output": "mixed.wav"}
))
```
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult

logger = logging.getLogger(__name__)


class SoXAdapter(CLIAdapter):
    """AI-Bridge adapter for SoX audio processing."""
    
    cli_name = "sox"
    cli_module = None  # SoX is a system binary
    auto_install_cli = False
    
    SUPPORTED_ACTIONS = [
        "convert", "trim", "concat", "mix", "normalize",
        "fade", "speed", "reverse", "info", "silence",
        "bass", "treble", "equalizer", "reverb", "chorus"
    ]

    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Map action names to handler methods."""
        return {
            "convert": self._handle_convert,
            "trim": self._handle_trim,
            "concat": self._handle_concat,
            "mix": self._handle_mix,
            "normalize": self._handle_normalize,
            "fade": self._handle_fade,
            "speed": self._handle_speed,
            "reverse": self._handle_reverse,
            "info": self._handle_info,
            "silence": self._handle_silence,
            "effects": self._handle_effects,
        }

    async def _handle_convert(self, action: Action) -> Response:
        """Convert audio format."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        args = [input_file]
        
        # 可选参数
        if params.get("rate"):  # 采样率
            args.extend(["-r", str(params["rate"])])
        if params.get("channels"):  # 声道数
            args.extend(["-c", str(params["channels"])])
        if params.get("bits"):  # 位深
            args.extend(["-b", str(params["bits"])])
        
        args.append(output_file)
        
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_trim(self, action: Action) -> Response:
        """Trim audio to specified duration."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_trimmed.")
        start = params.get("start", "0")
        end = params.get("end")
        duration = params.get("duration")
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = [input_file, output_file, "trim", str(start)]
        
        if duration:
            args.append(str(duration))
        elif end:
            # 计算持续时间
            args.append(f"={end}")
        
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_concat(self, action: Action) -> Response:
        """Concatenate multiple audio files."""
        params = action.params
        inputs = params.get("inputs", [])
        output_file = params.get("output")
        
        if len(inputs) < 2:
            return Response(success=False, error="At least 2 input files required")
        if not output_file:
            return Response(success=False, error="output is required")
        
        args = inputs + [output_file]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_mix(self, action: Action) -> Response:
        """Mix multiple audio files together."""
        params = action.params
        inputs = params.get("inputs", [])
        output_file = params.get("output")
        
        if len(inputs) < 2:
            return Response(success=False, error="At least 2 input files required")
        if not output_file:
            return Response(success=False, error="output is required")
        
        # 使用 -m 参数进行混音
        args = ["-m"] + inputs + [output_file]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_normalize(self, action: Action) -> Response:
        """Normalize audio volume."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_normalized.")
        level = params.get("level", "-0.1")  # dB, 默认接近最大
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = [input_file, output_file, "norm", str(level)]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_fade(self, action: Action) -> Response:
        """Add fade in/out effects."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_faded.")
        fade_in = params.get("fade_in", 0)
        fade_out = params.get("fade_out", 0)
        fade_type = params.get("type", "t")  # t=triangle, q=quarter, h=half, l=linear, p=parabolic
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = [input_file, output_file, "fade", fade_type, str(fade_in)]
        
        if fade_out:
            # 需要指定总时长和淡出时长
            args.extend(["0", str(fade_out)])
        
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_speed(self, action: Action) -> Response:
        """Change playback speed."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_speed.")
        factor = params.get("factor", 1.0)  # 1.0 = normal, 2.0 = double speed
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = [input_file, output_file, "speed", str(factor)]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_reverse(self, action: Action) -> Response:
        """Reverse audio."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_reversed.")
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        args = [input_file, output_file, "reverse"]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_info(self, action: Action) -> Response:
        """Get audio file information."""
        input_file = action.params.get("input")
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        # 使用 soxi 获取信息
        result = await self._run_soxi(input_file)
        return self._cli_result_to_response(result)

    async def _handle_silence(self, action: Action) -> Response:
        """Remove silence from audio."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output") or input_file.replace(".", "_nosilence.")
        threshold = params.get("threshold", "1%")  # 静音阈值
        duration = params.get("duration", "0.5")  # 静音持续时间
        
        if not input_file:
            return Response(success=False, error="input is required")
        
        # silence 1 {duration} {threshold} : 移除开头静音
        # reverse silence 1 {duration} {threshold} reverse : 移除结尾静音
        args = [
            input_file, output_file,
            "silence", "1", str(duration), str(threshold),
            "reverse",
            "silence", "1", str(duration), str(threshold),
            "reverse"
        ]
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _handle_effects(self, action: Action) -> Response:
        """Apply custom effects chain."""
        params = action.params
        input_file = params.get("input")
        output_file = params.get("output")
        effects = params.get("effects", [])  # 效果列表
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        if not effects:
            return Response(success=False, error="effects list is required")
        
        args = [input_file, output_file] + effects
        result = await self._run_sox(args)
        return self._cli_result_to_response(result)

    async def _run_sox(self, args: List[str]) -> CLIResult:
        """Run SoX with arguments."""
        cmd = ["sox"] + args
        
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

    async def _run_soxi(self, input_file: str) -> CLIResult:
        """Run soxi to get audio info."""
        cmd = ["soxi", input_file]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            # 解析输出为结构化数据
            info = {}
            for line in stdout.decode('utf-8', errors='replace').strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip().lower().replace(' ', '_')] = value.strip()
            
            return CLIResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                data=info,
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
