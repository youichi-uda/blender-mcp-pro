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
    Import an image file as a plane in the scene.

    Enables the 'Import Images as Planes' addon if not already enabled.

    Args:
        filepath: Path to the image file.
        location: Tuple (x, y, z) for placement. Defaults to origin.

    Returns:
        dict with status and the created object name.
    """
    if not os.path.isfile(filepath):
        return {"status": "error", "message": f"File not found: {filepath}"}

    # Enable the addon if not already enabled
    addon_name = "io_import_images_as_planes"
    try:
        if addon_name not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=addon_name)
    except Exception as e:
        return {"status": "error", "message": f"Failed to enable 'Import Images as Planes' addon: {str(e)}"}

    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    existing_objects = set(obj.name for obj in bpy.data.objects)

    try:
        bpy.ops.import_image.to_plane(
            files=[{"name": filename}],
            directory=directory,
        )
    except Exception as e:
        return {"status": "error", "message": f"Image import failed: {str(e)}"}

    # Find the newly created object
    new_objects = [obj.name for obj in bpy.data.objects if obj.name not in existing_objects]

    if not new_objects:
        return {"status": "error", "message": "No object was created during image import"}

    # Set location on the imported plane
    obj_name = new_objects[0]
    obj = bpy.data.objects.get(obj_name)
    if obj:
        obj.location = location

    return {
        "status": "success",
        "object_name": obj_name,
        "filepath": filepath,
        "location": list(location),
    }


HANDLERS = {
    "import_file": import_file,
    "export_object": export_object,
    "export_scene": export_scene,
    "import_image_as_plane": import_image_as_plane,
}
