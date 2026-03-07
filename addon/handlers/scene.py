"""Handler for Blender scene query operations."""

import bpy


def get_scene_info():
    """Return comprehensive information about the current Blender scene.

    Returns a dict containing:
        - name: scene name
        - frame_range: start, end, current frame and fps
        - render_engine: active render engine identifier
        - render_resolution: x, y and percentage scale
        - objects: list of all objects with core properties
        - collections: list of all collections and their direct objects
        - materials: list of all material names
    """
    scene = bpy.context.scene

    # --- Frame / timing info ---
    frame_info = {
        "start": scene.frame_start,
        "end": scene.frame_end,
        "current": scene.frame_current,
        "fps": scene.render.fps,
    }

    # --- Render info ---
    render_resolution = {
        "x": scene.render.resolution_x,
        "y": scene.render.resolution_y,
        "percentage": scene.render.resolution_percentage,
    }

    # --- Objects ---
    objects = []
    for obj in scene.objects:
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location),
            "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale),
            "visible": obj.visible_get(),
            "parent": obj.parent.name if obj.parent else None,
        })

    # --- Collections ---
    collections = []
    for coll in bpy.data.collections:
        collections.append({
            "name": coll.name,
            "objects": [obj.name for obj in coll.objects],
        })

    # --- Materials ---
    materials = [mat.name for mat in bpy.data.materials]

    return {
        "name": scene.name,
        "frame_range": frame_info,
        "render_engine": scene.render.engine,
        "render_resolution": render_resolution,
        "objects": objects,
        "collections": collections,
        "materials": materials,
    }


def get_object_info(name):
    """Return detailed information about a specific object.

    Args:
        name: The name of the Blender object to inspect.

    Returns a dict with detailed properties, or a dict with an ``error`` key
    when the object cannot be found.
    """
    if not name:
        return {"error": "No object name provided."}

    obj = bpy.data.objects.get(name)
    if obj is None:
        return {
            "error": f"Object '{name}' not found. "
                     f"Available objects: {[o.name for o in bpy.data.objects]}"
        }

    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
        "parent": obj.parent.name if obj.parent else None,
        "children": [child.name for child in obj.children],
        "visible": obj.visible_get(),
    }

    # --- Modifiers ---
    info["modifiers"] = [
        {"name": mod.name, "type": mod.type}
        for mod in obj.modifiers
    ]

    # --- Materials ---
    info["materials"] = [
        slot.material.name if slot.material else None
        for slot in obj.material_slots
    ]

    # --- Constraints ---
    info["constraints"] = [
        {"name": con.name, "type": con.type}
        for con in obj.constraints
    ]

    # --- Mesh-specific data (vertex / edge / face counts) ---
    if obj.type == "MESH" and obj.data:
        mesh = obj.data
        info["mesh"] = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "faces": len(mesh.polygons),
        }

    return info


HANDLERS = {
    "get_scene_info": get_scene_info,
    "get_object_info": get_object_info,
}
