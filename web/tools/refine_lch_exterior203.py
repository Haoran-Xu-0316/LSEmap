"""Restore Lincoln Chambers' seven-position street elevation.

Run in Blender Text Editor. The archived May2025 photograph shows two sash
columns per brick field and a black downpipe between them. Current dimensions
are inherited; sash widths and pipe fittings are photo estimates. The complete
v201 campus stays read-only and all source geometry, UVs and bindings survive.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'result/blender/LSE_campus_detailed_v201.blend'
OUT = ROOT / 'result/blender/lch-exterior203'
EXPECTED_SHA = '83f8532de4378e614f53a327b8c3397ae375e880d655bd584f5e0ea4980f2bec'
PREFIX = 'LCH203_'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from integrate_exterior_round194 import object_fingerprint
from facade_geometry import Geometry, materials

WALL_SOURCES = ['LCH_D5_V42_wall_' + part + '_brick' for part in ['piers','spandrel','head']]
SHARED_SOURCES = ['LCH_D5_V42_window_jamb_frame',
    'LCH_NEXT_EXTERIOR148_retained_sash_rails',
    'LCH_D5_V42_upper_glazing_bar_frame','LCH_D5_V42_window_sill_stone',
    'GLASS181_LCH_NEXT_GLAZING149_front_windows']
ARCHIVE = WALL_SOURCES + SHARED_SOURCES
COMPONENT = OUT / 'lch-exterior203-component.blend'


def update():
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']


def render_review(phase, origin, axis, normal, mid):
    scene = bpy.data.scenes.new(PREFIX + 'review_' + phase)
    review = bpy.data.collections.new(scene.name)
    scene.collection.children.link(review)
    for obj in bpy.data.collections['LCH_EXTERIOR'].all_objects:
        if not obj.hide_render:
            review.objects.link(obj)
    sky = bpy.data.worlds.new(scene.name)
    sky.use_nodes = True
    sky.node_tree.nodes['Background'].inputs['Color'].default_value = (.82,.85,.88,1)
    sky.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    scene.world = sky
    light = bpy.data.lights.new(scene.name + '_sun','SUN')
    light.energy, light.angle = 1.6,.12
    sun = bpy.data.objects.new(light.name,light)
    review.objects.link(sun)
    sun.rotation_euler = Vector((-.6,.5,-1)).to_track_quat('-Z','Y').to_euler()
    camera = bpy.data.cameras.new(scene.name + '_camera')
    cam = bpy.data.objects.new(camera.name,camera)
    review.objects.link(cam)
    scene.camera = cam
    focus = origin + axis*mid + Vector((0,0,6.5))
    cam.location = focus + normal*30 + axis*.3 + Vector((0,0,1))
    cam.rotation_euler = (focus-cam.location).to_track_quat('-Z','Y').to_euler()
    camera.type, camera.ortho_scale = 'ORTHO',20
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x,scene.render.resolution_y = 1400,1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.render.filepath = str(OUT/(phase+'-full-frontage.png'))
    bpy.ops.render.render(write_still=True,scene=scene.name)
    bpy.data.scenes.remove(scene)
    for obj in list(review.objects):
        if obj.type in {'LIGHT','CAMERA'}:
            bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(review)
    bpy.data.worlds.remove(sky)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update()
    originals = {obj.name:object_fingerprint(obj) for obj in bpy.data.objects}
    visibility = {obj.name:obj.hide_render for obj in bpy.data.objects}
    assert all(not bpy.data.objects[name].hide_render for name in ARCHIVE)
    reg = json.loads((ROOT/'result/blender/lch_exterior148/audit.json').read_text())['registration']
    origin,axis,normal = [Vector(reg[key]) for key in ['origin','axis','normal']]
    mid = reg['leftStoreCentreX']/2
    def local(point):
        delta=point-origin
        return Vector((delta.dot(axis),delta.dot(normal),point.z))
    def world(x,depth,z):
        return origin+axis*x+normal*depth+Vector((0,0,z))
    all_brick_points = [local(obj.matrix_world@v.co) for name in WALL_SOURCES
                        for obj in [bpy.data.objects[name]] for v in obj.data.vertices]
    fields=[]
    for side in [-1,1]:
        points=[p for p in all_brick_points if (p.x-mid)*side>0]
        fields.append((min(p.x for p in points),max(p.x for p in points)))
    def in_field(point):
        return 4.449<=point.z<=10.651 and any(lo-.001<=point.x<=hi+.001 for lo,hi in fields)
    collection = bpy.data.collections['LCH_EXTERIOR']
    if not (OUT/'current-full-frontage.png').exists():
        render_review('current',origin,axis,normal,mid)
    palette={}
    for key,name in [('brick','LCH_V42_brick'),('frame','LCH_V42_frame'),
                     ('stone','LCH_V42_stone'),
                     ('glass',bpy.data.objects[SHARED_SOURCES[-1]].data.materials[0].name)]:
        material=bpy.data.materials[name].copy()
        material.name=PREFIX+'material_'+key
        palette[key]=material
    pipe=bpy.data.materials.new(PREFIX+'material_black_iron')
    pipe.use_nodes=True
    pipe.diffuse_color=(.018,.021,.022,1)
    shader=pipe.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value=pipe.diffuse_color
    shader.inputs['Roughness'].default_value=.42
    palette['pipe']=pipe
    owned=[]
    changes=[]
    # Shared meshes contain the ground shopwork, end bays and central window.
    # Delete only fully disconnected old narrow-window pieces in brick fields.
    for name in SHARED_SOURCES:
        source=bpy.data.objects[name]
        clone=source.copy()
        clone.data=source.data.copy()
        clone.name=PREFIX+'retained_'+name.removeprefix('LCH_D5_V42_')
        clone.data.name=clone.name
        for index,material in enumerate(clone.data.materials):
            copy=material.copy()
            copy.name=PREFIX+'retained_material_'+str(len(owned))+'_'+str(index)
            clone.data.materials[index]=copy
        clone['originalObject']=name
        clone['webGeometrySource']=source.get('webGeometrySource',name)
        collection.objects.link(clone)
        bm=bmesh.new()
        bm.from_mesh(clone.data)
        selected=[v for v in bm.verts if in_field(local(clone.matrix_world@v.co))]
        removed=len(selected)
        assert removed>0,(name,fields)
        bmesh.ops.delete(bm,geom=selected,context='VERTS')
        bm.to_mesh(clone.data)
        bm.free()
        clone.data.update()
        clone.hide_render=False
        clone.hide_set(False)
        owned.append(clone)
        changes.append(dict(source=name,replacement=clone.name,removedOldFlankVertices=removed,
                            retainedVertices=len(clone.data.vertices),remainingCornerUVsPreserved=True))
    materials.clear()
    materials.update(palette)
    groups={}
    def group(role,finish):
        if role not in groups:
            groups[role]=Geometry('LCH','203_'+role,finish)
        return groups[role]
    angle=math.atan2(axis.y,axis.x)
    def box(role,finish,x,z,width,height,depth,offset):
        if width>.00001 and height>.00001:
            group(role,finish).box(world(x,offset,z),(width,depth,height),angle)
    centres=[]
    # Re-use photographed floor levels and field boundaries from v201.
    # Two sash lights flank a pipe; width 0.78 of half-field is estimated.
    for xlo,xhi in fields:
        spacing=(xhi-xlo)/2
        width=spacing*.78
        xs=[xlo+spacing*.5,xlo+spacing*1.5]
        for lo,hi in [(4.45,7.55),(7.55,10.65)]:
            bottom,top=lo+.30,hi-.35
            cursor=xlo
            for x in xs:
                left,right=x-width/2,x+width/2
                box('brick_piers','brick',(cursor+left)/2,(lo+hi)/2,left-cursor,hi-lo,.32,-.12)
                box('brick_spandrels','brick',x,(lo+bottom)/2,width,bottom-lo,.32,-.12)
                box('brick_heads','brick',x,(top+hi)/2,width,hi-top,.32,-.12)
                cursor=right
                box('sash_glass','glass',x,(bottom+top)/2,width,top-bottom,.04,-.10)
                for xx in [left,right]:
                    box('sash_jambs','frame',xx,(bottom+top)/2,.075,top-bottom+.08,.12,0)
                for zz in [bottom,(bottom+top)/2,top]:
                    box('sash_rails','frame',x,zz,width,.065,.12,0)
                for xx in [x-width/6,x+width/6]:
                    box('upper_sash_bars','frame',xx,(bottom+top*3)/4,.022,(top-bottom)/2,.06,.01)
                box('stone_sills','stone',x,bottom-.10,width+.14,.16,.42,0)
                centres.append(dict(x=x,z=(bottom+top)/2,width=width,bottom=bottom,top=top))
            box('brick_piers','brick',(cursor+xhi)/2,(lo+hi)/2,xhi-cursor,hi-lo,.32,-.12)
        # Only visible vertical run above cornice is restored. Roof connections
        # and pavement drainage are hidden/unknown and are not reconstructed.
        pipe_x=(xlo+xhi)/2
        def cylinder(zlo,zhi,radius):
            geometry=group('black_downpipes','pipe')
            count=16
            vertices=[world(pipe_x+radius*math.cos(2*math.pi*i/count),
                       .14+radius*math.sin(2*math.pi*i/count),z)
                      for z in [zlo,zhi] for i in range(count)]
            faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
            faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
            geometry.add(vertices,faces)
        cylinder(4.48,10.65,.055)
        for z in [4.70,6.38,7.60,9.22,10.25]:
            cylinder(z-.045,z+.045,.079)
            box('pipe_clamps','pipe',pipe_x,z,.22,.075,.04,.075)
    for role,geometry in groups.items():
        obj=geometry.finish()
        obj.name=PREFIX+role
        obj.data.name=obj.name
        # Closed primitives have correct outward normals in axis/normal/up.
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);bm.free()
        obj.data.update()
        if role.startswith('brick_'):
            obj['originalObject']=WALL_SOURCES[['brick_piers','brick_spandrels','brick_heads'].index(role)]
        obj['evidence']='Official archived LSE May2025 photograph; Historic England listing 1227132 seven windows wide'
        obj['dimensionBasis']='Inherited v201 field boundaries and floor levels; photo-estimated sash and pipe proportions'
        owned.append(obj)
    for name in ARCHIVE:
        bpy.data.objects[name].hide_render=True
        bpy.data.objects[name].hide_set(True)
    update()
    assert all(object_fingerprint(bpy.data.objects[name])==digest for name,digest in originals.items())
    assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items() if name not in ARCHIVE)
    # Probe actual new apertures: ray must first strike glass; brick must not
    # hide the opening, and no new solid panel is behind it.
    def probes():
        relevant=[obj for obj in collection.all_objects if not obj.hide_render and obj.type=='MESH']
        vertices=[];faces=[];owners=[]
        for obj in relevant:
            start=len(vertices)
            vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
            faces.extend(tuple(start+i for i in face.vertices) for face in obj.data.polygons)
            owners.extend([obj.name]*len(obj.data.polygons))
        tree=BVHTree.FromPolygons(vertices,faces)
        rows=[]
        for centre in centres:
            for z in [centre['bottom']+.33,centre['top']-.33]:
                point=world(centre['x']+centre['width']*.24,1,z)
                hit=tree.ray_cast(point,-normal,1.3)
                name=owners[hit[2]] if hit[2] is not None else None
                assert name==PREFIX+'sash_glass',(centre,z,name)
                behind=tree.ray_cast(world(centre['x']+centre['width']*.24,-.14,z),-normal,.35)
                backing=owners[behind[2]] if behind[2] is not None else None
                assert backing is None,(centre,z,backing)
                rows.append(dict(x=centre['x'],z=z,firstObject=name,nearOpaqueBacking=backing))
        return rows
    before_probes=probes()
    bpy.data.libraries.write(str(COMPONENT),set(owned),fake_user=True,compress=True)
    added=[obj.name for obj in owned]
    fingerprints={obj.name:object_fingerprint(obj) for obj in owned}
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update()
    collection=bpy.data.collections['LCH_EXTERIOR']
    with bpy.data.libraries.load(str(COMPONENT),link=False) as (src,dst):
        dst.objects=list(added)
    for obj in dst.objects:
        collection.objects.link(obj)
        obj.hide_render=False
        obj.hide_set(False)
    for name in ARCHIVE:
        bpy.data.objects[name].hide_render=True
        bpy.data.objects[name].hide_set(True)
    update()
    assert all(object_fingerprint(bpy.data.objects[name])==digest for name,digest in originals.items())
    assert all(object_fingerprint(bpy.data.objects[name])==digest for name,digest in fingerprints.items())
    assert all(bpy.data.objects[name].hide_render==value for name,value in visibility.items() if name not in ARCHIVE)
    after_probes=probes()
    assert before_probes==after_probes
    render_review('reopened',origin,axis,normal,mid)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED_SHA
    report=dict(building='LCH',baseline=str(BASE),baselineSha256=EXPECTED_SHA,
        componentPath=str(COMPONENT.relative_to(ROOT)),targetCollection='LCH_EXTERIOR',
        destinationCollection='LCH_EXTERIOR',addedObjects=added,archivedObjects=ARCHIVE,changedObjects=[],
        originalObjectMappings={obj.name:obj.get('originalObject') for obj in dst.objects if obj.get('originalObject')},
        changes=changes,registration=dict(origin=list(origin),axis=list(axis),normal=list(normal),fields=fields),
        sashLights=centres,upperSashCountBefore=4,upperSashCountAfter=8,streetWindowColumnsBefore=5,streetWindowColumnsAfter=7,
        references=[dict(path='data/collections/lincoln-review/lse-volunteer-may2025.jpg',
            sha256='72d559254bfb8703e01f0a6dc1994a38f51c183d79f95433412a972046a3f3eb',
            page='https://blogs.lse.ac.uk/vcb/2025/09/22/welcome-to-lse-or-welcome-back/',
            dateBasis='Filename May2025; article 2025-09-22; capture EXIF unverified'),
            dict(url='https://historicengland.org.uk/listing/the-list/list-entry/1227132',
                 verified='2026-10-14',support='Seven windows wide; sashes and canted end bays')],
        limitations=['Inherited overall dimensions are estimates, not measured survey',
            'Sash width and downpipe fittings are photo estimates; roof connections and concealed drainage omitted',
            'Existing transparent glass finish inherited; no interior layout or furnishing added',
            'Top roof cropped in reference; roof and rear geometry unchanged'],
        componentSha256=hashlib.sha256(COMPONENT.read_bytes()).hexdigest())
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'verification.json').write_text(json.dumps(dict(baselineUnchanged=True,
        sourceObjectCount=len(originals),sourceFingerprintsPreserved=True,unrelatedVisibilityPreserved=True,
        addedObjectsReopened=len(added),addedFingerprintsPreserved=True,savedComponentReopened=True,
        apertureProbes=after_probes,render='reopened-full-frontage.png',componentSha256=report['componentSha256']),indent=2)+'\n')
    print('LCH203_COMPONENT_REOPENED_VERIFIED',len(added),len(after_probes),flush=True)
    bpy.ops.wm.quit_blender()


if __name__=='__main__':
    main()
