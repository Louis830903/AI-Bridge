"""
Blender Adapter for AI-Bridge

Wraps Blender CLI to provide 3D modeling and rendering capabilities
to AI agents through the AI-Bridge protocol.

Requires:
    Blender installed and in PATH

Usage:
    adapter = BlenderAdapter()
    await adapter.initialize()
    
    # Create new scene
    result = await adapter.execute(Action(
        name="scene_new",
        params={"name": "MyScene"}
    ))
    
    # Add a cube
    result = await adapter.execute(Action(
        name="object_add",
        params={"type": "cube", "name": "MyCube", "location": [0, 0, 0]}
    ))
    
    # Render
    result = await adapter.execute(Action(
        name="render",
        params={"output_path": "/path/to/render.png", "resolution": [1920, 1080]}
    ))
"""

from typing import Any, Callable, Dict, List, Optional

from aibridge.core.protocol import Response
from .base import CLIAdapter, CLIResult


class BlenderAdapter(CLIAdapter):
    """
    AI-Bridge adapter for Blender 3D modeling and rendering.
    
    Provides:
    - Scene management (new, open, save)
    - Object operations (add, delete, duplicate, transform)
    - Materials and textures
    - Lighting and cameras
    - Animation (keyframes, curves)
    - Rendering (Eevee, Cycles)
    - Import/Export (FBX, OBJ, GLTF, etc.)
    """
    
    # CLI configuration
    cli_name = "blender"
    cli_module = None  # Blender is standalone
    auto_install_cli = False
    default_timeout = 300  # Rendering can take time
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.blend', '.obj', '.fbx', '.gltf', '.glb', '.stl', '.ply',
        '.x3d', '.dae', '.abc', '.usd', '.usda',
        '.png', '.jpg', '.jpeg', '.exr', '.hdr', '.tiff',
        '.mp4', '.mov', '.avi', '.mkv'
    }
    
    # Supported action types
    SUPPORTED_ACTIONS = [
        # Scene
        "scene_new", "scene_open", "scene_save", "scene_close",
        "scene_info", "scene_list", "scene_set_active",
        # Objects
        "object_add", "object_delete", "object_duplicate", "object_select",
        "object_deselect", "object_hide", "object_show", "object_list",
        "object_rename", "object_set_parent",
        # Transform
        "transform_translate", "transform_rotate", "transform_scale",
        "transform_reset", "transform_apply",
        # Materials
        "material_add", "material_remove", "material_assign",
        "material_set_color", "material_list",
        # Lighting
        "light_add", "light_set_energy", "light_set_color",
        # Camera
        "camera_add", "camera_set_active", "camera_set_resolution",
        # Animation
        "anim_keyframe_insert", "anim_set_frame",
        # Rendering
        "render", "render_preview", "render_settings",
        # Import/Export
        "import_file", "export_file",
        # Aliases
        "add_cube", "add_sphere", "add_light",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable]:
        """Map action names to handler methods."""
        return {
            # Scene
            "scene_new": self._handle_scene_new,
            "scene_open": self._handle_scene_open,
            "scene_save": self._handle_scene_save,
            "scene_close": self._handle_scene_close,
            "scene_info": self._handle_scene_info,
            "scene_list": self._handle_scene_list,
            # Objects
            "object_add": self._handle_object_add,
            "object_delete": self._handle_object_delete,
            "object_list": self._handle_object_list,
            # Transform
            "transform_translate": self._handle_transform_translate,
            "transform_rotate": self._handle_transform_rotate,
            "transform_scale": self._handle_transform_scale,
            # Materials
            "material_add": self._handle_material_add,
            "material_assign": self._handle_material_assign,
            "material_set_color": self._handle_material_set_color,
            "material_list": self._handle_material_list,
            # Lighting
            "light_add": self._handle_light_add,
            "light_set_energy": self._handle_light_set_energy,
            # Camera
            "camera_add": self._handle_camera_add,
            "camera_set_active": self._handle_camera_set_active,
            "camera_set_resolution": self._handle_camera_set_resolution,
            # Animation
            "anim_keyframe_insert": self._handle_anim_keyframe_insert,
            "anim_set_frame": self._handle_anim_set_frame,
            # Rendering
            "render": self._handle_render,
            "render_preview": self._handle_render_preview,
            # Import/Export
            "import_file": self._handle_import,
            "export_file": self._handle_export,
            # Aliases
            "add_cube": lambda a: self._handle_object_add_alias(a, "cube"),
            "add_sphere": lambda a: self._handle_object_add_alias(a, "sphere"),
            "add_light": self._handle_light_add,
        }
    
    # Scene Handlers
    async def _handle_scene_new(self, action) -> Response:
        """Create a new scene."""
        params = action.params
        result = await self._run_cli(
            "scene",
            args=["new"],
            kwargs={
                "name": params.get("name", "Scene"),
                "type": params.get("type", "empty"),
            }
        )
        return self._cli_result_to_response(result)
    
    async def _handle_scene_open(self, action) -> Response:
        """Open a Blender file."""
        file_path = action.params.get("file_path") or action.params.get("path")
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        self._session_state["current_file"] = file_path
        result = await self._run_cli("scene", args=["open", file_path])
        return self._cli_result_to_response(result)
    
    async def _handle_scene_save(self, action) -> Response:
        """Save the current scene."""
        kwargs = {}
        if "path" in action.params:
            kwargs["path"] = action.params["path"]
        
        result = await self._run_cli("scene", args=["save"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_scene_close(self, action) -> Response:
        """Close the current scene."""
        self._session_state.pop("current_file", None)
        result = await self._run_cli("scene", args=["close"])
        return self._cli_result_to_response(result)
    
    async def _handle_scene_info(self, action) -> Response:
        """Get scene information."""
        result = await self._run_cli("scene", args=["info"])
        return self._cli_result_to_response(result)
    
    async def _handle_scene_list(self, action) -> Response:
        """List all scenes."""
        result = await self._run_cli("scene", args=["list"])
        return self._cli_result_to_response(result)
    
    # Object Handlers
    async def _handle_object_add(self, action) -> Response:
        """Add a new object."""
        params = action.params
        obj_type = params.get("type") or params.get("object_type", "cube")
        
        kwargs = {
            "name": params.get("name"),
            "type": obj_type,
        }
        
        # Handle location
        location = params.get("location") or params.get("position")
        if location:
            kwargs["location"] = ",".join(str(x) for x in location)
        
        # Handle size/scale
        size = params.get("size") or params.get("radius")
        if size:
            kwargs["size"] = size
        
        result = await self._run_cli("object", args=["add"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_object_add_alias(self, action, obj_type: str) -> Response:
        """Alias handler for adding specific object types."""
        action.params["type"] = obj_type
        return await self._handle_object_add(action)
    
    async def _handle_object_delete(self, action) -> Response:
        """Delete selected or specified object."""
        obj_name = action.params.get("name") or action.params.get("object")
        kwargs = {}
        if obj_name:
            kwargs["name"] = obj_name
        
        result = await self._run_cli("object", args=["delete"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_object_list(self, action) -> Response:
        """List all objects in scene."""
        result = await self._run_cli("object", args=["list"])
        return self._cli_result_to_response(result)
    
    # Transform Handlers
    async def _handle_transform_translate(self, action) -> Response:
        """Translate/move object."""
        params = action.params
        location = params.get("location") or params.get("position") or params.get("translate")
        
        if not location or len(location) != 3:
            return Response(success=False, error="location must be [x, y, z]")
        
        kwargs = {
            "x": location[0],
            "y": location[1],
            "z": location[2],
        }
        
        obj_name = params.get("object") or params.get("name")
        if obj_name:
            kwargs["object"] = obj_name
        
        result = await self._run_cli("transform", args=["translate"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_transform_rotate(self, action) -> Response:
        """Rotate object."""
        params = action.params
        rotation = params.get("rotation") or params.get("euler")
        
        if rotation:
            kwargs = {
                "x": rotation[0] if len(rotation) > 0 else 0,
                "y": rotation[1] if len(rotation) > 1 else 0,
                "z": rotation[2] if len(rotation) > 2 else 0,
            }
        elif "axis" in params and "angle" in params:
            kwargs = {
                "axis": params["axis"],
                "angle": params["angle"],
            }
        else:
            return Response(success=False, error="rotation ([x,y,z]) or axis+angle required")
        
        obj_name = params.get("object") or params.get("name")
        if obj_name:
            kwargs["object"] = obj_name
        
        result = await self._run_cli("transform", args=["rotate"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_transform_scale(self, action) -> Response:
        """Scale object."""
        params = action.params
        scale = params.get("scale") or params.get("size")
        
        if not scale:
            return Response(success=False, error="scale factor or [x,y,z] required")
        
        if isinstance(scale, (int, float)):
            kwargs = {"x": scale, "y": scale, "z": scale}
        elif isinstance(scale, (list, tuple)) and len(scale) == 3:
            kwargs = {"x": scale[0], "y": scale[1], "z": scale[2]}
        else:
            return Response(success=False, error="scale must be number or [x,y,z]")
        
        obj_name = params.get("object") or params.get("name")
        if obj_name:
            kwargs["object"] = obj_name
        
        result = await self._run_cli("transform", args=["scale"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    # Material Handlers
    async def _handle_material_add(self, action) -> Response:
        """Add new material."""
        params = action.params
        result = await self._run_cli(
            "material",
            args=["add"],
            kwargs={"name": params.get("name")}
        )
        return self._cli_result_to_response(result)
    
    async def _handle_material_assign(self, action) -> Response:
        """Assign material to object."""
        params = action.params
        mat_name = params.get("material") or params.get("name")
        obj_name = params.get("object")
        
        if not mat_name:
            return Response(success=False, error="material name is required")
        
        kwargs = {"material": mat_name}
        if obj_name:
            kwargs["object"] = obj_name
        
        result = await self._run_cli("material", args=["assign"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_material_set_color(self, action) -> Response:
        """Set material color."""
        params = action.params
        mat_name = params.get("material") or params.get("name")
        color = params.get("color") or params.get("rgb")
        
        if not mat_name or not color:
            return Response(success=False, error="material name and color [r,g,b] required")
        
        kwargs = {
            "material": mat_name,
            "r": color[0],
            "g": color[1],
            "b": color[2],
        }
        
        result = await self._run_cli("material", args=["set-color"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_material_list(self, action) -> Response:
        """List all materials."""
        result = await self._run_cli("material", args=["list"])
        return self._cli_result_to_response(result)
    
    # Light Handlers
    async def _handle_light_add(self, action) -> Response:
        """Add a light to the scene."""
        params = action.params
        light_type = params.get("type", "point")
        
        kwargs = {
            "type": light_type,
            "name": params.get("name"),
        }
        
        location = params.get("location") or params.get("position")
        if location:
            kwargs["location"] = ",".join(str(x) for x in location)
        
        energy = params.get("energy") or params.get("power")
        if energy:
            kwargs["energy"] = energy
        
        result = await self._run_cli("light", args=["add"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_light_set_energy(self, action) -> Response:
        """Set light energy/power."""
        params = action.params
        light_name = params.get("light") or params.get("name")
        energy = params.get("energy") or params.get("power")
        
        if not light_name or energy is None:
            return Response(success=False, error="light name and energy required")
        
        result = await self._run_cli(
            "light",
            args=["set-energy", light_name, str(energy)]
        )
        return self._cli_result_to_response(result)
    
    # Camera Handlers
    async def _handle_camera_add(self, action) -> Response:
        """Add a camera."""
        params = action.params
        kwargs = {"name": params.get("name")}
        
        location = params.get("location") or params.get("position")
        if location:
            kwargs["location"] = ",".join(str(x) for x in location)
        
        rotation = params.get("rotation")
        if rotation:
            kwargs["rotation"] = ",".join(str(x) for x in rotation)
        
        result = await self._run_cli("camera", args=["add"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_camera_set_active(self, action) -> Response:
        """Set active camera."""
        camera_name = action.params.get("camera") or action.params.get("name")
        if not camera_name:
            return Response(success=False, error="camera name is required")
        
        result = await self._run_cli("camera", args=["set-active", camera_name])
        return self._cli_result_to_response(result)
    
    async def _handle_camera_set_resolution(self, action) -> Response:
        """Set render resolution."""
        params = action.params
        resolution = params.get("resolution") or [1920, 1080]
        
        kwargs = {
            "width": resolution[0] if isinstance(resolution, (list, tuple)) else params.get("width", 1920),
            "height": resolution[1] if isinstance(resolution, (list, tuple)) else params.get("height", 1080),
        }
        
        result = await self._run_cli("camera", args=["set-resolution"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    # Animation Handlers
    async def _handle_anim_keyframe_insert(self, action) -> Response:
        """Insert keyframe."""
        params = action.params
        kwargs = {
            "frame": params.get("frame"),
            "type": params.get("type", "location"),
        }
        
        obj_name = params.get("object") or params.get("name")
        if obj_name:
            kwargs["object"] = obj_name
        
        result = await self._run_cli("anim", args=["keyframe-insert"], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_anim_set_frame(self, action) -> Response:
        """Set current frame."""
        frame = action.params.get("frame")
        if frame is None:
            return Response(success=False, error="frame number is required")
        
        result = await self._run_cli("anim", args=["set-frame", str(frame)])
        return self._cli_result_to_response(result)
    
    # Render Handlers
    async def _handle_render(self, action) -> Response:
        """Render image or animation."""
        params = action.params
        output_path = params.get("output_path") or params.get("path")
        
        kwargs = {
            "engine": params.get("engine", "cycles"),
            "samples": params.get("samples", 128),
        }
        
        if output_path:
            kwargs["output"] = output_path
        
        resolution = params.get("resolution")
        if resolution:
            kwargs["width"] = resolution[0]
            kwargs["height"] = resolution[1]
        
        if params.get("animation"):
            kwargs["animation"] = True
            kwargs["frame-start"] = params.get("frame_start", 1)
            kwargs["frame-end"] = params.get("frame_end", 250)
        
        # Use longer timeout for rendering
        result = await self._run_cli(
            "render",
            kwargs=kwargs,
            timeout=params.get("timeout", 300)
        )
        return self._cli_result_to_response(result)
    
    async def _handle_render_preview(self, action) -> Response:
        """Render preview (low quality, fast)."""
        params = action.params
        kwargs = {
            "engine": "eevee",
            "samples": 16,
            "preview": True,
        }
        
        output_path = params.get("output_path") or params.get("path")
        if output_path:
            kwargs["output"] = output_path
        
        result = await self._run_cli("render", kwargs=kwargs, timeout=60)
        return self._cli_result_to_response(result)
    
    # Import/Export Handlers
    async def _handle_import(self, action) -> Response:
        """Import a file."""
        file_path = action.params.get("file_path") or action.params.get("path")
        if not file_path:
            return Response(success=False, error="file_path is required")
        
        kwargs = {
            "type": action.params.get("format") or action.params.get("type"),
        }
        
        result = await self._run_cli("import", args=[file_path], kwargs=kwargs)
        return self._cli_result_to_response(result)
    
    async def _handle_export(self, action) -> Response:
        """Export to a file."""
        params = action.params
        output_path = params.get("output_path") or params.get("path")
        
        if not output_path:
            return Response(success=False, error="output_path is required")
        
        kwargs = {
            "type": params.get("format") or params.get("type"),
            "selected": params.get("selected", False),
        }
        
        result = await self._run_cli("export", args=[output_path], kwargs=kwargs)
        return self._cli_result_to_response(result)
