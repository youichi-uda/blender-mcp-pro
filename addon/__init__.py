bl_info = {
    "name": "Blender MCP Pro",
    "author": "BlenderMCPPro",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > BM Pro",
    "description": "Professional MCP server for controlling Blender from AI assistants",
    "category": "Interface",
}

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


classes = (
    BMPRO_PT_MainPanel,
    BMPRO_OT_StartServer,
    BMPRO_OT_StopServer,
    server.BMPRO_OT_ModalServer,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    server.stop()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
