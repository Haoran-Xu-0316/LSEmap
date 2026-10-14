"""Audit OLD source-to-campus registration without changing the baseline.

The historic reception drawing has no labelled scale. Main-door opening widths
from AccessAble are compared with specific native door leaves, not glass unions.
No exterior/interior repair is made without multiple matching control points.
"""
from pathlib import Path
import base64
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/old-registration213'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v212.blend'
EXPECTED_SHA = '65165c8a72c8208170c839085fef2954bf61a4f19a4a134d75ebcd289b9d7207'


def run_registration_audit():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
    assert baseline_sha == EXPECTED_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.view_layer.update()
    sys.path.insert(0, str(ROOT / 'web/tools'))
    from refine_old_foyer174 import entrance_frame
    from integrate_exterior_round194 import object_fingerprint
    origin, right, outward, scale = entrance_frame()
    inward = -outward
    frame = bpy.data.objects['OLD174_foyer_upper_dark_wood_floor'].matrix_world.copy()
    inverse = frame.inverted()
    originals = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}

    def bounds(points):
        return [[min(v[i] for v in points), max(v[i] for v in points)] for i in range(3)]

    pane = bpy.data.objects['OLD_NEXT_GLAZING172_single_door_panes']
    pane_spans = []
    for face in pane.data.polygons:
        points = [inverse @ (pane.matrix_world @ pane.data.vertices[i].co) for i in face.vertices]
        limits = bounds(points)
        pane_spans.append(dict(polygon=face.index, localBounds=limits, widthMetres=limits[0][1]-limits[0][0], heightMetres=limits[2][1]-limits[2][0]))
    ring = next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['code']=='OLD')['rings'][0]
    plan_ring = []
    for point in ring:
        q = inverse @ Vector((point[0],point[1],0))
        plan_ring.append([762+q.x/scale,814-q.y/scale])
    slice_height = 1.245
    sections = []
    for obj in bpy.data.collections['OLD_EXTERIOR'].all_objects:
        if obj.type != 'MESH' or obj.hide_render or obj.name.startswith(('OLD174','OLD196','OLD_PUBLIC212')): continue
        world_points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if not world_points or min(v.z for v in world_points)>slice_height or max(v.z for v in world_points)<slice_height: continue
        edges = []
        for face in obj.data.polygons:
            vertices = [world_points[i] for i in face.vertices]
            cuts = []
            for a,b in zip(vertices,vertices[1:]+vertices[:1]):
                if (a.z-slice_height)*(b.z-slice_height)<=0 and abs(b.z-a.z)>1e-8:
                    q = inverse @ a.lerp(b,(slice_height-a.z)/(b.z-a.z))
                    cuts.append([762+q.x/scale,814-q.y/scale])
            if len(cuts)>=2: edges.append(cuts[:2])
        if edges: sections.append(dict(object=obj.name, segments=edges))
    foyer_bounds = []
    for name in ['OLD196_FOYER_lower_limestone_floor','OLD174_foyer_upper_dark_wood_floor','OLD174_foyer_reception_counter','OLD_PUBLIC212_historical_public_T_corridor_floor']:
        obj=bpy.data.objects[name]
        points=[inverse@(obj.matrix_world@v.co) for v in obj.data.vertices]
        foyer_bounds.append(dict(object=name,localBounds=bounds(points)))
    audit = dict(version=213,kind='read-only-registration-diagnostic',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=baseline_sha,componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],targetCollection='OLD_MAIN_FOYER174',destinationCollection='OLD_MAIN_FOYER174',frame=dict(origin=list(origin),right=list(right),inward=list(inward),metresPerPlanPixel=scale,doorCentrePlanPixel=[762,814]),nativePaneSpans=pane_spans,nativeGlazingUnionWidthMetres=122*scale,nativeFloorAndCounterBounds=foyer_bounds,mappedFootprintInHistoricPlanPixels=plan_ring,exteriorSectionAtWorldZ=slice_height,exteriorSections=sections,baselineFileUnchanged=True,originalObjectFingerprintsUnchanged=True,originalObjects=len(originals))
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==baseline_sha
    (OUT/'native-registration.json').write_text(json.dumps(audit,indent=2)+'\n')
    image_path=ROOT/'result/blender/old_foyer173/reception8.jpg'
    image_uri='data:image/jpeg;base64,'+base64.b64encode(image_path.read_bytes()).decode()
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1080" viewBox="0 0 1500 1080">','<rect width="1500" height="1080" fill="white"/>',f'<image href="{image_uri}" x="0" y="0" width="1500" height="1000"/>']
    ring_text=' '.join(f'{x:.2f},{y:.2f}' for x,y in plan_ring)
    svg.append(f'<polygon points="{ring_text}" stroke="#1766aa" stroke-width="3" fill="none"/>')
    for section in sections:
        if any(k in section['object'] for k in ['stone_facades','stone_sills','sill_bearing']):
            for (a,b) in section['segments']:
                svg.append(f'<path d="M{a[0]:.2f},{a[1]:.2f} L{b[0]:.2f},{b[1]:.2f}" stroke="#c83236" stroke-width="2"/>')
    svg.append('<circle cx="762" cy="814" r="7" fill="#1766aa"/><text x="20" y="1035" font-family="sans-serif" font-size="22">OLD v212 door-based registration diagnostic. Blue: mapped footprint. Red: native stone at world Z1.245m.</text><text x="20" y="1067" font-family="sans-serif" font-size="20">Historical2011reception plan. No surveyed scale or complete/current floor registration established.</text></svg>')
    (OUT/'native-plan-overlay.svg').write_text(''.join(svg))
    print('OLD_REG213_NATIVE',json.dumps(dict(scale=scale,glazingWidth=122*scale,paneSpans=pane_spans,foyerBounds=foyer_bounds,objects=len(originals))),flush=True)


if __name__ == '__main__':
    run_registration_audit()
