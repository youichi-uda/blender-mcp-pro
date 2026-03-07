"""
Blender addon handler for external asset services: Poly Haven, Sketchfab, Hyper3D Rodin.

Provides functions to search, download, and import assets from these services
directly into Blender scenes.
"""

import bpy
import json
import os
import tempfile
import urllib.request
import urllib.parse
import urllib.error
import zipfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30  # seconds


def _fetch_json(url, headers=None, method="GET", data=None, timeout=_DEFAULT_TIMEOUT):
    """Perform an HTTP request and return parsed JSON."""
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", "BlenderMCPPro/1.0")
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    if data is not None:
        if isinstance(data, dict):
            data = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        elif isinstance(data, str):
            data = data.encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}: {exc.reason}"}
    except urllib.error.URLError as exc:
        return {"error": f"URL error: {exc.reason}"}
    except Exception as exc:
        return {"error": str(exc)}


def _download_file(url, dest_path, timeout=_DEFAULT_TIMEOUT):
    """Download a file from *url* to *dest_path*. Returns True on success."""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "BlenderMCPPro/1.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(dest_path, "wb") as fh:
                fh.write(resp.read())
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Poly Haven
# ---------------------------------------------------------------------------

def get_polyhaven_status():
    """Return availability status for Poly Haven."""
    return {"available": True, "service": "Poly Haven"}


def get_polyhaven_categories(asset_type):
    """Return a list of categories for the given *asset_type*.

    Parameters
    ----------
    asset_type : str
        One of ``"hdris"``, ``"textures"``, ``"models"``.
    """
    url = f"https://api.polyhaven.com/categories/{asset_type}"
    result = _fetch_json(url)
    if isinstance(result, dict) and "error" in result:
        return result
    # The API returns a dict of {category_name: count}; return just the names.
    if isinstance(result, dict):
        return sorted(result.keys())
    return result


def search_polyhaven_assets(query=None, asset_type="all", categories=None):
    """Search Poly Haven assets.

    Parameters
    ----------
    query : str or None
        Substring to match against asset names.
    asset_type : str
        Asset type filter (``"hdris"``, ``"textures"``, ``"models"``, or ``"all"``).
    categories : str or None
        Comma-separated category names to filter by.

    Returns
    -------
    list[dict]
        Up to 20 results with keys ``id``, ``name``, ``type``, ``categories``.
    """
    url = f"https://api.polyhaven.com/assets?t={asset_type}"
    result = _fetch_json(url)
    if isinstance(result, dict) and "error" in result:
        return result

    assets = []
    category_set = None
    if categories:
        category_set = {c.strip().lower() for c in categories.split(",")}

    for asset_id, info in result.items():
        name = info.get("name", asset_id)

        # Substring filter on name
        if query and query.lower() not in name.lower():
            continue

        # Category filter
        asset_cats = info.get("categories", [])
        if category_set:
            asset_cat_lower = {c.lower() for c in asset_cats}
            if not category_set & asset_cat_lower:
                continue

        assets.append({
            "id": asset_id,
            "name": name,
            "type": info.get("type", asset_type),
            "categories": asset_cats,
        })

        if len(assets) >= 20:
            break

    return assets


def download_polyhaven_asset(asset_id, asset_type, resolution="1k"):
    """Download and import a Poly Haven asset into the current Blender scene.

    Parameters
    ----------
    asset_id : str
        The Poly Haven asset identifier.
    asset_type : str
        One of ``"hdris"``, ``"textures"``, ``"models"``.
    resolution : str
        Desired resolution, e.g. ``"1k"``, ``"2k"``, ``"4k"``.

    Returns
    -------
    dict
        Confirmation with details of what was added or an error message.
    """
    files_url = f"https://api.polyhaven.com/files/{asset_id}"
    files_data = _fetch_json(files_url)
    if isinstance(files_data, dict) and "error" in files_data:
        return files_data

    try:
        if asset_type == "hdris":
            return _import_polyhaven_hdri(asset_id, files_data, resolution)
        elif asset_type == "textures":
            return _import_polyhaven_texture(asset_id, files_data, resolution)
        elif asset_type == "models":
            return _import_polyhaven_model(asset_id, files_data, resolution)
        else:
            return {"error": f"Unknown asset_type: {asset_type}"}
    except Exception as exc:
        return {"error": f"Failed to import asset '{asset_id}': {exc}"}


