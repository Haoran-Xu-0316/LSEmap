"""Warm SAL's photographed principal-elevation stock brick independently.

Two archived built photographs support warm orange/buff brick rather than the
legacy dark terracotta finish. Colours remain visual estimates, not calibrated
albedo or a current survey. Geometry, UVs, mortar and brick scale are retained.
Unphotographed rear and secondary proxy finishes are deliberately retained.
"""
import bpy
PREFIX='SAL183_'
TARGETS=(
    'SAL_Pilaster_brick_cores','SAL_Chimney_stacks',
    'SAL_Tower_upper_front_masonry','SAL_Boundary_pier_brick',
    'SAL_NEXT_GLAZING149_opened_six_gable_masonry',
    'SAL_NEXT_GLAZING149_opened_left_gable_frontbrick',
)
COLOUR=(.53,.285,.14,1)

def apply_sal_palette183():
    if bpy.data.objects.get(PREFIX+TARGETS[0]):
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[]}
    cache={};records=[]
    for name in TARGETS:
        source=bpy.data.objects[name];assert not source.hide_render
        target=source.copy();target.data=source.data.copy();target.name=PREFIX+name
        target.data.name=target.name
        for collection in source.users_collection:collection.objects.link(target)
        bindings=[]
        for slot,old in enumerate(list(target.data.materials)):
            if not old or 'Ochre_red_stock_brick' not in old.name:continue
            if old.name not in cache:
                material=old.copy();material.name=PREFIX+old.name
                material.diffuse_color=COLOUR
                shader=material.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=COLOUR
                for node in material.node_tree.nodes:
                    if node.type=='TEX_BRICK':
                        node.inputs['Color1'].default_value=COLOUR
                        node.inputs['Color2'].default_value=tuple(c*.8 for c in COLOUR[:3])+(1,)
                material['colourBasis']='Warm stock brick estimated from two undated built photos; mortar and scale retained'
                cache[old.name]=material
            target.data.materials[slot]=cache[old.name]
            bindings.append({'slot':slot,'source':old.name,'target':cache[old.name].name})
        assert bindings,name
        source.hide_render=True;source.hide_set(True)
        target.hide_render=False;target.hide_set(False)
        records.append({'source':name,'target':target.name,'bindings':bindings})
    return {'alreadyApplied':False,'code':'SAL','version':183,
      'addedObjects':[r['target']for r in records],'archivedObjects':[r['source']for r in records],'changedObjects':[],
      'records':records,'colour':COLOUR,
      'scope':'Principal brick pilasters, chimney stacks, front towers, boundary piers and registered gable surfaces; geometry and glass retained. Unseen rear and secondary proxies unchanged.',
      'sources':['https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/32L-300x400.jpg'],
      'photoCaptureDates':'unknown','calibratedColour':False}
