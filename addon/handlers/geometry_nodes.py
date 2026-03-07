"""
Blender addon handler for Geometry Nodes operations.
Provides functions to create, inspect, and manipulate Geometry Nodes modifiers and node trees.
"""

import bpy


def get_geometry_nodes_status(object_name):
    """Check if an object has Geometry Nodes modifiers and return their info."""
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    gn_modifiers = []
    for mod in obj.modifiers:
        if mod.type == 'NODES':
            node_group_name = mod.node_group.name if mod.node_group else None
            gn_modifiers.append({
                "modifier_name": mod.name,
                "node_group_name": node_group_name,
            })

    return {
        "status": "ok",
        "object_name": object_name,
        "has_geometry_nodes": len(gn_modifiers) > 0,
        "modifiers": gn_modifiers,
    }


def get_node_group_info(node_group_name):
    """Get detailed information about a node group including nodes, links, and group I/O."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    nodes_info = []
    for node in node_group.nodes:
        inputs = []
        for inp in node.inputs:
            input_data = {"name": inp.name, "type": inp.type}
            if hasattr(inp, "default_value"):
                try:
                    val = inp.default_value
                    if hasattr(val, "__len__"):
                        input_data["default_value"] = list(val)
                    else:
                        input_data["default_value"] = val
                except Exception:
                    pass
            inputs.append(input_data)

        outputs = []
        for out in node.outputs:
            outputs.append({"name": out.name, "type": out.type})

        nodes_info.append({
            "name": node.name,
            "type": node.type,
            "bl_idname": node.bl_idname,
            "location": list(node.location),
            "inputs": inputs,
            "outputs": outputs,
        })

    links_info = []
    for link in node_group.links:
        links_info.append({
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name,
        })

    # Group inputs and outputs
    group_inputs = []
    group_outputs = []
    try:
        # Blender 4.x
        for item in node_group.interface.items_tree:
            entry = {"name": item.name, "socket_type": item.socket_type if hasattr(item, "socket_type") else None}
            if hasattr(item, "in_out"):
                if item.in_out == 'INPUT':
                    group_inputs.append(entry)
                elif item.in_out == 'OUTPUT':
                    group_outputs.append(entry)
    except AttributeError:
        # Blender 3.x fallback
        for inp in node_group.inputs:
            group_inputs.append({"name": inp.name, "type": inp.type})
        for out in node_group.outputs:
            group_outputs.append({"name": out.name, "type": out.type})

    return {
        "status": "ok",
        "node_group_name": node_group_name,
        "nodes": nodes_info,
        "links": links_info,
        "group_inputs": group_inputs,
        "group_outputs": group_outputs,
    }


def create_geometry_nodes_modifier(object_name, node_group_name=None):
    """Add a Geometry Nodes modifier to an object, optionally using an existing node group."""
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    modifier = obj.modifiers.new(name="GeometryNodes", type='NODES')

    if node_group_name and node_group_name in bpy.data.node_groups:
        modifier.node_group = bpy.data.node_groups[node_group_name]
    else:
        # Create a new node group
        ng = bpy.data.node_groups.new(name=node_group_name or "Geometry Nodes", type='GeometryNodeTree')

        group_input = ng.nodes.new('NodeGroupInput')
        group_input.location = (-200, 0)

        group_output = ng.nodes.new('NodeGroupOutput')
        group_output.location = (200, 0)

        # Add default geometry input and output sockets
        try:
            # Blender 4.x
            ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
            ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        except AttributeError:
            # Blender 3.x fallback
            ng.inputs.new('NodeSocketGeometry', 'Geometry')
            ng.outputs.new('NodeSocketGeometry', 'Geometry')

        # Connect Group Input Geometry to Group Output Geometry
        ng.links.new(group_input.outputs[0], group_output.inputs[0])

        modifier.node_group = ng

    return {
        "status": "ok",
        "modifier_name": modifier.name,
        "node_group_name": modifier.node_group.name,
    }


def add_geometry_node(node_group_name, node_type, location=(0, 0), name=None):
    """Add a node of the given type to a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    try:
        node = node_group.nodes.new(type=node_type)
    except RuntimeError as e:
        return {"status": "error", "message": f"Failed to create node of type '{node_type}': {str(e)}"}

    node.location = (location[0], location[1])
    if name:
        node.name = name
        node.label = name

    return {
        "status": "ok",
        "node_name": node.name,
        "node_type": node.bl_idname,
    }


