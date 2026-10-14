"""Replace 51L's opaque glass proxies with independent dielectric glazing.

Run in Blender's Text Editor. The 2025-07-31 official photograph supports
existing window arrangement and transparent glazing, not measured optics or
interior reconstruction. All source meshes, UVs and bindings remain intact.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v203.blend'
OUT = ROOT / 'result/blender/51l-exterior204'
COMPONENT = OUT / '51l-exterior204-component.blend'
EXPECTED_SHA = '976e645ef4b58e19485feff1fe3ff2fb64d9b5d497739642a2429548d821df8a'
PREFIX = '51L204_'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_exterior_round194 import object_fingerprint
from refine_exterior_glass181 import surface_components


def geometry_signature(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    mesh = obj.data
    for items, field, kind, width in [(mesh.vertices,'co','f',3),
                                     (mesh.loops,'vertex_index','i',1),
                                     (mesh.polygons,'material_index','i',1),
                                     (mesh.polygons,'loop_total','i',1)]:
        values = array.array(kind,[0])*(len(items)*width)
        items.foreach_get(field,values)
        digest.update(values.tobytes())
    for layer in mesh.uv_layers:
        values = array.array('f',[0])*(len(layer.data)*2)
        layer.data.foreach_get('uv',values)
        digest.update(layer.name.encode()+values.tobytes())
    return digest.hexdigest()


def finish_state(material):
    node = material.node_tree.nodes.get('Principled BSDF')
    return dict(color=list(material.diffuse_color),
                shaderColor=list(node.inputs['Base Color'].default_value),
                metallic=float(node.inputs['Metallic'].default_value),
                roughness=float(node.inputs['Roughness'].default_value),
                transmission=float(node.inputs['Transmission Weight'].default_value),
                alpha=float(node.inputs['Alpha'].default_value),
                webOpacity=material.get('webOpacity'))


def update():
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


def window_probes():
    reg = json.loads((ROOT/'result/blender/stage92/lincolns-three-bay-audit.json').read_text())
    origin,axis,normal = [Vector(reg['frame'][key]) for key in ['origin','right','normal']]
    trees=[]
    for obj in bpy.data.collections['51L_EXTERIOR'].all_objects:
        if obj.hide_render or obj.type!='MESH':
            continue
        trees.append((obj.name,BVHTree.FromPolygons(
            [obj.matrix_world@v.co for v in obj.data.vertices],
            [list(poly.vertices) for poly in obj.data.polygons])))
    result=[]
    for win in reg['windows']:
        if win['floor']==0:
            continue
        center=origin+axis*win['centerX']+Vector((0,0,(win['lower']+win['upper'])/2+.12))
        start=center+normal*2+axis*.17
        hits=[]
        for name,tree in trees:
            point,_,_,distance=tree.ray_cast(start,-normal,3)
            if point is not None:
                hits.append((distance,name,[round(v,6)for v in point]))
        hits.sort()
        assert hits,win
        result.append(dict(floor=win['floor'],bay=win['bay'],firstSurface=hits[0][1],
                           distance=round(hits[0][0],6),point=hits[0][2]))
    return result


def pane_backing_audit(sources):
    collection=bpy.data.collections['51L_EXTERIOR']
    points=[obj.matrix_world@v.co for obj in collection.all_objects
            if obj.type=='MESH' and not obj.hide_render for v in obj.data.vertices]
    center=Vector([(min(p[i]for p in points)+max(p[i]for p in points))/2 for i in range(3)])
    backing=[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render or obj in sources:
            continue
        if not any(word in obj.name.lower()for word in ['brick','stone','wood','slab','backing','recess','dark']):
            continue
        backing.append((obj.name,BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],
                         [list(poly.vertices)for poly in obj.data.polygons])))
    records=[]
    for obj in sources:
        mesh=bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.normal_update()
        normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
        slots=[slot for slot,material in enumerate(obj.data.materials)if material and 'glass' in material.name.lower()]
        pane=0
        for slot in slots:
            for faces,closed,volume in surface_components(mesh,slot):
                if not faces:
                    continue
                pane+=1
                front=max(faces,key=lambda face: (normal_matrix@face.normal).dot(
                    Vector(((obj.matrix_world@face.calc_center_median()-center).x,
                            (obj.matrix_world@face.calc_center_median()-center).y,0))))
                point=obj.matrix_world@front.calc_center_median()
                normal=(normal_matrix@front.normal).normalized()
                hits=[]
                for name,tree in backing:
                    hit,_,_,distance=tree.ray_cast(point-normal*.06,-normal,1.2)
                    if hit is not None:
                        hits.append((distance+.06,name,[round(v,6)for v in hit]))
                hits.sort()
                records.append(dict(object=obj.name,pane=pane,closedShell=closed,
                    signedVolume=volume,worldOrientationOutward=(not closed or volume*obj.matrix_world.to_3x3().determinant()>0),
                    frontPoint=[round(v,6)for v in point],frontNormal=[round(v,6)for v in normal],
                    nearbyOpaqueBacking=hits[0][1]if hits else None,
                    backingDistance=round(hits[0][0],6)if hits else None,
                    treatment='Restrained opacity0.72; no verified room interior exposed'))
        mesh.free()
    assert all(record['worldOrientationOutward']for record in records)
    records.sort(key=lambda row:(row['object'].removeprefix(PREFIX),row['frontPoint'],row['frontNormal']))
    counts={}
    for row in records:
        counts[row['object']]=counts.get(row['object'],0)+1
        row['pane']=counts[row['object']]
    return records


def render_review(phase):
    scene=bpy.data.scenes.new(PREFIX+'review_'+phase)
    collection=bpy.data.collections.new(scene.name)
    scene.collection.children.link(collection)
    for obj in bpy.data.collections['51L_EXTERIOR'].all_objects:
        if not obj.hide_render:
            collection.objects.link(obj)
    world=bpy.data.worlds.new(scene.name)
    world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.82,.85,.88,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
    scene.world=world
    sun_data=bpy.data.lights.new(scene.name+'_sun','SUN')
    sun_data.energy,sun_data.angle=1.8,.15
    sun=bpy.data.objects.new(sun_data.name,sun_data)
    collection.objects.link(sun)
    sun.rotation_euler=Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    reg=json.loads((ROOT/'result/blender/stage92/lincolns-three-bay-audit.json').read_text())['frame']
    origin,axis,normal=[Vector(reg[k])for k in ['origin','right','normal']]
    focus=origin+axis*(reg['length']/2)+Vector((0,0,11))
    data=bpy.data.cameras.new(scene.name+'_camera')
    camera=bpy.data.objects.new(data.name,data)
    collection.objects.link(camera)
    camera.location=focus+normal*38+axis*5+Vector((0,0,1.5))
    camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type,data.ortho_scale='ORTHO',26
    scene.camera=camera
    scene.render.engine='BLENDER_EEVEE'
    scene.eevee.taa_render_samples=32
    scene.render.resolution_x,scene.render.resolution_y=1000,1300
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    scene.render.filepath=str(OUT/(phase+'-full-exterior.png'))
    bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene)
    for obj in list(collection.objects):
        if obj.type in {'CAMERA','LIGHT'}:
            bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(collection)
    bpy.data.worlds.remove(world)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update()
    originals={obj.name:object_fingerprint(obj)for obj in bpy.data.objects}
    visibility={obj.name:obj.hide_render for obj in bpy.data.objects}
    sources=[obj for obj in bpy.data.collections['51L_EXTERIOR'].all_objects
             if obj.type=='MESH' and not obj.hide_render and
             any(mat and 'glass' in mat.name.lower() and
                 any(poly.material_index==slot for poly in obj.data.polygons)
                 for slot,mat in enumerate(obj.data.materials))]
    assert len(sources)==6,len(sources)
    pane_backing=pane_backing_audit(sources)
    before=window_probes()
    if not (OUT/'current-full-exterior.png').exists():
        render_review('current')
    added=[]
    materials={}
    original_materials={}
    replacements=[]
    for source in sources:
        signature=geometry_signature(source)
        target=source.copy()
        target.data=source.data.copy()
        target.name=PREFIX+source.name
        target.data.name=target.name
        target['originalObject']=source.name
        target['webGeometrySource']=source.get('webGeometrySource',source.name.removeprefix('GLASS181_'))
        target['glazingEvidence']='Official LSE GSoS photograph published2025-07-31; capture date unknown'
        for collection in source.users_collection:
            collection.objects.link(target)
        bindings=[]
        for slot,source_material in enumerate(source.data.materials):
            if not source_material or 'glass' not in source_material.name.lower():
                continue
            original_materials[source_material.name]=finish_state(source_material)
            if source_material.name not in materials:
                material=source_material.copy()
                material.name=PREFIX+'clear_'+source_material.name
                material.diffuse_color=(.14,.18,.20,.72)
                node=material.node_tree.nodes['Principled BSDF']
                node.inputs['Base Color'].default_value=(.14,.18,.20,1)
                node.inputs['Metallic'].default_value=0
                node.inputs['Roughness'].default_value=.16
                node.inputs['Transmission Weight'].default_value=.48
                node.inputs['Alpha'].default_value=.72
                node.inputs['IOR'].default_value=1.45
                material['webOpacity']=.72
                material['opticsStatus']='Estimated neutral transparent dielectric; no measured glass specification'
                material.surface_render_method='DITHERED'
                materials[source_material.name]=material
            target.data.materials[slot]=materials[source_material.name]
            bindings.append(dict(slot=slot,sourceMaterial=source_material.name,
                                 material=target.data.materials[slot].name))
        source.hide_render=True
        source.hide_set(True)
        assert geometry_signature(target)==signature
        added.append(target)
        replacements.append(dict(source=source.name,target=target.name,
                                 geometryAndUvSignature=signature,bindings=bindings))
    update()
    after=window_probes()
    assert all({k:v for k,v in a.items()if k!='firstSurface'}==
               {k:v for k,v in b.items()if k!='firstSurface'}for a,b in zip(before,after))
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
    assert all(finish_state(bpy.data.materials[name])==state for name,state in original_materials.items())
    fingerprints={obj.name:object_fingerprint(obj)for obj in added}
    bpy.data.libraries.write(str(COMPONENT),set(added),fake_user=True,compress=True)
    audit=dict(version=204,code='51L',baselineSha256=EXPECTED_SHA,targetCollection='51L_EXTERIOR',
               componentPath=str(COMPONENT.relative_to(ROOT)),
               componentSha256=hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
               addedObjects=[obj.name for obj in added],archivedObjects=[obj.name for obj in sources],changedObjects=[],
               originalFingerprints=originals,originalVisibility=visibility,originalSourceMaterials=original_materials,
               replacements=replacements,addedFingerprints=fingerprints,
               geometricProbesBefore=before,geometricProbesAfter=after,paneBackingAudit=pane_backing,
               source=dict(local='data/collections/lincolns-frontage-review/51l-gsos-2025.jpg',
                           url='https://www.lse.ac.uk/global-school-of-sustainability/news/2025/first-recipients-Global-Sustainability-Research-Fund',
                           published='2025-07-31',captureDate=None),
               scope='Six existing51L glass batches receive independently estimated neutral dielectric finishes with restrained opacity0.72 and estimated transmission0.48. Existing windows, frames, masonry, roof, original meshes, per-corner UVs and source materials retained.',
               limitations='Optical values are estimates. Photograph capture date unknown; no2026 condition or complete interior claim. Existing dimensional and hidden-elevation limitations apply.')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update()
    with bpy.data.libraries.load(str(COMPONENT),link=False)as (source,target):
        target.objects=list(audit['addedObjects'])
    for obj in target.objects:
        for collection in bpy.data.objects[obj['originalObject']].users_collection:
            collection.objects.link(obj)
        obj.hide_render=False
    for name in audit['archivedObjects']:
        bpy.data.objects[name].hide_render=True
        bpy.data.objects[name].hide_set(True)
    update()
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
    assert all(object_fingerprint(bpy.data.objects[name])==value for name,value in fingerprints.items())
    assert window_probes()==after
    reopened_backing=pane_backing_audit(list(target.objects))
    for old,new in zip(pane_backing,reopened_backing):
        assert {k:v for k,v in old.items()if k!='object'}=={k:v for k,v in new.items()if k!='object'}
    assert all(bpy.data.objects[name].hide_render==state for name,state in visibility.items()
               if name not in audit['archivedObjects'])
    render_review('reopened')
    proof=dict(savedComponentReopened=True,originalObjectCount=len(originals),
               originalGeometryUVsAndBindingsPreserved=True,allOriginalMaterialsPreserved=True,
               windowFirstSurfaceProbeCount=len(after),paneBackingProbeCount=len(pane_backing),
               outwardClosedShellsVerified=True,restrainedOpacityWithoutInventedInterior=True,savedReloadProbeParity=True,
               replacementGeometryAndUvIdentical=True,unrelatedVisibilityPreserved=True,
               sourceModelSha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
               componentSha256=audit['componentSha256'],preview='reopened-full-exterior.png')
    assert proof['sourceModelSha256']==EXPECTED_SHA
    (OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    print('51L204_VERIFIED',len(added),len(after),flush=True)


if __name__=='__main__':
    main()
