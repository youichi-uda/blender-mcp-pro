# Blender MCP Pro — Addon

Blender addon that provides a TCP bridge server for [Blender MCP Pro](https://github.com/youichi-uda/blender-mcp-pro-private) MCP server.

## Features

This addon exposes Blender's full API over a local TCP socket, enabling AI assistants (Claude, Cursor, Windsurf) to control Blender through the MCP protocol.

**110+ operations across 16 categories:**

- **Scene & Objects** — Create, modify, delete, transform, collections
- **Materials** — Principled BSDF, node duplication bug fix
- **Shader Nodes** — Full node tree control, custom materials
- **Lights** — Point/Sun/Spot/Area, three-point lighting
- **Modifiers** — 22 modifier types (Subsurf, Bevel, Boolean, Array...)
- **Animation** — Keyframes, interpolation, actions, NLA
- **Geometry Nodes** — Build node networks, connect, parameterize
- **Camera** — Lens, DOF, tracking, auto-framing
- **Render** — Engine settings, render to file, viewport screenshot
- **Import/Export** — FBX, OBJ, GLTF/GLB, USD, STL, DAE, PLY, SVG, ABC
- **UV & Texture** — 7 unwrap methods, texture baking
- **Batch Processing** — Multi-camera render, turntable, batch I/O
- **Assets** — Poly Haven, Sketchfab, Hyper3D Rodin
- **Rigging** — Armature, bones, vertex groups, constraints
- **Code Execution** — Run arbitrary Python in Blender context

## Installation

1. Download this repository as ZIP (or clone it)
2. In Blender: **Edit > Preferences > Add-ons > Install**
3. Select the `addon/` folder (or the ZIP file)
4. Enable **"Blender MCP Pro"** in the addon list
5. Open the **N panel** (sidebar) in 3D Viewport > **BM Pro** tab
6. Click **Start Server**

The addon listens on `localhost:9877`.

## Usage with MCP Server

This addon is the Blender-side component. You also need the **Blender MCP Pro MCP Server** to connect your AI assistant:

Get the MCP server: [Blender MCP Pro](https://buymeacoffee.com/youichi_uda) — $5/month with 7-day free trial.

### MCP Client Configuration

Add to your MCP client config (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "blender-mcp-pro": {
      "command": "python",
      "args": ["/path/to/blender-mcp-pro-private/server.py"]
    }
  }
}
```

## Architecture

```
AI Assistant (Claude/Cursor/Windsurf)
    |
    | MCP Protocol (stdio)
    v
MCP Server (server.py) — private/paid
    |
    | TCP Socket (localhost:9877)
    v
Blender Addon (this repo)
    |
    | bpy API (main thread via Modal Operator)
    v
Blender
```

The addon uses a **Modal Operator + command queue** pattern to ensure all `bpy` calls happen on the main thread, avoiding Blender's thread-safety restrictions.

## License

MIT License

## Author

[@youichi-uda](https://github.com/youichi-uda)
