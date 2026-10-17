"""KGS237: continuous cupola shading without geometry changes.

Run in Blender Text Editor. Fixed accepted baseline; only an isolated library is
saved. The shell's disconnected authored quads require coincident-position
normal sharing, rather than a topology weld. Seams and all materials stay intact.
"""
from pathlib import Path
import ast, array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
ROOT=Path('/Users/haoranxu/Desktop/LSEmap')
BASE=ROOT/'result/blender/LSE_campus_detailed_v236.blend'
BASE_SHA='3834a5f04b94806175ec8344944a03da7694d7ef1447e9cbb37ed44a684bf6bd'
OUT=ROOT/'result/blender/kgs-surface237'
COMPONENT=OUT/'component.blend'
SOURCE='KGS_D5_lead_dome_lead'
ADDED='KGS237_continuous_lead_cupola'
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,update_scene

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def normal_record(mesh):
    smooth=[p.use_smooth for p in mesh.polygons]
    normals=array.array('f',[0])*(len(mesh.corner_normals)*3)
    mesh.corner_normals.foreach_get('vector',normals)
    return dict(smoothFaces=sum(smooth),faces=len(smooth),hasCustomNormals=mesh.has_custom_normals,
                smoothFlagsSha256=hashlib.sha256(bytes(smooth)).hexdigest(),
                cornerNormalsSha256=hashlib.sha256(normals.tobytes()).hexdigest(),
                sharpEdges=[e.index for e in mesh.edges if e.use_edge_sharp])
def protected_state():
    return {o.name:dict(fingerprint=object_fingerprint(o),normals=normal_record(o.data) if o.type=='MESH' else None,
                       owners=sorted(c.name for c in o.users_collection),properties=repr(sorted(o.items())),
                       modifiers=repr([(m.name,m.type,[(p.identifier,repr(getattr(m,p.identifier))) for p in m.bl_rna.properties if not p.is_readonly and p.identifier!='name'])for m in o.modifiers]))for o in bpy.data.objects}
def rooms():
    meta=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    return {s['collection']:sorted(o.name for o in bpy.data.collections[s['collection']].all_objects)for s in meta['spaces']}
def smooth_shell(mesh):
    sums={}
    key=lambda co:tuple(round(v,5)for v in co)
    for p in mesh.polygons:
        indices=list(p.vertices)
        for i,vi in enumerate(indices):
            a=mesh.vertices[indices[i-1]].co-mesh.vertices[vi].co
            b=mesh.vertices[indices[(i+1)%len(indices)]].co-mesh.vertices[vi].co
            angle=a.angle(b,0) if a.length>1e-8 and b.length>1e-8 else 0
            k=key(mesh.vertices[vi].co)
            sums.setdefault(k,Vector())
            sums[k] += p.normal*(angle if angle>1e-8 else math.pi/2)
    normals=[]
    for loop in mesh.loops:
        n=sums[key(mesh.vertices[loop.vertex_index].co)]
        assert n.length>1e-8
        normals.append(tuple(n.normalized()))
    for p in mesh.polygons:p.use_smooth=True
    mesh.normals_split_custom_set(normals)
    mesh.update()
    return len(sums)
def export_private(label, full_detail=True):
    # Execute only reusable production function definitions, never its top-level
    # file writes. This retains actual evaluated bevel/UV/material/export policy.
    tree=ast.parse((ROOT/'web/tools/export_scene.py').read_text())
    wanted={'source_geometry_name','surface_descriptor','web_material','clip_below_ground','clone_group','export_scene'}
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in wanted]
    namespace=dict(bpy=bpy,bmesh=bmesh,Vector=Vector,re=__import__('re'),json=json,full_detail=full_detail,
                   material_cache={},OUTPUT=OUT,depsgraph=bpy.context.evaluated_depsgraph_get())
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'production-export-functions','exec'),namespace)
    states=[]
    for o in bpy.data.collections['KGS_EXTERIOR'].all_objects:
        for m in o.modifiers:
            if m.type=='BEVEL' and not namespace['source_geometry_name'](o).startswith(('KGS_NEXT_',)):
                states.append((m,m.show_viewport,m.show_render));m.show_viewport=False;m.show_render=False
    bpy.context.view_layer.update();namespace['depsgraph']=bpy.context.evaluated_depsgraph_get()
    scene=bpy.data.scenes.new('KGS237_PRIVATE_'+label)
    obj,_=namespace['clone_group'](list(bpy.data.collections['KGS_EXTERIOR'].all_objects),'KGS',scene)
    namespace['export_scene'](scene,label+'.glb')
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.scenes.remove(scene)
    for m,v,r in states:m.show_viewport=v;m.show_render=r
    update_scene()

