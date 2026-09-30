"""Inspect the saved oriel cross-section; do not alter the native file."""
from pathlib import Path
import bpy,json
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v54.blend'))
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());building=next(b for b in site['buildings']if b['code']=='KSW');ring=building['rings'][0]
a,b=Vector((*ring[11],0)),Vector((*ring[0],0));origin=(a+b)/2;u=(b-a).normalized();n=Vector((u.y,-u.x,0))
if (origin-Vector((*building['center'],0))).dot(n)<0:n=-n
obj=bpy.data.objects['KSW_D3_oriel_curved_sill_approximation'];points=[obj.matrix_world@v.co-origin for v in obj.data.vertices]
center=max(p.dot(n)for p in points if abs(p.dot(u))<.15);edge=max(p.dot(n)for p in points if abs(p.dot(u))>.95)
assert .20<center-edge<.50,(center,edge)
result={'centerFrontDepth':center,'edgeFrontDepth':edge,'measuredBowDifference':center-edge,'vertexCount':len(points)}
(ROOT/'result/blender/stage54/oriel-cross-section.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
