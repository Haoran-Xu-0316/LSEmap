"""Register the historical Old Building entrance foyer to its existing doors.

Design Engine's2011built photographs and foyer plan support the split levels,
reception counter, waiting bench and red display walls. Plan scaling, heights,
hidden construction and furniture placement are estimates, not a current survey.
Only the public entrance sequence is represented; adjoining rooms and lift pockets remain absent.
"""
from pathlib import Path
import math
import bpy
from mathutils import Vector, Matrix
from build_room_samples167 import RoomGeometry
ROOT = Path(__file__).resolve().parents[2]
COLLECTION = 'OLD_MAIN_FOYER174'
PREFIX = 'OLD174_foyer_'
SOURCE = 'https://www.designengine.co.uk/projects/reception-london-school-of-economics/'


def entrance_frame():
    pane = bpy.data.objects['OLD_NEXT_GLAZING172_single_door_panes']
    vertices = [pane.matrix_world @ v.co for v in pane.data.vertices]
    normal = (pane.matrix_world.to_3x3().inverted().transposed() @ pane.data.polygons[0].normal).normalized()
    normal.z = 0; normal.normalize()
    # This normal points to Houghton Street in the accepted172door geometry.
    right = Vector((-normal.y, normal.x, 0))
    center = sum(vertices, Vector()) / len(vertices); center.z = min(v.z for v in vertices)
    coordinates = [(v-center).dot(right) for v in vertices]
    return center, right, normal, (max(coordinates)-min(coordinates))/122


def outside_copy(source, collection, origin, outward, added):
    """Keep entire connected exterior rail parts with exact vertices and loop UVs."""
    adjacency = {v.index:set() for v in source.data.vertices}
    for edge in source.data.edges:
        a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
    todo=set(adjacency);selected=set()
    while todo:
        seed=todo.pop();component={seed};stack=[seed]
        while stack:
            for other in adjacency[stack.pop()] & todo:
                todo.remove(other);component.add(other);stack.append(other)
        center=sum((source.matrix_world @ source.data.vertices[i].co for i in component),Vector())/len(component)
        if (center-origin).dot(outward)>0:selected.update(component)
    faces=[p for p in source.data.polygons if all(i in selected for i in p.vertices)]
    ids=sorted(selected);mapping={old:new for new,old in enumerate(ids)}
    mesh=bpy.data.meshes.new(PREFIX+'exterior_'+source.name.rsplit('_',1)[-1]);mesh.from_pydata([source.data.vertices[i].co for i in ids],[],[[mapping[i]for i in p.vertices]for p in faces]);mesh.update()
    for mat in source.data.materials:mesh.materials.append(mat)
    for target,original in zip(mesh.polygons,faces):target.material_index=original.material_index
    for source_uv in source.data.uv_layers:
        uv=mesh.uv_layers.new(name=source_uv.name)
        for target,original in zip(mesh.polygons,faces):
            for a,b in zip(target.loop_indices,original.loop_indices):uv.data[a].uv=source_uv.data[b].uv
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(mesh.name,mesh);obj.matrix_world=source.matrix_world.copy();collection.objects.link(obj);added.append(obj.name)


