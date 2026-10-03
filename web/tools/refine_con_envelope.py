"""Evidence-gated read-only review of Connaught House's entire envelope.
No component is fabricated while the upper facade has no registered photograph.
Run inside Blender. Constant paths only; never saves the whole campus.
"""

from pathlib import Path
import array, hashlib, json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v139.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, width in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * width)
            data.foreach_get(field, values)
            h.update(values.tobytes())
        for layer in o.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            h.update(values.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
photo = (
    ROOT / "data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg"
)
inventory = json.loads((OUT / "native-inventory.json").read_text())
glass = next(
    r for r in inventory if r["name"] == "CON_NEXT_PORTAL_WINDOW_recessed_glass"
)
audit = {
    "status": "upper-envelope-registration-blocked-no-component",
    "baseline": str(BASE.relative_to(ROOT)),
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "building": "CON Connaught House",
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": [],
    "archivedObjects": [],
    "changes": [],
    "reference": {
        "path": str(photo.relative_to(ROOT)),
        "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "sourceUrl": "https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate",
        "captureDate": "unknown",
        "resolution": [300, 400],
        "coverage": "Entrance, compact window directly above, portions of two adjacent lower windows. No roof, upper window rows or full street frontage.",
    },
    "nativeRegistration": {
        "origin": [-16.17835807800293, -130.22201538085938, 0],
        "right": [-0.9859890937805176, -0.16680996119976044, 0],
        "outward": [0.16680996119976044, -0.9859890937805176, 0],
        "streetFacadeWidthEstimate": 16.07383,
        "mainWindowColumnCenters": [-6.429532, -3.214765, 0, 3.214765, 6.429532],
        "ordinaryUpperWindowRowCenters": [
            6.775,
            10.675,
            14.675,
            18.675,
            22.675,
            26.625,
        ],
        "highestGlassEdge": 27.81,
        "roofHeight": 29,
        "parapetCopingTop": 29.36,
        "registrationStatus": "Inherited model and GIS estimates, not independently proven by photographs.",
        "glassParts": glass["parts"],
    },
    "wholeEnvelopeAssessment": {
        "windowRowsColumns": "Current five-column repeated upper facade cannot be certified or corrected from entrance-only imagery.",
        "setbacksAndRoof": "No archived full-height CON photograph registers roof position, cornice setbacks or storey count.",
        "stone": "Lower granite/upper limestone partition already corrected and supported by entrance photograph; no new material discrepancy established.",
        "glass": "Lower photograph shows strong street reflections; does not justify making all upper windows transparent without known interior boundaries. Existing glass retained.",
        "alreadyCorrected": "Compact above-portal window and recessed vestibule preserved; no redundant entrance edits.",
    },
    "supplementarySourceReview": [
        {
            "url": "https://prewett-bizley.squarespace.com/-lse-index",
            "stage": "2010 feasibility study",
            "observation": "Architect describes nine-storey Connaught and Columbia entrances, with proposed lobby linings. Text and proposal images do not establish a built full-height CON elevation, roof profile, or whether storey count includes lower-ground levels.",
            "usableForEnvelopeModification": False,
        },
        {
            "url": "https://commons.wikimedia.org/wiki/File:L.S.E._front_to_Aldwych,_2009_-_geograph.org.uk_-_6715110.jpg",
            "photoDate": "2009-03-14",
            "observation": "Viewed image shows a long classical frontage with paired giant columns and balcony. No CON entrance anchor identifies the current16m Connaught face; building identification unproven. Excluded from modelling rather than treating generic LSE caption as CON attribution.",
            "usableForEnvelopeModification": False,
        },
    ],
    "missingEvidence": [
        "Near-frontal photograph containing identifiable Connaught portal plus all five assumed upper bay positions and roof edge.",
        "At least one full-height oblique photograph to register parapet/upper setback and adjoining building boundary.",
    ],
    "nextExecutableAction": "Register one identified whole-height CON street photo to portal origin and bay rhythm before any upper-row, roof or stone-color correction. No geometry proposal is safe until that correspondence exists.",
    "fullModelSaved": False,
    "componentWritten": False,
}
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
)
proof = {
    "baselineSha256": audit["baselineSha256"],
    "nativeReadCompleted": True,
    "originalObjectCount": len(originals),
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "componentWritten": False,
    "savedComponentReopened": False,
    "geometryCorrectionClaimed": False,
    "fullModelSaved": False,
    "noRenderStarted": True,
    "blenderExitRequested": True,
}
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("CON_ENVELOPE_READONLY_VERIFIED", len(originals))
bpy.ops.wm.quit_blender()
