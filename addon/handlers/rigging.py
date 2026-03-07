"""Blender addon handler for rigging and bone/armature operations."""

import bpy
import mathutils


def create_armature(name="Armature", location=(0, 0, 0)):
    """Create an armature data block and object, link to the active scene."""
    armature_data = bpy.data.armatures.new(name)
    armature_obj = bpy.data.objects.new(name, armature_data)
    armature_obj.location = mathutils.Vector(location)

    collection = bpy.context.collection
    collection.objects.link(armature_obj)

    bpy.context.view_layer.objects.active = armature_obj

    return {
        "status": "success",
        "name": armature_obj.name,
        "location": list(armature_obj.location),
    }


def add_bone(armature_name, bone_name, head=(0, 0, 0), tail=(0, 0, 1), parent_bone=None):
    """Add a bone to an armature with specified head/tail positions and optional parent."""
    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    try:
        edit_bones = armature_obj.data.edit_bones
        bone = edit_bones.new(bone_name)
        bone.head = mathutils.Vector(head)
        bone.tail = mathutils.Vector(tail)

        if parent_bone is not None:
            parent = edit_bones.get(parent_bone)
            if parent is None:
                bpy.ops.object.mode_set(mode='OBJECT')
                return {"status": "error", "message": f"Parent bone '{parent_bone}' not found"}
            bone.parent = parent

        actual_name = bone.name
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "status": "success",
        "armature": armature_name,
        "bone_name": actual_name,
        "head": list(head),
        "tail": list(tail),
        "parent_bone": parent_bone,
    }


def set_bone_property(armature_name, bone_name, property, value):
    """Set a property on a bone in edit mode.

    Supported properties: head, tail, roll, use_connect, use_deform,
    envelope_distance, head_radius, tail_radius.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    valid_properties = {
        "head", "tail", "roll", "use_connect", "use_deform",
        "envelope_distance", "head_radius", "tail_radius",
    }
    if property not in valid_properties:
        return {"status": "error", "message": f"Invalid property '{property}'. Valid: {sorted(valid_properties)}"}

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    try:
        bone = armature_obj.data.edit_bones.get(bone_name)
        if bone is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            return {"status": "error", "message": f"Bone '{bone_name}' not found"}

        if property in ("head", "tail"):
            setattr(bone, property, mathutils.Vector(value))
        else:
            setattr(bone, property, value)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "status": "success",
        "armature": armature_name,
        "bone_name": bone_name,
        "property": property,
        "value": value,
    }


def delete_bone(armature_name, bone_name):
    """Delete a bone from an armature."""
    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    try:
        bone = armature_obj.data.edit_bones.get(bone_name)
        if bone is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            return {"status": "error", "message": f"Bone '{bone_name}' not found"}

        armature_obj.data.edit_bones.remove(bone)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "status": "success",
        "armature": armature_name,
        "deleted_bone": bone_name,
    }


def list_bones(armature_name):
    """Return a list of all bones in an armature with their properties."""
    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    bones_info = []
    for bone in armature_obj.data.bones:
        bone_data = {
            "name": bone.name,
            "head": list(bone.head_local),
            "tail": list(bone.tail_local),
            "parent": bone.parent.name if bone.parent else None,
            "children": [child.name for child in bone.children],
            "use_connect": bone.use_connect,
            "use_deform": bone.use_deform,
        }
        bones_info.append(bone_data)

    return {
        "status": "success",
        "armature": armature_name,
        "bone_count": len(bones_info),
        "bones": bones_info,
    }


def parent_mesh_to_armature(mesh_name, armature_name, method="AUTOMATIC"):
    """Parent a mesh object to an armature with the specified skinning method.

    Methods: AUTOMATIC (auto weights), EMPTY (empty groups), ENVELOPE.
    """
    mesh_obj = bpy.data.objects.get(mesh_name)
    if mesh_obj is None or mesh_obj.type != 'MESH':
        return {"status": "error", "message": f"Mesh '{mesh_name}' not found"}

    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    method_map = {
        "AUTOMATIC": 'ARMATURE_AUTO',
        "EMPTY": 'ARMATURE_NAME',
        "ENVELOPE": 'ARMATURE_ENVELOPE',
    }
    parent_type = method_map.get(method)
    if parent_type is None:
        return {"status": "error", "message": f"Invalid method '{method}'. Valid: AUTOMATIC, EMPTY, ENVELOPE"}

    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    bpy.ops.object.parent_set(type=parent_type)

    return {
        "status": "success",
        "mesh": mesh_name,
        "armature": armature_name,
        "method": method,
    }


def add_bone_constraint(armature_name, bone_name, constraint_type, **params):
    """Add a constraint to a pose bone.

    Supported constraint_type values: IK, COPY_LOCATION, COPY_ROTATION,
    COPY_SCALE, TRACK_TO, DAMPED_TRACK, LIMIT_LOCATION, LIMIT_ROTATION.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        return {"status": "error", "message": f"Armature '{armature_name}' not found"}

    valid_constraints = {
        "IK", "COPY_LOCATION", "COPY_ROTATION", "COPY_SCALE",
        "TRACK_TO", "DAMPED_TRACK", "LIMIT_LOCATION", "LIMIT_ROTATION",
    }
    if constraint_type not in valid_constraints:
        return {"status": "error", "message": f"Invalid constraint type '{constraint_type}'. Valid: {sorted(valid_constraints)}"}

    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')

    try:
        pose_bone = armature_obj.pose.bones.get(bone_name)
        if pose_bone is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            return {"status": "error", "message": f"Bone '{bone_name}' not found in armature"}

        constraint = pose_bone.constraints.new(type=constraint_type)

        for param_name, param_value in params.items():
            if param_name == "target":
                target_obj = bpy.data.objects.get(param_value)
                if target_obj:
                    constraint.target = target_obj
            elif param_name == "subtarget":
                constraint.subtarget = param_value
            elif param_name == "chain_count" and constraint_type == "IK":
                constraint.chain_count = param_value
            elif param_name == "influence":
                constraint.influence = param_value
            elif hasattr(constraint, param_name):
                setattr(constraint, param_name, param_value)

        constraint_name = constraint.name
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    return {
        "status": "success",
        "armature": armature_name,
        "bone_name": bone_name,
        "constraint_type": constraint_type,
        "constraint_name": constraint_name,
        "params": {k: v for k, v in params.items()},
    }


def create_vertex_group(object_name, group_name, vertex_indices=None, weight=1.0):
    """Add a vertex group to a mesh object, optionally assigning vertices with a weight."""
    obj = bpy.data.objects.get(object_name)
    if obj is None or obj.type != 'MESH':
        return {"status": "error", "message": f"Mesh object '{object_name}' not found"}

    vgroup = obj.vertex_groups.new(name=group_name)

    if vertex_indices is not None and len(vertex_indices) > 0:
        vgroup.add(vertex_indices, weight, 'REPLACE')

    return {
        "status": "success",
        "object": object_name,
        "group_name": vgroup.name,
        "vertex_count": len(vertex_indices) if vertex_indices else 0,
        "weight": weight,
    }


HANDLERS = {
    "create_armature": create_armature,
    "add_bone": add_bone,
    "set_bone_property": set_bone_property,
    "delete_bone": delete_bone,
    "list_bones": list_bones,
    "parent_mesh_to_armature": parent_mesh_to_armature,
    "add_bone_constraint": add_bone_constraint,
    "create_vertex_group": create_vertex_group,
}
