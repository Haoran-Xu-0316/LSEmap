"""Keep flush footway borders on the continuous outline, not segment end caps.

Fixed authoring paths reuse the accepted213 route coverage, metric UVs, heights
and materials. Run in MachineLearning to prepare, then Blender to build a small
component. No road width, raised kerb, traffic marking or route is inferred.
"""
from pathlib import Path
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v214.blend'
SHA='58d38dabb75db4fed63d79e1e26ad46da5c7ba809567ab074c70329f9b4880a6'
OUT=ROOT/'result/blender/streets215'
PLAN=OUT/'plan.json'
SOURCE=ROOT/'result/blender/streets213/plan.json'
MATERIALS=['SITE213_SITE_V47_slab_footway_courses','SITE213_SITE_V47_slab_concrete_courses','SITE213_SITE_V47_slab_flush_edge_courses','Road asphalt']
sys.path.insert(0,str(ROOT/'web/tools'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def prepare():
 from shapely import make_valid,set_precision,constrained_delaunay_triangles
 from shapely.geometry import Polygon,mapping
 from shapely.ops import unary_union
 old=json.loads(SOURCE.read_text())
 # Ten-micrometre planar precision closes arithmetic cracks between source
 # triangles before offsetting. It is below the independent0.1mm tolerance.
 def mesh_area(triangles):return set_precision(make_valid(unary_union([set_precision(Polygon(t),.00001) for t in triangles])),.00001)
 def triangles(g):return [list(p.exterior.coords)[:-1] for p in constrained_delaunay_triangles(g).geoms if p.area>1e-8]
 areas=[mesh_area(r['body']+r['edge']) for r in old['regions']]
 whole=unary_union(areas)
 # Erode the continuous walking surface once. A centreline node or way split
 # cannot then manufacture a transverse strip across an uninterrupted footway.
 # Close numerical cracks only for border classification. The actual walking
 # surface remains unchanged, including its original route boundaries.
 outline=whole.buffer(.0001,join_style='mitre').buffer(-.0001,join_style='mitre')
 border=set_precision(outline.difference(outline.buffer(-.14,join_style='mitre')),.00001)
 save(OUT/'edge-outline.json',dict(sourcePlanSha256=sha(SOURCE),geometry=mapping(outline),planarPrecisionMetres=.00001,crackWeldMetres=.0001))
 previous=unary_union([mesh_area(r['edge']) for r in old['regions'] if r['edge']])
 regions=[]
 for r,g in zip(old['regions'],areas):
  edge=g.intersection(border).intersection(previous) if r['kind']!='asphalt' else Polygon()
  regions.append({**r,'edge':triangles(edge),'body':triangles(g.difference(edge))})
 coverage=unary_union([Polygon(t) for r in regions for t in r['body']+r['edge']])
 assert whole.difference(coverage.buffer(.0001)).area<.00001
 assert coverage.difference(whole.buffer(.0001)).area<.00001
 assert coverage.symmetric_difference(whole).area<whole.length*.0001
 added_border=unary_union([Polygon(t) for r in regions for t in r['edge']])
 assert added_border.difference(border.buffer(.0001)).area<.001
 assert previous.difference(added_border).area>1
 plan=dict(baselineSha256=SHA,sourcePlanSha256=sha(SOURCE),sourceWays=old['sourceWays'],namedWays=old['namedWays'],sourceObjects=['SITE213_mapped_footway_body','SITE213_mapped_footway_edge'],regions=regions,retainedAreaM2=whole.area,previousBandAreaM2=previous.area,continuousBandAreaM2=added_border.area,removedInternalBandAreaM2=previous.difference(added_border).area,coverageErrorM2=coverage.symmetric_difference(whole).area,limitations='Accepted213mapped widths, positions, heights and material identities retained. Flush0.14m edge bands and0.6m joints are presentation estimates. No new route, raised kerb, traffic marking or surveyed layout claim.')
 save(PLAN,plan);print('STREETS215_PLAN',{k:v for k,v in plan.items() if k not in ['regions','namedWays']},flush=True)

def build():
 import bpy
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 assert sha(BASE)==SHA
 plan=json.loads(PLAN.read_text());assert plan['baselineSha256']==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 originals={o.name:object_fingerprint(o) for o in bpy.data.objects};materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
 owned=[];records=[]
 for family in ['body','edge']:
  vertices=[];faces=[];uvs=[];slots=[]
  for r in plan['regions']:
   for triangle in r[family]:
    t=[tuple(struct.unpack('f',struct.pack('f',v))[0] for v in p) for p in triangle]
    signed=(t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0])
    if abs(signed)<1e-8:continue
    if signed<0:t.reverse()
    start=len(vertices);vertices.extend((p[0],p[1],.024) for p in t);faces.append((start,start+1,start+2));slots.append(2 if family=='edge' else ['stone','concrete','edge','asphalt'].index(r['kind']))
    for p in t:
     delta=[p[i]-r['origin'][i] for i in range(2)];uvs.append((sum(delta[i]*r['u'][i] for i in range(2)),sum(delta[i]*r['v'][i] for i in range(2))))
  name='SITE215_mapped_footway_'+family;mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
  for name_mat in MATERIALS:mesh.materials.append(bpy.data.materials[name_mat])
  for p,slot in zip(mesh.polygons,slots):p.material_index=slot
  uv=mesh.uv_layers.new(name='MetricUV')
  for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
  mesh.normals_split_custom_set_from_vertices([(0,0,1)]*len(vertices))
  obj=bpy.data.objects.new(name,mesh);obj['originalObject']='SITE213_mapped_footway_'+family;obj['scope']=plan['limitations'];bpy.data.collections['00_SITE'].objects.link(obj);owned.append(obj);records.append(dict(name=name,triangles=len(faces),vertices=len(vertices)))
 assert all(object_fingerprint(bpy.data.objects[n])==f for n,f in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==f for n,f in materials.items())
 fingerprints={o.name:object_fingerprint(o) for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(component),link=False) as (_,target):target.objects=list(fingerprints)
 for obj in target.objects:
  bpy.context.scene.collection.objects.link(obj);assert object_fingerprint(obj)==fingerprints[obj.name]
 report={k:plan[k] for k in ['baselineSha256','sourceWays','retainedAreaM2','previousBandAreaM2','continuousBandAreaM2','removedInternalBandAreaM2','coverageErrorM2','limitations']}
 report.update(version=215,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='00_SITE',addedObjects=list(fingerprints),archivedObjects=plan['sourceObjects'],replacementMaterialBindings={n:MATERIALS for n in fingerprints},records=records,componentReopened=True,originalObjectsPreserved=len(originals),originalMaterialsPreserved=len(materials))
 save(OUT/'audit.json',report);print('STREETS215_COMPONENT',records,flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:prepare()
 else:build()
