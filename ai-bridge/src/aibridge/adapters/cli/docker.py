"""Docker Adapter for AI-Bridge

Provides container management capabilities through Docker CLI.

Usage example:
```python
from aibridge.adapters.cli import DockerAdapter
from aibridge.core.protocol import Action

adapter = DockerAdapter()
await adapter.initialize()

# List containers
result = await adapter.execute(Action(name="ps", params={}))

# Run container
result = await adapter.execute(Action(
    name="run",
    params={"image": "nginx", "name": "my-nginx", "detach": True}
))

# Execute command in container
result = await adapter.execute(Action(
    name="exec",
    params={"container": "my-nginx", "command": "ls -la"}
))

# Build image
result = await adapter.execute(Action(
    name="build",
    params={"path": ".", "tag": "myapp:latest"}
))
```
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult

logger = logging.getLogger(__name__)


class DockerAdapter(CLIAdapter):
    """AI-Bridge adapter for Docker container management."""
    
    cli_name = "docker"
    cli_module = None  # Docker is a system binary
    auto_install_cli = False
    
    SUPPORTED_ACTIONS = [
        # Container management
        "ps", "run", "start", "stop", "restart", "rm", "exec", "logs",
        # Image management
        "images", "pull", "push", "build", "rmi", "tag",
        # Volume management
        "volumes", "volume_create", "volume_rm",
        # Network management
        "networks", "network_create", "network_rm",
        # System
        "info", "version", "prune"
    ]

    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Map action names to handler methods."""
        return {
            # Container
            "ps": self._handle_ps,
            "run": self._handle_run,
            "start": self._handle_start,
            "stop": self._handle_stop,
            "restart": self._handle_restart,
            "rm": self._handle_rm,
            "exec": self._handle_exec,
            "logs": self._handle_logs,
            # Image
            "images": self._handle_images,
            "pull": self._handle_pull,
            "build": self._handle_build,
            "rmi": self._handle_rmi,
            "tag": self._handle_tag,
            # Volume
            "volumes": self._handle_volumes,
            "volume_create": self._handle_volume_create,
            "volume_rm": self._handle_volume_rm,
            # Network
            "networks": self._handle_networks,
            # System
            "info": self._handle_info,
            "version": self._handle_version,
            "prune": self._handle_prune,
        }

    # Container Management
    async def _handle_ps(self, action: Action) -> Response:
        """List containers."""
        params = action.params
        args = ["ps"]
        
        if params.get("all"):
            args.append("-a")
        if params.get("quiet"):
            args.append("-q")
        
        # JSON 输出便于解析
        args.extend(["--format", "{{json .}}"])
        
        result = await self._run_docker(args)
        
        # 解析 JSON 输出
        if result.success:
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            result.data = {"containers": containers}
        
        return self._cli_result_to_response(result)

    async def _handle_run(self, action: Action) -> Response:
        """Run a container."""
        params = action.params
        image = params.get("image")
        
        if not image:
            return Response(success=False, error="image is required")
        
        args = ["run"]
        
        if params.get("detach"):
            args.append("-d")
        if params.get("name"):
            args.extend(["--name", params["name"]])
        if params.get("rm"):
            args.append("--rm")
        if params.get("interactive"):
            args.append("-i")
        if params.get("tty"):
            args.append("-t")
        
        # 端口映射
        for port in params.get("ports", []):
            args.extend(["-p", port])
        
        # 环境变量
        for env in params.get("env", []):
            args.extend(["-e", env])
        
        # 卷挂载
        for volume in params.get("volumes", []):
            args.extend(["-v", volume])
        
        # 网络
        if params.get("network"):
            args.extend(["--network", params["network"]])
        
        # 工作目录
        if params.get("workdir"):
            args.extend(["-w", params["workdir"]])
        
        args.append(image)
        
        # 命令
        if params.get("command"):
            if isinstance(params["command"], list):
                args.extend(params["command"])
            else:
                args.append(params["command"])
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _handle_start(self, action: Action) -> Response:
        """Start a stopped container."""
        container = action.params.get("container")
        if not container:
            return Response(success=False, error="container is required")
        
        result = await self._run_docker(["start", container])
        return self._cli_result_to_response(result)

    async def _handle_stop(self, action: Action) -> Response:
        """Stop a running container."""
        params = action.params
        container = params.get("container")
        if not container:
            return Response(success=False, error="container is required")
        
        args = ["stop"]
        if params.get("time"):
            args.extend(["-t", str(params["time"])])
        args.append(container)
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _handle_restart(self, action: Action) -> Response:
        """Restart a container."""
        container = action.params.get("container")
        if not container:
            return Response(success=False, error="container is required")
        
        result = await self._run_docker(["restart", container])
        return self._cli_result_to_response(result)

    async def _handle_rm(self, action: Action) -> Response:
        """Remove a container."""
        params = action.params
        container = params.get("container")
        if not container:
            return Response(success=False, error="container is required")
        
        args = ["rm"]
        if params.get("force"):
            args.append("-f")
        if params.get("volumes"):
            args.append("-v")
        args.append(container)
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _handle_exec(self, action: Action) -> Response:
        """Execute command in container."""
        params = action.params
        container = params.get("container")
        command = params.get("command")
        
        if not container or not command:
            return Response(success=False, error="container and command are required")
        
        args = ["exec"]
        if params.get("interactive"):
            args.append("-i")
        if params.get("tty"):
            args.append("-t")
        if params.get("user"):
            args.extend(["-u", params["user"]])
        if params.get("workdir"):
            args.extend(["-w", params["workdir"]])
        
        args.append(container)
        
        if isinstance(command, list):
            args.extend(command)
        else:
            args.extend(["sh", "-c", command])
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _handle_logs(self, action: Action) -> Response:
        """Get container logs."""
        params = action.params
        container = params.get("container")
        if not container:
            return Response(success=False, error="container is required")
        
        args = ["logs"]
        if params.get("follow"):
            args.append("-f")
        if params.get("tail"):
            args.extend(["--tail", str(params["tail"])])
        if params.get("timestamps"):
            args.append("-t")
        args.append(container)
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    # Image Management
    async def _handle_images(self, action: Action) -> Response:
        """List images."""
        args = ["images", "--format", "{{json .}}"]
        
        if action.params.get("all"):
            args.insert(1, "-a")
        
        result = await self._run_docker(args)
        
        if result.success:
            images = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        images.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            result.data = {"images": images}
        
        return self._cli_result_to_response(result)

    async def _handle_pull(self, action: Action) -> Response:
        """Pull an image."""
        image = action.params.get("image")
        if not image:
            return Response(success=False, error="image is required")
        
        result = await self._run_docker(["pull", image])
        return self._cli_result_to_response(result)

    async def _handle_build(self, action: Action) -> Response:
        """Build an image."""
        params = action.params
        path = params.get("path", ".")
        
        args = ["build"]
        
        if params.get("tag"):
            args.extend(["-t", params["tag"]])
        if params.get("file"):
            args.extend(["-f", params["file"]])
        if params.get("no_cache"):
            args.append("--no-cache")
        
        # Build args
        for arg in params.get("build_args", []):
            args.extend(["--build-arg", arg])
        
        args.append(path)
        
        result = await self._run_docker(args, timeout=600)
        return self._cli_result_to_response(result)

    async def _handle_rmi(self, action: Action) -> Response:
        """Remove an image."""
        params = action.params
        image = params.get("image")
        if not image:
            return Response(success=False, error="image is required")
        
        args = ["rmi"]
        if params.get("force"):
            args.append("-f")
        args.append(image)
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _handle_tag(self, action: Action) -> Response:
        """Tag an image."""
        params = action.params
        source = params.get("source")
        target = params.get("target")
        
        if not source or not target:
            return Response(success=False, error="source and target are required")
        
        result = await self._run_docker(["tag", source, target])
        return self._cli_result_to_response(result)

    # Volume Management
    async def _handle_volumes(self, action: Action) -> Response:
        """List volumes."""
        result = await self._run_docker(["volume", "ls", "--format", "{{json .}}"])
        
        if result.success:
            volumes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        volumes.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            result.data = {"volumes": volumes}
        
        return self._cli_result_to_response(result)

    async def _handle_volume_create(self, action: Action) -> Response:
        """Create a volume."""
        name = action.params.get("name")
        if not name:
            return Response(success=False, error="name is required")
        
        result = await self._run_docker(["volume", "create", name])
        return self._cli_result_to_response(result)

    async def _handle_volume_rm(self, action: Action) -> Response:
        """Remove a volume."""
        name = action.params.get("name")
        if not name:
            return Response(success=False, error="name is required")
        
        result = await self._run_docker(["volume", "rm", name])
        return self._cli_result_to_response(result)

    # Network Management
    async def _handle_networks(self, action: Action) -> Response:
        """List networks."""
        result = await self._run_docker(["network", "ls", "--format", "{{json .}}"])
        
        if result.success:
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        networks.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            result.data = {"networks": networks}
        
        return self._cli_result_to_response(result)

    # System
    async def _handle_info(self, action: Action) -> Response:
        """Get Docker system info."""
        result = await self._run_docker(["info", "--format", "{{json .}}"])
        
        if result.success:
            try:
                result.data = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        
        return self._cli_result_to_response(result)

    async def _handle_version(self, action: Action) -> Response:
        """Get Docker version."""
        result = await self._run_docker(["version", "--format", "{{json .}}"])
        
        if result.success:
            try:
                result.data = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        
        return self._cli_result_to_response(result)

    async def _handle_prune(self, action: Action) -> Response:
        """Remove unused data."""
        params = action.params
        args = ["system", "prune", "-f"]
        
        if params.get("all"):
            args.append("-a")
        if params.get("volumes"):
            args.append("--volumes")
        
        result = await self._run_docker(args)
        return self._cli_result_to_response(result)

    async def _run_docker(self, args: List[str], timeout: int = 120) -> CLIResult:
        """Run Docker with arguments."""
        cmd = ["docker"] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
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
