bl_info = {
    "name": "Blender MCP Pro",
    "author": "BlenderMCPPro",
    "version": (1, 3, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > BM Pro",
    "description": "Professional MCP server for controlling Blender from AI assistants",
    "category": "Interface",
}

import time

import bpy
from . import server


class BMPRO_PT_MainPanel(bpy.types.Panel):
    bl_label = "Blender MCP Pro"
    bl_idname = "BMPRO_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BM Pro"

    def draw(self, context):
        layout = self.layout
        state = server.get_server_state()

        if state["running"]:
            layout.label(text=f"Server running on port {state['port']}", icon="CHECKMARK")
            layout.operator("bmpro.stop_server", text="Stop Server", icon="CANCEL")
        else:
            layout.operator("bmpro.start_server", text="Start Server", icon="PLAY")

        if state["last_error"]:
            box = layout.box()
            box.label(text="Last Error:", icon="ERROR")
            box.label(text=state["last_error"])


class BMPRO_PT_StatsPanel(bpy.types.Panel):
    bl_label = "Session Stats"
    bl_idname = "BMPRO_PT_stats"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BM Pro"
    bl_parent_id = "BMPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return server.get_server_state()["running"]

    def draw(self, context):
        layout = self.layout
        state = server.get_server_state()
        stats = state["stats"]

        row = layout.row()
        row.label(text=f"Total: {stats['total']}")
        row.label(text=f"OK: {stats['ok']}")
        row.label(text=f"Err: {stats['error']}")

        if stats["start_time"] > 0:
            elapsed = time.time() - stats["start_time"]
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            layout.label(text=f"Uptime: {mins}m {secs}s")


class BMPRO_PT_LogPanel(bpy.types.Panel):
    bl_label = "Activity Log"
    bl_idname = "BMPRO_PT_log"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BM Pro"
    bl_parent_id = "BMPRO_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return server.get_server_state()["running"]

    def draw(self, context):
        layout = self.layout
        state = server.get_server_state()
        log = state["activity_log"]

        if not log:
            layout.label(text="No commands yet", icon="INFO")
            return

        layout.operator("bmpro.clear_log", text="Clear Log", icon="TRASH")

        # Show most recent entries first (last 20 to avoid UI overflow)
        for entry in reversed(log[-20:]):
            icon = "CHECKMARK" if entry["status"] == "ok" else "ERROR"
            row = layout.row()
            row.label(text=f"{entry['time']}", icon=icon)
            row.label(text=entry["command"])
            row.label(text=f"{entry['duration_ms']}ms")


class BMPRO_OT_StartServer(bpy.types.Operator):
    bl_idname = "bmpro.start_server"
    bl_label = "Start BM Pro Server"
    bl_description = "Start the MCP Pro TCP server"

    def execute(self, context):
        server.start(context)
        return {"FINISHED"}


class BMPRO_OT_StopServer(bpy.types.Operator):
    bl_idname = "bmpro.stop_server"
    bl_label = "Stop BM Pro Server"
    bl_description = "Stop the MCP Pro TCP server"

    def execute(self, context):
        server.stop()
        return {"FINISHED"}


class BMPRO_OT_ClearLog(bpy.types.Operator):
    bl_idname = "bmpro.clear_log"
    bl_label = "Clear Activity Log"
    bl_description = "Clear the command activity log"

    def execute(self, context):
        server._activity_log.clear()
        return {"FINISHED"}


classes = (
    BMPRO_PT_MainPanel,
    BMPRO_PT_StatsPanel,
    BMPRO_PT_LogPanel,
    BMPRO_OT_StartServer,
    BMPRO_OT_StopServer,
    BMPRO_OT_ClearLog,
    server.BMPRO_OT_ModalServer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    server.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
