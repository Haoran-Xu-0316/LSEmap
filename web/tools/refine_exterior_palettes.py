"""Edition 26: source-level exterior finishes, including the user's CBG palette.

Colours are visual estimates; CBG red/orange is explicit user direction.
Reference photographs remain private. No geometry or room layout is changed.
"""
from pathlib import Path
import array, hashlib, json, math, re
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage26';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v25.blend'))

def geometry(obj):
    data=array.array('f',[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get('co',data)
    indices=array.array('i',[0])*len(obj.data.loops);obj.data.loops.foreach_get('vertex_index',indices)
    return hashlib.sha256(data.tobytes()+indices.tobytes()).hexdigest()
before={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
changes=[];cache={}
def copy_material(old,code):
    key=(old.name,code)
    if key not in cache:
        new=old.copy();new.name=old.name+'_palette26_'+code;cache[key]=new
    return cache[key]
def colour(mat,value):
    mat.diffuse_color=(*value,1)
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*value,1)
    return p
for code in ['MAR','SAW','CBG']:
    for obj in bpy.data.collections[code+'_EXTERIOR'].all_objects:
        if obj.type!='MESH':continue
        for index,old in enumerate(list(obj.data.materials)):
            name=old.name
            if '_palette26_' in name:continue
            kind=None
            if code=='MAR':
                if re.search('MAR_D3_concrete|MAR15_stone',name):kind='concrete'
                if re.search('MAR_D3_glass|MAR15_glass|D2_glass',name):kind='glass'
            if code=='SAW':
                if re.search(r'D2_brick(?:_\d+)?$',name):kind='brick'
                if re.search('D2_glass$',name):kind='glass'
            if code=='CBG':
                if 'ochre_anodised_blade' in name:kind='blade'
                if 'clear_green_glass' in name:kind='glass'
            if not kind:continue
            m=copy_material(old,code);obj.data.materials[index]=m
            if kind=='concrete':
                colour(m,(.62,.61,.57))
                for node in m.node_tree.nodes:
                    if node.type=='VALTORGB':
                        node.color_ramp.elements[0].color=(.60,.59,.55,1);node.color_ramp.elements[-1].color=(.64,.63,.59,1)
            if kind=='glass':
                rgb,opacity={'MAR':((.095,.17,.22),.86),'CBG':((.20,.32,.34),.56),'SAW':((.18,.25,.26),.62)}[code]
                p=colour(m,rgb);p.inputs['Roughness'].default_value=.13;m['webOpacity']=opacity
            if kind=='brick':
                factors=(1.10,.82,1.08)
                colour(m,tuple(old.diffuse_color[i]*factors[i] for i in range(3)))
                for node in m.node_tree.nodes:
                    if node.type=='TEX_BRICK':
                        for socket in ['Color1','Color2']:
                            original=next(n for n in old.node_tree.nodes if n.type=='TEX_BRICK')
                            node.inputs[socket].default_value=tuple(original.inputs[socket].default_value[i]*factors[i] for i in range(3))+(1,)
                        node.inputs['Mortar'].default_value=(.40,.36,.31,1)
            if kind=='blade':
                p=colour(m,(.66,.026,.018));p.inputs['Metallic'].default_value=.24;p.inputs['Roughness'].default_value=.38
                orange=m.copy();orange.name='CBG_D_orange_blade_returns_palette26';colour(orange,(.80,.19,.035))
                obj.data.materials.append(orange);orange_index=len(obj.data.materials)-1
                axis=Vector((math.cos(math.radians(58)),math.sin(math.radians(58)),0))
                normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
                for face in obj.data.polygons:
                    if face.material_index==index and abs((normal_matrix@face.normal).normalized().dot(axis))<.7:face.material_index=orange_index
            changes.append({'code':code,'object':obj.name,'original':name,'material':m.name,'kind':kind})
after={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
assert before==after,'Palette work changed geometry'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v26.blend'))
(OUT/'palette-audit.json').write_text(json.dumps({'unchangedMeshes':len(before),'changes':changes,'scope':'Exterior material assignments only; CBG red/orange per explicit user request. MAR and SAW photo-guided visual estimates.'},indent=2)+'\n')
print('PALETTE_COMPLETE',len(changes),'material assignments;',len(before),'unchanged mesh geometries')
