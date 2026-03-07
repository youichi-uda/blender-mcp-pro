import bpy
import mathutils
import math


def create_light(type="POINT", name=None, location=(0, 0, 0), rotation=(0, 0, 0),
                 energy=10.0, color=(1, 1, 1)):
    """Create a light of the given type and add it to the scene."""
    if type not in ("POINT", "SUN", "SPOT", "AREA"):
        return {"status": "error", "message": f"Invalid light type: {type}. Must be POINT, SUN, SPOT, or AREA."}

    if name is None:
        name = f"{type.capitalize()}_Light"

    light_data = bpy.data.lights.new(name=name, type=type)
    light_data.energy = energy
    light_data.color = (color[0], color[1], color[2])

    if type == "SPOT":
        light_data.spot_size = 0.785
        light_data.spot_blend = 0.15
    elif type == "AREA":
        light_data.size = 1.0

    light_obj = bpy.data.objects.new(name=name, object_data=light_data)
    light_obj.location = (location[0], location[1], location[2])
    light_obj.rotation_euler = (rotation[0], rotation[1], rotation[2])

    bpy.context.collection.objects.link(light_obj)

    return {
        "status": "success",
        "name": light_obj.name,
        "type": type,
        "location": list(light_obj.location),
        "energy": light_data.energy,
    }


def set_light_property(name, property, value):
    """Set a property on a light's data block."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"status": "error", "message": f"Object '{name}' not found."}
    if obj.type != 'LIGHT':
        return {"status": "error", "message": f"Object '{name}' is not a light."}

    light_data = obj.data

    if property == "color":
        light_data.color = (value[0], value[1], value[2])
    elif property in ("energy", "radius", "shadow_soft_size", "spot_size", "spot_blend",
                       "size", "specular_factor"):
        setattr(light_data, property, value)
    elif property == "use_shadow":
        light_data.use_shadow = bool(value)
    elif property == "use_contact_shadow":
        light_data.use_contact_shadow = bool(value)
    else:
        return {"status": "error", "message": f"Unknown light property: {property}"}

    return {
        "status": "success",
        "message": f"Set '{property}' to {value} on light '{name}'.",
    }


def delete_light(name):
    """Delete a light object from the scene and Blender data."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return {"status": "error", "message": f"Object '{name}' not found."}
    if obj.type != 'LIGHT':
        return {"status": "error", "message": f"Object '{name}' is not a light."}

    light_data = obj.data

    # Remove from all collections
    for col in obj.users_collection:
        col.objects.unlink(obj)

    bpy.data.objects.remove(obj)
    bpy.data.lights.remove(light_data)

    return {
        "status": "success",
        "message": f"Light '{name}' deleted.",
    }


def list_lights():
    """Return a list of all light objects in the scene."""
    lights = []
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            lights.append({
                "name": obj.name,
                "type": obj.data.type,
                "location": list(obj.location),
                "energy": obj.data.energy,
                "color": list(obj.data.color),
            })

    return {
        "status": "success",
        "lights": lights,
        "count": len(lights),
    }


def _direction_to_rotation(direction):
    """Compute an Euler rotation so that -Z axis points along the given direction vector."""
    direction = direction.normalized()
    # Blender lights emit along their local -Z axis
    track_quat = direction.to_track_quat('-Z', 'Y')
    return track_quat.to_euler()


def create_three_point_lighting(subject_name=None, key_energy=1000, fill_energy=500,
                                rim_energy=750):
    """Create a classic three-point lighting setup aimed at a subject."""
    # Determine subject center
    if subject_name:
        subject = bpy.data.objects.get(subject_name)
        if subject is None:
            return {"status": "error", "message": f"Subject object '{subject_name}' not found."}
        center = mathutils.Vector(subject.location)
    else:
        center = mathutils.Vector((0, 0, 0))

    distance = 5.0
    created_lights = []

    # --- Key Light: front-right, above at ~45 degrees ---
    key_angle_h = math.radians(45)
    key_angle_v = math.radians(45)
    key_pos = center + mathutils.Vector((
        distance * math.sin(key_angle_h) * math.cos(key_angle_v),
        -distance * math.cos(key_angle_h) * math.cos(key_angle_v),
        distance * math.sin(key_angle_v),
    ))
    key_dir = center - key_pos
    key_rot = _direction_to_rotation(key_dir)

    key_result = create_light(
        type="AREA",
        name="Key_Light",
        location=tuple(key_pos),
        rotation=tuple(key_rot),
        energy=key_energy,
        color=(1, 1, 1),
    )
    created_lights.append(key_result.get("name", "Key_Light"))

    # --- Fill Light: front-left, lower angle ---
    fill_angle_h = math.radians(-45)
    fill_angle_v = math.radians(20)
    fill_pos = center + mathutils.Vector((
        distance * math.sin(fill_angle_h) * math.cos(fill_angle_v),
        -distance * math.cos(fill_angle_h) * math.cos(fill_angle_v),
        distance * math.sin(fill_angle_v),
    ))
    fill_dir = center - fill_pos
    fill_rot = _direction_to_rotation(fill_dir)

    fill_result = create_light(
        type="AREA",
        name="Fill_Light",
        location=tuple(fill_pos),
        rotation=tuple(fill_rot),
        energy=fill_energy,
        color=(1, 1, 1),
    )
    created_lights.append(fill_result.get("name", "Fill_Light"))

    # --- Rim / Back Light: behind and above the subject ---
    rim_angle_h = math.radians(180)
    rim_angle_v = math.radians(45)
    rim_pos = center + mathutils.Vector((
        distance * math.sin(rim_angle_h) * math.cos(rim_angle_v),
        -distance * math.cos(rim_angle_h) * math.cos(rim_angle_v),
        distance * math.sin(rim_angle_v),
    ))
    rim_dir = center - rim_pos
    rim_rot = _direction_to_rotation(rim_dir)

    rim_result = create_light(
        type="AREA",
        name="Rim_Light",
        location=tuple(rim_pos),
        rotation=tuple(rim_rot),
        energy=rim_energy,
        color=(1, 1, 1),
    )
    created_lights.append(rim_result.get("name", "Rim_Light"))

    return {
        "status": "success",
        "message": "Three-point lighting setup created.",
        "lights": created_lights,
        "subject": subject_name if subject_name else "origin",
    }


HANDLERS = {
    "create_light": create_light,
    "set_light_property": set_light_property,
    "delete_light": delete_light,
    "list_lights": list_lights,
    "create_three_point_lighting": create_three_point_lighting,
}
