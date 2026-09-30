"""Build the officially attributed Three Tuns ground-floor plan and window sign.
An independent historical cutaway, not a reconstruction of the 2026 refurbishment.
"""
from pathlib import Path
import bpy,json,sys,math,hashlib,array
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage48'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
originals=list(bpy.data.objects)
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes())
 return h.hexdigest()
before={o.name:fingerprint(o)for o in originals}
collection=bpy.data.collections.new('SAW_THREE_TUNS_study');scene=bpy.data.scenes.new('ROOM48_THREE_TUNS');scene.collection.children.link(collection)
collection['roomSample']=True;collection['roomLabel']='Three Tuns入口与2014平面'
bpy.context.window.scene=scene
palette={'floor':(.29,.28,.25),'wall':(.70,.69,.64),'wood':(.36,.18,.078),'glass':(.30,.43,.42),'letter':(.77,.85,.82),'metal':(.12,.13,.13)}
materials.clear()
for key,color in palette.items():
 m=bpy.data.materials.new('SAW_V48_TUNS_'+key);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.70
 if key=='glass':p.inputs['Roughness'].default_value=.20;p.inputs['Metallic'].default_value=.12
 materials[key]=m
batches={}
def batch(key):
 if key not in batches:
  g=Geometry('SAW','tuns_'+key,key);g.collection=collection;g.name='SAW_V48_TUNS_'+key;batches[key]=g
 return batches[key]
def box(key,xyz,dimensions):batch(key).box(xyz,dimensions)
# Trace the pink Three Tuns zone of the official 2014 guide, PDF page32.
# The source gives topology; the pixel-to-metre scale remains estimated.
outline=[(864,650),(956,632),(980,578),(1248,610),(1178,878),(1270,902),(1238,1036),(945,960)]
points=[((x-1040)*.03,(810-y)*.03,0)for x,y in outline]
batch('floor').add(points,[tuple(reversed(range(len(points))))])
for i in [2,3,5,6]:
 a=Vector(points[i]);b=Vector(points[(i+1)%len(points)]);d=b-a;middle=(a+b)/2
 batch('wall').box((middle.x,middle.y,1.40),(d.length,.14,2.8),math.atan2(d.y,d.x))
# Photo-supported timber window lettering. Door/window dimensions are estimates;
# it is presented as an entrance sample, not geolocated furniture inside the bar.
y=-7.50
box('glass',(0,y,1.43),(2.25,.035,2.58))
for side in [-1,1]:
 box('wood',(side*1.17,y,1.43),(.11,.17,2.78));box('wood',(0,y,.08 if side==-1 else 2.78),(2.45,.18,.12))
 box('wood',(side*1.13,y-.10,1.43),(.025,.035,2.55))
font=bpy.data.fonts.load('/System/Library/Fonts/Supplemental/Arial.ttf')
for word,z,size in [('THE',2.10,.38),('THREE',1.38,.56),('TUNS',.65,.56)]:
 c=bpy.data.curves.new('SAW_V48_TUNS_'+word,'FONT');c.body=word;c.font=font;c.size=size;c.align_x='CENTER';c.extrude=.0008;c.materials.append(materials['letter'])
 o=bpy.data.objects.new(c.name,c);collection.objects.link(o);o.location=(0,y-.026,z);o.rotation_euler=(math.pi/2,0,0)
for g in batches.values():g.finish()
for layer in scene.view_layers:layer.update()
assert all(fingerprint(o)==before[o.name]for o in originals)
cam=bpy.data.objects.new('ROOM48_THREE_TUNS_camera',bpy.data.cameras.new('ROOM48_THREE_TUNS_camera'));scene.collection.objects.link(cam)
cam.location=(1,-12,2.8);target=(0,-7.5,1.4);cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scope='依据LSE2014使用指南第32页复原Three Tuns首层区域轮廓，并按官方餐饮照片制作木框玻璃标识。尺寸和入口在样本内的位置估算；未添加无照片支持的吧台家具，也不代表2026翻新后的内部。'
record={'code':'SAW','id':'saw-three-tuns','label':'Three Tuns入口与2014平面','camera':list(cam.location),'target':list(target),'scope':scope,'collection':collection.name,'sources':[{'path':'data/documents/saw_occupants_guide_2014.pdf','pages':[32],'supports':'Named ground-floor bar footprint'},{'path':'data/collections/public-realm-2026/bars/three-tuns-reference.jpg','url':'https://info.lse.ac.uk/current-students/estates-division/Assets/Images/3-Tuns.jpg','supports':'Timber frame and three-line window lettering; capture date unknown'}]}
p=OUT/'room-spaces.json';d=json.loads(p.read_text());d['version']=48;d['spaces'].append(record);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
(OUT/'three-tuns-audit.json').write_text(json.dumps({'addedMeshes':[g.name for g in batches.values()],'originalGeometryPreserved':len(originals),'sourceScope':scope},ensure_ascii=False,indent=2)+'\n')
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v48.blend'))
print('THREE_TUNS_STUDY_SAVED')
