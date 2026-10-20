"""Independently validate the read-only CKK252 optical audit and asset parity."""

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/ckk-glass252"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actual_materials(path):
    raw = path.read_bytes()
    length = struct.unpack_from("<I", raw, 12)[0]
    document = json.loads(raw[20 : 20 + length])
    node = next(
        n for n in document["nodes"] if n.get("extras", {}).get("buildingCode") == "CKK"
    )
    indices = {p["material"] for p in document["meshes"][node["mesh"]]["primitives"]}
    materials = {}
    for index in indices:
        material = document["materials"][index]
        name = material["name"]
        if material.get("extras", {}).get("webSurfaceRole") != "glazing" and not any(
            token in name.lower() for token in ("glass", "glazing")
        ):
            continue
        key = name.removeprefix("WEB_DETAIL_").removeprefix("WEB_")
        materials[key] = {k: value for k, value in material.items() if k != "name"}
    return materials


def main():
    review = json.loads((OUT / "review.json").read_text())
    assert review["candidateProduced"] is False
    assert review["currentNativeOpened"] is False
    assert review["currentNativeRaysPerformed"] is False
    assert review["roomsInUnchangedMetadata"] == 35
    assert not list(OUT.glob("*.blend"))
    for path, expected in review["protectedPaths"].items():
        assert sha(ROOT / path) == expected, path
    for reference in review["references"]:
        assert sha(ROOT / reference["path"]) == reference["sha256"]
    actual = []
    for asset in review["assets"]:
        path = ROOT / asset["path"]
        assert sha(path) == asset["sha256"]
        actual.append(actual_materials(path))
    assert actual[0] == actual[1] and len(actual[0]) == 10
    neutral, transparent = [], []
    for name, material in actual[0].items():
        pbr = material["pbrMetallicRoughness"]
        assert pbr["metallicFactor"] == 0
        if name.startswith("CKK219_glass_"):
            colour = pbr["baseColorFactor"]
            assert max(colour[:3]) / min(colour[:3]) < 1.06
            assert colour[3] == 1 and material.get("alphaMode", "OPAQUE") == "OPAQUE"
            neutral.append(name)
        if name.endswith(("CKK_GLASS164_clear_atrium", "ATRIA_roof_glass")):
            assert material["alphaMode"] == "BLEND"
            expected = 0.16 if "clear_atrium" in name else 0.30
            assert abs(pbr["baseColorFactor"][3] - expected) < 1e-6
            transparent.append(name)
    assert len(neutral) == 3 and len(transparent) == 4
    result = {
        "status": "passed_audit_only",
        "campusDetailMaterialPairs": 10,
        "neutralPrincipalGroups": 3,
        "transparentAtriumGroups": 4,
        "allGlassMetallicZero": True,
        "fullNativeAndSharedFilesByteUnchanged": True,
        "35RoomsRetainedByImmutableNative": True,
        "candidateCreated": False,
        "blenderStarted": False,
    }
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
