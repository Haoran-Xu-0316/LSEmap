"""Independently reopen the saved Portugal Street facade and inspect its geometry."""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage110'
audit=json.loads((OUT/'portugal-frontage-audit.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v110.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.view_layer.update()
def digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  v=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',v)
  i=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',i)
  h.update(v.tobytes());h.update(i.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
assert all(digest(bpy.data.objects[n])==h for n,h in audit['originalFingerprints'].items())
archived={r['source']for r in audit['clipped']}
for n,state in audit['originalVisibility'].items():assert bpy.data.objects[n].hide_render==(True if n in archived else state),n
extras={o.name for o in bpy.data.objects}-set(audit['originalFingerprints'])
assert extras==set(audit['addedObjects'])|{r['copy']for r in audit['clipped']if r['copy']}
assert len([o for o in audit['openings']if o['kind']=='triple'])==63
assert len([o for o in audit['openings']if o['kind']=='loft'])==18
# The drawing's narrow corner is screen-left, at the northeast GIS endpoint.
corner=[o['x']for o in audit['openings']if o['kind']=='corner']
assert min(corner)>audit['length']*.90
entry=next(o for o in audit['openings']if o['kind']=='ground-entry')
assert .35<entry['x']/audit['length']<.45
origin,axis,normal=[Vector(audit[k])for k in ['origin','axis','normal']]
for name in audit['addedObjects']:
 o=bpy.data.objects[name];assert not o.hide_render and not o.modifiers
 assert all(math.isfinite(c)for v in o.data.vertices for c in v.co)
 assert all(p.area>1e-10 for p in o.data.polygons),name
 if 'roof' in name:assert o['sharedInteriorRoof']
# Ray probes hit actual glass first, not masonry hidden immediately behind it.
objects=[o for o in bpy.data.collections['LRB_EXTERIOR'].all_objects if not o.hide_render and o.type=='MESH']
geometry=[]
for o in objects:
 vs=[o.matrix_world@v.co for v in o.data.vertices]
 geometry.append((o.name,BVHTree.FromPolygons(vs,[list(p.vertices)for p in o.data.polygons],all_triangles=False)))
probes=0
for opening in audit['openings']:
 if opening['kind']=='ground-service':continue
 # Pick the centre of a single pane, clear of any mullion or transom.
 x=opening['x']-opening['width']/2+opening['width']/opening['columns']*.5
 # The historic corner doorway has stone columns in front of its side lights.
 if opening['kind']=='corner-entry':x=opening['x']
 z=opening['low']+(opening['high']-opening['low'])/opening['rows']*.5
 p=origin+axis*x+normal*.6+Vector((0,0,z));hits=[]
 for name,bvh in geometry:
  loc,n,index,d=bvh.ray_cast(p,-normal,1.20)
  if loc is not None:hits.append((d,name))
 assert hits,(opening,hits)
 first=min(hits)
 assert 'portugal110_' in first[1] and 'glass' in first[1],(opening,first)
 assert not [(d,n)for d,n in hits if 'glass' not in n and first[0]+.04<d<first[0]+.45],(opening,hits)
 probes+=1
roof=bpy.data.objects['LRB_D5_portugal110_roof'];heights=[v.co.z for v in roof.data.vertices]
assert abs(min(heights)-17.37)<1e-4 and abs(max(heights)-20.59)<1e-4
verification={'version':110,'originalGeometryRetained':True,'unrelatedVisibilityRetained':True,'clippedSources':len(archived),'tripleUpperLights':63,'mansardWindows':18,'clearWindowProbes':probes,'newFamilies':len(audit['addedObjects'])}
(OUT/'saved-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
print('SAVED_PORTUGAL_FRONTAGE_VERIFIED',probes,len(extras),flush=True)
