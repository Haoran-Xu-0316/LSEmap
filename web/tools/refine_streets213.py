"""Unify mapped footways, correct named asphalt and orient slab courses per route.

Open this fixed-config file in Blender to inspect the accepted model, prepare in
MachineLearning Python, then open in Blender again to build a small component.
Route widths and elevations are inherited estimates; no new roads are inferred.
"""
from pathlib import Path
import hashlib,json,math,sys,struct
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v212.blend'
SHA='65165c8a72c8208170c839085fef2954bf61a4f19a4a134d75ebcd289b9d7207'
OUT=ROOT/'result/blender/streets213'
PLAN=OUT/'plan.json'
sys.path.insert(0,str(ROOT/'web/tools'))
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def inspect():
 import bpy
 from mathutils import Vector
 assert sha(BASE)==SHA
 OUT.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 rows=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or o.hide_render or o.hide_get():continue
  if not o.name.startswith(('SITE','GROUND','Road_','00_SITE')):continue
  if min((o.matrix_world@Vector(p)).z for p in o.bound_box)>.1:continue
  vertices=[o.matrix_world@v.co for v in o.data.vertices];faces=[]
  for f in o.data.polygons:
   ps=[vertices[i] for i in f.vertices]
   if max(p.z for p in ps)-min(p.z for p in ps)>1e-5:continue
   if not .02<ps[0].z<.12 or f.normal.z<.5:continue
   mat=o.data.materials[f.material_index].name if o.data.materials else ''
   if not any(t in mat.lower() for t in ['paving','asphalt','tarmac','slab','yorkstone','grout','edge']):continue
   faces.append(dict(points=[list(p) for p in ps],material=mat))
  if faces:rows.append(dict(name=o.name,faces=faces))
 save(OUT/'native.json',dict(baselineSha256=SHA,objects=rows))
 print('STREETS213_INSPECT',len(rows),flush=True)