def apply_old_foyer174():
    if bpy.data.collections.get(COLLECTION):return {'code':'OLD','version':174,'alreadyApplied':True}
    origin,right,outward,scale=entrance_frame()
    inward=-outward
    collection=bpy.data.collections.new(COLLECTION);bpy.data.collections['OLD_EXTERIOR'].children.link(collection)
    g=RoomGeometry(collection,PREFIX)
    colours={'wall':(.76,.75,.69),'white':(.80,.78,.72),'dark':(.055,.049,.043),'red':(.38,.008,.014),'steel':(.37,.39,.38),'carpet':(.25,.24,.215),'glass':(.30,.002,.004),'light':(.90,.89,.79)}
    for key,colour in colours.items():
        mat=g.materials[key];mat.diffuse_color=(*colour,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
    g.materials['glass']['webOpacity']=.20
    g.materials['glass'].node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
    def p(x,y):return ((x-762)*scale,(814-y)*scale)
    lower=.69;upper=1.245
    outline=[p(x,y)for x,y in [(550,685),(953,685),(953,786),(835,786),(835,804),(823,814),(701,814),(690,804),(690,786),(550,786)]]
    g.prism('lower_limestone_floor','white',outline,lower-.14,.14)
    # Preserve the full outside threshold; trim only its unseen inside portion.
    threshold=bpy.data.objects['OLD_NEXT_ACCESS_threshold_landing']
    import bmesh
    clipped=threshold.copy();clipped.data=threshold.data.copy();clipped.name=PREFIX+'outside_threshold';bpy.data.collections['OLD_EXTERIOR'].objects.link(clipped)
    bm=bmesh.new();bm.from_mesh(clipped.data)
    point=clipped.matrix_world.inverted() @ origin
    normal=clipped.matrix_world.to_3x3().transposed() @ outward
    result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=point,plane_no=normal,clear_inner=True,clear_outer=False)
    edges=[e for e in result['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(clipped.data);bm.free();clipped.data.update()
    added=[clipped.name]
    upper_outline=[p(x,y)for x,y in [(692,643),(692,488),(833,488),(833,643)]]
    g.prism('upper_dark_wood_floor','dark',upper_outline,upper-.14,.14)
    x0,d0=p(701,685);x1,d1=p(823,643);run=(d1-d0)/4
    for i in range(4):
        top=lower+(i+1)*(upper-lower)/4
        g.box('four_solid_risers','white',((x0+x1)/2,d0+(i+.5)*run,(lower-.14+top)/2),(x1-x0,run,top-lower+.14))
    # Low side panels are observed; their exact thickness is estimated.
    for start,end in [(550,692),(833,953)]:
        a,d=p(start,685);b,_=p(end,685)
        g.box('split_level_back_wall','wall',((a+b)/2,d+.095,lower+1.48),(b-a,.19,2.96))
        g.box('ruby_display_backing','red',((a+b)/2,d-.022,lower+1.45),(b-a-.10,.035,2.65))
        g.box('display_clear_skin','glass',((a+b)/2,d-.048,lower+1.45),(b-a-.10,.012,2.65))
        g.box('display_skirt','dark',((a+b)/2,d-.055,lower+.09),(b-a,.045,.18))
    # Two partial side walls retain an open cutaway, not an invented closed roof.
    front=p(550,786)[1];back=p(550,685)[1]
    for pixel in [550,953]:
        x,_=p(pixel,685);g.box('vestibule_sidewalls','wall',(x,(front+back)/2,lower+1.55),(.18,back-front,3.1))
    # Upper corridor wall strips stop at the photo-visible lift pockets.
    for pixel in [692,833]:
        x,_=p(pixel,643)
        for ya,yb in [(643,605),(542,488)]:
            _,a=p(pixel,ya);_,b=p(pixel,yb)
            g.box('upper_corridor_walls','wall',(x,(a+b)/2,upper+1.50),(.16,b-a,3))
    # The built photograph shows a shallow arch; omit its unmodelled crest.
    left,depth=p(692,641);right_edge,_=p(833,641);center=(left+right_edge)/2
    inner_half=2.35;spring=2.0;rise=1.0
    arch=[(left,upper),(left,upper+3.3),(right_edge,upper+3.3),(right_edge,upper),(center+inner_half,upper),(center+inner_half,upper+spring)]
    arch.extend((center+inner_half*math.cos(i*math.pi/24),upper+spring+rise*math.sin(i*math.pi/24))for i in range(1,25))
    arch.append((center-inner_half,upper))
    g.prism('upper_corridor_arch','wall',arch,depth-.12,.24)
    vertices,faces=g.batches[('upper_corridor_arch','wall')]
    g.batches[('upper_corridor_arch','wall')]=([(x,z,y)for x,y,z in vertices],[tuple(reversed(f))for f in faces])
    # Lift pockets lie outside the reliably registered central strip and remain unbuilt.
    # Long dark waiting bench and two stone reception counter sections.
    a,d=p(591,747);b,_=p(675,747)
    g.box('waiting_bench','dark',((a+b)/2,d,lower+.45),(b-a,.50,.075))
    for x in [a+.18,b-.18]:g.box('bench_supports','steel',(x,d,lower+.21),(.075,.38,.42))
    x,d=p(884,744);g.box('reception_counter','white',(x,d,lower+.46),(2.55,.68,.92))
    g.box('accessible_counter','white',(x-1.55,d,lower+.37),(.54,.68,.74))
    for shift in [-.70,.65]:
        g.box('counter_monitor_stands','dark',(x+shift,d,lower+1.04),(.035,.035,.20))
        g.box('counter_monitors','dark',(x+shift,d+.035,lower+1.18),(.38,.035,.24))
    # Stainless guards follow the relocated four-riser stair sequence.
    for x in [x0-.09,x1+.09]:
        for d,z in [(d0-.10,lower),(d1+.13,upper)]:g.tube('guard_posts','steel',(x,d,z),(x,d,z+.90),.023)
        g.tube('guard_handrails','steel',(x,d0-.15,lower+.90),(x,d1+.20,upper+.90),.023)
    for px in [617,710,805,899]:
        x,d=p(px,751)
        g.tube('pendant_stems','steel',(x,d,lower+2.8),(x,d,lower+3.18),.013)
        g.tube('disc_light_rims','dark',(x,d,lower+2.73),(x,d,lower+2.80),.24)
        g.tube('disc_light_diffusers','light',(x,d,lower+2.72),(x,d,lower+2.733),.22)
    objects=g.finish()
    # Display covers are single outward skins, avoiding overlapping pane sides.
    cover=next(o for o in objects if o.name==PREFIX+'display_clear_skin')
    mesh=bmesh.new();mesh.from_mesh(cover.data)
    bmesh.ops.delete(mesh,geom=[f for f in mesh.faces if f.normal.y>-.99],context='FACES')
    mesh.to_mesh(cover.data);mesh.free();cover.data.update()
    assert len(cover.data.polygons)==2
    g.solid_proof.pop('display_clear_skin')
    # The localXYbasis has positive determinant: right cross inward is+Z.
    basis=Matrix(((right.x,inward.x,0,origin.x),(right.y,inward.y,0,origin.y),(0,0,1,0),(0,0,0,1)))
    for obj in objects:obj.matrix_world=basis;obj['referencePeriod']='2011';obj['dimensionBasis']='photo-plan-estimate'
    added.extend(obj.name for obj in objects)
    archived=['OLD_NEXT_ACCESS_foyer_four_steps','OLD_NEXT_ACCESS_foyer_gf_landing','OLD_NEXT_ACCESS_interior_handrails',threshold.name,'OLD_NEXT_ACCESS_rail_posts','OLD_NEXT_ACCESS_rail_feet']
    for name in archived[-2:]:outside_copy(bpy.data.objects[name],bpy.data.collections['OLD_EXTERIOR'],origin,outward,added)
    for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
    return {'code':'OLD','version':174,'addedObjects':added,'archivedObjects':archived,'changedObjects':[],
      'source':SOURCE,'sourcePeriod':'2011built refurbishment','scope':'Registered main entrance foyer only; adjoining rooms and present-day arrangement unverified',
      'dimensions':'Door-width-scaled architect plan; furniture, height and thickness estimates',
      'frame':{'origin':list(origin),'right':list(right),'outward':list(outward),'metersPerPlanPixel':scale},
      'levels':{'lower':lower,'upper':upper,'risers':4,'rise':(upper-lower)/4,'run':run},'solidProof':g.solid_proof,'outwardGlassSkinFaces':2}
