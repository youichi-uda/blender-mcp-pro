"""Handler for rendering and viewport screenshot operations.

Fixes ahujasid/blender-mcp Issue #189 - viewport screenshot reliability.
Uses bpy.ops.render.opengl(write_still=True) with temporary render output
path swap instead of the unreliable bpy.ops.screen.screenshot approach.
"""

import base64
import os
import tempfile

import bpy


# Max dimension (px) for base64-encoded images returned to the LLM.
_THUMBNAIL_MAX_PX = 320


def _image_to_thumbnail_base64(filepath):
    """Read *filepath*, resize to fit within _THUMBNAIL_MAX_PX, return base64 JPEG."""
    tmp_thumb = os.path.join(tempfile.gettempdir(), "bmpro_thumb.jpg")

    img = bpy.data.images.load(filepath, check_existing=False)
    try:
        w, h = img.size
        if w > _THUMBNAIL_MAX_PX or h > _THUMBNAIL_MAX_PX:
            scale = _THUMBNAIL_MAX_PX / max(w, h)
            img.scale(max(1, int(w * scale)), max(1, int(h * scale)))
        img.filepath_raw = tmp_thumb
        img.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = 50
        img.save()
    finally:
        bpy.data.images.remove(img)

    with open(tmp_thumb, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def get_viewport_screenshot(filepath=None):
    """Capture a screenshot of the active 3D viewport.

    Uses ``bpy.ops.render.opengl(write_still=True)`` which is the most
    reliable method across platforms and Blender versions.  The render
    output path is temporarily swapped so the image is written to the
    requested *filepath*, then the original path is restored.

    Args:
        filepath: Destination PNG path.  When *None* a temporary file is
            used automatically.

    Returns:
        dict with ``filepath`` and ``image_base64`` (base64-encoded PNG).
    """

    scene = bpy.context.scene
    render = scene.render

    # Determine output path
    if filepath is None:
        tmp_dir = tempfile.gettempdir()
        filepath = os.path.join(tmp_dir, "bmpro_screenshot.png")

    # Normalise to absolute path (resolves Blender '//' prefix too)
    filepath = bpy.path.abspath(filepath)

    # Ensure the directory exists
    dirpath = os.path.dirname(filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    # ---- Save current render output settings ----
    orig_filepath = render.filepath
    orig_format = render.image_settings.file_format
    orig_color_mode = render.image_settings.color_mode

    try:
        # Configure output for our screenshot
        render.filepath = filepath
        render.image_settings.file_format = "PNG"
        render.image_settings.color_mode = "RGBA"

        # Use opengl render – this captures the viewport reliably
        # (Fix for issue #189: bpy.ops.screen.screenshot is unreliable
        #  because it depends on window-manager context and may capture
        #  the wrong region or fail silently on headless setups.)
        result = bpy.ops.render.opengl(write_still=True)

        if result != {"FINISHED"}:
            return {"error": "Viewport screenshot failed. Ensure a 3D viewport is visible."}

        # Read the written file, resize, and encode to base64
        if not os.path.isfile(filepath):
            return {"error": f"Screenshot file was not created at {filepath}"}

        image_base64 = _image_to_thumbnail_base64(filepath)

        return {
            "filepath": filepath,
            "image_base64": image_base64,
        }
    finally:
        # ---- Restore original settings ----
        render.filepath = orig_filepath
        render.image_settings.file_format = orig_format
        render.image_settings.color_mode = orig_color_mode


def set_render_engine(engine):
    """Set the render engine.

    Args:
        engine: One of ``CYCLES``, ``BLENDER_EEVEE_NEXT`` (4.x),
            ``BLENDER_EEVEE`` (3.x), or ``BLENDER_WORKBENCH``.
            For EEVEE the function tries ``BLENDER_EEVEE_NEXT`` first and
            falls back to ``BLENDER_EEVEE`` for compatibility.

    Returns:
        dict with the active ``engine`` name.
    """

    scene = bpy.context.scene
    engine = engine.upper()

    # Normalise common aliases
    if engine in ("EEVEE", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        # Try 4.x name first
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE"
    else:
        try:
            scene.render.engine = engine
        except TypeError:
            return {"error": f"Unknown render engine: {engine}"}

    return {"engine": scene.render.engine}


def render_image(output_path, resolution_x=1920, resolution_y=1080,
                 samples=128, engine=None):
    """Render the current scene to an image file.

    Args:
        output_path: Destination file path.  The format is derived from
            the file extension (``.png``, ``.jpg``, ``.exr``, etc.).
        resolution_x: Horizontal resolution in pixels.
        resolution_y: Vertical resolution in pixels.
        samples: Number of render samples.
        engine: Optional render engine to use (see :func:`set_render_engine`).

    Returns:
        dict with ``filepath``, ``resolution``, ``engine``, ``samples``,
        and ``image_base64``.
    """

    scene = bpy.context.scene
    render = scene.render

    # Engine ---
    if engine is not None:
        engine_result = set_render_engine(engine)
        if "error" in engine_result:
            return engine_result

    # Resolution ---
    render.resolution_x = int(resolution_x)
    render.resolution_y = int(resolution_y)
    render.resolution_percentage = 100

    # Samples ---
    current_engine = render.engine
    if current_engine == "CYCLES":
        scene.cycles.samples = int(samples)
    elif current_engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = int(samples)
        elif hasattr(scene.eevee, "samples"):
            scene.eevee.samples = int(samples)

    # Output path & format ---
    output_path = bpy.path.abspath(output_path)
    dirpath = os.path.dirname(output_path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)

    ext_format_map = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".bmp": "BMP",
        ".tif": "TIFF",
        ".tiff": "TIFF",
        ".exr": "OPEN_EXR",
        ".hdr": "HDR",
    }
    ext = os.path.splitext(output_path)[1].lower()
    file_format = ext_format_map.get(ext, "PNG")

    render.filepath = output_path
    render.image_settings.file_format = file_format

    # Render ---
    result = bpy.ops.render.render(write_still=True)
    if result != {"FINISHED"}:
        return {"error": "Render did not complete successfully."}

    # Base64 encode a thumbnail of the result ---
    image_base64 = ""
    if os.path.isfile(output_path):
        image_base64 = _image_to_thumbnail_base64(output_path)

    return {
        "filepath": output_path,
        "resolution": [render.resolution_x, render.resolution_y],
        "engine": current_engine,
        "samples": int(samples),
        "image_base64": image_base64,
    }


def set_render_output(format="PNG", path=None, color_depth=None,
                      compression=None, quality=None):
    """Configure render output settings.

    Args:
        format: Image format – ``PNG``, ``JPEG``, ``BMP``, ``TIFF``,
            ``OPEN_EXR``, ``HDR``.
        path: Optional output directory / file path.
        color_depth: Bits per channel (``8``, ``16``, ``32`` – availability
            depends on format).
        compression: PNG compression percentage (0-100).
        quality: JPEG quality percentage (0-100).

    Returns:
        dict describing the current output settings.
    """

    scene = bpy.context.scene
    render = scene.render
    img = render.image_settings

    img.file_format = format.upper()

    if path is not None:
        render.filepath = path

    if color_depth is not None:
        img.color_depth = str(color_depth)

    if compression is not None and hasattr(img, "compression"):
        img.compression = int(compression)

    if quality is not None and hasattr(img, "quality"):
        img.quality = int(quality)

    return {
        "file_format": img.file_format,
        "filepath": render.filepath,
        "color_depth": img.color_depth,
        "color_mode": img.color_mode,
    }


def set_render_settings(samples=None, use_denoising=None, denoiser=None,
                        film_transparent=None, use_motion_blur=None,
                        use_bloom=None, use_ambient_occlusion=None):
    """Set various render settings for the active scene.

    Handles both Cycles and EEVEE engine-specific properties gracefully.

    Returns:
        dict summarising the updated settings.
    """

    scene = bpy.context.scene
    render = scene.render
    engine = render.engine

    # --- Samples ---
    if samples is not None:
        samples = int(samples)
        if engine == "CYCLES":
            scene.cycles.samples = samples
        elif engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            if hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = samples
            elif hasattr(scene.eevee, "samples"):
                scene.eevee.samples = samples

    # --- Denoising ---
    if use_denoising is not None:
        if engine == "CYCLES":
            scene.cycles.use_denoising = bool(use_denoising)
        elif hasattr(render, "use_eevee_denoising"):
            render.use_eevee_denoising = bool(use_denoising)

    if denoiser is not None and engine == "CYCLES":
        if hasattr(scene.cycles, "denoiser"):
            scene.cycles.denoiser = denoiser.upper()

    # --- Film transparent ---
    if film_transparent is not None:
        render.film_transparent = bool(film_transparent)

    # --- Motion blur ---
    if use_motion_blur is not None:
        if engine == "CYCLES":
            render.use_motion_blur = bool(use_motion_blur)
        elif hasattr(scene.eevee, "use_motion_blur"):
            scene.eevee.use_motion_blur = bool(use_motion_blur)

    # --- Bloom (EEVEE only) ---
    if use_bloom is not None:
        if hasattr(scene.eevee, "use_bloom"):
            scene.eevee.use_bloom = bool(use_bloom)

    # --- Ambient Occlusion (EEVEE) ---
    if use_ambient_occlusion is not None:
        if hasattr(scene.eevee, "use_gtao"):
            scene.eevee.use_gtao = bool(use_ambient_occlusion)

    # --- Build response ---
    result = {"engine": engine}

    if engine == "CYCLES":
        result["samples"] = scene.cycles.samples
        result["use_denoising"] = scene.cycles.use_denoising
        if hasattr(scene.cycles, "denoiser"):
            result["denoiser"] = scene.cycles.denoiser
    elif engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if hasattr(scene.eevee, "taa_render_samples"):
            result["samples"] = scene.eevee.taa_render_samples
        elif hasattr(scene.eevee, "samples"):
            result["samples"] = scene.eevee.samples
        if hasattr(scene.eevee, "use_bloom"):
            result["use_bloom"] = scene.eevee.use_bloom
        if hasattr(scene.eevee, "use_gtao"):
            result["use_ambient_occlusion"] = scene.eevee.use_gtao

    result["film_transparent"] = render.film_transparent
    result["use_motion_blur"] = getattr(render, "use_motion_blur", False)

    return result


HANDLERS = {
    "get_viewport_screenshot": get_viewport_screenshot,
    "set_render_engine": set_render_engine,
    "render_image": render_image,
    "set_render_output": set_render_output,
    "set_render_settings": set_render_settings,
}
