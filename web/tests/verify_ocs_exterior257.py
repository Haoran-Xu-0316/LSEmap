"""Independently reopen OCS257 and verify three rows of bars per accepted pane.

All original objects, material graphs,35rooms and the original single-sheet
optics remain exact. Each retained box keeps its contour/UV/material and changes
only vertical position; one redundant thin box per pane is excluded.
"""

import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_ocs_exterior257 import (
    ADDED,
    BASE,
    COLLECTION,
    GLASS,
    OUT,
    SHA,
    SOURCE,
    capture,
    parts,
    protect,
    sha,
    write,
)


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == audit["baselineSha256"]
    component = ROOT / audit["componentPath"]
    assert sha(component) == audit["componentSha256"]
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in audit["sources"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    source = bpy.data.objects[SOURCE]
    glass = bpy.data.objects[GLASS]
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [ADDED]
    obj = loaded.objects[0]
    assert obj and obj.name == ADDED
    for i, name in enumerate(audit["replacementMaterialBindings"][ADDED]):
        obj.data.materials[i] = bpy.data.materials[name]
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.hide_render = False
    set_layer_hidden(obj, False)
    update_scene()
    assert object_fingerprint(obj) == audit["addedFingerprints"][ADDED]
    assert obj.matrix_world == source.matrix_world
    assert list(obj.data.materials) == list(source.data.materials)
    assert len(obj.data.vertices) == 72 and len(obj.data.polygons) == 54
    assert len(source.data.vertices) == 96 and len(parts(source.data)) == 12
    assert len(parts(obj.data)) == 9
    expected_faces = audit["sourceFaceIndices"]
    assert len(expected_faces) == 54
    old_to_new = {}
    displacements = []
    for window in audit["windows"]:
        assert len(window["bars"]) == 3
        for bar in window["bars"]:
            ids = bar["sourceVertexIndices"]
            new = bar["replacementVertexIndices"]
            assert len(ids) == len(new) == 8
            for old, i in zip(ids, new):
                assert old not in old_to_new
                old_to_new[old] = i
                old_world = source.matrix_world @ source.data.vertices[old].co
                new_world = obj.matrix_world @ obj.data.vertices[i].co
                delta = new_world - old_world
                assert abs(delta.x) < 1e-6 and abs(delta.y) < 1e-6
                assert (
                    delta
                    - source.matrix_world.to_3x3() @ Vector(bar["localTranslation"])
                ).length < 1e-6
                displacements.append(delta.z)
    assert len(old_to_new) == 72 and len(set(old_to_new.values())) == 72
    discarded = {
        i for window in audit["windows"] for i in window["discardedSourceVertexIndices"]
    }
    assert (
        len(discarded) == 24
        and discarded | set(old_to_new) == set(range(96))
        and not discarded & set(old_to_new)
    )
    for f, old_index in zip(obj.data.polygons, expected_faces):
        original = source.data.polygons[old_index]
        assert list(f.vertices) == [old_to_new[i] for i in original.vertices]
        assert (
            f.material_index == original.material_index
            and f.use_smooth == original.use_smooth
        )
        assert f.normal.dot(original.normal) > 0.999999
        for layer in source.data.uv_layers:
            new = obj.data.uv_layers[layer.name]
            for li, old_li in zip(f.loop_indices, original.loop_indices):
                assert (new.data[li].uv - layer.data[old_li].uv).length < 1e-7
    assert [u.name for u in obj.data.uv_layers] == [
        u.name for u in source.data.uv_layers
    ]
    assert (obj.data.uv_layers.active.name if obj.data.uv_layers.active else None) == (
        source.data.uv_layers.active.name if source.data.uv_layers.active else None
    )
    # Independently derive real saved bar centres and pane heights, then count.
    pane_rows = []
    for face in glass.data.polygons:
        pp = [glass.matrix_world @ glass.data.vertices[i].co for i in face.vertices]
        pane_rows.append(
            {
                "center": sum(pp, Vector()) / len(pp),
                "bottom": min(p.z for p in pp),
                "top": max(p.z for p in pp),
                "bars": [],
            }
        )
    for ids in parts(obj.data):
        pp = [obj.matrix_world @ obj.data.vertices[i].co for i in ids]
        center = sum(pp, Vector()) / len(pp)
        pane = min(pane_rows, key=lambda r: (center.xy - r["center"].xy).length)
        assert (center.xy - pane["center"].xy).length < 0.08
        pane["bars"].append(
            {
                "centerZ": center.z,
                "fraction": (center.z - pane["bottom"])
                / (pane["top"] - pane["bottom"]),
                "height": max(p.z for p in pp) - min(p.z for p in pp),
            }
        )
    for pane in pane_rows:
        bars = sorted(pane["bars"], key=lambda r: r["centerZ"])
        assert len(bars) == 3
        assert all(
            abs(r["fraction"] - fraction) < 1e-6
            for r, fraction in zip(bars, [0.25, 0.5, 0.75])
        )
        assert 0.05 < bars[1]["height"] < 0.06 and all(
            0.02 < bars[i]["height"] < 0.024 for i in [0, 2]
        )
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.free()
    assert sum(len(f.vertices) - 2 for f in source.data.polygons) == 144
    assert sum(len(f.vertices) - 2 for f in obj.data.polygons) == 108
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    after = capture()
    protect(before, after)
    assert set(after["objects"]) - set(before["objects"]) == {ADDED}
    assert object_fingerprint(glass) == before["objects"][GLASS]["fingerprint"]
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(before["objects"]),
            "protectedMaterialGraphs": len(before["materials"]),
            "protectedRoomStudies": len(before["rooms"]),
            "protectedRoomMembers": sum(len(v) for v in before["rooms"].values()),
            "sourceBars": 12,
            "replacementBars": 9,
            "sourceTriangles": 144,
            "replacementTriangles": 108,
            "triangleDelta": -36,
            "threeWindowsAtQuarterMidThreeQuarter": [
                {k: v for k, v in pane.items() if k != "center"} for pane in pane_rows
            ],
            "allRetainedBoxesOnlyTranslatedVertically": True,
            "exactRetainedUVsTopologyAndMaterials": True,
            "unchangedGlassGeometryUVsOpticsAndVisibility": True,
            "closedPositiveVolume": volume,
            "allOriginalObjectsAndMaterialGraphsProtected": True,
            "all35RoomsAndCampusMembershipsProtected": True,
            "baselineBytesUnchanged": True,
        },
    )
    print("OCS257_VERIFIED", 9, volume, flush=True)


if __name__ == "__main__":
    main()