def connect_gn_nodes(node_group_name, from_node, from_socket, to_node, to_socket):
    """Create a link between two nodes in a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    src_node = node_group.nodes.get(from_node)
    if not src_node:
        return {"status": "error", "message": f"Source node '{from_node}' not found"}

    dst_node = node_group.nodes.get(to_node)
    if not dst_node:
        return {"status": "error", "message": f"Destination node '{to_node}' not found"}

    # Resolve from_socket
    if isinstance(from_socket, int):
        if from_socket < len(src_node.outputs):
            out_socket = src_node.outputs[from_socket]
        else:
            return {"status": "error", "message": f"Output socket index {from_socket} out of range on '{from_node}'"}
    else:
        out_socket = src_node.outputs.get(from_socket)
        if not out_socket:
            return {"status": "error", "message": f"Output socket '{from_socket}' not found on '{from_node}'"}

    # Resolve to_socket
    if isinstance(to_socket, int):
        if to_socket < len(dst_node.inputs):
            in_socket = dst_node.inputs[to_socket]
        else:
            return {"status": "error", "message": f"Input socket index {to_socket} out of range on '{to_node}'"}
    else:
        in_socket = dst_node.inputs.get(to_socket)
        if not in_socket:
            return {"status": "error", "message": f"Input socket '{to_socket}' not found on '{to_node}'"}

    node_group.links.new(out_socket, in_socket)

    return {
        "status": "ok",
        "message": f"Connected '{from_node}'.'{out_socket.name}' -> '{to_node}'.'{in_socket.name}'",
    }


def set_gn_node_input(node_group_name, node_name, input_name, value):
    """Set the default value of a node input in a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    node = node_group.nodes.get(node_name)
    if not node:
        return {"status": "error", "message": f"Node '{node_name}' not found"}

    # Resolve input socket
    if isinstance(input_name, int):
        if input_name < len(node.inputs):
            socket = node.inputs[input_name]
        else:
            return {"status": "error", "message": f"Input index {input_name} out of range on '{node_name}'"}
    else:
        socket = node.inputs.get(input_name)
        if not socket:
            return {"status": "error", "message": f"Input '{input_name}' not found on '{node_name}'"}

    if not hasattr(socket, "default_value"):
        return {"status": "error", "message": f"Input '{socket.name}' on '{node_name}' has no default_value"}

    try:
        if isinstance(value, (list, tuple)):
            socket.default_value = type(socket.default_value)(value)
        elif isinstance(value, bool):
            socket.default_value = value
        elif isinstance(value, float):
            socket.default_value = value
        elif isinstance(value, int):
            socket.default_value = value
        else:
            socket.default_value = value
    except Exception as e:
        return {"status": "error", "message": f"Failed to set value: {str(e)}"}

    return {
        "status": "ok",
        "message": f"Set '{node_name}'.'{socket.name}' to {value}",
    }


