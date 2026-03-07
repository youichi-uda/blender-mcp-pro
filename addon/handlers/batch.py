"""
Blender addon handler for batch processing and automation operations.
"""

import os
import math

import bpy


def batch_render(camera_names, output_dir, format="PNG", resolution_x=1920, resolution_y=1080, samples=128):
    """Render from multiple cameras sequentially.

    Args:
        camera_names: List of camera object names to render from.
        output_dir: Directory to save rendered images.
        format: Image format (e.g. "PNG", "JPEG", "OPEN_EXR").
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.

    Returns:
        Dict with list of rendered filepaths.
    """
    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.image_settings.file_format = format

    if hasattr(scene, "cycles"):
        scene.cycles.samples = samples

    ext_map = {
        "PNG": ".png",
        "JPEG": ".jpg",
        "BMP": ".bmp",
        "TIFF": ".tiff",
        "OPEN_EXR": ".exr",
        "OPEN_EXR_MULTILAYER": ".exr",
        "HDR": ".hdr",
        "TARGA": ".tga",
    }
    ext = ext_map.get(format, ".png")

    os.makedirs(bpy.path.abspath(output_dir), exist_ok=True)

    rendered = []
    errors = []

    for cam_name in camera_names:
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj is None or cam_obj.type != 'CAMERA':
            errors.append(f"Camera '{cam_name}' not found or is not a camera object")
            continue

        scene.camera = cam_obj
        filepath = os.path.join(output_dir, cam_name + ext)
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        rendered.append(bpy.path.abspath(filepath))

    return {
        "status": "success" if rendered else "error",
        "rendered_filepaths": rendered,
        "count": len(rendered),
        "errors": errors,
    }


def render_turntable(object_name, frames=36, output_dir="//turntable/", format="PNG",
                     resolution_x=1920, resolution_y=1080, distance=None):
    """Render a turntable animation around an object.

    Creates a temporary camera (or uses the active one), positions it at an
    appropriate distance, and renders the object from evenly spaced angles.

    Args:
        object_name: Name of the target object to orbit around.
        frames: Number of frames (angles) in the turntable.
        output_dir: Output directory for rendered frames.
        format: Image format.
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        distance: Camera distance from object center. Auto-calculated if None.

    Returns:
        Dict with output directory and frame count.
    """
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.image_settings.file_format = format

    abs_output_dir = bpy.path.abspath(output_dir)
    os.makedirs(abs_output_dir, exist_ok=True)

    # Calculate object center and bounding box size in world space
    bbox_corners = [obj.matrix_world @ mathutils_vector(c) for c in obj.bound_box]
    center = sum((c for c in bbox_corners), mathutils_vector((0, 0, 0))) / 8
    max_dim = max(
        max(c[i] for c in bbox_corners) - min(c[i] for c in bbox_corners)
        for i in range(3)
    )

    if distance is None:
        distance = max_dim * 2.5

    # Use active camera or create a temporary one
    created_camera = False
    cam_obj = scene.camera
    if cam_obj is None or cam_obj.type != 'CAMERA':
        cam_data = bpy.data.cameras.new("TurntableCam")
        cam_obj = bpy.data.objects.new("TurntableCam", cam_data)
        bpy.context.collection.objects.link(cam_obj)
        scene.camera = cam_obj
        created_camera = True

    ext_map = {
        "PNG": ".png",
        "JPEG": ".jpg",
        "BMP": ".bmp",
        "TIFF": ".tiff",
        "OPEN_EXR": ".exr",
        "HDR": ".hdr",
        "TARGA": ".tga",
    }
    ext = ext_map.get(format, ".png")

    rendered = []
    angle_step = 2 * math.pi / frames

    for i in range(frames):
        angle = angle_step * i
        cam_x = center.x + distance * math.cos(angle)
        cam_y = center.y + distance * math.sin(angle)
        cam_z = center.z + max_dim * 0.5

        cam_obj.location = (cam_x, cam_y, cam_z)

        direction = center - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        filepath = os.path.join(output_dir, f"frame_{i:04d}{ext}")
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        rendered.append(bpy.path.abspath(filepath))

    # Clean up temporary camera
    if created_camera:
        bpy.data.objects.remove(cam_obj, do_unlink=True)

    return {
        "status": "success",
        "output_dir": abs_output_dir,
        "frame_count": len(rendered),
        "rendered_filepaths": rendered,
    }


def mathutils_vector(coords):
    """Helper to create a mathutils.Vector from coordinates."""
    from mathutils import Vector
    return Vector(coords)


def _get_import_func(ext):
    """Return the appropriate bpy import operator for a file extension."""
    import_map = {
        ".obj": lambda fp: bpy.ops.wm.obj_import(filepath=fp),
        ".fbx": lambda fp: bpy.ops.import_scene.fbx(filepath=fp),
        ".gltf": lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
        ".glb": lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
        ".stl": lambda fp: bpy.ops.import_mesh.stl(filepath=fp),
        ".ply": lambda fp: bpy.ops.import_mesh.ply(filepath=fp),
        ".dae": lambda fp: bpy.ops.wm.collada_import(filepath=fp),
        ".abc": lambda fp: bpy.ops.wm.alembic_import(filepath=fp),
        ".usd": lambda fp: bpy.ops.wm.usd_import(filepath=fp),
        ".usda": lambda fp: bpy.ops.wm.usd_import(filepath=fp),
        ".usdc": lambda fp: bpy.ops.wm.usd_import(filepath=fp),
        ".svg": lambda fp: bpy.ops.import_curve.svg(filepath=fp),
    }
    return import_map.get(ext.lower())


RECOGNIZED_EXTENSIONS = {
    ".obj", ".fbx", ".gltf", ".glb", ".stl", ".ply",
    ".dae", ".abc", ".usd", ".usda", ".usdc", ".svg",
}


