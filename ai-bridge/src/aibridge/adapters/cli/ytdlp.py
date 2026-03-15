"""
yt-dlp Adapter for AI-Bridge

Wraps yt-dlp CLI to provide video downloading capabilities.

Requires: yt-dlp installed: pip install yt-dlp

Usage:
    adapter = YTDLPAdapter()
    await adapter.initialize()
    
    # Download video
    result = await adapter.execute(Action(
        name="download",
        params={"url": "https://youtube.com/watch?v=...", "format": "mp4"}
    ))
"""

from typing import Any, Callable, Dict, List, Optional
from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult


class YTDLPAdapter(CLIAdapter):
    """AI-Bridge adapter for yt-dlp video downloading."""
    
    cli_name = "yt-dlp"
    cli_module = "yt-dlp"
    auto_install_cli = True
    default_timeout = 600  # Downloads can take time
    
    ALLOWED_EXTENSIONS = {
        '.mp4', '.mkv', '.webm', '.avi', '.mov',
        '.mp3', '.m4a', '.wav', '.flac', '.ogg',
        '.srt', '.vtt', '.txt'
    }
    
    SUPPORTED_ACTIONS = [
        "download", "dl",
        "audio", "extract_audio",
        "video", "download_video",
        "playlist", "download_playlist",
        "info", "get_info",
        "list_formats",
        "subtitle", "download_subtitle",
        "thumbnail", "download_thumbnail",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        return {
            "download": self._handle_download,
            "dl": self._handle_download,
            "audio": self._handle_audio,
            "extract_audio": self._handle_audio,
            "video": self._handle_video,
            "download_video": self._handle_video,
            "playlist": self._handle_playlist,
            "download_playlist": self._handle_playlist,
            "info": self._handle_info,
            "get_info": self._handle_info,
            "list_formats": self._handle_list_formats,
            "subtitle": self._handle_subtitle,
            "download_subtitle": self._handle_subtitle,
            "thumbnail": self._handle_thumbnail,
            "download_thumbnail": self._handle_thumbnail,
        }
    
    async def _handle_download(self, action: Action) -> Response:
        """Download video with options."""
        params = action.params
        url = params.get("url") or params.get("link")
        output_dir = params.get("output_dir") or params.get("directory", ".")
        format_spec = params.get("format") or params.get("quality", "best")
        
        if not url:
            return Response(success=False, error="url is required")
        
        # Validate URL (basic check)
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = [url, "-f", format_spec]
        
        # Output directory
        cmd_args.extend(["-o", f"{output_dir}/%(title)s.%(ext)s"])
        
        # Additional options
        if params.get("audio_only"):
            cmd_args.extend(["-x", "--audio-format", params.get("audio_format", "mp3")])
        
        if params.get("subtitles"):
            cmd_args.extend(["--write-subs", "--sub-langs", params.get("sub_lang", "en")])
        
        if params.get("thumbnail"):
            cmd_args.append("--write-thumbnail")
        
        if params.get("metadata"):
            cmd_args.append("--add-metadata")
        
        if params.get("playlist"):
            cmd_args.append("--yes-playlist")
        else:
            cmd_args.append("--no-playlist")
        
        result = await self._run_cli("", args=cmd_args, timeout=params.get("timeout", 600))
        return self._cli_result_to_response(result)
    
    async def _handle_audio(self, action: Action) -> Response:
        """Extract audio only."""
        params = action.params
        params["audio_only"] = True
        return await self._handle_download(action)
    
    async def _handle_video(self, action: Action) -> Response:
        """Download video only."""
        params = action.params
        params["audio_only"] = False
        return await self._handle_download(action)
    
    async def _handle_playlist(self, action: Action) -> Response:
        """Download playlist."""
        params = action.params
        params["playlist"] = True
        return await self._handle_download(action)
    
    async def _handle_info(self, action: Action) -> Response:
        """Get video info without downloading."""
        params = action.params
        url = params.get("url") or params.get("link")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = [url, "-j"]  # JSON output
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_list_formats(self, action: Action) -> Response:
        """List available formats for a video."""
        params = action.params
        url = params.get("url") or params.get("link")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = [url, "-F"]  # List formats
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_subtitle(self, action: Action) -> Response:
        """Download subtitles only."""
        params = action.params
        url = params.get("url") or params.get("link")
        lang = params.get("lang") or params.get("language", "en")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = [url, "--write-subs", "--sub-langs", lang, "--skip-download"]
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
    
    async def _handle_thumbnail(self, action: Action) -> Response:
        """Download thumbnail only."""
        params = action.params
        url = params.get("url") or params.get("link")
        
        if not url:
            return Response(success=False, error="url is required")
        
        if not url.startswith(("http://", "https://")):
            return Response(success=False, error="invalid URL format")
        
        cmd_args = [url, "--write-thumbnail", "--skip-download"]
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
