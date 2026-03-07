"""
Blender addon handler for import/export operations.
"""

import os
import bpy


def _get_blender_major_version():
    """Return the major version of Blender (e.g. 3 or 4)."""
    return bpy.app.version[0]


def _detect_format(filepath):
    """Auto-detect format from file extension."""
    ext = os.path.splitext(filepath)[1].lower()
    format_map = {
        ".fbx": "FBX",
        ".obj": "OBJ",
        ".gltf": "GLTF",
        ".glb": "GLB",
        ".usd": "USD",
        ".usda": "USD",
        ".usdc": "USD",
        ".usdz": "USD",
        ".stl": "STL",
        ".dae": "DAE",
        ".ply": "PLY",
        ".svg": "SVG",
        ".abc": "ABC",
    }
    return format_map.get(ext)


def import_file(filepath, format=None):
    """
    Import a file into Blender.

    Auto-detects format from extension if not provided.
    Tracks objects before/after to identify imported objects.

    Args:
        filepath: Path to the file to import.
        format: Optional format override (FBX, OBJ, GLTF, GLB, USD, STL, DAE, PLY, SVG, ABC).

    Returns:
        dict with status, imported object names, and format.
    """
    if not os.path.isfile(filepath):
        return {"status": "error", "message": f"File not found: {filepath}"}

    if format is None:
        format = _detect_format(filepath)
    if format is None:
        return {"status": "error", "message": f"Could not detect format for: {filepath}"}

    format = format.upper()
    major = _get_blender_major_version()

    # Track existing objects before import
    existing_objects = set(obj.name for obj in bpy.data.objects)

    try:
        if format == "FBX":
            bpy.ops.import_scene.fbx(filepath=filepath)

        elif format == "OBJ":
            if major >= 4:
                try:
                    bpy.ops.wm.obj_import(filepath=filepath)
                except Exception:
                    bpy.ops.import_scene.obj(filepath=filepath)
            else:
                try:
                    bpy.ops.import_scene.obj(filepath=filepath)
                except Exception:
                    bpy.ops.wm.obj_import(filepath=filepath)

        elif format in ("GLTF", "GLB"):
            bpy.ops.import_scene.gltf(filepath=filepath)

        elif format == "USD":
            bpy.ops.wm.usd_import(filepath=filepath)

        elif format == "STL":
            if major >= 4:
                try:
                    bpy.ops.wm.stl_import(filepath=filepath)
                except Exception:
                    bpy.ops.import_mesh.stl(filepath=filepath)
            else:
                try:
                    bpy.ops.import_mesh.stl(filepath=filepath)
                except Exception:
                    bpy.ops.wm.stl_import(filepath=filepath)

        elif format == "DAE":
            bpy.ops.wm.collada_import(filepath=filepath)

        elif format == "PLY":
            if major >= 4:
                try:
                    bpy.ops.wm.ply_import(filepath=filepath)
                except Exception:
                    bpy.ops.import_mesh.ply(filepath=filepath)
            else:
                try:
                    bpy.ops.import_mesh.ply(filepath=filepath)
                except Exception:
                    bpy.ops.wm.ply_import(filepath=filepath)

        elif format == "SVG":
            bpy.ops.import_curve.svg(filepath=filepath)

        elif format == "ABC":
            bpy.ops.wm.alembic_import(filepath=filepath)

        else:
            return {"status": "error", "message": f"Unsupported format: {format}"}

    except Exception as e:
        return {"status": "error", "message": f"Import failed: {str(e)}"}

    # Identify newly imported objects
    new_objects = [obj.name for obj in bpy.data.objects if obj.name not in existing_objects]

    return {
        "status": "success",
        "format": format,
        "imported_objects": new_objects,
        "count": len(new_objects),
    }


def export_object(object_names, filepath, format=None):
    """
    Export specific objects to a file.

    Selects only the named objects and exports with use_selection=True.

    Args:
        object_names: List of object names to export.
        filepath: Destination file path.
        format: Optional format override.

    Returns:
        dict with status and filepath.
    """
    if format is None:
        format = _detect_format(filepath)
    if format is None:
        return {"status": "error", "message": f"Could not detect format for: {filepath}"}

    format = format.upper()

    # Deselect all, then select only the requested objects
    bpy.ops.object.select_all(action="DESELECT")
    missing = []
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            missing.append(name)
        else:
            obj.select_set(True)

    if missing:
        return {"status": "error", "message": f"Objects not found: {missing}"}

    major = _get_blender_major_version()
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if format == "FBX":
            bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True)

        elif format == "OBJ":
            if major >= 4:
                try:
                    bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=True)
                except Exception:
                    bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
            else:
                try:
                    bpy.ops.export_scene.obj(filepath=filepath, use_selection=True)
                except Exception:
                    bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=True)

        elif format in ("GLTF", "GLB"):
            if ext == ".glb":
                export_fmt = "GLB"
            else:
                export_fmt = "GLTF_SEPARATE"
            bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True, export_format=export_fmt)

        elif format == "USD":
            bpy.ops.wm.usd_export(filepath=filepath, selected_objects_only=True)

        elif format == "STL":
            if major >= 4:
                try:
                    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
                except Exception:
                    bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
            else:
                try:
                    bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
                except Exception:
                    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)

        elif format == "DAE":
            bpy.ops.wm.collada_export(filepath=filepath, selected=True)

        elif format == "PLY":
            if major >= 4:
                try:
                    bpy.ops.wm.ply_export(filepath=filepath, export_selected_objects=True)
                except Exception:
                    bpy.ops.export_mesh.ply(filepath=filepath, use_selection=True)
            else:
                try:
                    bpy.ops.export_mesh.ply(filepath=filepath, use_selection=True)
                except Exception:
                    bpy.ops.wm.ply_export(filepath=filepath, export_selected_objects=True)

        elif format == "ABC":
            bpy.ops.wm.alembic_export(filepath=filepath, selected=True)

        else:
            return {"status": "error", "message": f"Unsupported export format: {format}"}

    except Exception as e:
        return {"status": "error", "message": f"Export failed: {str(e)}"}

    return {
        "status": "success",
        "filepath": filepath,
        "format": format,
        "exported_objects": object_names,
    }


