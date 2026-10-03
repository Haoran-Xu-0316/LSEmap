"""Audit the complete retained Houghton frontage against archived built evidence.

Run in Blender's Text Editor. No geometry is constructed until the external
approach is registered to its actual local street datum and route plan.
"""

from pathlib import Path
import array, hashlib, json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old_houghton_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v137.blend"
EXPECTED = "868b9ef1f8d4d2b0680752a90e96a80a575ffb0c1b54b0013cd2995c51cc7d7f"
PRIOR_AUDIT = None
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
else:
    # Retired full-campus versions are not retained. This evidence can be reused
    # only while the OLD object inventory, geometry and display states match.
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda path: int(path.stem.rsplit("v", 1)[1]),
    )
    EXPECTED = hashlib.sha256(BASE.read_bytes()).hexdigest()
    PRIOR_AUDIT = json.loads((OUT / "audit.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]


def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, width in (
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ):
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


originals = {o.name: fingerprint(o) for o in bpy.data.objects}
states = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
if PRIOR_AUDIT:
    prior_names = {
        name for name in PRIOR_AUDIT["originalFingerprints"] if name.startswith("OLD_")
    }
    current_names = {name for name in originals if name.startswith("OLD_")}
    assert (
        current_names == prior_names
    ), "OLD inventory changed; re-register frontage evidence"
    assert all(
        originals[name] == PRIOR_AUDIT["originalFingerprints"][name]
        and states[name] == PRIOR_AUDIT["originalVisibility"][name]
        for name in prior_names
    ), "OLD geometry or visibility changed; re-register frontage evidence"
frame = json.loads(
    (ROOT / "result/blender/stage52/old-houghton-audit.json").read_text()
)
origin, right, normal = [Vector(frame[k]) for k in ["origin", "right", "outward"]]
refs = []
for filename, coverage, date, url in [
    (
        "data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg",
        "Unobstructed built Houghton portal, blue window hierarchy, approach treads and right raised route/rail; far right route termination outside frame.",
        "Capture date unknown",
        "https://webbyates.com/projects/the-old-building/",
    ),
    (
        "data/collections/old-user-reference/houghton-user-entrance-20261002.png",
        "User entrance oblique view, arch masonry and tread edges; text hides middle/lower doorway and right route endpoint.",
        "Capture date unknown; received2026-10-02",
        None,
    ),
    (
        "data/collections/public-realm-2026/user-references/reference-09.png",
        "Oblique long street view of OLD raised route and silver rail; uncalibrated perspective and incomplete endpoints.",
        "Capture date unknown",
        None,
    ),
    (
        "data/collections/old-roof-2024/existing-south.pdf",
        "Full existing/strip-out Houghton south elevation; floor datums, whole frontage, ground-level outline. No curb plan or exterior route section.",
        "Drawing title block2022-12-07; not a2024 measured access survey",
        "https://idoxpa.westminster.gov.uk/online-applications/files/97633D2FC04D7E918333D7F9B365101F/pdf/22_08664_FULL-EXISTING___STRIP_OUT_SOUTH_ELEVATION-7612991.pdf",
    ),
]:
    p = ROOT / filename
    refs.append(
        {
            "file": filename,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "coverage": coverage,
            "date": date,
            "url": url,
        }
    )
audit = {
    "status": "whole-frontage audit; no safely registered new component",
    "baseline": str(BASE),
    "baselineSha256": EXPECTED,
    "originalFingerprints": originals,
    "originalVisibility": states,
    "ownedObjects": [],
    "archivedObjects": [],
    "changes": [],
    "componentSaved": False,
    "fullModelSaved": False,
    "sourceReferences": refs,
    "oneNewPrimaryLookup": {
        "url": "https://www.accessable.co.uk/london-school-of-economics/access-guides/old-building",
        "outcome": "403 on direct read; search summary confirms slight ramp/platform lift only, not dimensional registration.",
        "relatedResult": "https://www.accessable.co.uk/london-school-of-economics/access-guides/fourth-floor-restaurant",
        "observation": "Search summary mentions4 entrance stairs; detailed entrance chapter not personally read, so not treated as standalone measured validation.",
        "checked": "2026-10-04",
    },
    "registration": {
        "origin": list(origin),
        "right": list(right),
        "outward": list(normal),
        "frontageRange": [-34.5, 22.48],
        "nativeLandingHeight": 1.245,
        "nativeLandingBounds": {"x": [-30.39774, -22.39774], "outward": [-0.7, 1.25]},
        "nativeStair": "OLD_V116_chamfered_fan_stair",
        "nativeStairCount": 6,
        "nativeStairCountVerified": False,
        "stairCountStatus": "Six risers are retained geometry, not a photo-verified or surveyed count.",
        "nativeRiserHeight": 0.2075,
        "nativeEntranceRailOwners": [
            "OLD_V112_entry_D5_entry65_frame",
            "OLD_V112_entry_D5_entry65_steel",
        ],
        "nativeEntranceRailAlongStreetBounds": [-31.30362, -25.74306],
    },
    "wholeFrontageAssessment": [
        {
            "part": "Massing and window tiers",
            "finding": "Houghton main blocks and distinct entrance pavilion already registered through112 against the full planning elevation. The visible blue tiers, roof dormer split and stone-zone hierarchy have accepted subsequent corrections; no new evidence supports rescaling the full front.",
        },
        {
            "part": "Arch, crest and artwork",
            "finding": "Radial stone arch, crest, portal overlap clearance and multi-figure lattice artwork already present. Artwork remains a photo-guided approximation; no new source gives sculpture depth or supports replacing it with guessed solid figures.",
        },
        {
            "part": "External approach, largest remaining photo-supported difference",
            "finding": "Raised stone-sided route and continuous silver rail to the entrance right are explicit in built photographs but absent from the registered OLD exterior assembly. The observed route is not equivalent to the two short portal handrails. Missing continuous approach materially changes how the building meets the street.",
            "safeModificationRange": None,
            "blocker": "Only the landing right edgex=-22.39774 is registered. A first route bay ending at entrance-wing boundaryx=-18.29549 would be an arbitrary clipping station, not a proven endpoint/landing; photo perspective does not determine local slope or curb offset. No component constructed.",
        },
        {
            "part": "Tread count/local street datum conflict",
            "finding": "Front photograph and user view suggest fewer visible external risers than the retained6. Existing stage112 inferred1.245m from GF19.345 minus street GL18.100; that drawing datum difference has not been demonstrated to equal the exposed local external flight rise.",
            "unsafeShortcut": "Changing6 risers to4 while retaining1.245m would imply.31125m risers. This would substitute an unverified access geometry for the accepted approximate one.",
            "nextAction": "Obtain a ground-level route section or ground plan paired with surveyed entrance curb/landing spot heights; distinguish external exposed flight from internal foyer stairs.",
        },
    ],
    "alreadyAcceptedNotRepeated": [
        "OLD_NEXT_PORTAL_clear_rusticated_blocks",
        "OLD_NEXT_CLARE_sealed_window_head_stone",
        "OLD_NEXT_mansard_four_column_blue",
        "OLD_V116_chamfered_fan_stair",
        "OLD_V112_entry_V111_lattice_figures",
    ],
    "remaining": [
        "Registered external raised-route plan/section, curb offsets and terminal access connection missing.",
        "External tread-count versus local datum discrepancy requires ground survey/section before altering flight.",
        "Sculpture depth, face details and some masonry ornament remain approximations; no scan or orthographic relief survey.",
    ],
    "preview": "whole-houghton-native.png",
}
# One unsaved diagnostic render of the whole face, retaining the native model.
col = bpy.data.collections["OLD_EXTERIOR"]
visible = {o.name for o in col.all_objects}
scene = bpy.context.scene
for o in scene.objects:
    if o.type in {"MESH", "FONT", "CURVE", "SURFACE"} and o.name not in visible:
        o.hide_render = True
focus = origin + right * (-6.01) + Vector((0, 0, 13.5))
cam = bpy.data.objects.new(
    "OLD_HOUGHTON_DIAGNOSTIC", bpy.data.cameras.new("OLD_HOUGHTON_DIAGNOSTIC")
)
scene.collection.objects.link(cam)
cam.location = focus + normal * 100 + right * 3 + Vector((0, 0, 12))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = 67
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "whole-houghton-native.png")
bpy.ops.render.render(write_still=True)
for name, state in states.items():
    o = bpy.data.objects[name]
    o.hide_render, o.hide_viewport = state[:2]
    o.hide_set(state[2])
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == state
    for n, state in states.items()
)
audit["originalGeometryPreserved"] = True
audit["unrelatedVisibilityPreserved"] = True
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
(OUT / "verification.json").write_text(
    json.dumps(
        {
            "baselineSha256": EXPECTED,
            "originalObjectCount": len(originals),
            "originalGeometryPreserved": True,
            "unrelatedVisibilityPreserved": True,
            "componentSaved": False,
            "fullModelSaved": False,
            "savedComponentReopened": False,
            "reason": "No supported candidate was constructed; source remained read-only.",
            "ownBlenderExited": "Process calls quit_blender after this verification.",
        },
        indent=2,
    )
    + "\n"
)
print("OLD_HOUGHTON_READONLY_VERIFIED", len(originals))
bpy.ops.wm.quit_blender()
