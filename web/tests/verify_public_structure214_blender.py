"""Check the saved CLM correction and actual MAR public-selection ownership."""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from public_interior_objects import public_interior_objects
from refine_portsmouth_exterior207 import material_fingerprint
OUT=ROOT/'result/blender/stage214';BASE=ROOT/'result/blender/LSE_campus_detailed_v213.blend';CURRENT=ROOT/'result/blender/LSE_campus_detailed_v214.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE));materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
for name,value in materials.items():assert material_fingerprint(bpy.data.materials[name])==value,name
bpy.context.window.scene=bpy.data.scenes['01_MAR_DETAIL_REVIEW'];bpy.context.view_layer.update()
record=next(b for b in json.loads((ROOT/'web/tools/building-metadata.json').read_text())['buildings'] if b['code']=='MAR')
objects=list(bpy.data.collections['MAR_PUBLIC_INTERIOR_study'].all_objects)
legacy=[o for o in objects if '_floor_way/' not in o.name or max((o.matrix_world@Vector(c)).z for c in o.bound_box)<=13]
legacy+=[o for o in bpy.data.collections['MAR_EXTERIOR'].all_objects if 'ground_glass_panes' in o.name]
selected=public_interior_objects(record)
visible=lambda os:[o for o in os if o.type=='MESH' and not o.hide_render]
removed=[o for o in visible(legacy) if o not in selected]
assert len(removed)==8,[o.name for o in removed]
assert all(o.name.startswith('MAR188_floor_infill_') for o in removed)
assert all(min((o.matrix_world@Vector(c)).z for c in o.bound_box)>=17.5 for o in removed)
rows=[]
for o in removed:
 points=[o.matrix_world@v.co for v in o.data.vertices];rows.append(dict(name=o.name,minZ=min(p.z for p in points),maxZ=max(p.z for p in points),triangles=sum(len(f.vertices)-2 for f in o.data.polygons),retainedGeographic=True))
 for name in ['00_CAMPUS_COMPLETE','01_MAR_DETAIL_REVIEW']:assert o.name in bpy.data.scenes[name].objects
 assert not o.hide_render
before_top=max((o.matrix_world@v.co).z for o in visible(legacy) for v in o.data.vertices)
after_top=max((o.matrix_world@v.co).z for o in visible(selected) for v in o.data.vertices)
assert abs(before_top-30.5)<1e-5 and abs(after_top-12.8)<.001
assert set(visible(selected))==set(visible(legacy))-set(removed)
audit=dict(version=214,sourceModelSha256=hashlib.sha256(CURRENT.read_bytes()).hexdigest(),originalMaterialNodesVerified=len(materials),removedFromDedicatedStudy=rows,legacyPublicTopZ=before_top,correctedPublicTopZ=after_top,groundStairAndAllSupportedPublicObjectsRetained=True,geographicObjectsUnchanged=True,nativeSourceUnchangedByExportSelection=True,scope='Remove eight detached geographic upper-floor patches from the dedicated public study. No native floor or exterior is deleted; this is export ownership repair, not a new current floor survey.',sourceURLs=['https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf','https://www.macegroup.com/en-us/projects/the-lese-marshall-building/'],sourceNotes='2022 architect-authored built plans and contractor project description corroborate separate public hall, teaching and upper office structure; inherited13m export range is not newly measured ceiling height.')
(OUT/'public-structure-verification.json').write_text(json.dumps(audit,indent=2)+'\n');(ROOT/'result/blender/mar-structure214/audit.json').write_text(json.dumps(audit,indent=2)+'\n')
assert hashlib.sha256(CURRENT.read_bytes()).hexdigest()==audit['sourceModelSha256'];print('PUBLIC_STRUCTURE214',len(removed),before_top,after_top,len(materials),flush=True)