def main():
    OUT.mkdir(parents=True,exist_ok=True);assert sha(BASE)==BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    baseline_material_count=len(bpy.data.materials)
    baseline=protected_state();room_before=rooms();assert len(baseline)==8584 and len(room_before)==35
    before=normal_record(bpy.data.objects[SOURCE].data)
    export_private('before')
    export_private('overview-before',False)
    source=bpy.data.objects[SOURCE]
    replacement=source.copy();replacement.data=source.data.copy();replacement.name=ADDED;replacement.data.name=ADDED
    bpy.data.collections['KGS_EXTERIOR'].objects.link(replacement)
    replacement['originalObject']=SOURCE;replacement['webGeometrySource']=SOURCE;replacement['destinationCollection']='KGS_EXTERIOR'
    replacement['scope']='Continuous normals across coincident shell vertices; no topology weld or seam alteration'
    coincident=smooth_shell(replacement.data)
    assert object_fingerprint(replacement)==object_fingerprint(source)
    expected=normal_record(replacement.data);assert expected['smoothFaces']==768 and expected['hasCustomNormals']
    bpy.data.libraries.write(str(COMPONENT),{replacement},fake_user=True)
    # Reopen the baseline and independently append the saved library.
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    with bpy.data.libraries.load(str(COMPONENT),link=False)as(_,target):target.objects=[ADDED]
    replacement=target.objects[0]
    for i,m in enumerate(bpy.data.objects[SOURCE].data.materials):replacement.data.materials[i]=m
    bpy.data.collections['KGS_EXTERIOR'].objects.link(replacement);update_scene()
    assert normal_record(replacement.data)==expected
    assert object_fingerprint(replacement)==baseline[SOURCE]['fingerprint']
    assert {k:v for k,v in protected_state().items()if k in baseline}==baseline
    assert rooms()==room_before
    bpy.data.objects[SOURCE].hide_render=True
    export_private('after')
    export_private('overview-after',False)
    assert normal_record(replacement.data)==expected
    write('baseline-state.json',dict(objects=baseline,rooms=room_before))
    report=dict(version=237,code='KGS',baselineSha256=BASE_SHA,componentPath=str(COMPONENT.relative_to(ROOT)),
                componentSha256=sha(COMPONENT),destinationCollection='KGS_EXTERIOR',addedObjects=[ADDED],archivedObjects=[SOURCE],
                replacementMaterialBindings={ADDED:[m.name for m in replacement.data.materials]},
                addedFingerprints={ADDED:object_fingerprint(replacement)},sourceObjectCount=len(baseline),sourceMaterialCount=baseline_material_count,
                protectedSpaceCount=35,protectedSpaceMembers=len({n for r in room_before.values()for n in r}),
                sourceNormals=before,replacementNormals=expected,coincidentPositionGroups=coincident,
                independentAppendVerified=True,allOriginalExtendedStatesPreserved=True,roomMembershipPreserved=True,
                originalsArchivedVisibilityOnly=[SOURCE],displayOwnership='KGS_EXTERIOR shared by overview and exterior; existing internal room unchanged',
                geometryTopologyUVMaterialsUnchanged=True,seamsObjectUntouched='KGS_NEXT_lead_cupola_seams',
                sourceBoundary='Existing LSE estate photograph supports continuous lead shell and separate standing seams. Normals are a presentation estimate on accepted existing geometry; roof shape and finial are not reconstructed.',
                privateExports={label:dict(path=label+'.glb',sha256=sha(OUT/(label+'.glb')))for label in ['before','after','overview-before','overview-after']})
    write('audit.json',report);assert sha(BASE)==BASE_SHA
    print('KGS237_COMPONENT_READY',report['componentSha256'],flush=True)
if __name__=='__main__':main()
