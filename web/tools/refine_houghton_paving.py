"""Replace Houghton Street with small grey setts observed in the supplied photo.
Read the prepared local plan; run in Blender's Text Editor. Dimensions estimated.
"""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
r=json.loads((ROOT/'result/blender/stage48/houghton-plan.json').read_text())
old=bpy.data.objects['SITE_V47_Houghton_Street'];old.hide_render=True;old.hide_set(True)
vertices=[];faces=[];indices=[]
materials=[bpy.data.materials['SITE_V47_'+name]for name in ['grout',*[f'slab_{i}'for i in range(5)],'edge_1','edge_2']]
def add(triangles,z,index):
 for triangle in triangles:
  offset=len(vertices);vertices.extend((p[0],p[1],p[2]if len(p)>2 else z)for p in triangle);faces.append((offset,offset+1,offset+2));indices.append(index)
add(r['base'],.040,0)
for tile in r['tiles']:add(tile['top'],.050,tile['shade']+1)
for border in r['borders']:
 add(border['top'],.050,border['shade']+6);add(border['bevel'],.047,border['shade']+6)
mesh=bpy.data.meshes.new('SITE_V48_Houghton_Street');mesh.from_pydata(vertices,[],faces)
for m in materials:mesh.materials.append(m)
for p,i in zip(mesh.polygons,indices):p.material_index=i
mesh.update();obj=bpy.data.objects.new(mesh.name,mesh);bpy.data.collections['00_SITE'].objects.link(obj)
obj['scope']=r['scope'];obj['paverCount']=len(r['tiles'])
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
print('HOUGHTON_SETTS_SAVED',len(r['tiles']))
