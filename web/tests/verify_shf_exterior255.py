"""Independently reopen SHF255 and verify blind wall, retained windows and scope."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_shf_exterior255 import (
    BASE,
    COLLECTION,
    OUT,
    SHA,
    capture,
    check_protection,
    face_record,
    probes,
    sha,
    write,
)


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    assert capture() == protected
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = record["addedObjects"]
    for obj in loaded.objects:
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == record["addedFingerprints"][obj.name], (
            obj.name
        )
        bpy.data.collections[COLLECTION].objects.link(obj)
    # Append may create suffixed copies of accepted source materials. All
    # replacement slots already use explicit canonical bindings; remove only
    # those newly introduced, unused datablocks, never any original graph.
    for material in list(bpy.data.materials):
        if material.name not in protected["materials"] and material.users == 0:
            bpy.data.materials.remove(material)
    for name in record["archivedObjects"]:
        obj = bpy.data.objects[name]
        obj.hide_render = True
        set_layer_hidden(obj, True)
    update_scene()
    for row in record["retainedGeometry"]:
        obj = bpy.data.objects["SHF255_" + row["source"]]
        assert [face_record(obj, p) for p in obj.data.polygons] == row[
            "retainedFaceRecords"
        ], obj.name
    rows = probes(bpy.data.collections[COLLECTION].all_objects)
    assert rows == record["afterBlindWallProbes"]
    assert len(rows) == 18
    check_protection(protected, capture(), record["archivedObjects"])
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "savedComponentReopened": True,
            "originalObjectsProtected": len(protected["objects"]),
            "originalMaterialGraphsProtected": len(protected["materials"]),
            "roomStudiesProtected": len(protected["rooms"]),
            "retainedOtherFacesNormalsAndUVs": True,
            "formerApertureProbes": rows,
            "falseWindowCountRemoved": 2,
            "visualReviewRequired": "Production frontal and oblique view must show blank right bay without remaining glass, sill or window rails",
        },
    )
    print("SHF255_REOPEN_VERIFIED", len(rows), flush=True)


if __name__ == "__main__":
    main()