def add_gn_group_input(node_group_name, input_name, input_type, default_value=None):
    """Add a group-level input socket to a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    type_map = {
        "FLOAT": "NodeSocketFloat",
        "INT": "NodeSocketInt",
        "VECTOR": "NodeSocketVector",
        "BOOLEAN": "NodeSocketBool",
        "RGBA": "NodeSocketColor",
        "STRING": "NodeSocketString",
        "OBJECT": "NodeSocketObject",
        "COLLECTION": "NodeSocketCollection",
        "MATERIAL": "NodeSocketMaterial",
        "GEOMETRY": "NodeSocketGeometry",
    }

    socket_type = type_map.get(input_type)
    if not socket_type:
        return {"status": "error", "message": f"Unknown input type '{input_type}'. Valid types: {list(type_map.keys())}"}

    try:
        # Blender 4.x
        new_input = node_group.interface.new_socket(
            name=input_name, in_out='INPUT', socket_type=socket_type
        )
    except AttributeError:
        # Blender 3.x fallback
        new_input = node_group.inputs.new(socket_type, input_name)

    if default_value is not None and hasattr(new_input, "default_value"):
        try:
            if isinstance(default_value, (list, tuple)):
                new_input.default_value = type(new_input.default_value)(default_value)
            else:
                new_input.default_value = default_value
        except Exception:
            pass

    return {
        "status": "ok",
        "input_name": input_name,
        "socket_type": socket_type,
    }


def add_gn_group_output(node_group_name, output_name, output_type):
    """Add a group-level output socket to a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    type_map = {
        "FLOAT": "NodeSocketFloat",
        "INT": "NodeSocketInt",
        "VECTOR": "NodeSocketVector",
        "BOOLEAN": "NodeSocketBool",
        "RGBA": "NodeSocketColor",
        "STRING": "NodeSocketString",
        "OBJECT": "NodeSocketObject",
        "COLLECTION": "NodeSocketCollection",
        "MATERIAL": "NodeSocketMaterial",
        "GEOMETRY": "NodeSocketGeometry",
    }

    socket_type = type_map.get(output_type)
    if not socket_type:
        return {"status": "error", "message": f"Unknown output type '{output_type}'. Valid types: {list(type_map.keys())}"}

    try:
        # Blender 4.x
        node_group.interface.new_socket(
            name=output_name, in_out='OUTPUT', socket_type=socket_type
        )
    except AttributeError:
        # Blender 3.x fallback
        node_group.outputs.new(socket_type, output_name)

    return {
        "status": "ok",
        "output_name": output_name,
        "socket_type": socket_type,
    }


def list_gn_node_types():
    """Return a categorized dictionary of available geometry node types."""
    return {
        "status": "ok",
        "node_types": {
            "Mesh Primitives": {
                "GeometryNodeMeshGrid": "Grid",
                "GeometryNodeMeshCube": "Cube",
                "GeometryNodeMeshUVSphere": "UV Sphere",
                "GeometryNodeMeshCylinder": "Cylinder",
                "GeometryNodeMeshCone": "Cone",
            },
            "Curve Primitives": {
                "GeometryNodeCurvePrimitiveLine": "Curve Line",
                "GeometryNodeCurvePrimitiveCircle": "Curve Circle",
            },
            "Curve Operations": {
                "GeometryNodeCurveToMesh": "Curve to Mesh",
                "GeometryNodeFillCurve": "Fill Curve",
            },
            "Mesh Operations": {
                "GeometryNodeMeshBoolean": "Mesh Boolean",
                "GeometryNodeExtrudeMesh": "Extrude Mesh",
                "GeometryNodeSubdivideMesh": "Subdivide Mesh",
                "GeometryNodeScaleElements": "Scale Elements",
                "GeometryNodeMergeByDistance": "Merge by Distance",
            },
            "Point Operations": {
                "GeometryNodeDistributePointsOnFaces": "Distribute Points on Faces",
                "GeometryNodeInstanceOnPoints": "Instance on Points",
            },
            "Geometry": {
                "GeometryNodeJoinGeometry": "Join Geometry",
                "GeometryNodeRealizeInstances": "Realize Instances",
                "GeometryNodeTransform": "Transform",
                "GeometryNodeSetPosition": "Set Position",
                "GeometryNodeSetMaterial": "Set Material",
            },
            "Input": {
                "GeometryNodeInputPosition": "Position",
            },
            "Attribute": {
                "GeometryNodeAttributeStatistic": "Attribute Statistic",
                "GeometryNodeCaptureAttribute": "Capture Attribute",
            },
            "Math": {
                "GeometryNodeMath": "Math (GN)",
                "ShaderNodeMath": "Math",
                "ShaderNodeVectorMath": "Vector Math",
                "GeometryNodeBooleanMath": "Boolean Math",
                "FunctionNodeCompare": "Compare",
            },
            "Utilities": {
                "GeometryNodeSwitch": "Switch",
                "FunctionNodeRandomValue": "Random Value",
                "GeometryNodeViewer": "Viewer",
            },
        },
    }


