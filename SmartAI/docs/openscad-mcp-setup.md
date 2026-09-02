# OpenSCAD MCP setup (3D modeling in Cursor)

Enables AI-assisted validate / preview / STL export for `assets/models/*.scad`.

## Recommended MCP: [petrijr/openscad-mcp](https://github.com/petrijr/openscad-mcp)

| Why | Detail |
|-----|--------|
| Stable v1.0 tool surface | `validate_scad`, `export_model`, `render_preview`, `batch_render_scad` |
| Local-first | stdio transport, workspace-locked |
| Docker option | Headless PNG/STL without local GUI |

**Alternatives:** [quellant/openscad-mcp](https://github.com/quellant/openscad-mcp) (multi-view compare), [ClemensSchartmueller/openscad-mcp-server](https://github.com/ClemensSchartmueller/openscad-mcp-server) (customizer parse).

## 1. Install OpenSCAD

```powershell
winget install --id OpenSCAD.OpenSCAD -e
```

Verify: `openscad --version`

## 2. Install MCP server

```powershell
cd $env:USERPROFILE\Tools
git clone https://github.com/petrijr/openscad-mcp.git
cd openscad-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 3. Cursor MCP config

Project config: `SmartAI/.cursor/mcp.json` (already scaffolded).

Or add to **Cursor Settings → MCP** globally:

```json
{
  "mcpServers": {
    "openscad": {
      "command": "C:\\Users\\user\\Tools\\openscad-mcp\\.venv\\Scripts\\openscad-mcp.exe",
      "env": {
        "OPENSCAD_MCP_MODULE_ROOT": "C:\\Users\\user\\Documents\\brightnessControl\\PythonTools\\SmartAI\\assets\\models",
        "OPENSCAD_MCP_KEEP_ARTIFACTS": "true",
        "OPENSCAD_MCP_ARTIFACT_ROOT": "C:\\Users\\user\\Documents\\brightnessControl\\PythonTools\\SmartAI\\assets\\models\\exports"
      }
    }
  }
}
```

Adjust clone path if different. Restart Cursor after saving.

## 4. Module registry (optional)

Create `assets/models/index.json`:

```json
{
  "modules": [
    { "id": "variant_a", "description": "Compact home chassis", "entry": "variant_a" },
    { "id": "variant_b", "description": "Tall navigator", "entry": "variant_b" },
    { "id": "variant_c", "description": "Wide stable", "entry": "variant_c" }
  ]
}
```

## 5. Example agent prompts

- "Validate `variant-a-compact-home.scad`"
- "Export variant B to STL at 0.2mm resolution"
- "Render isometric PNG preview of variant C"
- "Batch export all three variants with `$fn=64`"

## 6. Security

- MCP runs locally over stdio only.
- Keep `OPENSCAD_MCP_MODULE_ROOT` scoped to `assets/models/`.
- Do not point at repo root (OpenSCAD `use` can pull arbitrary files).

## 7. No Blender MCP?

No mature Blender MCP in this workspace yet. Use:

- **OpenSCAD MCP** — parametric CAD (this project)
- **Blender bpy script** — `assets/models/generate_variants.py` (if present after BoN merge)
- **Manual** — OpenSCAD → STL → Blender import
