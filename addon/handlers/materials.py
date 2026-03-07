import bpy


def create_material(name):
    """Create a new material with nodes enabled."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    return {"material_name": mat.name}


def assign_material(object_name, material_name):
    """Assign a material to an object."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"Object '{object_name}' not found"}

    mat = bpy.data.materials.get(material_name)
    if mat is None:
        return {"error": f"Material '{material_name}' not found"}

    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat

    return {"message": f"Material '{material_name}' assigned to object '{object_name}'"}


def set_principled_bsdf(
    material_name,
    base_color=None,
    metallic=None,
    roughness=None,
    specular=None,
    emission_color=None,
    emission_strength=None,
    alpha=None,
    transmission=None,
    ior=None,
    subsurface_weight=None,
    coat_weight=None,
    sheen_weight=None,
    anisotropic=None,
    normal_strength=None,
):
    """Set Principled BSDF node properties on a material.

    Fix for Issue #190: Always checks for an existing Principled BSDF node
    before creating one, preventing duplicate nodes.
    """
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        return {"error": f"Material '{material_name}' not found"}

    if not mat.use_nodes:
        mat.use_nodes = True

    node_tree = mat.node_tree

    # Fix for Issue #190 - Find existing Principled BSDF node instead of
    # always creating a new one, which caused duplicate nodes.
    principled_node = None
    for node in node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            principled_node = node
            break

    if principled_node is None:
        principled_node = node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
        principled_node.location = (0, 0)

        # Connect to Material Output if one exists
        output_node = None
        for node in node_tree.nodes:
            if node.type == "OUTPUT_MATERIAL":
                output_node = node
                break

        if output_node is None:
            output_node = node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            output_node.location = (300, 0)

        node_tree.links.new(
            principled_node.outputs["BSDF"], output_node.inputs["Surface"]
        )

    # Map parameter names to Blender 4.x Principled BSDF input names
    param_to_input = {
        "base_color": "Base Color",
        "metallic": "Metallic",
        "roughness": "Roughness",
        "specular": "Specular IOR Level",
        "emission_color": "Emission Color",
        "emission_strength": "Emission Strength",
        "alpha": "Alpha",
        "transmission": "Transmission Weight",
        "ior": "IOR",
        "subsurface_weight": "Subsurface Weight",
        "coat_weight": "Coat Weight",
        "sheen_weight": "Sheen Weight",
        "anisotropic": "Anisotropic",
        "normal_strength": "Normal",
    }

    params = {
        "base_color": base_color,
        "metallic": metallic,
        "roughness": roughness,
        "specular": specular,
        "emission_color": emission_color,
        "emission_strength": emission_strength,
        "alpha": alpha,
        "transmission": transmission,
        "ior": ior,
        "subsurface_weight": subsurface_weight,
        "coat_weight": coat_weight,
        "sheen_weight": sheen_weight,
        "anisotropic": anisotropic,
        "normal_strength": normal_strength,
    }

    set_values = {}

    for param_name, value in params.items():
        if value is None:
            continue

        input_name = param_to_input.get(param_name)
        if input_name is None:
            continue

        if input_name not in principled_node.inputs:
            continue

        if isinstance(value, list):
            principled_node.inputs[input_name].default_value = value
        else:
            principled_node.inputs[input_name].default_value = value

        set_values[param_name] = value

    return {"material_name": material_name, "set_values": set_values}


def get_material_info(material_name):
    """Return detailed information about a material's node tree."""
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        return {"error": f"Material '{material_name}' not found"}

    result = {"name": mat.name, "nodes": [], "links": []}

    if not mat.use_nodes or mat.node_tree is None:
        return result

    for node in mat.node_tree.nodes:
        node_info = {
            "type": node.type,
            "name": node.name,
            "inputs": {},
        }
        for inp in node.inputs:
            try:
                node_info["inputs"][inp.name] = {
                    "type": inp.type,
                    "default_value": list(inp.default_value)
                    if hasattr(inp.default_value, "__iter__")
                    else inp.default_value,
                }
            except (AttributeError, TypeError):
                node_info["inputs"][inp.name] = {"type": inp.type}
        result["nodes"].append(node_info)

    for link in mat.node_tree.links:
        result["links"].append(
            {
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            }
        )

    return result


def list_materials():
    """Return a list of all material names in the blend file."""
    return {"materials": [mat.name for mat in bpy.data.materials]}


def delete_material(name):
    """Remove a material from bpy.data.materials."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        return {"error": f"Material '{name}' not found"}

    bpy.data.materials.remove(mat)
    return {"message": f"Material '{name}' deleted"}


def set_material_slot(object_name, slot_index, material_name):
    """Set a specific material slot on an object to a given material."""
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {"error": f"Object '{object_name}' not found"}

    mat = bpy.data.materials.get(material_name)
    if mat is None:
        return {"error": f"Material '{material_name}' not found"}

    if slot_index < 0 or slot_index >= len(obj.data.materials):
        return {
            "error": f"Slot index {slot_index} out of range "
            f"(object has {len(obj.data.materials)} slots)"
        }

    obj.data.materials[slot_index] = mat
    return {
        "message": f"Material slot {slot_index} on '{object_name}' set to '{material_name}'"
    }


HANDLERS = {
    "create_material": create_material,
    "assign_material": assign_material,
    "set_principled_bsdf": set_principled_bsdf,
    "get_material_info": get_material_info,
    "list_materials": list_materials,
    "delete_material": delete_material,
    "set_material_slot": set_material_slot,
}
