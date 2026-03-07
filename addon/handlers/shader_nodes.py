import bpy
import os


def create_shader_node(material_name, node_type, location=(0, 0)):
    """Create a shader node in the specified material's node tree."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    if not mat.use_nodes:
        mat.use_nodes = True
    tree = mat.node_tree
    node = tree.nodes.new(type=node_type)
    node.location = (location[0], location[1])
    return {
        "name": node.name,
        "type": node.bl_idname,
        "location": [node.location.x, node.location.y],
    }


def connect_shader_nodes(material_name, from_node, from_socket, to_node, to_socket):
    """Connect two shader nodes via their sockets."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    tree = mat.node_tree
    node_from = tree.nodes.get(from_node)
    if not node_from:
        return {"error": f"Node '{from_node}' not found"}
    node_to = tree.nodes.get(to_node)
    if not node_to:
        return {"error": f"Node '{to_node}' not found"}

    if isinstance(from_socket, int):
        output = node_from.outputs[from_socket]
    else:
        output = node_from.outputs[from_socket]

    if isinstance(to_socket, int):
        inp = node_to.inputs[to_socket]
    else:
        inp = node_to.inputs[to_socket]

    tree.links.new(output, inp)
    return {"status": "ok", "message": f"Connected {from_node}[{from_socket}] -> {to_node}[{to_socket}]"}


def disconnect_shader_nodes(material_name, node_name, input_name):
    """Remove links connected to a specific input on a node."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    tree = mat.node_tree
    node = tree.nodes.get(node_name)
    if not node:
        return {"error": f"Node '{node_name}' not found"}

    if isinstance(input_name, int):
        inp = node.inputs[input_name]
    else:
        inp = node.inputs[input_name]

    links_to_remove = [link for link in tree.links if link.to_socket == inp]
    for link in links_to_remove:
        tree.links.remove(link)
    return {"status": "ok", "message": f"Disconnected {len(links_to_remove)} link(s) from {node_name}[{input_name}]"}


def set_shader_node_value(material_name, node_name, input_name, value):
    """Set the default_value of a node input. Handles float, vector, and color."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    tree = mat.node_tree
    node = tree.nodes.get(node_name)
    if not node:
        return {"error": f"Node '{node_name}' not found"}

    if isinstance(input_name, int):
        inp = node.inputs[input_name]
    else:
        inp = node.inputs[input_name]

    if isinstance(value, (list, tuple)):
        inp.default_value = value
    else:
        inp.default_value = value

    return {"status": "ok", "message": f"Set {node_name}[{input_name}] = {value}"}


def get_shader_node_tree(material_name):
    """Return the full node tree: nodes with inputs and links."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    if not mat.use_nodes:
        return {"error": f"Material '{material_name}' does not use nodes"}
    tree = mat.node_tree

    nodes_info = []
    for node in tree.nodes:
        inputs_info = []
        for inp in node.inputs:
            inp_data = {"name": inp.name, "type": inp.type}
            if hasattr(inp, "default_value"):
                val = inp.default_value
                try:
                    inp_data["default_value"] = list(val)
                except TypeError:
                    inp_data["default_value"] = val
            inputs_info.append(inp_data)
        nodes_info.append({
            "name": node.name,
            "type": node.bl_idname,
            "location": [node.location.x, node.location.y],
            "inputs": inputs_info,
        })

    links_info = []
    for link in tree.links:
        links_info.append({
            "from_node": link.from_node.name,
            "from_socket": link.from_socket.name,
            "to_node": link.to_node.name,
            "to_socket": link.to_socket.name,
        })

    return {"nodes": nodes_info, "links": links_info}


def delete_shader_node(material_name, node_name):
    """Remove a node from the material's node tree."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    tree = mat.node_tree
    node = tree.nodes.get(node_name)
    if not node:
        return {"error": f"Node '{node_name}' not found"}
    tree.nodes.remove(node)
    return {"status": "ok", "message": f"Deleted node '{node_name}' from '{material_name}'"}


def add_image_texture_node(material_name, image_path):
    """Create a ShaderNodeTexImage and load an image from the given path."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    if not mat.use_nodes:
        mat.use_nodes = True
    tree = mat.node_tree
    node = tree.nodes.new(type="ShaderNodeTexImage")

    abs_path = os.path.abspath(bpy.path.abspath(image_path))
    image = bpy.data.images.load(abs_path, check_existing=True)
    node.image = image

    return {"name": node.name, "image": image.name}


def create_emission_material(name, color=(1, 1, 1, 1), strength=1.0):
    """Create a material with an Emission shader connected to the output."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree

    # Clear default nodes
    for node in tree.nodes:
        tree.nodes.remove(node)

    output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    emission_node = tree.nodes.new(type="ShaderNodeEmission")
    emission_node.location = (0, 0)
    emission_node.inputs["Color"].default_value = color
    emission_node.inputs["Strength"].default_value = strength

    tree.links.new(emission_node.outputs["Emission"], output_node.inputs["Surface"])

    return {"material": mat.name}


def create_glass_material(name, color=(1, 1, 1, 1), ior=1.45, roughness=0.0):
    """Create a material with a Glass BSDF shader connected to the output."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree

    # Clear default nodes
    for node in tree.nodes:
        tree.nodes.remove(node)

    output_node = tree.nodes.new(type="ShaderNodeOutputMaterial")
    output_node.location = (300, 0)

    glass_node = tree.nodes.new(type="ShaderNodeBsdfGlass")
    glass_node.location = (0, 0)
    glass_node.inputs["Color"].default_value = color
    glass_node.inputs["IOR"].default_value = ior
    glass_node.inputs["Roughness"].default_value = roughness

    tree.links.new(glass_node.outputs["BSDF"], output_node.inputs["Surface"])

    return {"material": mat.name}


def set_shader_node_property(material_name, node_name, property_name, value):
    """Set a property directly on a node (e.g., blend_type, operation, interpolation)."""
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return {"error": f"Material '{material_name}' not found"}
    tree = mat.node_tree
    node = tree.nodes.get(node_name)
    if not node:
        return {"error": f"Node '{node_name}' not found"}
    if not hasattr(node, property_name):
        return {"error": f"Node '{node_name}' has no property '{property_name}'"}
    setattr(node, property_name, value)
    return {"status": "ok", "message": f"Set {node_name}.{property_name} = {value}"}


HANDLERS = {
    "create_shader_node": create_shader_node,
    "connect_shader_nodes": connect_shader_nodes,
    "disconnect_shader_nodes": disconnect_shader_nodes,
    "set_shader_node_value": set_shader_node_value,
    "get_shader_node_tree": get_shader_node_tree,
    "delete_shader_node": delete_shader_node,
    "add_image_texture_node": add_image_texture_node,
    "create_emission_material": create_emission_material,
    "create_glass_material": create_glass_material,
    "set_shader_node_property": set_shader_node_property,
}
