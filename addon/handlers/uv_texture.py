"""Handler for UV unwrapping and texture bake operations."""

import bpy
import os
from math import radians


def unwrap_uv(object_name, method="SMART_PROJECT", angle_limit=66.0, island_margin=0.02, correct_aspect=True):
    """Unwrap UVs for a mesh object using the specified method.

    Args:
        object_name: Name of the object to unwrap.
        method: Unwrap method - SMART_PROJECT, ANGLE_BASED, CONFORMAL,
                LIGHTMAP_PACK, CUBE_PROJECT, CYLINDER_PROJECT, SPHERE_PROJECT.
        angle_limit: Angle limit in degrees for SMART_PROJECT.
        island_margin: Margin between UV islands.
        correct_aspect: Whether to correct aspect ratio (SMART_PROJECT).

    Returns:
        dict with status and details.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    valid_methods = [
        "SMART_PROJECT", "ANGLE_BASED", "CONFORMAL", "LIGHTMAP_PACK",
        "CUBE_PROJECT", "CYLINDER_PROJECT", "SPHERE_PROJECT"
    ]
    if method not in valid_methods:
        return {"status": "error", "message": f"Invalid method '{method}'. Must be one of {valid_methods}"}

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    try:
        if method == "SMART_PROJECT":
            bpy.ops.uv.smart_project(
                angle_limit=radians(angle_limit),
                island_margin=island_margin,
                correct_aspect=correct_aspect
            )
        elif method == "ANGLE_BASED":
            bpy.ops.uv.unwrap(method='ANGLE_BASED')
        elif method == "CONFORMAL":
            bpy.ops.uv.unwrap(method='CONFORMAL')
        elif method == "LIGHTMAP_PACK":
            bpy.ops.uv.lightmap_pack(PREF_MARGIN_DIV=island_margin)
        elif method == "CUBE_PROJECT":
            bpy.ops.uv.cube_project()
        elif method == "CYLINDER_PROJECT":
            bpy.ops.uv.cylinder_project()
        elif method == "SPHERE_PROJECT":
            bpy.ops.uv.sphere_project()
    except Exception as e:
        bpy.ops.object.mode_set(mode='OBJECT')
        return {"status": "error", "message": f"Unwrap failed: {str(e)}"}

    bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "status": "success",
        "object": object_name,
        "method": method,
        "message": f"UV unwrap completed using {method}"
    }


def bake_texture(object_name, bake_type, resolution=1024, output_path=None, samples=16, margin=16):
    """Bake a texture map for the specified object using Cycles.

    Args:
        object_name: Name of the object to bake from.
        bake_type: Type of bake - DIFFUSE, ROUGHNESS, NORMAL, AO, SHADOW,
                   EMIT, COMBINED, GLOSSY, TRANSMISSION.
        resolution: Image resolution in pixels (square).
        output_path: File path to save the baked image. Auto-generated if None.
        samples: Number of render samples for baking.
        margin: Margin in pixels around UV islands.

    Returns:
        dict with status, filepath, resolution, and bake_type.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    valid_bake_types = [
        "DIFFUSE", "ROUGHNESS", "NORMAL", "AO", "SHADOW",
        "EMIT", "COMBINED", "GLOSSY", "TRANSMISSION"
    ]
    if bake_type not in valid_bake_types:
        return {"status": "error", "message": f"Invalid bake_type '{bake_type}'. Must be one of {valid_bake_types}"}

    # Remember original render engine to restore later
    original_engine = bpy.context.scene.render.engine

    # Switch to Cycles (required for baking)
    bpy.context.scene.render.engine = 'CYCLES'

    # Select and activate the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Create a new image for baking
    image_name = f"{object_name}_{bake_type}_bake"
    bake_image = bpy.data.images.new(
        name=image_name,
        width=resolution,
        height=resolution,
        alpha=True
    )

    # Ensure the object has a material
    if len(obj.data.materials) == 0:
        mat = bpy.data.materials.new(name=f"{object_name}_bake_material")
        mat.use_nodes = True
        obj.data.materials.append(mat)

    # For each material, add an image texture node and set it active
    for mat_slot in obj.material_slots:
        mat = mat_slot.material
        if mat is None:
            continue
        if not mat.use_nodes:
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = bake_image
        tex_node.name = "BakeTarget"
        # Set as active node for baking
        nodes.active = tex_node

    # Configure bake settings
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.render.bake.margin = margin

    try:
        bpy.ops.object.bake(type=bake_type)
    except Exception as e:
        bpy.context.scene.render.engine = original_engine
        return {"status": "error", "message": f"Bake failed: {str(e)}"}

    # Determine output path
    if output_path is None:
        output_dir = bpy.path.abspath("//")
        if not output_dir:
            output_dir = os.path.expanduser("~")
        output_path = os.path.join(output_dir, f"{image_name}.png")

    # Save the baked image
    bake_image.filepath_raw = output_path
    bake_image.file_format = 'PNG'
    bake_image.save_render(output_path)

    # Restore original render engine
    bpy.context.scene.render.engine = original_engine

    return {
        "status": "success",
        "object": object_name,
        "filepath": output_path,
        "resolution": resolution,
        "bake_type": bake_type,
        "message": f"Texture baked and saved to {output_path}"
    }


