"""Audit only three MAR podium panes before choosing a local glass finish.
Run in Blender. Comparison edits exist in memory only; no campus file is saved.
"""
import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/mar_glass_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v133.blend'
if not BASE.exists():
    BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda path:int(path.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
ring=next(b['rings'][0]for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b.get('code')=='MAR');p,q=[Vector((*ring[k],0))for k in [13,0]];u=(q-p).normalized();n=Vector((-u.y,u.x,0))
source=bpy.data.objects['MAR_V115_retained_V104_recessed_window_glass'];windows=[]
for face in source.data.polygons:
 m=source.data.materials[face.material_index]
 if 'MAR_V104_podium_glass' in m.name:
  vs=[source.matrix_world@source.data.vertices[i].co for i in face.vertices];xs=[(v-p).dot(u)for v in vs];zs=[v.z for v in vs];ds=[(v-p).dot(n)for v in vs]
  windows.append({'face':face.index,'x':[min(xs),max(xs)],'z':[min(zs),max(zs)],'depth':[min(ds),max(ds)]})
assert len(windows)==3,len(windows)
visible=set()
def walk(c):
 if c.hide_render:return
 visible.update(o for o in c.objects if not o.hide_render)
 for child in c.children:walk(child)
walk(scene.collection)
trees=[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],all_triangles=False))for o in visible if o.type=='MESH' and len(o.data.polygons)]
checks=[]
for wi,w in enumerate(windows):
 for fx,fz in [(.25,.25),(.75,.25),(.25,.75),(.75,.75)]:
  x=w['x'][0]+(w['x'][1]-w['x'][0])*fx;z=w['z'][0]+(w['z'][1]-w['z'][0])*fz;start=p+u*x+n*(w['depth'][1]+.6)+Vector((0,0,z));hits=[]
  for name,tree in trees:
   hit=tree.ray_cast(start,-n,60)
   if hit[0]is not None:hits.append({'object':name,'distance':hit[3],'point':list(hit[0])})
  hits.sort(key=lambda h:h['distance']);assert hits and hits[0]['object']==source.name,(wi,hits[:2]);checks.append({'window':wi,'sample':[fx,fz],'glassFirstSurface':hits[0],'behindPane':hits[1:5]})
audit={'baseline':str(BASE),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'objectCount':len(bpy.data.objects),'sourceObject':source.name,'windows':windows,'firstSurfaceAndBehindChecks':checks,'fullModelSaved':False,'comparisonAlpha':.55,'componentCreated':False}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Show only current MAR exterior plus its render-visible room geometry. Other
# buildings remain excluded from the comparison image, but included in ray audit.
for o in scene.objects:
 if o.type=='MESH' and not o.name.startswith('MAR'):o.hide_render=True
xmin=min(w['x'][0]for w in windows);xmax=max(w['x'][1]for w in windows);focus=p+u*((xmin+xmax)/2)+Vector((0,0,6.5));cd=bpy.data.cameras.new('MAR_GLASS_NEXT_COMPARE');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+n*50+Vector((0,0,.5));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=xmax-xmin+4;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1300;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.render.filepath=str(OUT/'current-opaque-panes.png');bpy.ops.render.render(write_still=True)
mat=next(m for m in source.data.materials if 'MAR_V104_podium_glass' in m.name).copy();mat.name='MAR_GLASS_NEXT_comparison_only';mat.surface_render_method='DITHERED';mat.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.55
for index,m in enumerate(source.data.materials):
 if 'MAR_V104_podium_glass' in m.name:source.data.materials[index]=mat
scene.render.filepath=str(OUT/'comparison-alpha055.png');bpy.ops.render.render(write_still=True)
print('MAR_THREE_GLASS_COMPARISON',json.dumps([(c['window'],[(h['object'],round(h['distance'],2))for h in c['behindPane'][:2]])for c in checks]));bpy.ops.wm.quit_blender()
