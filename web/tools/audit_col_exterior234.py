"""Bounded read-only COL upper-envelope review against official evidence.

Run in Blender's Text Editor with the fixed v233 baseline. The script creates
private context previews and a no-change evidence audit; no campus or component
is saved when the sources do not establish a defensible geometric correction.
"""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v233.blend'
BASE_SHA='b1d01b4b74a7f9e33d9bab25e73f51f39361659b9236ca98c34056137d8b6660'
OUT=ROOT/'result/blender/col-exterior234'
DATA=ROOT/'data/collections/col-exterior234'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def snapshot():
    """Record geometry/UV/material bindings and all untouched datablock owners."""
    return {o.name:dict(fingerprint=object_fingerprint(o),owners=sorted(c.name for c in o.users_collection),visibility=[o.hide_render,o.hide_viewport],properties=repr(sorted(o.items())),modifiers=repr([(m.name,m.type,m.as_pointer())for m in o.modifiers]))for o in bpy.data.objects}


def bounds(obj):
    points=[obj.matrix_world@Vector(p)for p in obj.bound_box]
    return [[min(p[i]for p in points),max(p[i]for p in points)]for i in range(3)]


def pane_groups(obj):
    """Connected actual glass islands expose the modeled vertical row centres."""
    adjacency=[set()for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
    visited=set();rows=[]
    for seed in range(len(adjacency)):
        if seed in visited:continue
        stack=[seed];visited.add(seed);indices=[]
        while stack:
            index=stack.pop();indices.append(index)
            for neighbour in adjacency[index]-visited:visited.add(neighbour);stack.append(neighbour)
        points=[obj.matrix_world@obj.data.vertices[index].co for index in indices]
        if points:rows.append(dict(vertexCount=len(indices),bounds=[[min(p[i]for p in points),max(p[i]for p in points)]for i in range(3)],centreHeight=sum(p.z for p in points)/len(points)))
    return rows


def render_context(target):
    """A temporary scene links visible native geometry without editing it."""
    scene=bpy.data.scenes.new('COL234_private_context');collection=bpy.data.collections.new('COL234_private_context');scene.collection.children.link(collection)
    linked=[]
    for obj in bpy.data.scenes['00_CAMPUS_COMPLETE'].objects:
        if obj.type not in {'MESH','FONT','CURVE'}or obj.hide_render:continue
        bb=bounds(obj)
        if bb[0][1]<-25 or bb[0][0]>48 or bb[1][1]<-165 or bb[1][0]>-65:continue
        collection.objects.link(obj);linked.append(obj)
    camera_data=bpy.data.cameras.new('COL234_private_camera');camera=bpy.data.objects.new(camera_data.name,camera_data);collection.objects.link(camera);scene.camera=camera
    world=bpy.data.worlds.new('COL234_private_world');world.color=(.8,.8,.8);scene.world=world
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True;scene.display.shading.background_type='WORLD';scene.render.resolution_x=1300;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    views=[dict(id='current-whole-context',position=[-21,-181,31],target=[10,-119,14],scale=45),dict(id='current-houghton-context',position=[-41,-154,29],target=[7,-111,14],scale=43)]
    for view in views:
        camera.location=Vector(view['position']);camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.type='ORTHO';camera_data.ortho_scale=view['scale'];scene.render.filepath=str(OUT/(view['id']+'.png'));bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene);bpy.data.objects.remove(camera,do_unlink=True);bpy.data.cameras.remove(camera_data);bpy.data.collections.remove(collection);bpy.data.worlds.remove(world)
    return dict(views=views,actualContextObjects=len(linked),scope='Current unchanged native geometry with adjacent buildings and street; Workbench material colours are diagnostic, not calibrated finish verification.')


def review():
    assert sha(BASE)==BASE_SHA
    OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    assert len(bpy.data.objects)==8529
    original=snapshot();materials={m.name:m.as_pointer()for m in bpy.data.materials}
    metadata=json.loads((ROOT/'web/tools/building-metadata.json').read_text());spaces={s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in metadata['spaces']}
    assert len(spaces)==34 and len({n for members in spaces.values()for n in members})==1433
    col=bpy.data.collections['COL_EXTERIOR'];rows=[];glass=[]
    for obj in col.all_objects:
        if obj.hide_render or obj.type!='MESH':continue
        rows.append(dict(name=obj.name,bounds=bounds(obj),vertices=len(obj.data.vertices),materials=[m.name if m else None for m in obj.data.materials]))
        if 'recessed_glass'in obj.name:glass.append(dict(name=obj.name,islands=pane_groups(obj)))
    write(OUT/'current-native-envelope.json',dict(baselineSha256=BASE_SHA,visibleMeshes=rows,actualGlassIslands=glass))
    context=render_context(col)
    assert snapshot()==original
    assert {m.name:m.as_pointer()for m in bpy.data.materials}==materials
    assert {name:sorted(o.name for o in bpy.data.collections[name].all_objects)for name in spaces}==spaces
    assert sha(BASE)==BASE_SHA
    refs=json.loads((DATA/'sources.json').read_text())
    audit=dict(version=234,building='COL',auditOnly=True,status='no-source-supported-upper-envelope-correction',baselinePath=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,targetCollection='COL_EXTERIOR',componentProduced=False,componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],changedObjects=[],sourceManifest=str((DATA/'sources.json').relative_to(ROOT)),nativeEvidence='current-native-envelope.json',context=context,verification=dict(fullNativeOpened=True,originalObjectsVerified=len(original),originalMaterialsUntouched=len(materials),allOriginalGeometryUVBindingsTransformsPropertiesModifiersOwnersUnchanged=True,allVisibilityUnchanged=True,protectedSpaces=len(spaces),protectedSpaceObjects=len({n for members in spaces.values()for n in members}),baselineBytesUnchanged=True,componentReappendNotApplicable=True,fullCampusSaved=False),findings=[dict(region='Upper window rows',finding='The retained model has seven primary facade bands with boundaries0/4.8/8.6/12.1/15.6/19.1/22.6/26.1m; current actual glass-island heights are captured separately. The official estate corner photo crops the upper building and does not establish a complete band count.'),dict(region='Roof and cornice',finding='Existing inset roof26.4–29m and upper/cornice shape remain estimates. No complete roof/parapet photograph or measured elevation obtained in the single bounded official lookup.'),dict(region='Internal floor numbering',finding='New official2023/24maintenance document states Columbia communal spaces on LevelsGto8. This establishes numbered occupied levels through8 in that programme, not a direct mapping of each level to a street-facing window band or roof height. Possible under-modeling remains unresolved; adding two facade storeys would be speculative.'),dict(region='Main material and accepted lower facade',finding='Archived official photographs support pale stone and dark joinery. No newly supported structural/material mismatch established; accepted portal, Garrick sign and175piers remain unchanged.')],decision='Retain the accepted COL envelope; no zero-change component or fabricated before/after improvement. Two current full-context native views document the unresolved upper extent.',nextEvidenceNeeded='A built full-height Aldwych/Houghton elevation with recognizable portal/Garrick corner and roof/parapet, or a dimensioned existing elevation/section mappingG–8 to absolute levels.',limitations=['Historical official source dates do not establish2026as-built condition.','No change candidate exists, so save/reappend validation and before/after improvement are not claimed.','The2023/24floor-numbering clue alone cannot settle street storey count, mezzanines, setbacks, cornice dimensions or roof profile.','No new glazing opacity, room backing, upper windows or roof geometry is invented.'])
    write(OUT/'audit.json',audit)
    print('COL234_READONLY_READY',len(original),len(rows),len(glass),len(materials),flush=True)


if __name__=='__main__':review()