def _import_polyhaven_hdri(asset_id, files_data, resolution):
    """Download an HDRI and set it as the world environment texture."""
    hdri_formats = files_data.get("hdri", {})
    # Prefer EXR, fall back to HDR
    fmt = "exr" if "exr" in hdri_formats else next(iter(hdri_formats), None)
    if fmt is None:
        return {"error": "No HDRI file formats available."}

    res_data = hdri_formats[fmt].get(resolution) or hdri_formats[fmt].get(
        next(iter(hdri_formats[fmt]))
    )
    download_url = res_data.get("url")
    if not download_url:
        return {"error": "Could not determine HDRI download URL."}

    ext = ".exr" if fmt == "exr" else ".hdr"
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, prefix=f"ph_{asset_id}_")
    tmp.close()

    if not _download_file(download_url, tmp.name, timeout=120):
        return {"error": "Failed to download HDRI file."}

    img = bpy.data.images.load(tmp.name)
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()

    bg_node = tree.nodes.new(type="ShaderNodeBackground")
    env_node = tree.nodes.new(type="ShaderNodeTexEnvironment")
    output_node = tree.nodes.new(type="ShaderNodeOutputWorld")
    env_node.image = img
    tree.links.new(env_node.outputs["Color"], bg_node.inputs["Color"])
    tree.links.new(bg_node.outputs["Background"], output_node.inputs["Surface"])

    return {
        "success": True,
        "asset_id": asset_id,
        "type": "hdri",
        "resolution": resolution,
        "message": f"HDRI '{asset_id}' set as world environment.",
    }


def _import_polyhaven_texture(asset_id, files_data, resolution):
    """Download texture maps and create a PBR material."""
    tex_section = files_data.get("Diffuse") or files_data.get("diffuse", {})
    nor_section = files_data.get("nor_gl") or files_data.get("Normal", {})
    rough_section = files_data.get("Rough") or files_data.get("rough", {})

    def _get_url(section, res):
        for fmt in ("jpg", "png", "exr"):
            entry = section.get(fmt, {}).get(res)
            if entry and "url" in entry:
                return entry["url"], fmt
        # Fall back to first available resolution / format
        for fmt in section:
            for r in section[fmt]:
                entry = section[fmt][r]
                if isinstance(entry, dict) and "url" in entry:
                    return entry["url"], fmt
        return None, None

    downloaded = {}
    for map_name, section in [("diffuse", tex_section), ("normal", nor_section), ("roughness", rough_section)]:
        url, fmt = _get_url(section, resolution)
        if url:
            ext = f".{fmt}" if fmt else ".png"
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, prefix=f"ph_{asset_id}_{map_name}_")
            tmp.close()
            if _download_file(url, tmp.name, timeout=120):
                downloaded[map_name] = tmp.name

    if not downloaded:
        return {"error": "No texture maps could be downloaded."}

    mat = bpy.data.materials.new(name=f"PH_{asset_id}")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

    if "diffuse" in downloaded:
        tex_node = nodes.new(type="ShaderNodeTexImage")
        tex_node.image = bpy.data.images.load(downloaded["diffuse"])
        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    if "roughness" in downloaded:
        rough_node = nodes.new(type="ShaderNodeTexImage")
        rough_node.image = bpy.data.images.load(downloaded["roughness"])
        rough_node.image.colorspace_settings.name = "Non-Color"
        links.new(rough_node.outputs["Color"], bsdf.inputs["Roughness"])

    if "normal" in downloaded:
        nor_img_node = nodes.new(type="ShaderNodeTexImage")
        nor_img_node.image = bpy.data.images.load(downloaded["normal"])
        nor_img_node.image.colorspace_settings.name = "Non-Color"
        nor_map_node = nodes.new(type="ShaderNodeNormalMap")
        links.new(nor_img_node.outputs["Color"], nor_map_node.inputs["Color"])
        links.new(nor_map_node.outputs["Normal"], bsdf.inputs["Normal"])

    return {
        "success": True,
        "asset_id": asset_id,
        "type": "texture",
        "resolution": resolution,
        "material_name": mat.name,
        "maps_downloaded": list(downloaded.keys()),
        "message": f"Material '{mat.name}' created with maps: {', '.join(downloaded.keys())}.",
    }


def _import_polyhaven_model(asset_id, files_data, resolution):
    """Download a GLTF model and import it into the scene."""
    gltf_data = files_data.get("gltf", {})
    res_entry = gltf_data.get(resolution) or gltf_data.get(next(iter(gltf_data), ""), {})
    download_url = None
    if isinstance(res_entry, dict):
        download_url = res_entry.get("url")
    if not download_url:
        return {"error": "Could not find a GLTF download URL for this model."}

    tmp = tempfile.NamedTemporaryFile(suffix=".glb", delete=False, prefix=f"ph_{asset_id}_")
    tmp.close()

    if not _download_file(download_url, tmp.name, timeout=180):
        return {"error": "Failed to download model file."}

    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=tmp.name)
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)

    return {
        "success": True,
        "asset_id": asset_id,
        "type": "model",
        "resolution": resolution,
        "imported_objects": new_objects,
        "message": f"Model '{asset_id}' imported. Objects: {', '.join(new_objects)}.",
    }


