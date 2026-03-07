"""Blender addon handler for modifier operations."""

import bpy


def add_modifier(object_name, type, name=None, **params):
    """Add a modifier to an object.

    Supported types: SUBSURF, SOLIDIFY, BEVEL, BOOLEAN, MIRROR, ARRAY, CURVE,
    DECIMATE, REMESH, WELD, SMOOTH, SHRINKWRAP, WIREFRAME, SKIN, TRIANGULATE,
    EDGE_SPLIT, SIMPLE_DEFORM, LATTICE, CAST, WAVE, DISPLACE, SCREW.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    supported_types = {
        "SUBSURF", "SOLIDIFY", "BEVEL", "BOOLEAN", "MIRROR", "ARRAY", "CURVE",
        "DECIMATE", "REMESH", "WELD", "SMOOTH", "SHRINKWRAP", "WIREFRAME",
        "SKIN", "TRIANGULATE", "EDGE_SPLIT", "SIMPLE_DEFORM", "LATTICE",
        "CAST", "WAVE", "DISPLACE", "SCREW",
    }

    if type not in supported_types:
        return {"status": "error", "message": f"Unsupported modifier type '{type}'"}

    if name is None:
        name = type.capitalize()

    try:
        modifier = obj.modifiers.new(name=name, type=type)
    except Exception as e:
        return {"status": "error", "message": f"Failed to add modifier: {str(e)}"}

    for param_name, param_value in params.items():
        try:
            if param_name == "object":
                target = bpy.data.objects.get(param_value)
                if target is None:
                    return {
                        "status": "error",
                        "message": f"Target object '{param_value}' not found for param 'object'",
                    }
                modifier.object = target
            elif param_name == "mirror_object":
                target = bpy.data.objects.get(param_value)
                if target is None:
                    return {
                        "status": "error",
                        "message": f"Mirror object '{param_value}' not found",
                    }
                modifier.mirror_object = target
            else:
                setattr(modifier, param_name, param_value)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to set param '{param_name}': {str(e)}",
            }

    return {
        "status": "ok",
        "modifier_name": modifier.name,
        "type": modifier.type,
    }


def set_modifier_param(object_name, modifier_name, param, value):
    """Set an attribute on a modifier."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifier = obj.modifiers.get(modifier_name)
    if modifier is None:
        return {
            "status": "error",
            "message": f"Modifier '{modifier_name}' not found on '{object_name}'",
        }

    try:
        if param == "object":
            target = bpy.data.objects.get(value)
            if target is None:
                return {
                    "status": "error",
                    "message": f"Target object '{value}' not found",
                }
            modifier.object = target
        else:
            setattr(modifier, param, value)
    except Exception as e:
        return {"status": "error", "message": f"Failed to set '{param}': {str(e)}"}

    return {
        "status": "ok",
        "message": f"Set '{param}' on modifier '{modifier_name}' of '{object_name}'",
    }


def apply_modifier(object_name, modifier_name):
    """Apply a modifier to an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifier = obj.modifiers.get(modifier_name)
    if modifier is None:
        return {
            "status": "error",
            "message": f"Modifier '{modifier_name}' not found on '{object_name}'",
        }

    try:
        # Blender 4.x context override using temp_override
        if hasattr(bpy.context, "temp_override"):
            with bpy.context.temp_override(object=obj):
                bpy.ops.object.modifier_apply(modifier=modifier_name)
        else:
            # Blender 3.x context override
            override = {"object": obj, "active_object": obj}
            bpy.ops.object.modifier_apply(override, modifier=modifier_name)
    except Exception as e:
        return {"status": "error", "message": f"Failed to apply modifier: {str(e)}"}

    return {
        "status": "ok",
        "message": f"Applied modifier '{modifier_name}' on '{object_name}'",
    }


def remove_modifier(object_name, modifier_name):
    """Remove a modifier from an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifier = obj.modifiers.get(modifier_name)
    if modifier is None:
        return {
            "status": "error",
            "message": f"Modifier '{modifier_name}' not found on '{object_name}'",
        }

    try:
        obj.modifiers.remove(modifier)
    except Exception as e:
        return {"status": "error", "message": f"Failed to remove modifier: {str(e)}"}

    return {
        "status": "ok",
        "message": f"Removed modifier '{modifier_name}' from '{object_name}'",
    }


def list_modifiers(object_name):
    """List all modifiers on an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifiers = []
    for mod in obj.modifiers:
        modifiers.append({
            "name": mod.name,
            "type": mod.type,
            "show_viewport": mod.show_viewport,
            "show_render": mod.show_render,
        })

    return {"status": "ok", "modifiers": modifiers}


def reorder_modifier(object_name, modifier_name, direction):
    """Reorder a modifier up or down in the stack.

    direction: 'UP' or 'DOWN'.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifier = obj.modifiers.get(modifier_name)
    if modifier is None:
        return {
            "status": "error",
            "message": f"Modifier '{modifier_name}' not found on '{object_name}'",
        }

    if direction not in ("UP", "DOWN"):
        return {
            "status": "error",
            "message": f"Invalid direction '{direction}', must be 'UP' or 'DOWN'",
        }

    try:
        if hasattr(bpy.context, "temp_override"):
            # Blender 4.x
            with bpy.context.temp_override(object=obj):
                if direction == "UP":
                    bpy.ops.object.modifier_move_up(modifier=modifier_name)
                else:
                    bpy.ops.object.modifier_move_down(modifier=modifier_name)
        else:
            # Blender 3.x
            override = {"object": obj, "active_object": obj}
            if direction == "UP":
                bpy.ops.object.modifier_move_up(override, modifier=modifier_name)
            else:
                bpy.ops.object.modifier_move_down(override, modifier=modifier_name)
    except Exception as e:
        return {"status": "error", "message": f"Failed to reorder modifier: {str(e)}"}

    return {
        "status": "ok",
        "message": f"Moved modifier '{modifier_name}' {direction} on '{object_name}'",
    }


HANDLERS = {
    "add_modifier": add_modifier,
    "set_modifier_param": set_modifier_param,
    "apply_modifier": apply_modifier,
    "remove_modifier": remove_modifier,
    "list_modifiers": list_modifiers,
    "reorder_modifier": reorder_modifier,
}
