# Blender MCP Pro

Control Blender entirely from AI assistants (Claude Code, Claude Desktop, Cursor, Windsurf) via MCP.

**100+ tools across 14 categories** — Scene management, materials, shader nodes, lights, modifiers, animation, geometry nodes, camera, rendering, import/export, UV/texture, batch processing, asset integration (Poly Haven, Sketchfab), rigging, and code execution.

## Get Started

1. **Subscribe on [Gumroad](https://y1uda.gumroad.com/l/bmp)** — 7-day free trial, $5/month
2. Download the ZIP containing the MCP server and this addon
3. Follow the setup instructions below

## Requirements

- **Blender 4.0+** (5.0 recommended)
- **Python 3.10+** (for the MCP server)
- MCP-compatible client (Claude Code / Claude Desktop / Cursor / Windsurf)

## Installation

### 1. Install MCP server dependencies

```bash
cd server
pip install -r requirements.txt
```

### 2. Install the Blender addon

1. Open Blender → **Edit > Preferences > Add-ons > Install**
2. Select the `addon/` folder from the downloaded ZIP
3. Enable **"Blender MCP Pro"**
4. Open the 3D Viewport sidebar (N key) → **BM Pro** tab → **Start Server**

### 3. Configure your MCP client

Add the following to your MCP client config. Replace `<path>` with the actual path where you extracted the ZIP.

#### Claude Code (`~/.claude.json`)

```json
{
  "mcpServers": {
    "blender-mcp-pro": {
      "command": "python",
      "args": ["<path>/server/server.py"],
      "env": {
        "BLENDER_MCP_PRO_LICENSE": "YOUR-LICENSE-KEY"
      }
    }
  }
}
```

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "blender-mcp-pro": {
      "command": "python",
      "args": ["<path>/server/server.py"],
      "env": {
        "BLENDER_MCP_PRO_LICENSE": "YOUR-LICENSE-KEY"
      }
    }
  }
}
```

#### Cursor / Windsurf

Add `server/server.py` in your MCP settings with the `BLENDER_MCP_PRO_LICENSE` environment variable.

## Usage

1. Start the addon server in Blender (N panel → **BM Pro** → **Start Server**)
2. Launch your MCP client (e.g., Claude Code)
3. Control Blender with natural language!

### Examples

```
"Create a Suzanne and add SubSurf and Bevel modifiers"
"Create a glass material and apply it"
"Set up three-point lighting"
"Set the camera to 85mm lens and track the object"
"Add a rotation animation"
"Render at 1920x1080 with Cycles"
```

## Architecture

```
AI Assistant (Claude / Cursor / Windsurf)
    │
    │ MCP Protocol (stdio)
    ▼
MCP Server (server.py)
    │
    │ TCP Socket (localhost:9877)
    ▼
Blender Addon (this repo)
    │
    │ bpy API (main thread)
    ▼
Blender
```

## Tool Categories

| Category | Description |
|----------|-------------|
| Scene & Objects | Create, transform, delete objects, manage collections |
| Materials | Principled BSDF material setup |
| Shader Nodes | Full node tree control |
| Lights | Point/Sun/Spot/Area, three-point lighting |
| Modifiers | 22 modifier types (SubSurf, Bevel, Boolean, Array...) |
| Animation | Keyframes, interpolation, actions, NLA |
| Geometry Nodes | Build node networks |
| Camera | Lens, DOF, tracking, auto-framing |
| Render | Engine settings, render to file, viewport screenshot |
| Import/Export | FBX, OBJ, GLTF/GLB, USD, STL, DAE, PLY, SVG, ABC |
| UV & Texture | 7 unwrap methods, texture baking |
| Batch Processing | Multi-camera render, turntable |
| Assets | Poly Haven, Sketchfab, Hyper3D Rodin integration |
| Rigging | Armature, bones, vertex groups, constraints |

## Lazy Loading

Only 15 core tools are loaded initially. Use `list_tool_categories()` to see all categories, then `enable_tools(category)` to activate on demand.

## License

- **Blender Addon** (`addon/`) — MIT License
- **MCP Server** — Proprietary. Distributed via [Gumroad](https://y1uda.gumroad.com/l/bmp).

## Author

[@youichi-uda](https://github.com/youichi-uda)
