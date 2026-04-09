# Blender MCP Pro

Control Blender entirely from AI assistants (Claude Code, Claude Desktop, Cursor, Windsurf) via MCP.

**120+ tools across 17 categories** — Scene management, materials, shader nodes, lights, modifiers, animation, geometry nodes (with scatter/array templates), camera, rendering, import/export, UV/texture, batch processing, asset integration (Poly Haven, Sketchfab), rigging, rig diagnostics, scene utilities, workflow presets, and code execution.

## Pricing

| | Subscription | One-Time Purchase |
|---|---|---|
| **Price** | $5/month (7-day free trial) | $15 |
| **Platform** | [Gumroad](https://y1uda.gumroad.com/l/bmp) | [itch.io](https://y1uda.itch.io/blender-mcp-pro) |
| **Updates** | Included while subscribed | Lifetime updates |

## Get Started

1. **Purchase on [itch.io](https://y1uda.itch.io/blender-mcp-pro)** ($15 one-time) or **subscribe on [Gumroad](https://y1uda.gumroad.com/l/bmp)** ($5/month with 7-day free trial)
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

## Updating

When a new version is released:

1. Download the latest ZIP from your Gumroad library or itch.io
2. Extract and overwrite the existing `server/` folder
3. In Blender: **Edit > Preferences > Add-ons** → remove the old "Blender MCP Pro"
4. Install the new `addon/` folder and enable it
5. Restart Blender

Your MCP client config and license key do not need to change.

## Usage

1. Start the addon server in Blender (N panel → **BM Pro** → **Start Server**)
2. Launch your MCP client (e.g., Claude Code)
3. Control Blender with natural language!

### Streamable HTTP Transport (optional)

By default, the MCP server uses stdio transport. For remote connections or web-based clients, you can use Streamable HTTP:

```bash
python server/server.py --transport streamable-http --port 8000
```

Then configure your MCP client to connect to `http://127.0.0.1:8000/mcp/`.

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
| Geometry Nodes | Build node networks, scatter setup, array along curve |
| Camera | Lens, DOF, tracking, auto-framing |
| Render | Engine settings, render to file, viewport screenshot |
| Import/Export | FBX, OBJ, GLTF/GLB, USD, STL, DAE, PLY, SVG, ABC |
| UV & Texture | 7 unwrap methods, texture baking |
| Batch Processing | Multi-camera render, turntable |
| Assets | Poly Haven, Sketchfab integration |
| Rigging | Armature, bones, vertex groups, constraints |
| Rig Diagnostics | Rig health check, bone naming fix, weight normalization, bone mirroring |
| Scene Utilities | Scene cleanup, batch rename, apply transforms, mesh analysis |
| Workflows | One-command PBR material, studio render setup, export preparation |

## Lazy Loading

Only 15 core tools are loaded initially. Use `list_tool_categories()` to see all categories, then `enable_tools(category)` to activate on demand.

## License

- **Blender Addon** (`addon/`) — MIT License
- **MCP Server** — Proprietary. Distributed via [Gumroad](https://y1uda.gumroad.com/l/bmp) and [itch.io](https://y1uda.itch.io/blender-mcp-pro).

## Author

[@youichi-uda](https://github.com/youichi-uda)