def create_uv_map(object_name, name="UVMap"):
    """Create a new UV map on the specified mesh object.

    Args:
        object_name: Name of the object.
        name: Name for the new UV map.

    Returns:
        dict with status and UV map name.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    uv_map = obj.data.uv_layers.new(name=name)

    return {
        "status": "success",
        "object": object_name,
        "uv_map_name": uv_map.name,
        "message": f"UV map '{uv_map.name}' created on '{object_name}'"
    }


def set_active_uv_map(object_name, uv_map_name):
    """Set the active UV map on the specified object.

    Args:
        object_name: Name of the object.
        uv_map_name: Name of the UV map to make active.

    Returns:
        dict with status and confirmation.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    uv_layer = obj.data.uv_layers.get(uv_map_name)
    if uv_layer is None:
        available = [uv.name for uv in obj.data.uv_layers]
        return {
            "status": "error",
            "message": f"UV map '{uv_map_name}' not found on '{object_name}'. Available: {available}"
        }

    uv_layer.active = True

    return {
        "status": "success",
        "object": object_name,
        "uv_map_name": uv_map_name,
        "message": f"UV map '{uv_map_name}' set as active on '{object_name}'"
    }


def list_uv_maps(object_name):
    """List all UV maps on the specified object.

    Args:
        object_name: Name of the object.

    Returns:
        dict with status and list of UV maps.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    uv_maps = []
    for uv_layer in obj.data.uv_layers:
        uv_maps.append({
            "name": uv_layer.name,
            "is_active": uv_layer.active
        })

    return {
        "status": "success",
        "object": object_name,
        "uv_maps": uv_maps,
        "count": len(uv_maps)
    }


def project_from_view(object_name, camera_name=None):
    """Project UVs from the current view or a specified camera.

    Args:
        object_name: Name of the object to project UVs for.
        camera_name: Optional camera name to project from. Uses current view if None.

    Returns:
        dict with status and confirmation.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.type != "MESH":
        return {"status": "error", "message": f"Object '{object_name}' is not a mesh"}

    # If a camera is specified, set it as the active camera
    original_camera = bpy.context.scene.camera
    if camera_name is not None:
        camera_obj = bpy.data.objects.get(camera_name)
        if camera_obj is None:
            return {"status": "error", "message": f"Camera '{camera_name}' not found"}
        if camera_obj.type != "CAMERA":
            return {"status": "error", "message": f"Object '{camera_name}' is not a camera"}
        bpy.context.scene.camera = camera_obj

    # Select and activate the object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    try:
        bpy.ops.uv.project_from_view(camera_bounds=camera_name is not None)
    except Exception as e:
        bpy.ops.object.mode_set(mode='OBJECT')
        if camera_name is not None:
            bpy.context.scene.camera = original_camera
        return {"status": "error", "message": f"Project from view failed: {str(e)}"}

    bpy.ops.object.mode_set(mode='OBJECT')

    # Restore original camera if changed
    if camera_name is not None:
        bpy.context.scene.camera = original_camera

    source = camera_name if camera_name else "current view"
    return {
        "status": "success",
        "object": object_name,
        "projected_from": source,
        "message": f"UVs projected from {source} onto '{object_name}'"
    }


HANDLERS = {
    "unwrap_uv": unwrap_uv,
    "bake_texture": bake_texture,
    "create_uv_map": create_uv_map,
    "set_active_uv_map": set_active_uv_map,
    "list_uv_maps": list_uv_maps,
    "project_from_view": project_from_view,
}
