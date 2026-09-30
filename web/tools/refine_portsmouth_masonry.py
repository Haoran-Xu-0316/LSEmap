"""Refine POR masonry and photographed roof stacks in Blender's Text Editor.
Native50 remains intact; undated estate photography is not a current survey.
The footprint and existing window/shop geometry remain unchanged.
"""
from pathlib import Path
import array,hashlib,json,sys,math
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage51';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v50.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
collection=bpy.data.collections['POR_EXTERIOR'];originals=list(collection.all_objects)
def fingerprint(obj):
    digest=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        digest.update(array.array('f',[value for vertex in obj.data.vertices for value in vertex.co]).tobytes())
        if obj.data.uv_layers.active:digest.update(array.array('f',[value for loop in obj.data.uv_layers.active.data for value in loop.uv]).tobytes())
        digest.update(str([mat.name if mat else '' for mat in obj.data.materials]).encode())
    return digest.hexdigest()
others=[obj for obj in bpy.data.objects if obj not in originals]
before={obj.name:fingerprint(obj)for obj in others}
# Copy material data before changing colours, so other buildings retain their palette.
colours={'brick':(.28,.21,.14),'redbrick':(.34,.115,.075),'cream':(.71,.68,.58),'frame':(.76,.75,.69),'slate':(.15,.17,.17)}
replacements={};wall_objects=[];hidden=[];updated_signs=[]
for obj in originals:
    if obj.type!='FONT':continue
    if obj.data.body=='ALPHA BOOKS':
        obj.data=obj.data.copy();obj.data.body='The Gilded Acorn';obj.data.size=min(obj.data.size,.24);updated_signs.append(obj.name)
    elif obj.data.body=='α':
        obj.hide_render=True;obj.hide_set(True)
for obj in originals:
    if any(part in obj.name for part in ['brick_stack','stack_coping']):
        obj.hide_render=True;obj.hide_set(True);hidden.append(obj.name);continue
    if obj.type!='MESH' or obj.hide_render:continue
    brick_slots=[]
    for index,mat in enumerate(obj.data.materials):
        if not mat or not mat.name.startswith('POR14_'):continue
        key=mat.name.removeprefix('POR14_')
        if key not in colours:continue
        if mat.name not in replacements:
            copy=mat.copy();copy.name='POR_V51_'+key;copy.diffuse_color=(*colours[key],1)
            shader=copy.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value=copy.diffuse_color
            for node in copy.node_tree.nodes:
                if node.type=='TEX_BRICK':
                    node.inputs['Color1'].default_value=copy.diffuse_color
                    node.inputs['Color2'].default_value=tuple(c*.82 for c in colours[key])+(1,)
                    node.inputs['Mortar'].default_value=(.28,.26,.22,1)
            replacements[mat.name]=copy
        obj.data=obj.data.copy() if obj.data.users>1 else obj.data
        obj.data.materials[index]=replacements[mat.name]
        if key in {'brick','redbrick'}:brick_slots.append(index)
    if not brick_slots:continue
    # World-height UVs stop box winding from rotating brick courses vertically.
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='SurfaceUV')
    for polygon in obj.data.polygons:
        if polygon.material_index not in brick_slots:continue
        normal=obj.matrix_world.to_3x3()@polygon.normal
        tangent=Vector((-normal.y,normal.x,0));vertical=abs(normal.z)<.9
        if vertical:tangent.normalize()
        for loop_index in polygon.loop_indices:
            point=obj.matrix_world@obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=(point.dot(tangent),point.z) if vertical else (point.x,point.y)
    wall_objects.append(obj.name)
materials.clear()
for key in ['brick','redbrick','slate']:materials[key]=bpy.data.materials['POR_V51_'+key]
metal=bpy.data.materials.new('POR_V51_roof_metal');metal.use_nodes=True
metal.diffuse_color=(.045,.055,.05,1);metal.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=metal.diffuse_color
materials['metal']=metal
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='POR')
# The Sheffield Street faces are redder than the sunlit Portsmouth stock brick.
red_field=bpy.data.materials['POR_V51_brick'].copy();red_field.name='POR_V51_weathered_red'
red_field.diffuse_color=(.29,.145,.105,1)
red_field.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=red_field.diffuse_color
for node in red_field.node_tree.nodes:
    if node.type=='TEX_BRICK':
        node.inputs['Color1'].default_value=red_field.diffuse_color
        node.inputs['Color2'].default_value=(.24,.115,.079,1)
