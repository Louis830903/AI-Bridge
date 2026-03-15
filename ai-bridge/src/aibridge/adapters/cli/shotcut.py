"""
Shotcut Adapter for AI-Bridge

Wraps Shotcut's MLT CLI (melt) to provide video editing capabilities
to AI agents through the AI-Bridge protocol.

Requires:
    Shotcut/MLT installed and in PATH (melt command)

Usage:
    adapter = ShotcutAdapter()
    await adapter.initialize()
    
    # Create new project
    result = await adapter.execute(Action(
        name="project_new",
        params={"name": "MyEdit", "profile": "hd1080p30"}
    ))
    
    # Add video to timeline
    result = await adapter.execute(Action(
        name="timeline_add_clip",
        params={"file_path": "/path/to/video.mp4", "track": 0}
    ))
"""

from typing import Any, Callable, Dict, List, Optional

from aibridge.core.protocol import Response
from .base import CLIAdapter, CLIResult


class ShotcutAdapter(CLIAdapter):
    """
    AI-Bridge adapter for Shotcut/MLT video editing.
    
    Provides:
    - Project management (new, open, save)
    - Timeline editing (add clips, trim, split)
    - Multi-track support
    - Transitions and effects
    - Filters (color correction, blur, etc.)
    - Audio mixing
    - Text/titles overlay
    - Export to various formats
    """
    
    # CLI configuration
    cli_name = "melt"  # MLT framework command-line tool
    cli_module = None
    auto_install_cli = False
    default_timeout = 300
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv',
        '.mp3', '.aac', '.wav', '.ogg', '.m4a', '.wma',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.mlt'
    }
    
    # Supported action types
    SUPPORTED_ACTIONS = [
        # Project
        "project_new", "project_open", "project_save", "project_close",
        "project_info", "project_set_profile",
        # Timeline
        "timeline_add_clip", "timeline_remove_clip", "timeline_move_clip",
        "timeline_trim_clip", "timeline_split_clip", "timeline_add_track",
        "timeline_remove_track", "timeline_clear",
        # Transitions
        "transition_add", "transition_remove",
        # Filters/Effects
        "filter_add", "filter_remove",
        "effect_brightness", "effect_contrast", "effect_blur",
        # Audio
        "audio_adjust_volume", "audio_fade_in", "audio_fade_out",
        # Text/Titles
        "text_add",
        # Preview/Export
        "preview", "export", "export_frame",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable]:
        """Map action names to handler methods."""
        return {
            # Project
            "project_new": self._handle_project_new,
            "project_open": self._handle_project_open,
            "project_save": self._handle_project_save,
            "project_close": self._handle_project_close,
            "project_info": self._handle_project_info,
            # Timeline
            "timeline_add_clip": self._handle_timeline_add_clip,
            "timeline_remove_clip": self._handle_timeline_remove_clip,
            "timeline_move_clip": self._handle_timeline_move_clip,
            "timeline_trim_clip": self._handle_timeline_trim_clip,
            "timeline_split_clip": self._handle_timeline_split_clip,
            "timeline_add_track": self._handle_timeline_add_track,
            "timeline_clear": self._handle_timeline_clear,
            # Transitions
            "transition_add": self._handle_transition_add,
            "transition_remove": self._handle_transition_remove,
            # Filters
            "filter_add": self._handle_filter_add,
            "filter_remove": self._handle_filter_remove,
            "effect_brightness": self._handle_effect_brightness,
            "effect_contrast": self._handle_effect_contrast,
            "effect_blur": self._handle_effect_blur,
            # Audio
            "audio_adjust_volume": self._handle_audio_adjust_volume,
            "audio_fade_in": self._handle_audio_fade_in,
            "audio_fade_out": self._handle_audio_fade_out,
            # Text
            "text_add": self._handle_text_add,
            # Export
            "export": self._handle_export,
            "export_frame": self._handle_export_frame,
            "preview": self._handle_preview,
        }
    
    # Project Handlers
    async def _handle_project_new(self, action) -> Response:
        """Create a new project."""
        params = action.params
        result = await self._run_cli(
            "project",
            args=["new"],
            kwargs={
                "name": params.get("name", "Untitled"),
                "profile": params.get("profile", "hd1080p30"),
            }
        )
        return self._cli_result_to_response(result)
    
    async def _handle_project_open(self, action) -> Response:
        """Open a Shotcut project file."""
        file_path = action.params.get("file_path") or action.params.get("path")
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        self._session_state["current_file"] = file_path
        result = await self._run_cli("project", args=["open", file_path])
        return self._cli_result_to_response(result)
    
    async def _handle_project_save(self, action) -> Response:
        """Save the current project."""
        kwargs = {}
        if "path" in action.params:
            kwargs["path"] = action.params["path"]
        
        result = await self._run_cli("project", args=["save"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_project_close(self, action) -> Response:
        """Close the current project."""
        self._session_state.pop("current_file", None)
        result = await self._run_cli("project", args=["close"])
        return self._cli_result_to_response(result)
    
    async def _handle_project_info(self, action) -> Response:
        """Get project information."""
        result = await self._run_cli("project", args=["info"])
        return self._cli_result_to_response(result)
    
    # Timeline Handlers
    async def _handle_timeline_add_clip(self, action) -> Response:
        """Add a clip to the timeline."""
        params = action.params
        file_path = params.get("file_path") or params.get("path") or params.get("source")
        
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        kwargs = {
            "track": params.get("track", 0),
            "position": params.get("position") or params.get("in", 0),
        }
        
        # Optional in/out points for trimming
        if "in_point" in params or "in" in params:
            kwargs["in"] = params.get("in_point") or params.get("in")
        if "out_point" in params or "out" in params:
            kwargs["out"] = params.get("out_point") or params.get("out")
        
        result = await self._run_cli("timeline", args=["add-clip", file_path], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_remove_clip(self, action) -> Response:
        """Remove a clip from the timeline."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id") or params.get("index")
        
        if clip_id is None:
            return Response(success=False, error="clip_id is required")
        
        kwargs = {"track": params.get("track", 0)}
        result = await self._run_cli("timeline", args=["remove-clip", str(clip_id)], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_move_clip(self, action) -> Response:
        """Move a clip to a new position."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        position = params.get("position") or params.get("to")
        
        if clip_id is None or position is None:
            return Response(success=False, error="clip_id and position are required")
        
        kwargs = {
            "track": params.get("track", 0),
            "new-track": params.get("new_track"),
        }
        
        result = await self._run_cli(
            "timeline",
            args=["move-clip", str(clip_id), str(position)],
            kwargs=kwargs
        )
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_trim_clip(self, action) -> Response:
        """Trim a clip on the timeline."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        
        if clip_id is None:
            return Response(success=False, error="clip_id is required")
        
        kwargs = {
            "track": params.get("track", 0),
            "in": params.get("in_point") or params.get("in"),
            "out": params.get("out_point") or params.get("out"),
        }
        
        result = await self._run_cli("timeline", args=["trim-clip", str(clip_id)], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_split_clip(self, action) -> Response:
        """Split a clip at a specific position."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        position = params.get("position") or params.get("at")
        
        if clip_id is None or position is None:
            return Response(success=False, error="clip_id and position are required")
        
        kwargs = {"track": params.get("track", 0)}
        result = await self._run_cli(
            "timeline",
            args=["split-clip", str(clip_id), str(position)],
            kwargs=kwargs
        )
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_add_track(self, action) -> Response:
        """Add a new track to the timeline."""
        params = action.params
        kwargs = {
            "type": params.get("type", "video"),  # video or audio
            "index": params.get("index"),
        }
        
        result = await self._run_cli("timeline", args=["add-track"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_timeline_clear(self, action) -> Response:
        """Clear all clips from timeline."""
        track = action.params.get("track")
        if track is not None:
            result = await self._run_cli("timeline", args=["clear", str(track)])
        else:
            result = await self._run_cli("timeline", args=["clear-all"])
        return self._cli_result_to_response(result)
    
    # Transition Handlers
    async def _handle_transition_add(self, action) -> Response:
        """Add a transition between clips."""
        params = action.params
        trans_type = params.get("type") or params.get("transition", "dissolve")
        
        kwargs = {
            "duration": params.get("duration", 1.0),
            "track": params.get("track", 0),
            "clip-a": params.get("clip_a") or params.get("clip1"),
            "clip-b": params.get("clip_b") or params.get("clip2"),
        }
        
        result = await self._run_cli("transition", args=["add", trans_type], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_transition_remove(self, action) -> Response:
        """Remove a transition."""
        trans_id = action.params.get("transition") or action.params.get("id")
        if trans_id is None:
            return Response(success=False, error="transition id is required")
        
        result = await self._run_cli("transition", args=["remove", str(trans_id)])
        return self._cli_result_to_response(result)
    
    # Filter/Effect Handlers
    async def _handle_filter_add(self, action) -> Response:
        """Add a filter to a clip."""
        params = action.params
        filter_name = params.get("filter") or params.get("name")
        clip_id = params.get("clip") or params.get("clip_id")
        
        if not filter_name:
            return Response(success=False, error="filter name is required")
        
        kwargs = {"track": params.get("track", 0)}
        if clip_id:
            kwargs["clip"] = clip_id
        
        # Add filter-specific parameters
        for key, value in params.items():
            if key not in ["filter", "name", "clip", "clip_id", "track"]:
                kwargs[key] = value
        
        result = await self._run_cli("filter", args=["add", filter_name], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_filter_remove(self, action) -> Response:
        """Remove a filter from a clip."""
        params = action.params
        filter_id = params.get("filter") or params.get("filter_id")
        clip_id = params.get("clip") or params.get("clip_id")
        
        kwargs = {"track": params.get("track", 0)}
        if clip_id:
            kwargs["clip"] = clip_id
        if filter_id:
            kwargs["id"] = filter_id
        
        result = await self._run_cli("filter", args=["remove"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_effect_brightness(self, action) -> Response:
        """Adjust brightness of a clip."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        value = params.get("value") or params.get("brightness", 0)
        
        kwargs = {
            "track": params.get("track", 0),
            "brightness": value,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("filter", args=["add", "brightness"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_effect_contrast(self, action) -> Response:
        """Adjust contrast of a clip."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        value = params.get("value") or params.get("contrast", 1.0)
        
        kwargs = {
            "track": params.get("track", 0),
            "contrast": value,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("filter", args=["add", "contrast"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_effect_blur(self, action) -> Response:
        """Apply blur to a clip."""
        params = action.params
        clip_id = params.get("clip") or params.get("clip_id")
        radius = params.get("radius") or params.get("value", 5)
        
        kwargs = {
            "track": params.get("track", 0),
            "radius": radius,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("filter", args=["add", "blur"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    # Audio Handlers
    async def _handle_audio_adjust_volume(self, action) -> Response:
        """Adjust audio volume of a clip or track."""
        params = action.params
        volume = params.get("volume") or params.get("gain") or params.get("level", 100)
        clip_id = params.get("clip") or params.get("clip_id")
        
        kwargs = {
            "track": params.get("track", 0),
            "volume": volume,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("audio", args=["set-volume"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_audio_fade_in(self, action) -> Response:
        """Add audio fade in."""
        params = action.params
        duration = params.get("duration") or params.get("length", 1.0)
        clip_id = params.get("clip") or params.get("clip_id")
        
        kwargs = {
            "track": params.get("track", 0),
            "duration": duration,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("audio", args=["fade-in"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_audio_fade_out(self, action) -> Response:
        """Add audio fade out."""
        params = action.params
        duration = params.get("duration") or params.get("length", 1.0)
        clip_id = params.get("clip") or params.get("clip_id")
        
        kwargs = {
            "track": params.get("track", 0),
            "duration": duration,
        }
        if clip_id:
            kwargs["clip"] = clip_id
        
        result = await self._run_cli("audio", args=["fade-out"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    # Text/Titles Handlers
    async def _handle_text_add(self, action) -> Response:
        """Add text overlay to timeline."""
        params = action.params
        text = params.get("text") or params.get("content")
        
        if not text:
            return Response(success=False, error="text content is required")
        
        kwargs = {
            "track": params.get("track", 1),  # Usually overlay track
            "position": params.get("position") or params.get("in", 0),
            "duration": params.get("duration") or params.get("length", 5.0),
            "x": params.get("x", 50),  # Center position (percent)
            "y": params.get("y", 90),  # Bottom position (percent)
            "size": params.get("size") or params.get("font_size", 48),
            "color": params.get("color", "white"),
            "font": params.get("font"),
        }
        
        result = await self._run_cli("text", args=["add", text], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    # Export Handlers
    async def _handle_export(self, action) -> Response:
        """Export the project to a video file."""
        params = action.params
        output_path = params.get("output_path") or params.get("output") or params.get("path")
        
        if not output_path:
            return Response(success=False, error="output_path is required")
        
        kwargs = {
            "format": params.get("format", "mp4"),
            "codec": params.get("codec", "libx264"),
            "quality": params.get("quality") or params.get("crf", 23),
            "preset": params.get("preset", "medium"),
        }
        
        # Resolution
        resolution = params.get("resolution")
        if resolution:
            kwargs["width"] = resolution[0]
            kwargs["height"] = resolution[1]
        else:
            if "width" in params:
                kwargs["width"] = params["width"]
            if "height" in params:
                kwargs["height"] = params["height"]
        
        # Frame rate
        if "fps" in params or "framerate" in params:
            kwargs["fps"] = params.get("fps") or params.get("framerate")
        
        result = await self._run_cli("export", args=[output_path], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_export_frame(self, action) -> Response:
        """Export a single frame as image."""
        params = action.params
        output_path = params.get("output_path") or params.get("output") or params.get("path")
        time_pos = params.get("time") or params.get("position") or params.get("frame", 0)
        
        if not output_path:
            return Response(success=False, error="output_path is required")
        
        kwargs = {
            "time": time_pos,
            "format": params.get("format", "png"),
            "quality": params.get("quality", 95),
        }
        
        if "width" in params:
            kwargs["width"] = params["width"]
        if "height" in params:
            kwargs["height"] = params["height"]
        
        result = await self._run_cli("export-frame", args=[output_path], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_preview(self, action) -> Response:
        """Start preview playback."""
        params = action.params
        kwargs = {}
        
        if "in" in params or "start" in params:
            kwargs["in"] = params.get("in") or params.get("start")
        if "out" in params or "end" in params:
            kwargs["out"] = params.get("out") or params.get("end")
        
        # Preview is non-blocking, just returns immediately
        result = await self._run_cli("preview", kwargs=kwargs)
        return self._cli_result_to_response(result)
