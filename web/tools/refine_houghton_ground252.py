"""Inspect bounded Houghton ground against the immutable campus251 native."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v251.blend"
BASE_SHA = "6fa67b6a4640411c1065f9ca5f4d660150bb9075968f8adf881267fe1a39a6e9"
OUT = ROOT / "result/blender/houghton-ground252"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        low = [min(v[i] for v in corners) for i in range(3)]
        high = [max(v[i] for v in corners) for i in range(3)]
        if (
            high[0] < -20
            or low[0] > 18
            or high[1] < -139
            or low[1] > -74
            or low[2] > 1.6
        ):
            continue
        vertices = [list(obj.matrix_world @ v.co) for v in obj.data.vertices]
        faces = [
            list(f.vertices)
            for f in obj.data.polygons
            if any(
                -20 < vertices[i][0] < 18
                and -139 < vertices[i][1] < -74
                and vertices[i][2] < 1.6
                for i in f.vertices
            )
        ]
        rows.append(
            {
                "name": obj.name,
                "bounds": [low, high],
                "owners": [c.name for c in obj.users_collection],
                "fingerprint": object_fingerprint(obj),
                "vertices": vertices,
                "faces": faces,
                "materials": [m.name if m else None for m in obj.data.materials],
            }
        )
    OUT.mkdir(exist_ok=True, parents=True)
    with gzip.open(OUT / "inventory.json.gz", "wt", encoding="utf-8") as handle:
        json.dump(
            {"baselineSha256": BASE_SHA, "objects": rows}, handle, separators=(",", ":")
        )
    print("HOUGHTON252_INVENTORY", len(rows), flush=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA


if __name__ == "__main__":
    main()