def export_scene(filepath, format=None):
    """
    Export the entire scene to a file.

    Args:
        filepath: Destination file path.
        format: Optional format override.

    Returns:
        dict with status and filepath.
    """
    if format is None:
        format = _detect_format(filepath)
    if format is None:
        return {"status": "error", "message": f"Could not detect format for: {filepath}"}

    format = format.upper()
    major = _get_blender_major_version()
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if format == "FBX":
            bpy.ops.export_scene.fbx(filepath=filepath)

        elif format == "OBJ":
            if major >= 4:
                try:
                    bpy.ops.wm.obj_export(filepath=filepath)
                except Exception:
                    bpy.ops.export_scene.obj(filepath=filepath)
            else:
                try:
                    bpy.ops.export_scene.obj(filepath=filepath)
                except Exception:
                    bpy.ops.wm.obj_export(filepath=filepath)

        elif format in ("GLTF", "GLB"):
            if ext == ".glb":
                export_fmt = "GLB"
            else:
                export_fmt = "GLTF_SEPARATE"
            bpy.ops.export_scene.gltf(filepath=filepath, export_format=export_fmt)

        elif format == "USD":
            bpy.ops.wm.usd_export(filepath=filepath)

        elif format == "STL":
            if major >= 4:
                try:
                    bpy.ops.wm.stl_export(filepath=filepath)
                except Exception:
                    bpy.ops.export_mesh.stl(filepath=filepath)
            else:
                try:
                    bpy.ops.export_mesh.stl(filepath=filepath)
                except Exception:
                    bpy.ops.wm.stl_export(filepath=filepath)

        elif format == "DAE":
            bpy.ops.wm.collada_export(filepath=filepath)

        elif format == "PLY":
            if major >= 4:
                try:
                    bpy.ops.wm.ply_export(filepath=filepath)
                except Exception:
                    bpy.ops.export_mesh.ply(filepath=filepath)
            else:
                try:
                    bpy.ops.export_mesh.ply(filepath=filepath)
                except Exception:
                    bpy.ops.wm.ply_export(filepath=filepath)

        elif format == "ABC":
            bpy.ops.wm.alembic_export(filepath=filepath)

        else:
            return {"status": "error", "message": f"Unsupported export format: {format}"}

    except Exception as e:
        return {"status": "error", "message": f"Export failed: {str(e)}"}

    return {
        "status": "success",
        "filepath": filepath,
        "format": format,
    }


def import_image_as_plane(filepath, location=(0, 0, 0)):
    """
    Import an image file as a textured plane in the scene.

    Creates a plane with the image's aspect ratio and applies the image
    as a material texture. Works on all Blender versions without addons.

    Args:
        filepath: Path to the image file.
        location: Tuple (x, y, z) for placement. Defaults to origin.

    Returns:
        dict with status and the created object name.
    """
    if not os.path.isfile(filepath):
        return {"status": "error", "message": f"File not found: {filepath}"}

    try:
        img = bpy.data.images.load(filepath)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load image: {str(e)}"}

    # Calculate aspect ratio for the plane
    width, height = img.size
    if width == 0 or height == 0:
        return {"status": "error", "message": "Image has zero dimensions"}
    aspect = width / height

    # Create plane mesh
    import bmesh
    mesh = bpy.data.meshes.new(img.name)
    bm = bmesh.new()
    half_w = aspect / 2.0
    half_h = 0.5
    verts = [
        bm.verts.new((-half_w, -half_h, 0)),
        bm.verts.new((half_w, -half_h, 0)),
        bm.verts.new((half_w, half_h, 0)),
        bm.verts.new((-half_w, half_h, 0)),
    ]
    face = bm.faces.new(verts)

    # Add UV layer
    uv_layer = bm.loops.layers.uv.new("UVMap")
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop, uv in zip(face.loops, uvs):
        loop[uv_layer].uv = uv

    bm.to_mesh(mesh)
    bm.free()

    # Create object
    obj = bpy.data.objects.new(img.name, mesh)
    obj.location = location
    bpy.context.collection.objects.link(obj)

    # Create material with the image texture
    mat = bpy.data.materials.new(name=img.name + "_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location = (-300, 0)
    tex_node.image = img

    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    # Connect alpha if the image has alpha
    if img.channels == 4:
        mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else mat.blend_method
        links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])

    obj.data.materials.append(mat)

    return {
        "status": "success",
        "object_name": obj.name,
        "filepath": filepath,
        "location": list(location),
        "image_size": [width, height],
    }


HANDLERS = {
    "import_file": import_file,
    "export_object": export_object,
    "export_scene": export_scene,
    "import_image_as_plane": import_image_as_plane,
}
