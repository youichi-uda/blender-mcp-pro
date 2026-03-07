"""Auto-start script for Blender MCP Pro server.
Usage: blender --python /path/to/startup_server.py
"""
import bpy

def _delayed_start():
    """Start server after Blender is fully initialized."""
    bpy.ops.preferences.addon_enable(module="blender_mcp_pro")
    bpy.ops.bmpro.start_server()
    print("BM Pro: Server started on port 9877")
    return None  # Don't repeat

bpy.app.timers.register(_delayed_start, first_interval=2.0)
print("BM Pro: Server will auto-start in 2 seconds...")
