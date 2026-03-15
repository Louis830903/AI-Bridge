"""GIMP Adapter for AI-Bridge

Wraps CLI-Anything generated GIMP CLI to provide image editing capabilities.

Requires: pip install cli-anything-gimp
"""

from typing import Any, Callable, Dict

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter


class GIMPAdapter(CLIAdapter):
    """AI-Bridge adapter for GIMP image editing via CLI-Anything generated CLI."""
    
    cli_name = "gimp-cli"
    cli_module = "cli_anything.gimp"
    auto_install_cli = False

    SUPPORTED_ACTIONS = [
        "project_new", "project_open", "project_save", "project_close",
        "layer_add", "layer_remove", "layer_list",
        "filter_blur", "filter_brightness", "filter_contrast",
        "canvas_resize", "canvas_crop", "canvas_rotate",
        "import_file", "export_image",
        "undo", "redo",
    ]

    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Map action names to handler methods."""
        return {
            "project_new": self._handle_project_new,
            "project_open": self._handle_project_open,
            "project_save": self._handle_project_save,
            "project_close": self._handle_project_close,
            "layer_add": self._handle_layer_add,
            "layer_remove": self._handle_layer_remove,
            "layer_list": self._handle_layer_list,
            "filter_blur": self._handle_filter_blur,
            "filter_brightness": self._handle_filter_brightness,
            "filter_contrast": self._handle_filter_contrast,
            "canvas_resize": self._handle_canvas_resize,
            "canvas_crop": self._handle_canvas_crop,
            "canvas_rotate": self._handle_canvas_rotate,
            "import_file": self._handle_import,
            "export_image": self._handle_export,
            "undo": self._handle_undo,
            "redo": self._handle_redo,
            # Aliases
            "open_image": self._handle_project_open,
            "apply_filter": self._handle_filter_add,
            "save_image": self._handle_project_save,
        }

    async def _handle_project_new(self, action: Action) -> Response:
        """Create a new project."""
        params = action.params
        result = await self._run_cli(
            "project",
            args=["new"],
            kwargs={
                "width": params.get("width", 1920),
                "height": params.get("height", 1080),
                "name": params.get("name"),
            }
        )
        return self._cli_result_to_response(result)

    async def _handle_project_open(self, action: Action) -> Response:
        """Open an image file or project."""
        file_path = action.params.get("file_path") or action.params.get("path")
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        self._session_state["current_file"] = file_path
        result = await self._run_cli("project", args=["open", file_path])
        return self._cli_result_to_response(result)

    async def _handle_project_save(self, action: Action) -> Response:
        """Save the current project."""
        params = action.params
        kwargs = {}
        if "path" in params:
            kwargs["path"] = params["path"]
        if "format" in params:
            kwargs["format"] = params["format"]
        
        result = await self._run_cli("project", args=["save"], kwargs=kwargs)
        return self._cli_result_to_response(result)

    async def _handle_project_close(self, action: Action) -> Response:
        """Close the current project."""
        self._session_state.pop("current_file", None)
        result = await self._run_cli("project", args=["close"])
        return self._cli_result_to_response(result)

    async def _handle_layer_add(self, action: Action) -> Response:
        """Add a new layer."""
        params = action.params
        result = await self._run_cli(
            "layer",
            args=["add"],
            kwargs={
                "name": params.get("name"),
                "width": params.get("width"),
                "height": params.get("height"),
                "fill": params.get("fill", "transparent"),
            }
        )
        return self._cli_result_to_response(result)

    async def _handle_layer_remove(self, action: Action) -> Response:
        """Remove a layer."""
        layer = action.params.get("layer") or action.params.get("index")
        if layer is None:
            return Response(success=False, error="layer index or name is required")
        
        result = await self._run_cli("layer", args=["remove", str(layer)])
        return self._cli_result_to_response(result)

    async def _handle_layer_list(self, action: Action) -> Response:
        """List all layers."""
        result = await self._run_cli("layer", args=["list"])
        return self._cli_result_to_response(result)

    async def _handle_filter_add(self, action: Action) -> Response:
        """Add a filter to the current layer."""
        params = action.params
        filter_name = params.get("filter") or params.get("name")
        if not filter_name:
            return Response(success=False, error="filter name is required")
        
        result = await self._run_cli(
            "filter",
            args=["add", filter_name],
            kwargs={"layer": params.get("layer")}
        )
        return self._cli_result_to_response(result)

    async def _handle_filter_blur(self, action: Action) -> Response:
        """Apply blur filter."""
        params = action.params
        result = await self._run_cli(
            "filter",
            args=["add", "blur"],
            kwargs={"layer": params.get("layer"), "radius": params.get("radius", 5)}
        )
        return self._cli_result_to_response(result)

    async def _handle_filter_brightness(self, action: Action) -> Response:
        """Adjust brightness."""
        params = action.params
        result = await self._run_cli(
            "filter",
            args=["add", "brightness"],
            kwargs={"layer": params.get("layer"), "factor": params.get("factor", 1.0)}
        )
        return self._cli_result_to_response(result)

    async def _handle_filter_contrast(self, action: Action) -> Response:
        """Adjust contrast."""
        params = action.params
        result = await self._run_cli(
            "filter",
            args=["add", "contrast"],
            kwargs={"layer": params.get("layer"), "factor": params.get("factor", 1.0)}
        )
        return self._cli_result_to_response(result)

    async def _handle_canvas_resize(self, action: Action) -> Response:
        """Resize canvas."""
        params = action.params
        result = await self._run_cli(
            "canvas",
            args=["resize"],
            kwargs={
                "width": params.get("width"),
                "height": params.get("height"),
                "anchor": params.get("anchor", "center"),
            }
        )
        return self._cli_result_to_response(result)

    async def _handle_canvas_crop(self, action: Action) -> Response:
        """Crop canvas."""
        params = action.params
        result = await self._run_cli(
            "canvas",
            args=["crop"],
            kwargs={
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "width": params.get("width"),
                "height": params.get("height"),
            }
        )
        return self._cli_result_to_response(result)

    async def _handle_canvas_rotate(self, action: Action) -> Response:
        """Rotate canvas."""
        params = action.params
        result = await self._run_cli(
            "canvas",
            args=["rotate"],
            kwargs={"angle": params.get("angle", 90), "expand": params.get("expand", True)}
        )
        return self._cli_result_to_response(result)

    async def _handle_import(self, action: Action) -> Response:
        """Import a file."""
        file_path = action.params.get("file_path") or action.params.get("path")
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        result = await self._run_cli(
            "media",
            args=["import", file_path],
            kwargs={"name": action.params.get("name")}
        )
        return self._cli_result_to_response(result)

    async def _handle_export(self, action: Action) -> Response:
        """Export the image."""
        params = action.params
        output_path = params.get("output_path") or params.get("path")
        if not output_path:
            return Response(success=False, error="output_path is required")
        
        result = await self._run_cli(
            "export",
            args=[output_path],
            kwargs={"format": params.get("format"), "quality": params.get("quality")}
        )
        return self._cli_result_to_response(result)

    async def _handle_undo(self, action: Action) -> Response:
        """Undo last action."""
        steps = action.params.get("steps", 1)
        result = await self._run_cli("history", args=["undo", str(steps)])
        return self._cli_result_to_response(result)

    async def _handle_redo(self, action: Action) -> Response:
        """Redo last undone action."""
        steps = action.params.get("steps", 1)
        result = await self._run_cli("history", args=["redo", str(steps)])
        return self._cli_result_to_response(result)
