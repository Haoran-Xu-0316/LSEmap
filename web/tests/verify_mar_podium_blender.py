"""Reopen MAR correction and measure the three replacement high windows."""
from pathlib import Path
import array, hashlib, json, math
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage104'
audit=json.loads((OUT/'mar-podium-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v104.blend'))
def fingerprint(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
 return h.hexdigest()
for name,digest in audit['originalFingerprints'].items():assert fingerprint(bpy.data.objects[name])==digest,name
assert set(bpy.data.objects.keys())-set(audit['originalFingerprints']) == {r['copy'] for r in audit['copies']}|set(audit['addedObjects'])
for record in audit['copies']:
 source,copy=[bpy.data.objects[record[k]] for k in ['source','copy']]
 assert source.hide_render and not copy.hide_render
 assert source.matrix_world==copy.matrix_world
 if 'removedVertexIndices' in record:
  removed=set(record['removedVertexIndices'])
  expected=[tuple(v.co) for v in source.data.vertices if v.index not in removed]
  assert expected==[tuple(v.co) for v in copy.data.vertices]
  assert len(removed)==20*8
 elif record['source'] in ['MAR_window_sills','MAR_D5_V16_metal_sill_channel','MAR_D5_V17_sill_front_fascia','MAR_D3_mezzanine_slab_with_stair_aperture']:
  assert len(copy.data.vertices)>0
 else:
  assert [tuple(v.co) for v in source.data.vertices]==[tuple(v.co) for v in copy.data.vertices]
  assert [tuple(p.vertices) for p in source.data.polygons]==[tuple(p.vertices) for p in copy.data.polygons]
  changed=[p.index for p,q in zip(copy.data.polygons,source.data.polygons) if p.material_index!=q.material_index]
  assert changed==audit['paneIndices'] and len(changed)==3
surface=audit['surface'];p,q=[Vector((*surface[k],0)) for k in ['p','q']]
u=(q-p).normalized();n=Vector((-u.y,u.x,0))
joinery=bpy.data.objects[audit['addedObjects'][0]]
bm=bmesh.new();bm.from_mesh(joinery.data)
assert all(edge.is_manifold for edge in bm.edges) and bm.calc_volume()>0
bm.free()
assert len(joinery.data.vertices)==15*8
for a,b,c,d in audit['windows']:
 components=[]
 for start in range(0,len(joinery.data.vertices),8):
  points=[joinery.matrix_world@v.co for v in list(joinery.data.vertices)[start:start+8]]
  center=sum(points,Vector())/8
  if a-.1<=(center-p).dot(u)<=c+.1 and b-.1<=center.z<=d+.1:components.append(points)
 assert len(components)==5
 vertical=[points for points in components if max(v.z for v in points)-min(v.z for v in points)>1]
 assert len(vertical)==2
 xs=sorted((sum(points,Vector())/8-p).dot(u) for points in vertical)
 assert abs(xs[0]-a)<2e-5 and abs(xs[1]-c)<2e-5
 horizontal=[points for points in components if points not in vertical]
 heights=sorted((sum(points,Vector())/8).z for points in horizontal)
 for actual,expected in zip(heights,[b,(b+d)/2,d]):assert abs(actual-expected)<2e-5
for record in audit['overlapCorrections']:
 trim=bpy.data.objects[record['object']]
 bm=bmesh.new();bm.from_mesh(trim.data)
 assert all(edge.is_manifold for edge in bm.edges),trim.name
 assert bm.calc_volume()>0
 bm.free()
 inverse=trim.matrix_world.inverted()
 for a,b,c,d in audit['windows']:
  origin=p+u*((a+c)/2)+n*.65+Vector((0,0,7.2 if 'mezzanine_slab' in trim.name else 7.91))
  hit=trim.ray_cast(inverse@origin,trim.matrix_world.to_3x3().inverted()@(-n),distance=1.5)[0]
  assert not hit,(trim.name,a,c)
slab_record=next(r for r in audit['copies'] if 'mezzanine_slab' in r['source'])
source,slab=[bpy.data.objects[slab_record[k]] for k in ['source','copy']]
source_heights=[(source.matrix_world@v.co).z for v in source.data.vertices]
new_heights=[(slab.matrix_world@v.co).z for v in slab.data.vertices]
assert abs(min(source_heights)-min(new_heights))<2e-5
assert abs(max(source_heights)-max(new_heights))<2e-5
# Probe retained slab and void positions behind the facade, including the stair zone.
for x in range(1,54,2):
 origin=p+u*x+n*.65+Vector((0,0,7.2));inv=slab.matrix_world.inverted()
 hit,location,normal,index=slab.ray_cast(inv@origin,inv.to_3x3()@(-n),distance=2)
 if hit:assert (slab.matrix_world@location-p).dot(n)<-.29
probes=0
for x in range(0,55,2):
 for depth in range(-35,-2,2):
  origin=p+u*x+n*depth+Vector((0,0,10))
  rays=[]
  for obj in [source,slab]:
   inv=obj.matrix_world.inverted();hit,location,normal,index=obj.ray_cast(inv@origin,inv.to_3x3()@Vector((0,0,-1)),distance=5)
   rays.append((hit,(obj.matrix_world@location).z if hit else None))
  assert rays[0][0]==rays[1][0],(x,depth)
  if rays[0][0]:assert abs(rays[0][1]-rays[1][1])<2e-5
  probes+=1
material=bpy.data.materials['MAR_V104_podium_glass']
assert abs(material['webOpacity']-1)<1e-6
assert not any(node.type=='TEX_IMAGE' for node in material.node_tree.nodes)
audit['savedMeasurements']={'originalObjectsUnchanged':True,'otherFrameVerticesUnchanged':True,
 'threePaneMeshesRetained':True,'threeSingleColumnTwoPaneWindows':True,'closedJoineryRails':15,
 'onlyThreePaneAssignmentsChanged':True,'obsoleteSillOverlapsRemoved':True,'mezzanineSlabClearOfWindows':True,'retainedSlabAndVoidProbes':probes,'slabHeightUnchanged':True,'slabBehindNorthFacade':True}
(OUT/'mar-podium-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('SAVED_MAR_PODIUM_VERIFIED',audit['savedMeasurements'],flush=True)
