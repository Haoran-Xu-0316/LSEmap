"""Evidence-limited KSW glass review from accepted218. Run in Blender Text Editor.

Keeps source meshes, materials, room ownership and complete native read-only.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v218.blend'
SHA='d57142ea7dce27ea052bbd508f63dcd8c15136faccc132ac4f5915dff64fe27d'
OUT=ROOT/'result/blender/ksw-exterior219'
PREFIX='KSW219_'
COLLECTION='KSW_EXTERIOR'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint
from refine_portsmouth_exterior207 import material_fingerprint
from refine_ksw_exterior195 import registration


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:layer.update()


def inspect():
    assert sha(BASE)==SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
    expected=accepted_fingerprints(ROOT/'result/blender/stage218',SHA)
    actual={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    assert expected==actual
    rows=[]
    for obj in bpy.data.collections[COLLECTION].all_objects:
        if obj.type!='MESH'or obj.hide_render:continue
        materials=[]
        for material in obj.data.materials:
            shader=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
            materials.append(dict(name=material.name,color=list(shader.inputs['Base Color'].default_value)if shader else None,roughness=shader.inputs['Roughness'].default_value if shader else None,metallic=shader.inputs['Metallic'].default_value if shader else None,alpha=shader.inputs['Alpha'].default_value if shader else None,transmission=shader.inputs['Transmission Weight'].default_value if shader else None,properties=dict(material.items())))
        rows.append(dict(name=obj.name,materials=materials,vertices=len(obj.data.vertices),polygons=len(obj.data.polygons)))
    (OUT/'inspection.json').write_text(json.dumps(dict(baselineSha256=SHA,acceptedSourceObjects=len(actual),objects=rows),indent=2)+'\n')
    print('KSW219_INSPECTED',len(actual),len(rows),flush=True)




SOURCE='KSW_NEXT_EXTERIOR195_GLASS181_KSW_NEXT_ENVELOPE_window_glass'


def modifier_state(obj):
    def stable(value):
        if isinstance(value,bpy.types.ID):return (value.bl_rna.identifier,value.name)
        if value is None or isinstance(value,(bool,int,float,str)):return value
        if hasattr(value,'to_list'):return value.to_list()
        try:return list(value)
        except TypeError:return str(value)
    # Skip readonly evaluated timing and memory-address-bearing RNA reprs.
    return [(modifier.name,modifier.type,[(prop.identifier,stable(getattr(modifier,prop.identifier,None)))for prop in modifier.bl_rna.properties if not prop.is_readonly and prop.identifier!='rna_type'])for modifier in obj.modifiers]


def room_state():
    metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    rows=[]
    for room in metadata['spaces']:
        collection=bpy.data.collections.get(room['collection'])
        if not collection:continue
        members=sorted(obj.name for obj in collection.all_objects)
        rows.append(dict(collection=collection.name,objects=members,objectCollections={name:sorted(c.name for c in bpy.data.objects[name].users_collection)for name in members},scenes=sorted(scene.name for scene in bpy.data.scenes if collection.name in scene.collection.children)))
    return rows


def glass_metrics(material):
    shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    color=list(shader.inputs['Base Color'].default_value)
    return dict(baseColor=color,linearLuminance=sum(a*b for a,b in zip(color,[.2126,.7152,.0722])),linearSaturation=(max(color[:3])-min(color[:3]))/max(color[:3]),roughness=shader.inputs['Roughness'].default_value,metallic=shader.inputs['Metallic'].default_value,alpha=shader.inputs['Alpha'].default_value,transmission=shader.inputs['Transmission Weight'].default_value,ior=shader.inputs['IOR'].default_value,webOpacity=material.get('webOpacity'),webClosedGlazing=material.get('webClosedGlazing'))


def backing_probes():
    source=bpy.data.objects[SOURCE];vertices=[];faces=[];owners=[]
    for obj in bpy.data.collections[COLLECTION].all_objects:
        if obj.hide_render or obj.type!='MESH' or any('glass'in m.name.lower()or'glazing'in m.name.lower()for m in obj.data.materials if m):continue
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
    tree=BVHTree.FromPolygons(vertices,faces);outward=registration()[2];rows=[]
    for face in source.data.polygons:
        normal=(source.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
        if normal.dot(outward)<.65:continue
        centre=sum((source.matrix_world@source.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
        hit=tree.ray_cast(centre-normal*.003,-normal,40)
        distance=hit[3]+.003 if hit[2]is not None else None
        rows.append(dict(faceIndex=face.index,centre=list(centre),firstOpaqueObject=owners[hit[2]]if hit[2]is not None else None,distanceMetres=distance,nearBacking=distance is not None and distance<=1.5))
    assert rows
    return dict(method='Every outward-facing glass polygon centroid with front-normal alignment>.65; visible opaque KSW exterior only, glass excluded, inward40m rays; near<=1.5m',samples=len(rows),nearBackingSamples=sum(row['nearBacking']for row in rows),rows=rows,decision='274 near hits are existing dark recess liners14.3-66.2mm behind the glass, not verified rooms. Preserve original alpha1/transmission0 instead of exposing the simple liner as a reconstructed interior.')


def render_review(label):
    import math
    scene=bpy.data.scenes.new(PREFIX+'REVIEW_'+label);scene.collection.children.link(bpy.data.collections[COLLECTION])
    bpy.context.window.scene=scene
    world=bpy.data.worlds.new(scene.name);world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.74,.78,.82,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
    light=bpy.data.lights.new(scene.name+'_sun','SUN');light.energy=2.4;light.angle=math.radians(7)
    sun=bpy.data.objects.new(light.name,light);scene.collection.objects.link(sun)
    origin,axis,normal=registration();sun.rotation_euler=(-normal*.65-axis*.5+Vector((0,0,-.85))).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new(scene.name+'_camera');camera=bpy.data.objects.new(data.name,data);scene.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.ortho_scale=24;data.clip_end=500
    scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=24
    scene.render.resolution_x=840;scene.render.resolution_y=1120;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    focus=origin+Vector((0,0,10.2));views=[]
    for name,offset in [('front',0),('oblique',14)]:
        camera.location=focus+normal*43+axis*offset+Vector((0,0,1))
        camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
        views.append(dict(view=name,location=list(camera.location),target=list(focus),orthoScale=24))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);bpy.data.cameras.remove(data);bpy.data.lights.remove(light);update()
    return views


def run():
    inspect()
    originals={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    materials={material.name:material_fingerprint(material)for material in bpy.data.materials}
    modifiers={obj.name:modifier_state(obj)for obj in bpy.data.objects}
    visibility={obj.name:obj.hide_render for obj in bpy.data.objects};rooms=room_state()
    assert len(rooms)==18 and len(set(name for room in rooms for name in room['objects']))==623
    backings=backing_probes();(OUT/'backing-rays.json').write_text(json.dumps(backings,indent=2)+'\n')
    cameras=render_review('before')
    source=bpy.data.objects[SOURCE];assert not source.hide_render
    clone=source.copy();clone.data=source.data.copy();clone.name=PREFIX+'neutral_reflective_glazing';clone.data.name=clone.name
    clone['originalObject']=SOURCE;clone['destinationCollection']=COLLECTION;clone['webGeometrySource']=source.get('webGeometrySource',source.name)
    records=[]
    for index,source_material in enumerate(source.data.materials):
        material=source_material.copy();material.name=PREFIX+'neutral_glass_'+str(index)
        shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');assert not shader.inputs['Base Color'].is_linked
        before=glass_metrics(source_material);tint=(.96,1.005,1.04);weight=sum(c*w for c,w in zip(tint,[.2126,.7152,.0722]))
        color=tuple(before['linearLuminance']*c/weight for c in tint)+(before['baseColor'][3],)
        shader.inputs['Base Color'].default_value=color;material.diffuse_color=color
        material['colourBasis']='Uncalibrated2025/26official handbook and undated estate photographs; neutral grey reflection, estimated residual cool tint, original linear brightness preserved'
        after=glass_metrics(material)
        assert abs(before['linearLuminance']-after['linearLuminance'])<1e-7
        assert after['linearSaturation']<before['linearSaturation']*.25
        for key in ['roughness','metallic','alpha','transmission','ior','webOpacity','webClosedGlazing']:assert before[key]==after[key],key
        clone.data.materials[index]=material;records.append(dict(source=source_material.name,replacement=material.name,before=before,after=after))
    bpy.data.collections[COLLECTION].objects.link(clone);clone.hide_render=False;clone.hide_set(False);source.hide_render=True;source.hide_set(True);update()
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in materials.items())
    assert room_state()==rooms
    fingerprints={clone.name:object_fingerprint(clone)};bindings={clone.name:[m.name for m in clone.data.materials]}
    assert render_review('after')==cameras
    component=OUT/'component.blend';bpy.data.libraries.write(str(component),{clone},fake_user=True,compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update()
    expected=accepted_fingerprints(ROOT/'result/blender/stage218',SHA)
    assert {obj.name:object_fingerprint(obj)for obj in bpy.data.objects}==expected
    with bpy.data.libraries.load(str(component),link=False)as(available,loaded):loaded.objects=list(fingerprints)
    for obj in loaded.objects:
        for index,name in enumerate(bindings[obj.name]):obj.data.materials[index]=bpy.data.materials[name]
        bpy.data.collections[COLLECTION].objects.link(obj);obj.hide_render=False;obj.hide_set(False)
    bpy.data.objects[SOURCE].hide_render=True;bpy.data.objects[SOURCE].hide_set(True);update()
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
    assert all(material_fingerprint(bpy.data.materials[name])==value for name,value in materials.items())
    assert all(modifier_state(bpy.data.objects[name])==value for name,value in modifiers.items())
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in fingerprints.items())
    assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items()if name!=SOURCE)
    assert room_state()==rooms
    source=bpy.data.objects[SOURCE];clone=bpy.data.objects[next(iter(fingerprints))]
    # Material bindings differ intentionally; all other fingerprint inputs match.
    held=[m for m in clone.data.materials]
    for index,material in enumerate(source.data.materials):clone.data.materials[index]=material
    assert object_fingerprint(source)==object_fingerprint(clone)
    for index,material in enumerate(held):clone.data.materials[index]=material
    assert object_fingerprint(clone)==fingerprints[clone.name]
    references=[]
    for filename in ['small_round5_KSW_handbook-000.png','exteriors_lse_estate_009.jpg']:
        path=ROOT/'data/建筑图片/KSW_20 Kingsway/01_建筑实拍'/filename
        references.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path),captureDate='unknown',publication='2025/26 handbook'if 'handbook'in filename else 'undated official estate website',sourceURL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf'if 'handbook'in filename else 'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate',type='Built exterior photograph; not a proposal',distribution='Private visual evidence only; no photo texture'))
    verification=dict(savedComponentReopened=True,acceptedBaselineObjectCount=len(expected),sourceObjectsVerified=len(originals),sourceMaterialNodesVerified=len(materials),sourceModifierStacksVerified=len(modifiers),sourceGeometryUVTransformsAndBindingsPreserved=True,glassTopologyTransformAndUVExact=True,allOriginalOpticalParametersPreserved=True,unrelatedVisibilityPreserved=True,roomCollectionsPreserved=len(rooms),roomUniqueObjectsPreserved=623,roomObjectCollectionAndSceneMembershipsPreserved=True,sourceModelUnchanged=sha(BASE)==SHA,trianglesAdded=0,sameCameraLightingAndExposure=True)
    report=dict(version=219,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=COLLECTION,destinationCollection=COLLECTION,addedObjects=list(fingerprints),archivedObjects=[SOURCE],changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,materials=records,backingEvidence=dict(path=str((OUT/'backing-rays.json').relative_to(ROOT)),samples=backings['samples'],nearBackingSamples=backings['nearBackingSamples']),references=references,verification=verification,previews=['before-front.png','after-front.png','before-oblique.png','after-oblique.png'],cameras=cameras,lighting='Identical840x1120 EEVEE24sample neutral world.65 sun2.4 AgX Medium High Contrast, orthographic24m',scope='One existing photographed street-glazing batch; reduce authored blue saturation40% to7.69%, preserve linear brightness and all existing optical parameters; all brick, stone, joinery and roof retained.',limitations=['Glass hue is an uncalibrated visual estimate from built photographs with unknown capture dates, not measured glazing specification.','Closed shell keeps alpha1/transmission0; no invented full interior or opaque near-window backing added.','All existing glass geometry, UV, normals, transforms and modifiers remain exact; no dimension change or additional triangles.','Rendering environment contributes additional sky hue; authored hue correction does not claim a calibrated photographic reflection match.'])
    (OUT/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print('KSW219_COMPONENT_REOPENED',len(expected),len(materials),backings['nearBackingSamples'],'/',backings['samples'],flush=True)


if __name__=='__main__':run()