def prepare():
 from shapely import make_valid,set_precision,constrained_delaunay_triangles
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 n=json.loads((OUT/'native.json').read_text());assert n['baselineSha256']==SHA
 site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
 def tidy(g):return set_precision(set_precision(make_valid(g),.000001),0)
 def footprint(row):return tidy(unary_union([Polygon([p[:2] for p in f['points']]) for f in row['faces']]))
 def tri(g):return [list(t.exterior.coords)[:-1] for t in constrained_delaunay_triangles(g).geoms if t.area>1e-8]
 ways=[r for r in site['roads'] if r['geometry']['type']=='LineString' and r['properties'].get('highway')=='footway']
 segments=[]
 for way in ways:
  for a,b in zip(way['geometry']['coordinates'],way['geometry']['coordinates'][1:]):
   length=math.dist(a,b)
   if length<=.1:continue
   u=[(b[i]-a[i])/length for i in range(2)];v=[-u[1],u[0]]
   poly=Polygon([(p[0]+sign*.025*u[0]+side*.8*v[0],p[1]+sign*.025*u[1]+side*.8*v[1]) for p,sign,side in [(a,-1,1),(b,1,1),(b,1,-1),(a,-1,-1)]])
   segments.append(dict(way=way,polygon=tidy(poly),u=u,v=v,origin=a))
 named_union=unary_union([r['polygon'] for r in segments if r['way']['properties'].get('name')])
 sources=[];registration=[]
 for row in n['objects']:
  if row['name']=='SITE209_Continuous_paved_footways':sources.append(row);continue
  if not row['name'].startswith('GROUND199_') or 'Road_' not in row['name']:continue
  if not all('Pale campus paving' in f['material'] and abs(f['points'][0][2]-.024)<1e-6 for f in row['faces']):continue
  g=footprint(row)
  error=g.difference(named_union.buffer(.0001)).area
  if error<.001:
   sources.append(row);registration.append(dict(name=row['name'],areaM2=g.area,outsideNamedMappedFootwayM2=error))
 assert len(sources)>10,len(sources)
 original=tidy(unary_union([footprint(r) for r in sources]))
 protected=tidy(unary_union([Polygon([p[:2] for p in f['points']]) for row in n['objects'] for f in row['faces'] if f['points'][0][2]>.025 and row not in sources]))
 road=tidy(unary_union([Polygon([p[:2] for p in f['points']]) for row in n['objects'] for f in row['faces'] if 'asphalt' in f['material'].lower() and row not in sources]))
 retained=tidy(original.difference(protected).difference(road))
 used=Polygon();regions=[];counts={};asphalt_area=0
 # Explicit asphalt evidence gets priority at overlapping segment boundaries.
 segments.sort(key=lambda r:r['way']['properties'].get('surface')!='asphalt')
 for r in segments:
  g=tidy(r['polygon'].intersection(retained).difference(used))
  if g.area<.00001:continue
  used=tidy(used.union(g));p=r['way']['properties'];kind='asphalt' if p.get('surface')=='asphalt' else 'concrete' if 'concrete' in p.get('surface','') else 'stone'
  edge=Polygon() if kind=='asphalt' else tidy(g.difference(r['polygon'].buffer(-.14)).intersection(g))
  body=tidy(g.difference(edge));regions.append(dict(id=r['way']['id'],name=p.get('name',p.get('street:name','')),kind=kind,sourceSurface=p.get('surface'),u=r['u'],v=r['v'],origin=r['origin'],body=tri(body),edge=tri(edge),areaM2=g.area))
  counts[r['way']['id']]=p.get('name',p.get('street:name',''))
  if kind=='asphalt':asphalt_area+=g.area
 remainder=tidy(retained.difference(used))
 assert remainder.difference(unary_union([r['polygon'] for r in segments]).buffer(.0002)).area<1e-6,remainder.area
 if remainder.area:regions.append(dict(id='rounding-remainder',name='',kind='stone',sourceSurface=None,u=[1,0],v=[0,1],origin=[0,0],body=tri(remainder),edge=[],areaM2=remainder.area))
 check=unary_union([Polygon(t) for r in regions for t in r['body']+r['edge']])
 assert check.symmetric_difference(retained).area<.01
 assert check.intersection(road).area<.001
 assert check.intersection(protected).area<.001
 save(PLAN,dict(baselineSha256=SHA,sourceObjects=[r['name'] for r in sources],registration=registration,originalAreaM2=original.area,retainedAreaM2=retained.area,coveredByExistingHigherPavingM2=original.intersection(protected).area,removedCoplanarRoadOverlapM2=original.difference(protected).intersection(road).area,explicitAsphaltM2=asphalt_area,sourceWays=len(counts),namedWays={k:v for k,v in counts.items() if v},regions=regions,coverageErrorM2=check.symmetric_difference(retained).area,limitations='OSM archived surface tags and existing1.6m strip widths. Slab modules, flush edge courses and colours are presentation estimates; no survey, new route, raised kerb or traffic marking. Higher detailed paving and road crossing surfaces remain authoritative.'))
 print('STREETS213_PLAN',len(sources),len(counts),round(retained.area,2),round(asphalt_area,2),flush=True)

