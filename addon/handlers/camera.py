import bpy
import mathutils
import math


def create_camera(name=None, location=(0, 0, 5), rotation=(0, 0, 0), lens=50.0):
    """Create a camera and add it to the scene."""
    if name is None:
        name = "Camera"

    cam_data = bpy.data.cameras.new(name=name)
    cam_data.lens = lens

    cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
    cam_obj.location = (location[0], location[1], location[2])
    cam_obj.rotation_euler = (rotation[0], rotation[1], rotation[2])

    bpy.context.collection.objects.link(cam_obj)

    return {
        "status": "success",
        "name": cam_obj.name,
        "location": list(cam_obj.location),
        "lens": cam_data.lens,
    }


def set_camera_lens(camera_name, lens_type=None, focal_length=None, value=None,
                    clip_start=None, clip_end=None, shift_x=None, shift_y=None,
                    sensor_width=None, dof_focus_distance=None,
                    dof_focus_object=None, dof_aperture_fstop=None):
    """Configure lens, clipping, shift, sensor, and DOF settings on a camera."""
    obj = bpy.data.objects.get(camera_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{camera_name}' not found."}
    if obj.type != 'CAMERA':
        return {"status": "error", "message": f"Object '{camera_name}' is not a camera."}

    cam = obj.data

    if lens_type is not None:
        if lens_type not in ("PERSP", "ORTHO", "PANO"):
            return {"status": "error", "message": f"Invalid lens_type: {lens_type}. Must be PERSP, ORTHO, or PANO."}
        cam.type = lens_type

    # Support both 'focal_length' and legacy 'value' parameter names
    focal = focal_length if focal_length is not None else value

    if focal is not None:
        current_type = cam.type
        if current_type == "PERSP":
            cam.lens = focal
        elif current_type == "ORTHO":
            cam.ortho_scale = focal

    if clip_start is not None:
        cam.clip_start = clip_start
    if clip_end is not None:
        cam.clip_end = clip_end
    if shift_x is not None:
        cam.shift_x = shift_x
    if shift_y is not None:
        cam.shift_y = shift_y
    if sensor_width is not None:
        cam.sensor_width = sensor_width

    # DOF settings
    if dof_focus_distance is not None or dof_focus_object is not None or dof_aperture_fstop is not None:
        cam.dof.use_dof = True

        if dof_focus_distance is not None:
            cam.dof.focus_distance = dof_focus_distance
        if dof_focus_object is not None:
            focus_obj = bpy.data.objects.get(dof_focus_object)
            if focus_obj is None:
                return {"status": "error", "message": f"DOF focus object '{dof_focus_object}' not found."}
            cam.dof.focus_object = focus_obj
        if dof_aperture_fstop is not None:
            cam.dof.aperture_fstop = dof_aperture_fstop

    return {
        "status": "success",
        "name": camera_name,
        "type": cam.type,
        "focal_length": cam.lens,
        "ortho_scale": cam.ortho_scale,
        "clip_start": cam.clip_start,
        "clip_end": cam.clip_end,
        "shift_x": cam.shift_x,
        "shift_y": cam.shift_y,
        "sensor_width": cam.sensor_width,
        "dof_enabled": cam.dof.use_dof,
        "dof_focus_distance": cam.dof.focus_distance,
        "dof_focus_object": cam.dof.focus_object.name if cam.dof.focus_object else None,
        "dof_aperture_fstop": cam.dof.aperture_fstop,
    }


def set_active_camera(camera_name):
    """Set the named camera as the active scene camera."""
    obj = bpy.data.objects.get(camera_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{camera_name}' not found."}
    if obj.type != 'CAMERA':
        return {"status": "error", "message": f"Object '{camera_name}' is not a camera."}

    bpy.context.scene.camera = obj

    return {
        "status": "success",
        "message": f"'{camera_name}' is now the active camera.",
    }


def frame_selected_objects(camera_name, object_names):
    """Position and orient a camera to frame the listed objects."""
    obj = bpy.data.objects.get(camera_name)
    if obj is None:
        return {"status": "error", "message": f"Camera '{camera_name}' not found."}
    if obj.type != 'CAMERA':
        return {"status": "error", "message": f"Object '{camera_name}' is not a camera."}

    targets = []
    for oname in object_names:
        t = bpy.data.objects.get(oname)
        if t is None:
            return {"status": "error", "message": f"Object '{oname}' not found."}
        targets.append(t)

    if not targets:
        return {"status": "error", "message": "No objects specified."}

    # Calculate combined bounding box in world space
    all_coords = []
    for t in targets:
        if t.bound_box:
            for corner in t.bound_box:
                world_corner = t.matrix_world @ mathutils.Vector(corner)
                all_coords.append(world_corner)
        else:
            all_coords.append(mathutils.Vector(t.location))

    if not all_coords:
        return {"status": "error", "message": "Could not determine bounding box for the specified objects."}

    bbox_min = mathutils.Vector((
        min(c.x for c in all_coords),
        min(c.y for c in all_coords),
        min(c.z for c in all_coords),
    ))
    bbox_max = mathutils.Vector((
        max(c.x for c in all_coords),
        max(c.y for c in all_coords),
        max(c.z for c in all_coords),
    ))

    center = (bbox_min + bbox_max) / 2.0
    bbox_size = bbox_max - bbox_min
    max_extent = max(bbox_size.x, bbox_size.y, bbox_size.z, 0.001)

    # Calculate distance based on camera FOV
    cam = obj.data
    fov = 2.0 * math.atan(cam.sensor_width / (2.0 * cam.lens))
    distance = (max_extent / 2.0) / math.tan(fov / 2.0)
    distance *= 1.5  # Add padding

    # Position camera along the direction from center, offset in Y and Z
    cam_pos = center + mathutils.Vector((0, -distance, distance * 0.5))
    obj.location = cam_pos

    # Point camera at center
    direction = center - cam_pos
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()

    return {
        "status": "success",
        "camera": camera_name,
        "position": list(obj.location),
        "framed_objects": object_names,
        "bounding_box_center": list(center),
    }


def add_camera_track_to(camera_name, target_object):
    """Add a Track To constraint to a camera, targeting the named object."""
    obj = bpy.data.objects.get(camera_name)
    if obj is None:
        return {"status": "error", "message": f"Camera '{camera_name}' not found."}
    if obj.type != 'CAMERA':
        return {"status": "error", "message": f"Object '{camera_name}' is not a camera."}

    target = bpy.data.objects.get(target_object)
    if target is None:
        return {"status": "error", "message": f"Target object '{target_object}' not found."}

    constraint = obj.constraints.new(type='TRACK_TO')
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    return {
        "status": "success",
        "message": f"Track To constraint added to '{camera_name}' targeting '{target_object}'.",
        "camera": camera_name,
        "target": target_object,
    }


def list_cameras():
    """Return a list of all camera objects in the scene."""
    active_camera = bpy.context.scene.camera
    cameras = []

    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            cameras.append({
                "name": obj.name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "focal_length": obj.data.lens,
                "is_active": (obj == active_camera),
            })

    return {
        "status": "success",
        "cameras": cameras,
        "count": len(cameras),
    }


def get_camera_info(camera_name):
    """Return detailed information about a camera."""
    obj = bpy.data.objects.get(camera_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{camera_name}' not found."}
    if obj.type != 'CAMERA':
        return {"status": "error", "message": f"Object '{camera_name}' is not a camera."}

    cam = obj.data
    constraints_info = []
    for c in obj.constraints:
        cinfo = {"type": c.type, "name": c.name}
        if hasattr(c, "target") and c.target:
            cinfo["target"] = c.target.name
        constraints_info.append(cinfo)

    return {
        "status": "success",
        "name": obj.name,
        "type": cam.type,
        "focal_length": cam.lens,
        "ortho_scale": cam.ortho_scale,
        "clip_start": cam.clip_start,
        "clip_end": cam.clip_end,
        "sensor_width": cam.sensor_width,
        "shift_x": cam.shift_x,
        "shift_y": cam.shift_y,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "dof": {
            "enabled": cam.dof.use_dof,
            "focus_distance": cam.dof.focus_distance,
            "focus_object": cam.dof.focus_object.name if cam.dof.focus_object else None,
            "aperture_fstop": cam.dof.aperture_fstop,
        },
        "constraints": constraints_info,
        "is_active": (obj == bpy.context.scene.camera),
    }


HANDLERS = {
    "create_camera": create_camera,
    "set_camera_lens": set_camera_lens,
    "set_active_camera": set_active_camera,
    "frame_selected_objects": frame_selected_objects,
    "add_camera_track_to": add_camera_track_to,
    "list_cameras": list_cameras,
    "get_camera_info": get_camera_info,
}
