import bpy


def _get_fcurves(action):
    """Get fcurves from an action, supporting both legacy and Blender 5.0 layered API."""
    # Blender 5.0+: layered action (layers -> strips -> channelbags -> fcurves)
    if hasattr(action, "layers") and len(action.layers) > 0:
        for layer in action.layers:
            if hasattr(layer, "strips"):
                for strip in layer.strips:
                    if hasattr(strip, "channelbags"):
                        for cbag in strip.channelbags:
                            if hasattr(cbag, "fcurves"):
                                yield from cbag.fcurves
        return
    # Legacy (Blender 3.x / 4.x): action.fcurves
    if hasattr(action, "fcurves"):
        yield from action.fcurves


def set_frame(frame):
    """Set the current frame of the scene."""
    bpy.context.scene.frame_set(frame)
    return {"status": "ok", "current_frame": bpy.context.scene.frame_current}


def set_frame_range(start, end, fps=None):
    """Set the scene frame range and optionally the FPS."""
    scene = bpy.context.scene
    scene.frame_start = start
    scene.frame_end = end
    if fps is not None:
        scene.render.fps = fps
    return {
        "status": "ok",
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": scene.render.fps,
    }


def insert_keyframe(object_name, frame, data_path, value=None, index=-1):
    """Insert a keyframe on an object property at a given frame."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    # Handle shorthand paths like "location.x" -> data_path="location", index=0
    axis_map = {"x": 0, "y": 1, "z": 2, "w": 3}
    parts = data_path.rsplit(".", 1)
    if len(parts) == 2 and parts[1].lower() in axis_map:
        data_path = parts[0]
        index = axis_map[parts[1].lower()]

    # Resolve dotted paths that span ID blocks (e.g. "data.energy")
    # keyframe_insert must be called on the owning ID block with the local path
    keyframe_target = obj
    keyframe_path = data_path
    if "." in data_path:
        parts = data_path.split(".")
        # Walk to the parent of the final property
        for part in parts[:-1]:
            next_target = getattr(keyframe_target, part, None)
            if next_target is None:
                return {"status": "error", "message": f"Property '{data_path}' not found on object"}
            keyframe_target = next_target
        keyframe_path = parts[-1]

    if value is not None:
        # Coerce value types: MCP may pass strings or ints for float properties
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                pass
        if isinstance(value, list):
            value = [float(v) if isinstance(v, str) else v for v in value]

        prop = getattr(keyframe_target, keyframe_path, None)
        if prop is None:
            return {"status": "error", "message": f"Property '{data_path}' not found on object"}

        if isinstance(value, (list, tuple)):
            # Set array property element by element
            for i, v in enumerate(value):
                prop[i] = v
            # Trigger update
            setattr(keyframe_target, keyframe_path, prop)
        elif index >= 0:
            prop[index] = value
            setattr(keyframe_target, keyframe_path, prop)
        else:
            setattr(keyframe_target, keyframe_path, value)

    keyframe_target.keyframe_insert(data_path=keyframe_path, frame=frame, index=index)
    return {
        "status": "ok",
        "object": object_name,
        "data_path": data_path,
        "frame": frame,
        "index": index,
    }


def delete_keyframe(object_name, frame, data_path, index=-1):
    """Delete a keyframe from an object property at a given frame."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    try:
        obj.keyframe_delete(data_path=data_path, frame=frame, index=index)
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}

    return {
        "status": "ok",
        "object": object_name,
        "data_path": data_path,
        "frame": frame,
        "index": index,
    }


def set_keyframe_interpolation(object_name, data_path, mode, frame=None):
    """Set the interpolation mode on keyframes for a given data path."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.animation_data is None or obj.animation_data.action is None:
        return {"status": "error", "message": f"Object '{object_name}' has no animation data"}

    action = obj.animation_data.action
    modified = 0

    for fcurve in _get_fcurves(action):
        if fcurve.data_path == data_path:
            for kp in fcurve.keyframe_points:
                if frame is None or int(kp.co[0]) == int(frame):
                    kp.interpolation = mode
                    modified += 1

    if modified == 0:
        return {"status": "error", "message": f"No keyframes found for '{data_path}'"}

    return {
        "status": "ok",
        "object": object_name,
        "data_path": data_path,
        "mode": mode,
        "keyframes_modified": modified,
    }


def get_keyframes(object_name, data_path=None):
    """Get keyframe data from an object, optionally filtered by data path."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.animation_data is None or obj.animation_data.action is None:
        return {"status": "ok", "object": object_name, "fcurves": []}

    action = obj.animation_data.action
    result = []

    for fcurve in _get_fcurves(action):
        if data_path is not None and fcurve.data_path != data_path:
            continue

        keyframes = []
        for kp in fcurve.keyframe_points:
            keyframes.append({
                "frame": kp.co[0],
                "value": kp.co[1],
                "interpolation": kp.interpolation,
                "handle_left": [kp.handle_left[0], kp.handle_left[1]],
                "handle_right": [kp.handle_right[0], kp.handle_right[1]],
            })

        result.append({
            "data_path": fcurve.data_path,
            "index": fcurve.array_index,
            "keyframes": keyframes,
        })

    return {"status": "ok", "object": object_name, "fcurves": result}