def build():
 import bpy
 from integrate_exterior_round194 import object_fingerprint
 from refine_portsmouth_exterior207 import material_fingerprint
 assert sha(BASE)==SHA
 plan=json.loads(PLAN.read_text());assert plan['baselineSha256']==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 before={o.name:object_fingerprint(o) for o in bpy.data.objects};materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
 def material(label,color,brick=False):
  m=bpy.data.materials.new('SITE213_SITE_V47_slab_'+label);m.use_nodes=True;m.diffuse_color=(*color,1)
  nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.92
  if brick:
   uv=nodes.new('ShaderNodeTexCoord');b=nodes.new('ShaderNodeTexBrick');b.offset=.5;b.offset_frequency=2
   for name,value in [('Scale',1.),('Brick Width',.90),('Row Height',.60),('Mortar Size',.003),('Mortar Smooth',.002)]:b.inputs[name].default_value=value
   b.inputs['Color1'].default_value=(*(c*.96 for c in color),1);b.inputs['Color2'].default_value=(*(c*1.04 for c in color),1);b.inputs['Mortar'].default_value=(.10,.105,.10,1)
   links.new(uv.outputs['UV'],b.inputs['Vector']);links.new(b.outputs['Color'],p.inputs['Base Color'])
   bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0006;links.new(b.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
  return m
 palette={'stone':material('footway_courses',(.25,.263,.25),True),'concrete':material('concrete_courses',(.28,.29,.278),True),'edge':material('flush_edge_courses',(.21,.223,.212)),'asphalt':bpy.data.materials['Road asphalt']}
 owned=[];records=[]
 for family in ['body','edge']:
  vertices=[];faces=[];uvs=[];slots=[];keys=list(palette)
  for r in plan['regions']:
   for t in r[family]:
    # GEOS overlay slivers can collapse when Blender stores float32 positions.
    # Filter in the actual storage precision and orient the retained triangle.
    t=[tuple(struct.unpack('f',struct.pack('f',v))[0] for v in p) for p in t]
    signed=(t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0])
    if abs(signed)<1e-8:continue
    if signed<0:t=list(reversed(t))
    base=len(vertices);vertices.extend((p[0],p[1],.024) for p in t);faces.append((base,base+1,base+2));slots.append(keys.index('edge' if family=='edge' else r['kind']))
    for p in t:
     delta=[p[i]-r['origin'][i] for i in range(2)];uvs.append((sum(delta[i]*r['u'][i] for i in range(2)),sum(delta[i]*r['v'][i] for i in range(2))))
  mesh=bpy.data.meshes.new('SITE213_'+family+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
  for k in keys:mesh.materials.append(palette[k])
  for f,slot in zip(mesh.polygons,slots):f.material_index=slot
  uv=mesh.uv_layers.new(name='MetricUV')
  for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
  mesh.normals_split_custom_set_from_vertices([(0,0,1)]*len(mesh.vertices))
  o=bpy.data.objects.new('SITE213_mapped_footway_'+family,mesh);bpy.data.collections['00_SITE'].objects.link(o);o['scope']=plan['limitations'];owned.append(o)
  records.append(dict(name=o.name,triangles=len(faces),vertices=len(vertices)))
 assert all(object_fingerprint(bpy.data.objects[n])==f for n,f in before.items())
 assert all(material_fingerprint(bpy.data.materials[n])==f for n,f in materials.items())
 fingerprints={o.name:object_fingerprint(o) for o in owned};component=OUT/'streets213-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 with bpy.data.libraries.load(str(component),link=False) as (_,target):target.objects=list(fingerprints)
 for o in target.objects:
  bpy.context.scene.collection.objects.link(o);assert object_fingerprint(o)==fingerprints[o.name]
 save(OUT/'audit.json',dict(version=213,baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection='00_SITE',addedObjects=list(fingerprints),archivedObjects=plan['sourceObjects'],records=records,sourceWays=plan['sourceWays'],namedWays=plan['namedWays'],retainedAreaM2=plan['retainedAreaM2'],explicitAsphaltM2=plan['explicitAsphaltM2'],removedCoplanarRoadOverlapM2=plan['removedCoplanarRoadOverlapM2'],scope='Include named mapped footways, correct explicit asphalt, align metric slab UVs with each route, add flush edge courses and remove duplicate paving over road crossings/higher paving.',limitations=plan['limitations'],verification=dict(componentReopened=True,originalObjectsPreserved=len(before),originalMaterialsPreserved=len(materials),coverageErrorM2=plan['coverageErrorM2'])))
 print('STREETS213_COMPONENT',records,flush=True)

if __name__=='__main__':
 try:import bpy
 except ImportError:prepare()
 else:build() if PLAN.exists() else inspect()
