"""Source-led St Clement Lane, LSE Square and John Watkins public realm review.

Fixed configuration for Blender's Text Editor. Complete221 native is read-only;
all source objects, materials and independent room studies remain protected.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v221.blend'
SHA='62b61a56a402120ab5047096113b02e20f85f7957442e39b6262557c151c69cb'
OUT=ROOT/'result/blender/street-environment222'
DATA=ROOT/'data/collections/street-environment222'
ROI=(10,-65,90,25)
sys.path.insert(0,str(ROOT/'web/tools'))

def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def inspect():
 import bpy
 from mathutils import Vector
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 expected=accepted_fingerprints(ROOT/'result/blender/stage221',SHA)
 actual={o.name:object_fingerprint(o)for o in bpy.data.objects};assert actual==expected and len(actual)==7651
 materials={m.name:material_fingerprint(m)for m in bpy.data.materials}
 rows=[];access=[]
 for obj in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects:
  if obj.type!='MESH' or obj.hide_render:continue
  bounds=[obj.matrix_world@Vector(p)for p in obj.bound_box]
  low=[min(v[i]for v in bounds)for i in range(3)];high=[max(v[i]for v in bounds)for i in range(3)]
  if low[0]>ROI[2]or high[0]<ROI[0]or low[1]>ROI[3]or high[1]<ROI[1]:continue
  if any(k in obj.name.lower()for k in ['step','ramp','approach','plaza','square','clement','guard','retaining']):access.append(dict(name=obj.name,low=low,high=high,materials=[m.name for m in obj.data.materials if m]))
  if high[2]<-.1 or low[2]>3.5:continue
  faces=[]
  for f in obj.data.polygons:
   pp=[obj.matrix_world@obj.data.vertices[i].co for i in f.vertices]
   if min(p.z for p in pp)<-.05 or max(p.z for p in pp)>3.5:continue
   if min(p.x for p in pp)>ROI[2]or max(p.x for p in pp)<ROI[0]or min(p.y for p in pp)>ROI[3]or max(p.y for p in pp)<ROI[1]:continue
   normal=(obj.matrix_world.to_3x3().inverted().transposed()@f.normal).normalized()
   if normal.z<.7:continue
   if len(pp)>100:continue
   faces.append(dict(index=f.index,points=[list(p)for p in pp],material=obj.data.materials[f.material_index].name if obj.data.materials else None))
  if faces:rows.append(dict(name=obj.name,low=low,high=high,faces=faces))
 save('native-surfaces.json',dict(baselineSha256=SHA,roi=ROI,objects=rows,accessObjects=access))
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 rooms={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']}
 assert len(rooms)==19 and len({n for names in rooms.values()for n in names})==678
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in actual.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in materials.items())
 save('native-preservation.json',dict(baselineSha256=SHA,acceptedObjectsVerified=len(actual),sourceMaterialsVerified=len(materials),protectedSpaces=19,protectedSpaceObjects=678,allOriginalFingerprintsUnchanged=True,allOriginalMaterialNodesUnchanged=True,completeNativeNeverSaved=True,nativeHashUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA))
 print('STREET222_INSPECTED',len(actual),len(materials),len(rows),len(access),flush=True)


PREFIX='SITE222_'
NAMES=[PREFIX+'Square_six_stone_tree_pool_enclosures',PREFIX+'Square_six_tree_pool_soil']


def prepare():
 from shapely.geometry import shape,mapping,Polygon
 from shapely.geometry.polygon import orient
 source=json.loads((ROOT/'result/blender/cbg-ground206/paving-plan.json').read_text())
 conflict=json.loads((ROOT/'result/blender/street-environment218/audit.json').read_text())
 from shapely.ops import unary_union
 conflicts=unary_union([shape(r['exposedGeometry'])for r in conflict['findings']])
 rows=[]
 for index,record in enumerate(source['mappedTreePools']):
  original=orient(shape(record),sign=1);foundation=orient(original.buffer(-.00002,join_style=2),sign=1);outer=orient(original.buffer(-.008,join_style=2),sign=1)
  inner=orient(outer.buffer(-.28,join_style=2),sign=1);soil=orient(inner.buffer(-.004,join_style=2),sign=1)
  assert all(g.is_valid and len(g.exterior.coords)==5 for g in [original,outer,inner,soil])
  assert outer.difference(original).area<1e-9 and outer.intersection(conflicts).area<1e-9
  outside=list(outer.exterior.coords)[:-1];inside=list(inner.exterior.coords)[:-1]
  rotations=[inside[k:]+inside[:k]for k in range(4)]
  inside=min(rotations,key=lambda ring:sum((a[0]-b[0])**2+(a[1]-b[1])**2 for a,b in zip(outside,ring)))
  rows.append(dict(index=index,sourceHole=mapping(original),outer=outside,inner=inside,soil=list(soil.exterior.coords)[:-1],sourceHoleAreaM2=original.area,stoneRingAreaM2=outer.area-inner.area,soilAreaM2=soil.area,foundation=list(foundation.exterior.coords)[:-1],wallThicknessEstimate=.28,pavingTop=.05,wallTopEstimate=.47,soilTopEstimate=.37))
 assert len(rows)==6
 save('planter-plan.json',dict(baselineSha256=SHA,sourceMappedHoles='result/blender/cbg-ground206/paving-plan.json:mappedTreePools',planters=rows,unresolvedJunctionOverlapM2=conflicts.area,newFootprintOutsideOriginalHolesM2=0,overlapWithUnresolvedJunctionM2=0,scope='Six existing mapped non-walking rectangular tree holes only; all road and walking-paving geometry retained.'))
 print('STREET222_PREPARED_SIX_POOLS',sum(r['stoneRingAreaM2']for r in rows),flush=True)


def render_views(label):
 import bpy
 from refine_street_connections194 import render_review
 scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 views=[('square-context',(30,-45,16),(38,-28,.7),36),('planter-group',(31,-41,7),(39,-28,.7),30)]
 for name,location,target,scale in views:render_review(scene,OUT/(label+'-'+name+'.png'),location,target,scale)
 return [dict(name=n,location=p,target=t,orthoScale=s)for n,p,t,s in views]


def build_component():
 import bpy,bmesh
 from mathutils import Vector
 from mathutils.bvhtree import BVHTree
 from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints,update_scene
 from refine_portsmouth_exterior207 import material_fingerprint
 from build_clm_hongkong_room220 import modifier_payload
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 expected=accepted_fingerprints(ROOT/'result/blender/stage221',SHA)
 originals={o.name:object_fingerprint(o)for o in bpy.data.objects};assert originals==expected and len(originals)==7651
 material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
 memberships={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects}
 modifiers={o.name:hashlib.sha256(json.dumps([modifier_payload(m)for m in o.modifiers],sort_keys=True).encode()).hexdigest()for o in bpy.data.objects}
 visibility={o.name:o.hide_render for o in bpy.data.objects}
 metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
 rooms={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']}
 assert len(rooms)==19 and len({n for names in rooms.values()for n in names})==678
 plan=json.loads((OUT/'planter-plan.json').read_text());assert plan['baselineSha256']==SHA
 bed=bpy.data.objects['SITE206_CBG_square_joint_bed'];assert not bed.hide_render
 tree=BVHTree.FromPolygons([bed.matrix_world@v.co for v in bed.data.vertices],[tuple(p.vertices)for p in bed.data.polygons])
 # The old tree holes have no active ground sheet. Close each original hole
 # with its soil foundation at the same flat native grade, then carry the
 # enclosures on this base. Register the base top to the actual paving bed
 # around every pit, rather than claiming a hidden datum is physical support.
 grade_source=bpy.data.objects['GROUND199_Road_LSE Square.001']
 grade=min((grade_source.matrix_world@v.co).z for v in grade_source.data.vertices);assert abs(grade)<1e-7
 support=[]
 for item in plan['planters']:
  boundary=item['sourceHole']['coordinates'][0][:-1];heights=[]
  for a,b in zip(boundary,boundary[1:]+boundary[:1]):
   edge=np.array(b)-a;outward=np.array([edge[1],-edge[0]])/np.linalg.norm(edge)
   for fraction in [.2,.5,.8]:
    point=np.array(a)*(1-fraction)+np.array(b)*fraction+outward*.05
    hit=tree.ray_cast(Vector((point[0],point[1],1)),Vector((0,0,-1)),2)
    assert hit[0]is not None and hit[1].z>.99,'Missing actual paving at original tree-hole perimeter'
    heights.append(hit[0].z);support.append(dict(pool=item['index'],point=list(point),sourceObject=bed.name,pavingBedZ=hit[0].z))
  assert max(heights)-min(heights)<1e-5 and abs(heights[0]-.04)<1e-5
  item['grade']=grade;item['base']=heights[0];item['foundationTop']=heights[0]
 cameras=render_views('before')
 def material(name,color,roughness):
  m=bpy.data.materials.new(PREFIX+name);m.use_nodes=True;m.diffuse_color=(*color,1)
  nodes=m.node_tree.nodes;shader=nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=(*color,1);shader.inputs['Roughness'].default_value=roughness
  uv=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=32
  bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.1;bump.inputs['Distance'].default_value=.0007
  m.node_tree.links.new(uv.outputs['UV'],noise.inputs['Vector']);m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
  m['source']='Gillespies built LSE public-square photographs; no source photo pixels or public texture';m['finishEstimate']=True
  return m
 stone=material('Square_planter_pale_stone',(.53,.54,.505),.82)
 cap=material('Square_planter_stone_cap',(.59,.60,.56),.78)
 soilmat=material('Square_planter_soil',(.075,.062,.041),.98)
 body_vertices=[];body_faces=[];body_slots=[];soil_vertices=[];soil_faces=[]
 def ring(item):
  outer=item['outer'];inner=item['inner'];bottom=item['base'];top=item['wallTopEstimate'];off=len(body_vertices)
  body_vertices.extend((x,y,z)for z in [bottom,top]for ring in [outer,inner]for x,y in ring)
  for i in range(4):
   j=(i+1)%4
   body_faces.extend([(off+8+i,off+8+j,off+12+j,off+12+i),(off+j,off+i,off+4+i,off+4+j),(off+i,off+j,off+8+j,off+8+i),(off+4+i,off+12+i,off+12+j,off+4+j)])
   body_slots.extend([1,0,0,0])
 def soil(item):
  outer=item['foundation'];inner=item['soil'];bottom=item['grade'];base=item['foundationTop'];top=item['soilTopEstimate'];off=len(soil_vertices)
  rotations=[inner[k:]+inner[:k]for k in range(4)];inner=min(rotations,key=lambda ring:sum((a[0]-b[0])**2+(a[1]-b[1])**2 for a,b in zip(outer,ring)))
  soil_vertices.extend((x,y,bottom)for x,y in outer);soil_vertices.extend((x,y,base)for x,y in outer)
  soil_vertices.extend((x,y,base)for x,y in inner);soil_vertices.extend((x,y,top)for x,y in inner)
  soil_faces.extend([tuple(off+i for i in [3,2,1,0]),tuple(off+i for i in [12,13,14,15])])
  for i in range(4):
   j=(i+1)%4
   soil_faces.extend([(off+i,off+j,off+4+j,off+4+i),(off+4+i,off+4+j,off+8+j,off+8+i),(off+8+i,off+8+j,off+12+j,off+12+i)])
 for item in plan['planters']:ring(item);soil(item)
 def mesh_object(name,vertices,faces,materials,slots=None):
  mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
  for material in materials:mesh.materials.append(material)
  if slots:
   for face,index in zip(mesh.polygons,slots):face.material_index=index
  uv=mesh.uv_layers.new(name='MetricUV')
  for face in mesh.polygons:
   for loop in face.loop_indices:
    p=mesh.vertices[mesh.loops[loop].vertex_index].co
    uv.data[loop].uv=(p.x,p.y)if abs(face.normal.z)>.5 else(p.x+p.y,p.z)
  obj=bpy.data.objects.new(name,mesh);bpy.data.collections['00_SITE'].objects.link(obj)
  obj['destinationCollection']='00_SITE';obj['scope']='Six photo-supported stone tree-pool enclosures wholly inside existing mapped holes; widths and heights photographic estimates'
  obj['sourceMappedArea']='relation/19133691';obj['sourceHoleCount']=6
  obj['reference']='https://www.gillespies.co.uk/projects/lse-global-centre-for-social-sciences'
  return obj
 owned=[mesh_object(NAMES[0],body_vertices,body_faces,[stone,cap],body_slots),mesh_object(NAMES[1],soil_vertices,soil_faces,[soilmat])]
 def solid_checks(objects):
  rows=[]
  for obj in objects:
   bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
   assert all(e.is_manifold for e in bm.edges),obj.name
   volume=bm.calc_volume(signed=True);assert volume>0
   rows.append(dict(object=obj.name,allEdgesManifold=True,positiveClosedVolumeM3=volume,vertices=len(bm.verts),faces=len(bm.faces)));bm.free()
  return rows
 solids=solid_checks(owned);update_scene();render_views('after')
 fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name for m in o.data.materials]for o in owned}
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
 assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
 with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
 for obj in loaded.objects:
  for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
  bpy.data.collections['00_SITE'].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 update_scene();solid_checks(loaded.objects)
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items())
 assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
 assert all(sorted(c.name for c in bpy.data.objects[n].users_collection)==v for n,v in memberships.items())
 assert all(hashlib.sha256(json.dumps([modifier_payload(m)for m in bpy.data.objects[n].modifiers],sort_keys=True).encode()).hexdigest()==v for n,v in modifiers.items())
 assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items())
 assert all(sorted(o.name for o in bpy.data.collections[c].all_objects)==names for c,names in rooms.items())
 # All new projected vertices are inside original non-walking holes. Thus no
 # retained road, stair, ramp or walking-paving face is removed or obstructed.
 # Float32 saved vertices remain within the original non-walking holes.
 def in_ring(point,ring,tolerance=.00001):
  return all((b[0]-a[0])*(point.y-a[1])-(b[1]-a[1])*(point.x-a[0])>=-tolerance for a,b in zip(ring,ring[1:]+ring[:1]))
 checked_vertices=0
 for name in NAMES:
  for vertex in bpy.data.objects[name].data.vertices:
   point=bpy.data.objects[name].matrix_world@vertex.co
   assert any(in_ring(point,item['sourceHole']['coordinates'][0][:-1])for item in plan['planters'])
   checked_vertices+=1
 soil_object=bpy.data.objects[NAMES[1]]
 soil_tree=BVHTree.FromPolygons([soil_object.matrix_world@v.co for v in soil_object.data.vertices],[tuple(p.vertices)for p in soil_object.data.polygons])
 contact_rows=[]
 for item in plan['planters']:
  for a,b in zip(item['outer'],item['inner']):
   point=(np.array(a)+b)/2
   hit=soil_tree.ray_cast(Vector((point[0],point[1],item['base']+.002)),Vector((0,0,-1)),.004)
   assert hit[0]is not None and abs(hit[0].z-item['base'])<.00001 and hit[1].z>.99
   contact_rows.append(dict(pool=item['index'],point=list(point),stoneBase=item['base'],actualSoilFoundationTop=hit[0].z))
 save('saved-component-contact.json',dict(savedComponentVerticesInsideOriginalHoles=checked_vertices,stoneFoundationContactSamples=len(contact_rows),allStoneFeetTouchClosedSoilFoundation=True,perimeterPlanSeamToleranceMetres=.0002,foundationGradeZ=grade,rows=contact_rows))
 verification=dict(savedComponentReopened=True,originalObjectsVerified=len(originals),sourceMaterialsVerified=len(material_states),allOriginalFingerprintsUnchanged=True,allOriginalMaterialNodesUnchanged=True,allOriginalModifiersUnchanged=True,allOriginalCollectionMembershipUnchanged=True,originalVisibilityPreserved=True,protectedSpaces=19,protectedSpaceObjects=678,protectedSpacesUnchanged=True,sourceNativeUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
 save('support-probes.json',dict(samples=len(support),sourcePavingBedObject='SITE206_CBG_square_joint_bed',sourceFlatGradeObject='GROUND199_Road_LSE Square.001',sourceFlatGradeZ=grade,allActualRimHits=True,foundationMethod='New closed soil foundation plugs only the existing non-walking hole at native flat grade; its top meets the original paving bed, and supports the stone ring. Hidden datum sheets are not used.',stoneBaseZByPool=[dict(pool=i['index'],base=i['base'])for i in plan['planters']],rows=support))
 audit=dict(version=222,baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),targetCollection='00_SITE',destinationCollection='00_SITE',addedObjects=list(fingerprints),archivedObjects=[],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,verification=verification,solids=solids,planters=[{k:v for k,v in item.items()if k not in ['outer','inner','soil','sourceHole']}for item in plan['planters']],supportEvidence='support-probes.json',sourceRefs=json.loads((DATA/'sources.json').read_text()),previews=['before-square-context.png','after-square-context.png','before-planter-group.png','after-planter-group.png'],cameras=cameras,unresolvedJunction=dict(exposedCoplanarAreaM2=10.505023739518649,modified=False,reason='No registered actual kerb boundary supports stone/asphalt priority. No Z offset or material override applied.'),coverage=dict(originalMappedHoleCount=6,newObjectFootprintOutsideOriginalHolesM2=0,walkingPavingRemovedM2=0,retainedWalkingPavingObstructedM2=0,unresolvedJunctionOverlapM2=0),scope='Complete six-pool pale-stone enclosure and soil group inside existing LSE Square tree-pool boundaries, registered by the unchanged mapped pits and trees. Existing outdoor walkways remain continuous.',limitations=['Photo capture dates are unknown; built appearance does not establish October2026 current condition.','Absolute native Z wall top0.47m,soil top0.37m,0.28m wall thickness and0.04m foundation depth are estimates; active surrounding paving bedZ0.04m and retained mapped XY outlines provide registration. Wall visible height above pavementZ0.05m is0.42m.','Eight-step and three-step library connections are not fabricated over the retained flat street levels; a shared vertical registration remains necessary.','Reference photographs are private evidence only; materials contain no source photograph textures.'])
 save('audit.json',audit);save('verification.json',verification)
 print('STREET222_COMPONENT_REOPENED',len(owned),len(originals),len(material_states),len(support),flush=True)

if __name__=='__main__':
 try:import bpy
 except ModuleNotFoundError:prepare()
 else:build_component()