def clear_animation(object_name):
    """Clear all animation data from an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    obj.animation_data_clear()
    return {"status": "ok", "object": object_name, "message": "Animation data cleared"}


def create_action(name):
    """Create a new action."""
    action = bpy.data.actions.new(name=name)
    return {"status": "ok", "action": action.name}


def assign_action(object_name, action_name):
    """Assign an action to an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    action = bpy.data.actions.get(action_name)
    if action is None:
        return {"status": "error", "message": f"Action '{action_name}' not found"}

    if obj.animation_data is None:
        obj.animation_data_create()

    obj.animation_data.action = action
    return {
        "status": "ok",
        "object": object_name,
        "action": action_name,
    }


def list_actions():
    """List all actions with their frame ranges."""
    actions = []
    for action in bpy.data.actions:
        actions.append({
            "name": action.name,
            "frame_start": action.frame_range[0],
            "frame_end": action.frame_range[1],
        })
    return {"status": "ok", "actions": actions}


def push_action_to_nla(object_name, action_name=None, start_frame=None, track_name=None):
    """Push an action to the NLA editor as a strip."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.animation_data is None:
        obj.animation_data_create()

    # Determine which action to push
    if action_name is not None:
        action = bpy.data.actions.get(action_name)
        if action is None:
            return {"status": "error", "message": f"Action '{action_name}' not found"}
    else:
        action = obj.animation_data.action
        if action is None:
            return {"status": "error", "message": "Object has no active action to push"}

    # Determine start frame
    if start_frame is None:
        start_frame = int(action.frame_range[0])

    # Get or create NLA track
    if track_name is not None:
        track = obj.animation_data.nla_tracks.get(track_name)
        if track is None:
            track = obj.animation_data.nla_tracks.new()
            track.name = track_name
    else:
        track = obj.animation_data.nla_tracks.new()
        track.name = action.name

    strip = track.strips.new(name=action.name, start=start_frame, action=action)

    return {
        "status": "ok",
        "object": object_name,
        "track": track.name,
        "strip": strip.name,
        "action": action.name,
        "frame_start": strip.frame_start,
        "frame_end": strip.frame_end,
    }


def set_keyframe_handle_type(object_name, data_path, frame, handle_type, index=-1):
    """Set the handle type on a specific keyframe."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if obj.animation_data is None or obj.animation_data.action is None:
        return {"status": "error", "message": f"Object '{object_name}' has no animation data"}

    action = obj.animation_data.action
    modified = 0

    for fcurve in _get_fcurves(action):
        if fcurve.data_path != data_path:
            continue
        if index >= 0 and fcurve.array_index != index:
            continue

        for kp in fcurve.keyframe_points:
            if int(kp.co[0]) == int(frame):
                kp.handle_left_type = handle_type
                kp.handle_right_type = handle_type
                modified += 1

    if modified == 0:
        return {"status": "error", "message": f"No keyframe found at frame {frame} for '{data_path}'"}

    return {
        "status": "ok",
        "object": object_name,
        "data_path": data_path,
        "frame": frame,
        "handle_type": handle_type,
        "keyframes_modified": modified,
    }


HANDLERS = {
    "set_frame": set_frame,
    "set_frame_range": set_frame_range,
    "insert_keyframe": insert_keyframe,
    "delete_keyframe": delete_keyframe,
    "set_keyframe_interpolation": set_keyframe_interpolation,
    "get_keyframes": get_keyframes,
    "clear_animation": clear_animation,
    "create_action": create_action,
    "assign_action": assign_action,
    "list_actions": list_actions,
    "push_action_to_nla": push_action_to_nla,
    "set_keyframe_handle_type": set_keyframe_handle_type,
}
