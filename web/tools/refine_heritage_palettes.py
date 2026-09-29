"""Edition 27: photo-guided SAL brick, OLD limestone and KGS entrance stone.

Visual estimates from locally attributed photographs, not measured albedos.
Copy exterior materials so neither other buildings nor room studies are recoloured.
"""
from pathlib import Path
import array, hashlib, json
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage27';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v26.blend'))
def geometry(obj):
    values=array.array('f',[0])*(3*len(obj.data.vertices));obj.data.vertices.foreach_get('co',values)
    indices=array.array('i',[0])*len(obj.data.loops);obj.data.loops.foreach_get('vertex_index',indices)
    return hashlib.sha256(values.tobytes()+indices.tobytes()).hexdigest()
before={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
changes=[];copies={}
for code in ['SAL','OLD','KGS']:
    for obj in bpy.data.collections[code+'_EXTERIOR'].all_objects:
        if obj.type!='MESH':continue
        for index,old in enumerate(list(obj.data.materials)):
            colour=None;kind=None
            if code=='SAL' and 'Ochre_red_stock_brick' in old.name:
                colour=(.53,.185,.095);kind='brick'
            if code=='OLD':
                if 'Portland_stone' in old.name:colour=(.62,.60,.55);kind='stone'
                if 'Cut_stone_edges' in old.name:colour=(.72,.70,.64);kind='stone'
            if code=='KGS' and any(part in obj.name for part in ['portal_', 'entrance_steps']):
                if 'HERITAGE09_stone' in old.name or 'HERITAGE09_trim' in old.name:
                    colour=(.41,.43,.43);kind='granite'
            if colour is None:continue
            key=(code,old.name)
            if key not in copies:
                material=old.copy();material.name=old.name+'_palette27_'+code
                material.diffuse_color=(*colour,1)
                nodes=material.node_tree.nodes;links=material.node_tree.links
                principled=nodes.get('Principled BSDF')
                principled.inputs['Base Color'].default_value=(*colour,1)
                principled.inputs['Roughness'].default_value=.84 if kind=='brick' else .72
                if kind=='brick':
                    for node in nodes:
                        if node.type=='TEX_BRICK':
                            node.inputs['Color1'].default_value=(*colour,1)
                            node.inputs['Color2'].default_value=tuple(v*.80 for v in colour)+(1,)
                            node.inputs['Mortar'].default_value=(.32,.28,.24,1)
                elif kind=='stone':
                    for node in nodes:
                        if node.type=='VALTORGB':
                            node.color_ramp.elements[0].color=tuple(v*.97 for v in colour)+(1,)
                            node.color_ramp.elements[-1].color=tuple(v*1.025 for v in colour)+(1,)
                else:
                    texture=nodes.new('ShaderNodeTexNoise');texture.inputs['Scale'].default_value=16
                    ramp=nodes.new('ShaderNodeValToRGB')
                    ramp.color_ramp.elements[0].color=(.38,.40,.40,1)
                    ramp.color_ramp.elements[1].color=(.44,.46,.46,1)
                    links.new(texture.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],principled.inputs['Base Color'])
                    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.2;bump.inputs['Distance'].default_value=.002
                    links.new(texture.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],principled.inputs['Normal'])
                copies[key]=material
            obj.data.materials[index]=copies[key]
            changes.append({'code':code,'object':obj.name,'original':old.name,'material':copies[key].name,'kind':kind})
after={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
assert before==after
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v27.blend'))
(OUT/'palette-audit.json').write_text(json.dumps({'unchangedMeshes':len(before),'changes':changes,'evidence':{'SAL':'SAL_geograph_6108067_01','OLD':'OLD_old_webbyates_01','KGS':'KGS_07; lse_estate_008'},'scope':'Exterior finishes only. CLM portal photo reviewed; existing tone retained. Dimensions and whole-building accuracy not certified.'},indent=2)+'\n')
print('PALETTE_COMPLETE',len(changes),'assignments;',len(before),'unchanged geometries')