def get_gn_node_tree(node_group_name):
    """Return the full node tree structure: nodes with input values and links."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    nodes_info = []
    for node in node_group.nodes:
        inputs = []
        for inp in node.inputs:
            input_data = {"name": inp.name, "type": inp.type, "is_linked": inp.is_linked}
            if hasattr(inp, "default_value"):
                try:
                    val = inp.default_value
                    if hasattr(val, "__len__"):
                        input_data["default_value"] = list(val)
                    else:
                        input_data["default_value"] = val
                except Exception:
                    pass
            inputs.append(input_data)

        outputs = []
        for out in node.outputs:
            outputs.append({"name": out.name, "type": out.type, "is_linked": out.is_linked})

        nodes_info.append({
            "name": node.name,
            "type": node.bl_idname,
            "location": list(node.location),
            "inputs": inputs,
            "outputs": outputs,
        })

    links_info = []
    for link in node_group.links:
        links_info.append({
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "from_socket_index": list(link.from_node.outputs).index(link.from_socket),
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name,
            "to_socket_index": list(link.to_node.inputs).index(link.to_socket),
        })

    return {
        "status": "ok",
        "node_group_name": node_group_name,
        "nodes": nodes_info,
        "links": links_info,
    }


def apply_geometry_nodes(object_name, modifier_name=None):
    """Apply a Geometry Nodes modifier on an object."""
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"status": "error", "message": f"Object '{object_name}' not found"}

    if modifier_name:
        mod = obj.modifiers.get(modifier_name)
        if not mod:
            return {"status": "error", "message": f"Modifier '{modifier_name}' not found on '{object_name}'"}
        if mod.type != 'NODES':
            return {"status": "error", "message": f"Modifier '{modifier_name}' is not a Geometry Nodes modifier"}
    else:
        # Find first GN modifier
        mod = None
        for m in obj.modifiers:
            if m.type == 'NODES':
                mod = m
                break
        if not mod:
            return {"status": "error", "message": f"No Geometry Nodes modifier found on '{object_name}'"}

    mod_name = mod.name

    # Set active object and apply
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.modifier_apply(modifier=mod_name)
    except RuntimeError as e:
        return {"status": "error", "message": f"Failed to apply modifier '{mod_name}': {str(e)}"}

    return {
        "status": "ok",
        "message": f"Applied modifier '{mod_name}' on '{object_name}'",
    }


def remove_geometry_node(node_group_name, node_name):
    """Remove a node from a geometry node group."""
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        return {"status": "error", "message": f"Node group '{node_group_name}' not found"}

    node = node_group.nodes.get(node_name)
    if not node:
        return {"status": "error", "message": f"Node '{node_name}' not found in '{node_group_name}'"}

    node_group.nodes.remove(node)

    return {
        "status": "ok",
        "message": f"Removed node '{node_name}' from '{node_group_name}'",
    }


HANDLERS = {
    "get_geometry_nodes_status": get_geometry_nodes_status,
    "get_node_group_info": get_node_group_info,
    "create_geometry_nodes_modifier": create_geometry_nodes_modifier,
    "add_geometry_node": add_geometry_node,
    "connect_gn_nodes": connect_gn_nodes,
    "set_gn_node_input": set_gn_node_input,
    "add_gn_group_input": add_gn_group_input,
    "add_gn_group_output": add_gn_group_output,
    "list_gn_node_types": list_gn_node_types,
    "get_gn_node_tree": get_gn_node_tree,
    "apply_geometry_nodes": apply_geometry_nodes,
    "remove_geometry_node": remove_geometry_node,
}