def _import_file(filepath):
    """Import a single file into Blender and return newly created object names."""
    ext = os.path.splitext(filepath)[1].lower()
    import_func = _get_import_func(ext)
    if import_func is None:
        return None

    existing_objects = set(bpy.data.objects.keys())
    import_func(filepath)
    new_objects = [name for name in bpy.data.objects.keys() if name not in existing_objects]
    return new_objects


def batch_import(directory, format=None, recursive=False):
    """Import all files of a given format from a directory.

    Args:
        directory: Path to the directory containing files to import.
        format: File extension filter (e.g. "fbx", "obj"). None imports all recognized formats.
        recursive: If True, walk subdirectories as well.

    Returns:
        Dict with list of imported files and object names.
    """
    if not os.path.isdir(directory):
        return {"status": "error", "message": f"Directory '{directory}' does not exist"}

    target_ext = None
    if format is not None:
        target_ext = format.lower() if format.startswith(".") else f".{format.lower()}"

    imported_files = []
    imported_objects = []
    errors = []

    def process_file(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if target_ext is not None and ext != target_ext:
            return
        if ext not in RECOGNIZED_EXTENSIONS:
            return

        new_objects = _import_file(filepath)
        if new_objects is not None:
            imported_files.append(filepath)
            imported_objects.extend(new_objects)
        else:
            errors.append(f"No importer available for '{filepath}'")

    if recursive:
        for root, _dirs, files in os.walk(directory):
            for filename in files:
                process_file(os.path.join(root, filename))
    else:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                process_file(filepath)

    return {
        "status": "success" if imported_files else "error",
        "imported_files": imported_files,
        "imported_objects": imported_objects,
        "count": len(imported_files),
        "errors": errors,
    }


def _get_export_func(ext):
    """Return the appropriate bpy export operator for a file extension."""
    export_map = {
        ".fbx": lambda fp: bpy.ops.export_scene.fbx(filepath=fp, use_selection=True),
        ".obj": lambda fp: bpy.ops.wm.obj_export(filepath=fp, export_selected_objects=True),
        ".gltf": lambda fp: bpy.ops.export_scene.gltf(filepath=fp, use_selection=True),
        ".glb": lambda fp: bpy.ops.export_scene.gltf(filepath=fp, use_selection=True,
                                                       export_format='GLB'),
        ".stl": lambda fp: bpy.ops.export_mesh.stl(filepath=fp, use_selection=True),
        ".ply": lambda fp: bpy.ops.export_mesh.ply(filepath=fp, use_selection=True),
        ".dae": lambda fp: bpy.ops.wm.collada_export(filepath=fp, selected=True),
        ".abc": lambda fp: bpy.ops.wm.alembic_export(filepath=fp, selected=True),
        ".usd": lambda fp: bpy.ops.wm.usd_export(filepath=fp, selected_objects_only=True),
        ".usda": lambda fp: bpy.ops.wm.usd_export(filepath=fp, selected_objects_only=True),
        ".usdc": lambda fp: bpy.ops.wm.usd_export(filepath=fp, selected_objects_only=True),
    }
    return export_map.get(ext.lower())


def batch_export(object_names, directory, format="FBX", individual=True):
    """Export objects to files.

    Args:
        object_names: List of object names to export.
        directory: Output directory.
        format: Export format (e.g. "FBX", "OBJ", "GLTF", "GLB", "STL").
        individual: If True, export each object as a separate file.
                    If False, export all objects as a single file.

    Returns:
        Dict with list of exported filepaths.
    """
    ext = format.lower() if format.startswith(".") else f".{format.lower()}"
    export_func = _get_export_func(ext)
    if export_func is None:
        return {"status": "error", "message": f"Unsupported export format: '{format}'"}

    os.makedirs(directory, exist_ok=True)

    # Validate all object names
    objects = []
    errors = []
    for name in object_names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            errors.append(f"Object '{name}' not found")
        else:
            objects.append(obj)

    if not objects:
        return {"status": "error", "message": "No valid objects found", "errors": errors}

    exported = []

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')

    if individual:
        for obj in objects:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            filepath = os.path.join(directory, obj.name + ext)
            export_func(filepath)
            exported.append(os.path.abspath(filepath))
    else:
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]

        filepath = os.path.join(directory, "batch_export" + ext)
        export_func(filepath)
        exported.append(os.path.abspath(filepath))

    return {
        "status": "success",
        "exported_filepaths": exported,
        "count": len(exported),
        "errors": errors,
    }


def apply_material_to_all(material_name, object_names=None):
    """Apply a material to objects.

    Args:
        material_name: Name of the material to apply.
        object_names: List of object names. If None, applies to all mesh objects.

    Returns:
        Dict with count of objects affected.
    """
    material = bpy.data.materials.get(material_name)
    if material is None:
        return {"status": "error", "message": f"Material '{material_name}' not found"}

    if object_names is not None:
        targets = []
        errors = []
        for name in object_names:
            obj = bpy.data.objects.get(name)
            if obj is None:
                errors.append(f"Object '{name}' not found")
            elif obj.type != 'MESH':
                errors.append(f"Object '{name}' is not a mesh (type: {obj.type})")
            else:
                targets.append(obj)
    else:
        targets = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        errors = []

    affected = 0
    for obj in targets:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        affected += 1

    return {
        "status": "success",
        "material": material_name,
        "objects_affected": affected,
        "errors": errors,
    }


HANDLERS = {
    "batch_render": batch_render,
    "render_turntable": render_turntable,
    "batch_import": batch_import,
    "batch_export": batch_export,
    "apply_material_to_all": apply_material_to_all,
}
