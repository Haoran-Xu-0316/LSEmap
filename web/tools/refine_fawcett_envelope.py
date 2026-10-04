"""Review Fawcett exterior without inventing unregistered elevations.
Run in Blender Text Editor. No component is created unless independent facade evidence supports a change.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/fawcett_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v141.blend"
BASE_SHA = "2da4d8e7b6aefbeae2f5c92c72881bb361eb876208b6684f0c26a5491a30f462"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, w in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            a = array.array(kind, [0]) * (len(data) * w)
            data.foreach_get(field, a)
            h.update(a.tobytes())
        for uv in o.data.uv_layers:
            a = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", a)
            h.update(a.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()



bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
originals={o.name:fingerprint(o) for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
assert len(originals)==5653
collection=bpy.data.collections['FAW_EXTERIOR']
objects=[o for o in collection.all_objects if o.type=='MESH' and len(o.data.vertices) and not o.hide_render]
vs=[];fs=[];names=[]
for o in objects:
    offset=len(vs);vs.extend(o.matrix_world@v.co for v in o.data.vertices);fs.extend(tuple(offset+i for i in f.vertices) for f in o.data.polygons);names.extend([o.name]*len(o.data.polygons))
tree=BVHTree.FromPolygons(vs,fs)
glass=bpy.data.objects['FAW_D3_recessed_window_bands'];probes=[]
for start in range(0,len(glass.data.vertices),8):
    ps=[glass.matrix_world@v.co for v in glass.data.vertices[start:start+8]];centre=sum(ps,Vector())/8;u=(ps[4]-ps[0]).normalized();n=Vector((u.y,-u.x,0));width=(ps[4]-ps[0]).length
    for fraction in [-.27,.27]:
        point=centre+u*width*fraction;hits=[]
        for sign in [-1,1]:
            normal=n*sign;hit=tree.ray_cast(point+normal*.8,-normal,1.6);hits.append(names[hit[2]] if hit[2] is not None else None)
        probes.append({'windowBand':start//8,'point':list(point),'firstHitsBothDirections':hits,'glassReachable':glass.name in hits})
assert len(probes)==288
assert all(p['glassReachable'] for p in probes)
geometry=[];materials={}
for o in objects:
    ps=[o.matrix_world@v.co for v in o.data.vertices];geometry.append({'name':o.name,'fingerprint':originals[o.name],'vertices':len(ps),'bounds':[[min(p[i] for p in ps) for i in range(3)],[max(p[i] for p in ps) for i in range(3)]],'materialSlots':[m.name if m else None for m in o.data.materials]})
    for m in o.data.materials:
        if not m or m.name in materials:continue
        node=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
        if node:materials[m.name]={'baseColor':list(node.inputs['Base Color'].default_value),'metallic':node.inputs['Metallic'].default_value,'roughness':node.inputs['Roughness'].default_value,'alpha':node.inputs['Alpha'].default_value,'transmission':node.inputs['Transmission Weight'].default_value,'baseColorLinked':node.inputs['Base Color'].is_linked,'webOpacity':m.get('webOpacity')}
photoRoot=ROOT/'data/建筑图片/FAW_Fawcett House/01_建筑实拍'
references=[]
for file,coverage,date in [('exteriors_lse_estate_007.jpg','Shared PAN entrance and its lower facade; not a registered independent FAW elevation.','unknown'),('tower_photos_round4_tower_round4_realm_p47_0.jpg','Shared PAN/FAW forecourt, PAN doorway, adjacent low walls; no whole FAW elevation.','2022 publication; capture unknown'),('tower_photos_round4_tower_round4_realm_p67_2.jpg','Shared-entry low glass and forecourt only.','2021-08-31 source date'),('interiors_0389.jpg','FAW.3.04 room, only partial inner window reveal; no identifiable exterior face/bay registration.','2022 webpage refresh; capture unknown'),('interiors_0931.jpg','FAW.2.01 room, partial inner window reveal and blinds; no identifiable exterior face/bay registration.','unknown')]:
    photo=photoRoot/file;references.append({'local':str(photo),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'coverage':coverage,'date':date})
audit={'baseline':str(BASE),'baselineSha256':BASE_SHA,'status':'reviewed-no-component-independent-FAW-elevation-cannot-be-registered','ownedObjects':[],'archivedObjects':[],'archiveObjects':[],'changes':[],'originalFingerprints':originals,'originalVisibility':visibility,'geometry':geometry,'materials':materials,'windowBandCount':144,'windowProbes':probes,'references':references,'primaryLookup':[{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','result':'Same existing shared-entry image;1971 building age does not resolve facade bay count.'},{'url':'https://www.accessable.co.uk/london-school-of-economics/access-guides/fawcett-house-tower-2','result':'403 blocked; indexed provider excerpt identifies twelfth-floor Media Studio, consistent with tall tower rather than cropped entrance height.'}],'wholeFacadeReview':{'massing':'13-storey/44m inherited provisional OSM envelope; photo crop does not justify reducing height. No metric height or independent complete elevation.','windows':'144 recessed native window bands with slender vertical mullions are accessible in288 off-mullion geometry probes. This verifies openings, not photo accuracy of rounded1.48m bay counts.','stoneBrick':'Warm aggregate/spandrels and pale metal finish already accepted58; no FAW-specific evidence of red brick or distinct stone-zone replacement.','glass':'Existing physical glazing/shader and selected blinds retained. Internal room photos show glazing/blinds but do not register which complete exterior bays differ.','entry':'Documented shared entrance belongs to PAN mesh, not copied or invented on FAW.','roof':'Existing flat roof/parapet retained; no identifiable whole-roof photograph or current equipment plan.'},'nextRequiredEvidence':['Independent north/east/south FAW full elevation with crown and identifiable connection to PAN','At least one complete street facade enabling exact bay registration','Attributable roof image for2ClementsInn; conversion/project render must be distinguished from built condition'],'limitations':['No full exterior completion claim.','No unsupported geometry/material changes or fake interior backing.','Window first-contact success is geometry evidence only, not architectural accuracy.']}
assert all(fingerprint(bpy.data.objects[n])==h for n,h in originals.items())
assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items())
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
(OUT/'verification.json').write_text(json.dumps({'componentCreated':False,'reason':'No independently registered exterior discrepancy; avoid false component acceptance','originalObjectCount':len(originals),'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'baselineUnchanged':True,'windowBandCount':144,'glassReachableProbeCount':len(probes),'savedComponentReopened':False,'nativeRenderCreated':False},indent=2)+'\n')
print('FAWCETT_BOUNDED_REVIEW',len(originals),len(probes),flush=True)
bpy.ops.wm.quit_blender()
