import bpy
import mathutils


def create_object(type, name=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    """Create a new object of the specified type."""
    type = type.upper()

    primitive_ops = {
        "CUBE": bpy.ops.mesh.primitive_cube_add,
        "SPHERE": bpy.ops.mesh.primitive_uv_sphere_add,
        "CYLINDER": bpy.ops.mesh.primitive_cylinder_add,
        "CONE": bpy.ops.mesh.primitive_cone_add,
        "TORUS": bpy.ops.mesh.primitive_torus_add,
        "PLANE": bpy.ops.mesh.primitive_plane_add,
        "CIRCLE": bpy.ops.mesh.primitive_circle_add,
        "MONKEY": bpy.ops.mesh.primitive_monkey_add,
    }

    if type == "EMPTY":
        obj_name = name or "Empty"
        obj = bpy.data.objects.new(obj_name, None)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = rotation
        obj.scale = scale
    elif type == "TEXT":
        bpy.ops.object.text_add(location=location, rotation=rotation, scale=scale)
        obj = bpy.context.active_object
        if name:
            obj.name = name
    elif type in primitive_ops:
        primitive_ops[type](location=location, rotation=rotation, scale=scale)
        obj = bpy.context.active_object
        if name:
            obj.name = name
    else:
        return {"error": f"Unknown object type: {type}"}

    return {
        "name": obj.name,
        "type": type,
        "location": list(obj.location),
    }


def delete_object(name):
    """Delete an object by name."""
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"error": f"Object '{name}' not found"}

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.delete()

    return {"deleted": name}


def duplicate_object(name, linked=False):
    """Duplicate an object, optionally as a linked duplicate."""
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"error": f"Object '{name}' not found"}

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    if linked:
        bpy.ops.object.duplicate_move_linked()
    else:
        bpy.ops.object.duplicate_move()

    new_obj = bpy.context.active_object

    return {
        "original": name,
        "new_name": new_obj.name,
        "linked": linked,
    }


def set_transform(name, location=None, rotation=None, scale=None):
    """Set the transform of an object. Only provided values are updated."""
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"error": f"Object '{name}' not found"}

    if location is not None:
        obj.location = location
    if rotation is not None:
        obj.rotation_euler = rotation
    if scale is not None:
        obj.scale = scale

    return {
        "name": name,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
    }


def set_parent(child, parent):
    """Set a parent-child relationship between two objects."""
    child_obj = bpy.data.objects.get(child)
    if not child_obj:
        return {"error": f"Child object '{child}' not found"}

    parent_obj = bpy.data.objects.get(parent)
    if not parent_obj:
        return {"error": f"Parent object '{parent}' not found"}

    child_obj.parent = parent_obj
    child_obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()

    return {
        "child": child_obj.name,
        "parent": parent_obj.name,
    }


def clear_parent(name, keep_transform=True):
    """Clear the parent of an object, optionally keeping its world transform."""
    obj = bpy.data.objects.get(name)
    if not obj:
        return {"error": f"Object '{name}' not found"}

    if not obj.parent:
        return {"error": f"Object '{name}' has no parent"}

    old_parent = obj.parent.name

    if keep_transform:
        world_matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world_matrix
    else:
        obj.parent = None

    return {
        "name": name,
        "old_parent": old_parent,
        "keep_transform": keep_transform,
    }


def create_collection(name):
    """Create a new collection and link it to the active scene."""
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)

    return {
        "name": collection.name,
    }


def move_to_collection(object_name, collection_name):
    """Move an object to a target collection, unlinking from all current collections."""
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"error": f"Object '{object_name}' not found"}

    target = bpy.data.collections.get(collection_name)
    if not target:
        return {"error": f"Collection '{collection_name}' not found"}

    for col in list(obj.users_collection):
        col.objects.unlink(obj)

    target.objects.link(obj)

    return {
        "object": obj.name,
        "collection": target.name,
    }


def join_objects(object_names):
    """Join multiple objects into one."""
    if not object_names or len(object_names) < 2:
        return {"error": "At least two object names are required"}

    objects = []
    for obj_name in object_names:
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return {"error": f"Object '{obj_name}' not found"}
        objects.append(obj)

    bpy.ops.object.select_all(action='DESELECT')

    for obj in objects:
        obj.select_set(True)

    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()

    result_obj = bpy.context.active_object

    return {
        "result_name": result_obj.name,
        "joined_count": len(object_names),
    }


HANDLERS = {
    "create_object": create_object,
    "delete_object": delete_object,
    "duplicate_object": duplicate_object,
    "set_transform": set_transform,
    "set_parent": set_parent,
    "clear_parent": clear_parent,
    "create_collection": create_collection,
    "move_to_collection": move_to_collection,
    "join_objects": join_objects,
}
