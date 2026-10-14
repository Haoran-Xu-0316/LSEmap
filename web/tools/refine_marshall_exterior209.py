"""Correct MAR's painted-blue glazing approximation without opening empty rooms.

Run in Blender. Completed-building photographs distinguish reflected sky from
intrinsic blue glass. Seven independently owned copies retain all source mesh,
UV, opacity, transmission and existing room geometry. No campus is overwritten.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/mar-exterior209'
BASE=ROOT/'result/blender/LSE_campus_detailed_v208.blend'
BASE_SHA='da07d198617bd18bceaece14682b9d0995a288655b6c5aa0ac8d2765e883b92c'
COMPONENT=OUT/'marshall-exterior209-component.blend'
COLLECTION='MAR_EXTERIOR'
SOURCES=['MAR187_podium_window_glass','MAR188_middle_glass','MAR188_north_glass',
         'MAR188_trim_MAR174_retained_loggia_12','MAR_EXTERIOR168_wing_dielectric_glass',
         'MAR_D5_left_recess_glazing_pane','MAR_D5_right_recess_glazing_pane']
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene,set_layer_hidden
from refine_61a_exterior208 import shape_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint
from refine_saw_exterior206 import optics
from refine_mar_exterior174 import world


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()



def analyse_backing():
    """Face-centre and quarterface probes against existing opaque MAR geometry."""
    from mathutils.bvhtree import BVHTree
    objects=set(bpy.data.collections[COLLECTION].all_objects)|set(bpy.data.collections['MAR_PUBLIC_INTERIOR_study'].all_objects)
    vertices,faces,owners=[],[],[]
    for obj in objects:
        if obj.hide_render or obj.type!='MESH':continue
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        for face in obj.data.polygons:
            material=obj.data.materials[face.material_index] if len(obj.data.materials)>face.material_index else None
            if material and ('glass' in material.name.lower() or 'dielectric' in material.name.lower()):continue
            faces.append(tuple(offset+i for i in face.vertices));owners.append(obj.name)
    tree=BVHTree.FromPolygons(vertices,faces,all_triangles=False);rows=[]
    from refine_mar_exterior174 import local
    for name in ['MAR188_north_glass','MAR188_middle_glass','MAR187_podium_window_glass','MAR_EXTERIOR168_wing_dielectric_glass']:
        obj=bpy.data.objects[name]
        for face in obj.data.polygons:
            normal=(obj.matrix_world.to_3x3()@face.normal).normalized();centre=obj.matrix_world@face.center
            points=[centre]+[centre.lerp(obj.matrix_world@obj.data.vertices[i].co,.5)for i in face.vertices]
            hits=[]
            for point in points:
                hit=tree.ray_cast(point-normal*.065,-normal,40)
                hits.append(dict(owner=owners[hit[2]]if hit[2] is not None else None,distance=hit[3]))
            rows.append(dict(source=name,face=face.index,centre=list(local(centre)),normal=list(normal),hits=hits))
    # Wing shells also contain edge faces; no connected-pane transparency
    # decision is inferred from those per-face hits.
    (OUT/'backing-rays.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def render(label):
    """Identical lighting before/after; front sun avoids compensating backlight."""
    scene=bpy.data.scenes.new('MAR209_REVIEW_'+label)
    scene.collection.children.link(bpy.data.collections[COLLECTION])
    scene.collection.children.link(bpy.data.collections['MAR_PUBLIC_INTERIOR_study'])
    bpy.context.window.scene=scene
    background=bpy.data.worlds.new('MAR209_REVIEW_WORLD_'+label);background.use_nodes=True
    background.node_tree.nodes['Background'].inputs[0].default_value=(.68,.74,.8,1)
    background.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=background
    sun=bpy.data.objects.new('MAR209_REVIEW_SUN_'+label,bpy.data.lights.new('MAR209_REVIEW_SUN_'+label,'SUN'))
    scene.collection.objects.link(sun);sun.data.energy=2;sun.data.angle=.16
    sun.location=world(-30,60,60)
    sun.rotation_euler=(world(-3,0,10)-sun.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.objects.new('MAR209_REVIEW_CAMERA_'+label,bpy.data.cameras.new('MAR209_REVIEW_CAMERA_'+label))
    scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_end=500
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=1100;scene.render.resolution_y=950;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
    cameras=[]
    for name,target,position,scale in [('whole',(-3,0,21),(-24,100,42),69),('north-windows',(-15,18.8,23),(-15,82,26),30)]:
        camera.location=world(*position);camera.rotation_euler=(world(*target)-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=scale;scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
        cameras.append(dict(view=name,target=list(world(*target)),position=list(camera.location),scale=scale))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in [sun,camera]:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(scene)
    return cameras


def main():
    OUT.mkdir(exist_ok=True);assert sha(BASE)==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    originals={o.name:object_fingerprint(o)for o in bpy.data.objects}
    material_states={m.name:material_fingerprint(m)for m in bpy.data.materials}
    visibility={o.name:o.hide_render for o in bpy.data.objects}
    analyse_backing()
    cameras=render('before');owned=[];changes=[];copies={}
    for i,name in enumerate(SOURCES):
        source=bpy.data.objects[name];assert not source.hide_render and source.parent is None
        obj=source.copy();obj.data=source.data.copy();obj.name='MAR209_neutral_glass_'+str(i).zfill(2)
        obj.data.name=obj.name;obj['originalObject']=name;obj['webGeometrySource']=name;obj['destinationCollection']=COLLECTION
        bpy.data.collections[COLLECTION].objects.link(obj);slots=[]
        for slot,old in enumerate(source.data.materials):
            if not old:continue
            shader=old.node_tree.nodes.get('Principled BSDF');colour=list(shader.inputs['Base Color'].default_value)
            if colour[2]-colour[0]<.05:continue
            if old.name not in copies:
                new=old.copy();new.name='MAR209_neutral_glass_'+old.name
                luminance=sum(x*w for x,w in zip(colour,(.2126,.7152,.0722)))
                neutral=tuple(.25*x+.75*luminance for x in colour[:3])+(colour[3],)
                n=new.node_tree.nodes['Principled BSDF'];n.inputs['Base Color'].default_value=neutral
                n.inputs['Roughness'].default_value=.12;new.diffuse_color=neutral
                new['opticsBasis']='Built photographs show sky reflections, not a uniformly blue substrate. Chroma reduced75percent at identical linear luminance; not measured glass.'
                new['proxyPolicy']='Original alpha/transmission retained. North upper/middle/podium inward probes show no complete near-room backing; no empty envelope is exposed.'
                assert abs(sum(x*w for x,w in zip(neutral,(.2126,.7152,.0722)))-luminance)<1e-7
                copies[old.name]=new
            obj.data.materials[slot]=copies[old.name]
            before=optics(old);after=optics(copies[old.name])
            for key in ['Alpha','Transmission Weight','webOpacity','Metallic','IOR']:assert before[key]==after[key],(name,key)
            slots.append(dict(slot=slot,before=before,after=after,sourceMaterial=old.name,ownedMaterial=copies[old.name].name))
        assert slots and shape_fingerprint(obj)==shape_fingerprint(source)
        changes.append(dict(source=name,owned=obj.name,originalObject=name,destinationCollection=COLLECTION,materialChanges=slots))
        owned.append(obj)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
    fingerprints={o.name:object_fingerprint(o)for o in owned}
    bpy.data.libraries.write(str(COMPONENT),set(owned),fake_user=True,compress=True)
    audit=dict(baselineSha256=BASE_SHA,component=str(COMPONENT.relative_to(ROOT)),componentSha256=sha(COMPONENT),
        targetCollection=COLLECTION,destinationCollection=COLLECTION,retainNewMaterials=True,
        addedObjects=[o.name for o in owned],archivedObjects=SOURCES,changes=changes,cameras=cameras,
        allOriginalGeometryUVBindingsPreserved=True,allOriginalMaterialsPreserved=True,
        improvement='Remove excessive intrinsic cyan at retained linear luminance and source opacity. Existing transparent entry/hall glass and all concrete unchanged.',
        opaqueProxyPolicy='No transmission or opacity reduction. North67upper/52middle/onepodium faces lack complete5point near3m room backing.',
        backingRayReport='result/blender/mar-exterior209/backing-rays.json',
        lightingDiagnosis=dict(concreteLinearRGB=[.69,.67,.625],roughness=.85,metallic=0,
            conclusion='North-facing default production gallery is backlit under its fixed sun. Do not increase pale concrete albedo to compensate.',publicRendererChanged=False),
        references=[dict(path='data/collections/architecture_round5/images/MAR/MAR_mar_kane_'+n+'.jpg',sha256=sha(ROOT/('data/collections/architecture_round5/images/MAR/MAR_mar_kane_'+n+'.jpg')),url='https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',rechecked='2026-10-15',captureDate='unknown')for n in ['02','03','05']],
        limitations=['Glass hue/roughness are visual estimates; source photographs have unknown capture dates.',
            'Upper/rear wing registration and complete office-room enclosure remain unresolved.2017design drawings are not built-survey evidence.',
            'Source opaque proxies remain opaque until actual interior structure is registered. No room boxes, roof or floors are invented.',
            'Same-light Cycles previews demonstrate material delta, not the final web environment reflection. Root must verify exported whole/detail parity.'])
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    with bpy.data.libraries.load(str(COMPONENT),link=False)as(src,dst):
        assert set(src.objects)==set(fingerprints);dst.objects=list(fingerprints)
    for obj in dst.objects:bpy.data.collections[COLLECTION].objects.link(obj)
    update_scene()
    for obj in dst.objects:
        assert object_fingerprint(obj)==fingerprints[obj.name]
        assert shape_fingerprint(obj)==shape_fingerprint(bpy.data.objects[obj['originalObject']])
        obj.hide_render=False;set_layer_hidden(obj,False)
    assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
    assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items())
    for name in SOURCES:bpy.data.objects[name].hide_render=True
    render('after')
    report=dict(componentSha256=sha(COMPONENT),componentReopened=True,sourceObjectCount=len(originals),
        addedObjectsVerified=len(owned),allSourceGeometryUVBindingsPreserved=True,allSourceMaterialsPreserved=True,
        addedGeometryUVNormalsEqual=True,sourceFileUnchanged=sha(BASE)==BASE_SHA,transmissionAndOpacityUnchanged=True,
        sourceVisibilityPreservedOnReload=True,wholeCampusSaved=False)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MAR209_COMPONENT_VERIFIED',json.dumps(report),flush=True);bpy.ops.wm.quit_blender()


if __name__=='__main__':main()