# ---------------------------------------------------------------------------
# Sketchfab
# ---------------------------------------------------------------------------

def get_sketchfab_status():
    """Return availability status for Sketchfab."""
    return {
        "available": True,
        "service": "Sketchfab",
        "note": "Requires SKETCHFAB_API_KEY env var",
    }


def search_sketchfab_models(query, categories=None, count=10, downloadable=True):
    """Search Sketchfab for 3D models.

    Parameters
    ----------
    query : str
        Search query string.
    categories : str or None
        Comma-separated category slugs.
    count : int
        Maximum number of results (default 10).
    downloadable : bool
        If True, only return downloadable models.

    Returns
    -------
    list[dict]
        Results with keys ``uid``, ``name``, ``description``, ``thumbnail_url``,
        ``vertex_count``, ``face_count``.
    """
    api_key = os.environ.get("SKETCHFAB_API_KEY", "")
    params = {
        "type": "models",
        "q": query,
        "downloadable": str(downloadable).lower(),
        "count": str(count),
    }
    if categories:
        params["categories"] = categories

    url = "https://api.sketchfab.com/v3/search?" + urllib.parse.urlencode(params)
    headers = {}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    result = _fetch_json(url, headers=headers)
    if isinstance(result, dict) and "error" in result:
        return result

    models = []
    for item in result.get("results", []):
        thumbnail_url = ""
        thumbs = item.get("thumbnails", {}).get("images", [])
        if thumbs:
            thumbnail_url = thumbs[0].get("url", "")

        models.append({
            "uid": item.get("uid", ""),
            "name": item.get("name", ""),
            "description": (item.get("description") or "")[:200],
            "thumbnail_url": thumbnail_url,
            "vertex_count": item.get("vertexCount", 0),
            "face_count": item.get("faceCount", 0),
        })

    return models


def download_sketchfab_model(model_uid):
    """Download and import a Sketchfab model into Blender.

    Parameters
    ----------
    model_uid : str
        The Sketchfab model UID.

    Returns
    -------
    dict
        Imported object names or an error message.
    """
    api_key = os.environ.get("SKETCHFAB_API_KEY", "")
    if not api_key:
        return {"error": "SKETCHFAB_API_KEY environment variable is not set."}

    headers = {"Authorization": f"Token {api_key}"}

    # Request download URL
    download_api_url = f"https://api.sketchfab.com/v3/models/{model_uid}/download"
    result = _fetch_json(download_api_url, headers=headers)
    if isinstance(result, dict) and "error" in result:
        return result

    # Prefer GLTF format
    gltf_info = result.get("gltf", result.get("glb"))
    if not gltf_info or "url" not in gltf_info:
        return {"error": "No downloadable GLTF/GLB format available for this model."}

    download_url = gltf_info["url"]

    tmp_dir = tempfile.mkdtemp(prefix=f"sf_{model_uid}_")
    archive_path = os.path.join(tmp_dir, "model.zip")

    if not _download_file(download_url, archive_path, timeout=180):
        return {"error": "Failed to download Sketchfab model archive."}

    # Extract archive
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(tmp_dir)
    except zipfile.BadZipFile:
        # Might be a raw GLB file instead of a zip
        os.rename(archive_path, os.path.join(tmp_dir, "model.glb"))

    # Find the GLTF/GLB file
    import_path = None
    for root, _dirs, files in os.walk(tmp_dir):
        for fname in files:
            if fname.lower().endswith((".gltf", ".glb")):
                import_path = os.path.join(root, fname)
                break
        if import_path:
            break

    if not import_path:
        return {"error": "Could not find a GLTF/GLB file in the downloaded archive."}

    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=import_path)
    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)

    return {
        "success": True,
        "model_uid": model_uid,
        "imported_objects": new_objects,
        "message": f"Sketchfab model imported. Objects: {', '.join(new_objects)}.",
    }


# ---------------------------------------------------------------------------
# Hyper3D Rodin
# ---------------------------------------------------------------------------

_RODIN_API_BASE = "https://hyperhuman.deemos.com/api/v2"


def get_hyper3d_status():
    """Return availability status for Hyper3D Rodin."""
    return {
        "available": True,
        "service": "Hyper3D Rodin",
        "note": "Requires HYPER3D_API_KEY env var",
    }


