"""Reopen the solid MAR third deck and check actual topology, voids and bearing."""

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
from refine_col_finish252 import sha
from refine_mar_structure258 import (
    BASE,
    COLLECTION,
    OUT,
    REPLACEMENT,
    SHA,
    SOURCE,
    capture,
    check_protection,
    section_proof,
    volume_contact_proof,
    write,
)


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / record["componentPath"]
    assert sha(BASE) == SHA == record["baselineSha256"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == protected
    source = bpy.data.objects[SOURCE]
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [REPLACEMENT]
    obj = loaded.objects[0]
    assert obj.name == REPLACEMENT
    bpy.data.collections[COLLECTION].objects.link(obj)
    for index, name in enumerate(record["replacementMaterialBindings"][REPLACEMENT]):
        obj.data.materials[index] = bpy.data.materials[name] if name else None
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    assert object_fingerprint(obj) == record["addedFingerprints"][REPLACEMENT]
    section = section_proof(source, obj)
    assert section == record["sectionProof"]
    contacts = volume_contact_proof(source, obj)
    assert contacts == record["actualVolumeContactProof"]
    check_protection(protected, capture())
    assert len(bpy.data.objects) == len(protected["objects"]) + 1
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(protected["objects"]),
            "protectedOriginalMaterials": len(protected["materials"]),
            "protectedRoomStudies": len(protected["rooms"]),
            "topCornerWorldAndUVPairsExact": True,
            "allExteriorSourceObjectsUnchanged": True,
            "sectionProof": section,
            "actualVolumeContactProof": contacts,
            "knownPeripheralConcreteContacts": "See exact retained4triangle source diagnostic; not claimed zero contact.",
            "sourceGeometryAndMaterialGraphsPreserved": True,
            "actualProductionRenderRequired": True,
        },
    )
    print("MAR258_INDEPENDENT_SOLID_DECK_VERIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