def nearest_wall(point):
    distances=[]
    for index,wall in enumerate(profile['walls']):
        p,q=Vector(wall['p']),Vector(wall['q']);span=q-p
        closest=p+span*max(0,min(1,(Vector(point.xy)-p).dot(span)/span.length_squared))
        distances.append(((Vector(point.xy)-closest).length,index))
    return min(distances)[1]
red_faces=0
for obj in originals:
    if obj.type!='MESH' or obj.hide_render:continue
    indices=[i for i,mat in enumerate(obj.data.materials)if mat and mat.name=='POR_V51_brick']
    if not indices:continue
    obj.data.materials.append(red_field);red_index=len(obj.data.materials)-1
    for polygon in obj.data.polygons:
        if polygon.material_index in indices and nearest_wall(obj.matrix_world@polygon.center)in {0,5,6}:
            polygon.material_index=red_index;red_faces+=1
groups={};stacks=[]
# These two visible stack locations are approximate registrations to the GIS roof.
for edge,x,width,depth,height in [(1,3.82,.74,.64,1.82),(5,1.08,.62,.65,2.08)]:
    facade=Facade(profile,profile['walls'][edge],groups)
    facade.box('photographed_stack','brick',x,14.30+height/2,width,height,depth,-.39)
    facade.box('stack_head_course','redbrick',x,14.30+height-.12,width+.07,.12,depth+.06,-.39)
    facade.box('stack_cap','slate',x,14.30+height+.025,width+.15,.09,depth+.15,-.39)
    stacks.append({'edge':edge,'x':x,'height':height,'centre':list(facade.point(x,14.30+height/2,-.39))})
    if edge==5:
        for dx in [-.19,.19]:
            centre=facade.point(x+dx,14.30+height+.64,-.39)
            ring=[];segments=12
            for z in [-.56,.56]:
                for i in range(segments):
                    angle=i*math.tau/segments
                    ring.append((centre[0]+.055*math.cos(angle),centre[1]+.055*math.sin(angle),centre[2]+z))
            # Hollow pipes: no false solid caps across the visible openings.
            facade.group('open_roof_flues','metal').add(ring,[(i,(i+1)%segments,(i+1)%segments+segments,i+segments)for i in range(segments)])
added=[]
for geometry in groups.values():
    geometry.name=geometry.name.replace('POR_D5_','POR_V51_');obj=geometry.finish();added.append(obj.name)
    if geometry.material.name in {'POR_V51_brick','POR_V51_redbrick'}:
        uv=obj.data.uv_layers.active.data
        for polygon in obj.data.polygons:
            tangent=Vector((-polygon.normal.y,polygon.normal.x,0));vertical=abs(polygon.normal.z)<.9
            if vertical:tangent.normalize()
            for index in polygon.loop_indices:
                point=obj.data.vertices[obj.data.loops[index].vertex_index].co
                uv[index].uv=(point.dot(tangent),point.z) if vertical else (point.x,point.y)
for layer in bpy.context.scene.view_layers:layer.update()
changed=[obj.name for obj in others if fingerprint(obj)!=before[obj.name]]
assert not changed,changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage50'/name).read_bytes())
record=json.loads((ROOT/'result/blender/stage16/portsmouth/portsmouth-manifest.json').read_text())['buildings'][0]
record['scope']='Photo-guided corner bookshop with neutral pale joinery, warm mixed masonry and two photographed roof stacks. Undated image; window geometry retained, roof registration estimated, Current bookshop name confirmed by LSE facilities guide; exact lettering and unseen interior unverified.'
record['components']=sum(g.parts for g in groups.values())
(OUT/'por-manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
audit={'version':51,'baseline':50,'changedOtherObjects':changed,'hiddenStackArchives':hidden,'metricWallUVObjects':wall_objects,'visibleStackCount':len(stacks),'openFlueCount':2,'stacks':stacks,'addedObjects':added,'palette':colours,'redFieldFaces':red_faces,'sourcePage':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','reference':record['reference'],'sourceDate':None,'updatedSigns':updated_signs,'bookshopName':'The Gilded Acorn','bookshopSourcePage':'https://info.lse.ac.uk/current-students/estates-division/facilities-guide/shops-banks-and-post-offices','bookshopSourceImage':'data/collections/portsmouth-2026/gilded-acorn-official.jpg','limitations':['Photo capture date unknown; not a current-condition survey','Two visible stacks only; hidden roof, stack heights and positions estimated','Current official bookshop photo is undated; exact logo not extrapolated','No attributed interior material; no interior invented']}
(OUT/'por-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v51.blend'))
print('PORTSMOUTH_MASONRY_SAVED',len(wall_objects),len(added))