def generate_hyper3d_model_from_text(description, bbox_condition=None):
    """Submit a text-to-3D generation request to Hyper3D Rodin.

    Parameters
    ----------
    description : str
        Text description of the 3D model to generate.
    bbox_condition : dict or None
        Optional bounding-box condition for the model, e.g.
        ``{"min": [x, y, z], "max": [x, y, z]}``.

    Returns
    -------
    dict
        Contains ``job_id`` for polling, or an error message.
    """
    api_key = os.environ.get("HYPER3D_API_KEY", "")
    if not api_key:
        return {"error": "HYPER3D_API_KEY environment variable is not set."}

    url = f"{_RODIN_API_BASE}/rodin"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"prompt": description}
    if bbox_condition is not None:
        payload["bbox_condition"] = bbox_condition

    result = _fetch_json(url, headers=headers, method="POST", data=payload)
    if isinstance(result, dict) and "error" in result:
        return result

    job_id = result.get("uuid") or result.get("job_id") or result.get("task_id")
    if not job_id:
        return {"error": "No job ID returned from Hyper3D API.", "response": result}

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Generation job submitted. Poll with job_id='{job_id}'.",
    }


def poll_rodin_job_status(job_id):
    """Check the status of a Hyper3D Rodin generation job.

    Parameters
    ----------
    job_id : str
        The job identifier returned by :func:`generate_hyper3d_model_from_text`.

    Returns
    -------
    dict
        ``status`` (``"processing"``, ``"completed"``, or ``"failed"``), and
        ``download_url`` if the job is completed.
    """
    api_key = os.environ.get("HYPER3D_API_KEY", "")
    if not api_key:
        return {"error": "HYPER3D_API_KEY environment variable is not set."}

    url = f"{_RODIN_API_BASE}/status"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"uuid": job_id}

    result = _fetch_json(url, headers=headers, method="POST", data=payload)
    if isinstance(result, dict) and "error" in result:
        return result

    status = result.get("status", "unknown")
    response = {"job_id": job_id, "status": status}

    if status == "completed" or status == "done":
        response["status"] = "completed"
        download_url = result.get("download_url") or result.get("output_url")
        if download_url:
            response["download_url"] = download_url

    return response


def import_rodin_model(job_id):
    """Download a completed Hyper3D Rodin model and import it into Blender.

    Parameters
    ----------
    job_id : str
        The job identifier for a completed generation job.

    Returns
    -------
    dict
        Imported object names or an error message.
    """
    api_key = os.environ.get("HYPER3D_API_KEY", "")
    if not api_key:
        return {"error": "HYPER3D_API_KEY environment variable is not set."}

    # First check the job status to get the download URL
    status_result = poll_rodin_job_status(job_id)
    if "error" in status_result:
        return status_result
    if status_result.get("status") != "completed":
        return {
            "error": f"Job is not completed yet. Current status: {status_result.get('status')}",
        }

    download_url = status_result.get("download_url")
    if not download_url:
        return {"error": "No download URL available for the completed job."}

    tmp_dir = tempfile.mkdtemp(prefix=f"rodin_{job_id}_")
    archive_path = os.path.join(tmp_dir, "model.zip")

    if not _download_file(download_url, archive_path, timeout=180):
        return {"error": "Failed to download Rodin model."}

    # Try extracting as a zip; if it fails, treat it as a raw GLB
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(tmp_dir)
    except zipfile.BadZipFile:
        glb_path = os.path.join(tmp_dir, "model.glb")
        os.rename(archive_path, glb_path)

    # Locate a GLTF/GLB/FBX/OBJ file for import
    import_path = None
    for root, _dirs, files in os.walk(tmp_dir):
        for fname in files:
            if fname.lower().endswith((".glb", ".gltf")):
                import_path = os.path.join(root, fname)
                break
            if fname.lower().endswith((".fbx", ".obj")) and import_path is None:
                import_path = os.path.join(root, fname)
        if import_path and import_path.lower().endswith((".glb", ".gltf")):
            break

    if not import_path:
        return {"error": "Could not find a supported 3D file in the downloaded model."}

    before = set(o.name for o in bpy.data.objects)

    ext = os.path.splitext(import_path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=import_path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=import_path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=import_path)

    after = set(o.name for o in bpy.data.objects)
    new_objects = sorted(after - before)

    return {
        "success": True,
        "job_id": job_id,
        "imported_objects": new_objects,
        "message": f"Rodin model imported. Objects: {', '.join(new_objects)}.",
    }


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

HANDLERS = {
    "get_polyhaven_status": get_polyhaven_status,
    "get_polyhaven_categories": get_polyhaven_categories,
    "search_polyhaven_assets": search_polyhaven_assets,
    "download_polyhaven_asset": download_polyhaven_asset,
    "get_sketchfab_status": get_sketchfab_status,
    "search_sketchfab_models": search_sketchfab_models,
    "download_sketchfab_model": download_sketchfab_model,
    "get_hyper3d_status": get_hyper3d_status,
    "generate_hyper3d_model_from_text": generate_hyper3d_model_from_text,
    "poll_rodin_job_status": poll_rodin_job_status,
    "import_rodin_model": import_rodin_model,
}
