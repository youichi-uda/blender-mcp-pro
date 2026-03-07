from . import (
    scene,
    objects,
    materials,
    shader_nodes,
    lights,
    modifiers,
    animation,
    geometry_nodes,
    camera,
    render,
    io_handlers,
    code_exec,
    uv_texture,
    batch,
    assets,
    rigging,
)

_MODULES = [
    scene,
    objects,
    materials,
    shader_nodes,
    lights,
    modifiers,
    animation,
    geometry_nodes,
    camera,
    render,
    io_handlers,
    code_exec,
    uv_texture,
    batch,
    assets,
    rigging,
]

_REGISTRY = {}

for mod in _MODULES:
    if hasattr(mod, "HANDLERS"):
        _REGISTRY.update(mod.HANDLERS)


def dispatch_command(cmd):
    command_name = cmd.get("command")
    params = cmd.get("params", {})

    if not command_name:
        raise ValueError("No 'command' field in request")

    handler = _REGISTRY.get(command_name)
    if not handler:
        available = sorted(_REGISTRY.keys())
        raise ValueError(
            f"Unknown command: '{command_name}'. "
            f"Available commands: {', '.join(available)}"
        )

    return handler(**params)
