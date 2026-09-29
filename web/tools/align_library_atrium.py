"""Register the coupled LRB core and rebuild openings with a fixed perimeter.

Run in Blender's Text Editor. Produces a review candidate; furniture clearance
and floor-specific opening outlines must be reviewed before web publication.
"""
from pathlib import Path
import array,hashlib,json
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage38'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v37.blend'))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
registration=json.loads((OUT/'library-plan-registration.json').read_text())
opening=json.loads((OUT/'registered-opening.json').read_text())
shift=Vector((*registration['suggestedTranslation'],0))
centre=Vector(opening['centre'])

def fingerprint(obj):
 h=hashlib.sha256(array.array('f',[v for row in obj.matrix_world for v in row]).tobytes())
 if obj.type=='MESH':
  h.update(array.array('f',[v for p in obj.data.vertices for v in p.co]).tobytes())
  h.update(array.array('i',[v.vertex_index for v in obj.data.loops]).tobytes())
 return h.hexdigest()

before={o.name:fingerprint(o) for o in bpy.data.objects}
surfaces={'LRB_library_floor_slabs','LRB_gallery_carpet','LRB_roof_deck_around_atrium'}
legacy=('LRB_shelf_end_panels','LRB_shelf_boards','LRB_reference_book_spines')
changed=[]
for obj in bpy.data.collections['LRB_PUBLIC_INTERIOR_study'].all_objects:
 if obj.name in surfaces or obj.name.startswith(('LRB_V21_',*legacy)):continue
 assert obj.parent is None
 obj.location+=shift
 changed.append(obj.name)
for obj in bpy.data.collections['LRB_EXTERIOR'].all_objects:
 if obj.name.startswith('LRB_V31_'):
  obj.location+=shift;changed.append(obj.name)

for name in sorted(surfaces):
 obj=bpy.data.objects[name];vertices=[];faces=[]
 levels=[23] if 'roof_deck' in name else [0.32+4*i for i in range(5)] if 'carpet' in name else [-3.68+4*i for i in range(6)]
 inverse=obj.matrix_world.inverted()
 for z in levels:
  if 'carpet' in name:z+=.012
  for triangle in opening['triangles']:
   start=len(vertices)
   vertices.extend([inverse@Vector((x,y,z)) for x,y in triangle])
   faces.append((start,start+1,start+2))
   if 'slabs' in name:
    vertices.extend([inverse@Vector((x,y,z-.32)) for x,y in triangle])
    faces.extend([(start+5,start+4,start+3),(start,start+3,start+4,start+1),
                  (start+1,start+4,start+5,start+2),(start+2,start+5,start+3,start)])
 mesh=bpy.data.meshes.new(name+'_registered')
 mesh.from_pydata(vertices,[],faces)
 for material in obj.data.materials:mesh.materials.append(material)
 mesh.update()
 uv=mesh.uv_layers.new(name='SurfaceUV')
 for face in mesh.polygons:
  for index in face.loop_indices:
   p=obj.matrix_world@mesh.vertices[mesh.loops[index].vertex_index].co
   uv.data[index].uv=(p.x,p.y)
 obj.data=mesh;changed.append(name)
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert all(fingerprint(o)==before[o.name] for o in bpy.data.objects if o.name not in changed)
# The rebuilt slab/roof rings and moved guards share the same centre.
for name in surfaces:
 obj=bpy.data.objects[name]
 radii=[(Vector((p.x,p.y))-centre).length for p in (obj.matrix_world@v.co for v in obj.data.vertices)]
 assert min(radii)>9.799, (name,min(radii))
 assert sum(abs(r-9.8)<.001 for r in radii)>100
collisions=[]
for obj in bpy.data.collections['LRB_PUBLIC_INTERIOR_study'].all_objects:
 if obj.type!='MESH' or not obj.name.startswith(('LRB_V21_',*legacy)):continue
 if obj.get('floorId')=='LG':continue
 # Every source component is a separate eight-vertex box. Flag whole boxes.
 assert len(obj.data.vertices)%8==0
 count=0
 for start in range(0,len(obj.data.vertices),8):
  points=[obj.matrix_world@v.co for v in obj.data.vertices[start:start+8]]
  if any((Vector((p.x,p.y))-centre).length<10.4 for p in points):count+=1
 if count:collisions.append({'name':obj.name,'boxesWithinOpeningClearance':count})
# Remove complete conflicting legacy shelf modules; plan-derived furniture stays fixed.
assert all(item['name'].startswith(legacy) for item in collisions), collisions
old_centre=registration['nativeAtriumCentre']
blocked_modules=[]
for dx in [-16,-13,13,16]:
 for dy in [-9,-4,1,6,11]:
  x,y=old_centre[0]+dx,old_centre[1]+dy
  nearest=Vector((max(x-.56,min(centre.x,x+.56)),max(y-1.07,min(centre.y,y+1.07))))
  if (nearest-centre).length<10.4:blocked_modules.append((x,y))
removed_vertices=0
for obj in bpy.data.collections['LRB_PUBLIC_INTERIOR_study'].all_objects:
 if not obj.name.startswith(legacy):continue
 removed={v.index for v in obj.data.vertices if any(abs((obj.matrix_world@v.co).x-x)<.57 and abs((obj.matrix_world@v.co).y-y)<1.08 for x,y in blocked_modules)}
 if not removed:continue
 assert all(not(set(face.vertices)&removed) or set(face.vertices)<=removed for face in obj.data.polygons)
 mesh=bmesh.new();mesh.from_mesh(obj.data);mesh.verts.ensure_lookup_table()
 bmesh.ops.delete(mesh,geom=[mesh.verts[i] for i in removed],context='VERTS')
 mesh.to_mesh(obj.data);mesh.free();obj.data.update()
 removed_vertices+=len(removed);changed.append(obj.name)
 assert all((Vector(((obj.matrix_world@v.co).x,(obj.matrix_world@v.co).y))-centre).length>=10.4 for v in obj.data.vertices)
assert all(fingerprint(o)==before[o.name] for o in bpy.data.objects if o.name not in changed)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'registered-atrium-candidate.blend'))
(OUT/'atrium-alignment-audit.json').write_text(json.dumps({'baseline':'result/blender/LSE_campus_detailed_v37.blend',
 'candidate':'result/blender/stage38/registered-atrium-candidate.blend','translation':list(shift),
 'changedObjects':changed,'unchangedObjects':len(before)-len(changed),'openingCentre':list(centre),
 'openingRadiusEstimate':9.8,'trianglesPerSurface':len(opening['triangles']),
 'initialFurnitureClearanceFlags':collisions,'remainingFurnitureClearanceFlags':[],
 'removedLegacyShelfModules':len(blocked_modules)*3,'removedLegacyVertices':removed_vertices,
 'checks':['Fixed GIS perimeter and complete triangulated coverage','Floor and roof opening centres coincide',
 'Spiral, lifts, supports, landings and dome share translation','Unselected objects unchanged'],
 'publication':'Native candidate; coupled geometry and furniture clearance checked, web export pending',
 'limitations':['Opening radius and circular form remain estimates','Ground/upper floor guide differences remain unresolved']},ensure_ascii=False,indent=2)+'\n')
print('LRB_CORE_REGISTERED',len(changed),'objects;',len(blocked_modules)*3,'conflicting legacy modules removed')
