"""Build CBG's photographed open top end and stepped roof as a private candidate.

Apply to an already loaded campus. This module never opens, saves or publishes a
file. Coordinates and registered design-stage stair dimensions are estimates; the
candidate requires full roof and circulation registration before release.
"""
from pathlib import Path
import hashlib
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'CBG_NEXT_ROOF_'
HEIGHT = 52.2
STEP = HEIGHT / 13
TERRACE = 11 * STEP
REAR_ROOF = 12 * STEP
ROOF_TERRACE_END_X = -22.4
ROOF_TERRACE_FRONT_Y = 6.2
CORE_END_X = -.5
# Rectangular estimate from the four registered level12 stair-well corners.
UPPER_STAIR_X = (-12.95, -9.25)
UPPER_STAIR_Y = (-1.02, 4.08)
SOURCES = [
    'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_05.jpg',
    'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_12.jpg',
    'data/collections/exteriors/images/cbg_archdaily_033.jpg',
    'data/collections/exteriors/images/cbg_archdaily_034.jpg',
    'data/collections/cbg_roof_registration/level12-plan-rshp-2016.jpg',
    'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_17.jpg',
]
CORNERS = ((0,0,0),(1,0,0),(1,1,0),(0,1,0),
           (0,0,1),(1,0,1),(1,1,1),(0,1,1))
BOX_FACES = ((3,2,1,0),(4,5,6,7),(0,1,5,4),
             (1,2,6,5),(2,3,7,6),(3,0,4,7))
STAIR_PARTS = {
    'CBG_D_tower_meandering_stair_treads': (216,24),
    'CBG_D_tower_stair_stringers': (18,2),
    'CBG_D_tower_stair_handrails': (18,2),
    'CBG_D_tower_stair_slotted_pale_guards': (810,90),
    'CBG_D_tower_stair_landing_platforms': (9,1),
}


def coordinates():
    import json
    site = json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    cx, cy = next(b['center'] for b in site['buildings'] if b['code']=='CBG')
    angle = math.radians(58)
    c, s = math.cos(angle), math.sin(angle)
    def local(point):
        return Vector((c*(point.x-cx)+s*(point.y-cy),
                       -s*(point.x-cx)+c*(point.y-cy), point.z))
    def world(point):
        x,y,z = point
        return Vector((cx+c*x-s*y, cy+s*x+c*y, z))
    return local, world


def clip_face(polygon, axis, value, above):
    """Interpolate original corner UVs while clipping one convex face."""
    result, intersections = [], []
    sign = 1 if above else -1
    for a,b in zip(polygon, polygon[1:]+polygon[:1]):
        da, db = sign*(a[0][axis]-value), sign*(b[0][axis]-value)
        if da >= -1e-5:
            result.append(a)
        if (da > 1e-5 and db < -1e-5) or (da < -1e-5 and db > 1e-5):
            t = da/(da-db)
            position=a[0].lerp(b[0],t)
            position[axis]=value
            point = (position, [u.lerp(v,t) for u,v in zip(a[1],b[1])])
            result.append(point)
            intersections.append(point)
    unique={}
    for point in result:
        unique.setdefault(tuple(round(x,5) for x in point[0]),point)
    result=list(unique.values())
    if len(result)<3:return [],intersections
    area=sum(((result[i][0]-result[0][0]).cross(result[i+1][0]-result[0][0]) for i in range(1,len(result)-1)),Vector()).length
    return (result if area>1e-10 else []), intersections


def clip_solid(faces, axis, value, above, closed):
    retained, cut = [], []
    for polygon, material, smooth in faces:
        clipped, intersections = clip_face(polygon,axis,value,above)
        if clipped:
            retained.append((clipped,material,smooth))
        cut.extend(intersections)
    if closed and retained:
        unique = {}
        for point in cut:
            unique.setdefault(tuple(round(x,5) for x in point[0]),point)
        if len(unique)>=3:
            points=list(unique.values())
            centre=sum((p[0] for p in points),Vector())/len(points)
            axes=[i for i in range(3) if i!=axis]
            points.sort(key=lambda p:math.atan2(p[0][axes[1]]-centre[axes[1]],p[0][axes[0]]-centre[axes[0]]))
            normal=(points[1][0]-points[0][0]).cross(points[2][0]-points[0][0])
            desired=-1 if above else 1
            if normal[axis]*desired<0:points.reverse()
            # A cut return inherits the nearest original face's material. Its UV
            # corners follow the intersected surface rather than losing UV0.
            retained.append((points,faces[0][1],False))
    return retained


def subtract_region(faces, bounds, closed):
    """Subtract an axis-aligned volume, retaining closed prism fragments."""
    points=[p[0] for polygon,_,_ in faces for p in polygon]
    if any(max(p[i] for p in points)<=bounds[0][i]+1e-5 or min(p[i] for p in points)>=bounds[1][i]-1e-5 for i in range(3)):
        return [faces]
    outside=[]
    remaining=faces
    for axis in range(3):
        for value,above in ((bounds[0][axis],True),(bounds[1][axis],False)):
            if not remaining:return outside
            points=[p[0] for face,_,_ in remaining for p in face]
            distances=[(p[axis]-value)*(1 if above else -1) for p in points]
            if min(distances)>=-1e-5:continue
            if max(distances)<=1e-5:
                outside.append(remaining)
                return outside
            piece=clip_solid(remaining,axis,value,not above,closed)
            if piece:outside.append(piece)
            remaining=clip_solid(remaining,axis,value,above,closed)
    return outside


def conform_shell(pieces, regions):
    """Align cut-face edges and remove paired internal partition faces."""
    planes=sorted(set((axis,region[side][axis]) for region in regions for axis in range(3) for side in (0,1)))
    faces=[]
    for piece in pieces:
        for polygon,material,smooth in piece:
            parts=[polygon]
            for axis,value in planes:
                divided=[]
                for part in parts:
                    distances=[point[0][axis]-value for point in part]
                    if min(distances)<-1e-5 and max(distances)>1e-5:
                        divided.extend(poly for above in (True,False) if (poly:=clip_face(part,axis,value,above)[0]))
                    else:divided.append(part)
                parts=divided
            faces.extend((part,material,smooth) for part in parts)
    # Mathutils uses float coordinates. Share a geometric point within the
    # source precision rather than rounding the two sides of a cut separately.
    points=[]
    snapped=[]
    for polygon,material,smooth in faces:
        adjusted=[]
        for point,uv in polygon:
            match=next((p for p in points if (p-point).length<3e-5),None)
            if match is None:match=point;points.append(point)
            if not adjusted or (match-adjusted[-1][0]).length>1e-7:adjusted.append((match,uv))
        if len(adjusted)>1 and (adjusted[0][0]-adjusted[-1][0]).length<1e-7:adjusted.pop()
        if len(adjusted)>=3:snapped.append((adjusted,material,smooth))
    # Insert shared cut vertices into both edge loops. A T junction may look
    # sealed in a raster view but otherwise leaves bevels and native solids open.
    faces=[]
    for polygon,material,smooth in snapped:
        conformed=[]
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            conformed.append(a)
            edge=b[0]-a[0];length=edge.length_squared
            if length<1e-12:continue
            intermediate=[]
            for point in points:
                t=(point-a[0]).dot(edge)/length
                if 1e-5<t<1-1e-5 and (point-(a[0]+edge*t)).length<3e-5:
                    intermediate.append((t,(point,[u.lerp(v,t) for u,v in zip(a[1],b[1])])) )
            conformed.extend(point for _,point in sorted(intermediate,key=lambda row:row[0]))
        faces.append((conformed,material,smooth))
    grouped={}
    for face in faces:
        key=tuple(sorted(tuple(round(value,5) for value in point[0]) for point in face[0]))
        grouped.setdefault(key,[]).append(face)
    assert all(len(group)<=2 for group in grouped.values()), [(key,len(group)) for key,group in grouped.items() if len(group)>2]
    return [group[0] for group in grouped.values() if len(group)==1]


def components(mesh):
    neighbours={v.index:set() for v in mesh.vertices}
    for edge in mesh.edges:
        a,b=edge.vertices
        neighbours[a].add(b);neighbours[b].add(a)
    unseen=set(neighbours)
    while unseen:
        seed=min(unseen);unseen.remove(seed);group={seed};stack=[seed]
        while stack:
            for other in neighbours[stack.pop()]:
                if other in unseen:unseen.remove(other);group.add(other);stack.append(other)
        yield group


def replace_mesh(source, local, world, regions):
    mesh=source.data
    points=[local(source.matrix_world@v.co) for v in mesh.vertices]
    faces_by_vertex={i:[] for i in range(len(points))}
    for face in mesh.polygons:
        for i in face.vertices:faces_by_vertex[i].append(face)
    vertices,polygons,materials,smoothing=[],[],[],[]
    uv_values=[[] for _ in mesh.uv_layers]
    altered=0
    for group in components(mesh):
        source_faces={face.index:face for i in group for face in faces_by_vertex[i]}
        faces=[]
        for face in source_faces.values():
            polygon=[(points[mesh.loops[i].vertex_index],
                      [Vector(layer.data[i].uv) for layer in mesh.uv_layers])
                     for i in face.loop_indices]
            faces.append((polygon,face.material_index,face.use_smooth))
        closed=len(group)==8 and len(faces)==6
        assert closed or (len(group)==4 and len(faces)==1), (source.name,len(group),len(faces))
        pieces=[faces]
        for region in regions:
            pieces=[part for piece in pieces for part in subtract_region(piece,region,closed)]
        original_count=sum(len(p) for p,_,_ in faces)
        unchanged=len(pieces)==1 and sum(len(p) for p,_,_ in pieces[0])==original_count
        if unchanged:
            unchanged=all((a[0]-b[0]).length<1e-7 for (pa,_,_),(pb,_,_) in zip(faces,pieces[0]) for a,b in zip(pa,pb))
        altered+=not unchanged
        if unchanged:
            mapping={index:len(vertices)+offset for offset,index in enumerate(sorted(group))}
            vertices.extend(mesh.vertices[index].co.copy() for index in sorted(group))
            for face in source_faces.values():
                polygons.append(tuple(mapping[index] for index in face.vertices))
                materials.append(face.material_index);smoothing.append(face.use_smooth)
                for original,values in zip(mesh.uv_layers,uv_values):values.extend(Vector(original.data[index].uv) for index in face.loop_indices)
            continue
        shell=conform_shell(pieces,regions) if closed and not unchanged else [face for piece in pieces for face in piece]
        indexed={}
        for polygon,material,smooth in shell:
            distinct={}
            for point,uv in polygon:
                distinct.setdefault(tuple(round(value,5) for value in point),(point,uv))
            polygon=list(distinct.values())
            if len(polygon)<3:continue
            normal=sum(((polygon[i][0]-polygon[0][0]).cross(polygon[i+1][0]-polygon[0][0]) for i in range(1,len(polygon)-1)),Vector())
            if normal.length<1e-10:continue
            indices=[]
            for point,_ in polygon:
                key=tuple(round(value,5) for value in point)
                if key not in indexed:
                    indexed[key]=len(vertices)
                    # A cut can modify a long column while retaining its lower
                    # corners. Reuse those native coordinates exactly instead
                    # of round-tripping them through world/local float matrices.
                    original=next((i for i in group if (points[i]-point).length<3e-5),None)
                    vertices.append(mesh.vertices[original].co.copy() if original is not None
                                    else source.matrix_world.inverted()@world(point))
                indices.append(indexed[key])
            assert len(set(indices))==len(indices), (source.name,'collapsed cut face')
            polygons.append(tuple(indices))
            materials.append(material);smoothing.append(smooth)
            for values,j in zip(uv_values,range(len(uv_values))):values.extend(p[1][j] for p in polygon)
    if not altered:return None
    target=source.copy();target.data=bpy.data.meshes.new(PREFIX+'trim_'+source.name)
    target.name=target.data.name
    target.data.from_pydata(vertices,[],polygons)
    for material in mesh.materials:target.data.materials.append(material)
    for face,material,smooth in zip(target.data.polygons,materials,smoothing):
        face.material_index=material;face.use_smooth=smooth
    for original,values in zip(mesh.uv_layers,uv_values):
        layer=target.data.uv_layers.new(name=original.name)
        for corner,value in zip(layer.data,values):corner.uv=value
        layer.active_render=original.active_render
    target.data.update();target['originalObject']=source.name
    for owner in source.users_collection:owner.objects.link(target)
    source.hide_render=True;source.hide_set(True)
    target.hide_render=False;target.hide_set(False)
    return dict(source=source.name,target=target.name,alteredComponents=altered)


def add_roof_garden(mesh_object,box,slab,frame,exterior):
    """Build photographed roof surfaces and planting as bounded native meshes."""
    import random
    def finish(name,colour,roughness=.8):
        material=slab.copy();material.name=PREFIX+name
        material.diffuse_color=(*colour,1)
        node=material.node_tree.nodes['Principled BSDF']
        node.inputs['Base Color'].default_value=material.diffuse_color
        node.inputs['Metallic'].default_value=0
        node.inputs['Roughness'].default_value=roughness
        return material
    paving=finish('roof_paving',(.67,.63,.53))
    soil=finish('garden_soil',(.075,.060,.041))
    edging=finish('garden_edging',(.18,.19,.17))
    wood=finish('bench_oak',(.37,.24,.12))
    greens=[finish('garden_leaf_'+str(i),colour) for i,colour in enumerate([
        (.13,.24,.045),(.22,.34,.12),(.28,.36,.19)])]
    flowers=[finish('garden_flower_'+str(i),colour) for i,colour in enumerate([
        (.70,.35,.025),(.33,.19,.39)])]
    buckets={material.name:[material,[],[]] for material in greens+flowers}
    def prism(material,vertices):
        _,points,faces=buckets[material.name];offset=len(points)
        points.extend(vertices);faces.extend(tuple(offset+i for i in face) for face in BOX_FACES)
    randomizer=random.Random(12)
    floor=REAR_ROOF+.04
    tiles,faces=[],[]
    columns=32;rows=13
    dx=(ROOF_TERRACE_END_X+42)/columns;dy=(14-ROOF_TERRACE_FRONT_Y)/rows
    for column in range(columns):
        for row in range(rows):
            x=-42+column*dx;y=ROOF_TERRACE_FRONT_Y+row*dy
            lo=(x+.006,y+.006,floor);hi=(x+dx-.006,y+dy-.006,floor+.028)
            offset=len(tiles);tiles.extend(tuple(lo[i]+(hi[i]-lo[i])*bit[i] for i in range(3)) for bit in CORNERS)
            faces.extend(tuple(offset+i for i in face) for face in BOX_FACES)
    mesh_object('roof_paving_tiles',tiles,faces,paving,exterior)
    for bed,(start,end) in enumerate([(-40.9,-35.8),(-34.65,-29.55),(-28.4,-23.3)]):
        for side,x in enumerate((start,end-.10)):
            box(f'bed_{bed}_end_{side}',(x,10.0,floor+.028),(x+.1,13.25,floor+.48),edging)
        for side,y in enumerate((10.0,13.15)):
            box(f'bed_{bed}_edge_{side}',(start+.10,y,floor+.028),(end-.10,y+.10,floor+.48),edging)
        box(f'bed_{bed}_soil',(start+.10,10.10,floor+.028),(end-.10,13.15,floor+.42),soil)
        # The photographed end benches share the bed support. Slats are batched
        # by finish rather than represented as hundreds of separate objects.
        slats=[];slat_faces=[]
        for slat in range(18):
            y=10.03+slat*.177;lo=(end-.10,y,floor+.48);hi=(end+.37,y+.145,floor+.535)
            offset=len(slats);slats.extend(tuple(lo[i]+(hi[i]-lo[i])*bit[i] for i in range(3)) for bit in CORNERS)
            slat_faces.extend(tuple(offset+i for i in face) for face in BOX_FACES)
        mesh_object(f'bed_{bed}_bench_slats',slats,slat_faces,wood,exterior)
        # Species are not inferred from pixels. Vary photographed green/yellow/
        # purple planting forms within each retained closed bed and soil surface.
        for plant in range(120):
            x=randomizer.uniform(start+.24,end-.25);y=randomizer.uniform(10.24,13.01)
            z=floor+.42;material=greens[plant%3]
            height=randomizer.uniform(.23,.67)
            for leaf in range(5):
                angle=leaf*math.tau/5+randomizer.random()*.5
                c,s=math.cos(angle),math.sin(angle);lean=randomizer.uniform(.10,.28)
                base=(x,y,z);tip=(x+c*lean,y+s*lean,z+height)
                a=(s*.027,-c*.027,0);b=(c*.008,s*.008,0)
                vertices=[]
                for point,width in ((base,1),(tip,.23)):
                    vertices.extend(tuple(point[i]+width*(a[i]*sa+b[i]*sb) for i in range(3))
                                    for sa,sb in ((-1,-1),(1,-1),(1,1),(-1,1)))
                prism(material,vertices)
            if plant%3==0:
                colour=flowers[(plant//3)%2];radius=randomizer.uniform(.035,.065)
                # Small closed heads, with the angular sides oriented away from
                # the same repeated direction. All foliage shares five meshes.
                lo=(x-radius,y-radius,z+height-.015);hi=(x+radius,y+radius,z+height+.025)
                prism(colour,[tuple(lo[i]+(hi[i]-lo[i])*bit[i] for i in range(3)) for bit in CORNERS])
    for material,vertices,faces in buckets.values():
        mesh_object(material.name.removeprefix(PREFIX)+'_geometry',vertices,faces,material,exterior)
    # The built photograph shows the core's green cap, edged by gravel. The
    # envelope beneath is retained; no hidden plant or new rooms are invented.
    gravel=finish('green_roof_gravel',(.41,.39,.33))
    turf=finish('core_green_roof',(.17,.29,.045))
    box('core_roof_gravel',(-20.8,4.5,HEIGHT+.015),(-1.1,13.6,HEIGHT+.075),gravel)
    box('core_green_roof',(-20.35,4.95,HEIGHT+.075),(-1.55,13.15,HEIGHT+.125),turf)



def add_registered_upper_stair(mesh_object, box, frame, slab, interior):
    """Replace the estimated top straight flight with the plan's return stair."""
    x_left, x_right = UPPER_STAIR_X
    y_front, y_rear = UPPER_STAIR_Y
    base = TERRACE - .02
    rise = STEP / 28
    going = .268
    landing_end = y_rear - 14 * going
    lane_width = 1.515
    lanes = [(x_right - .12 - lane_width, x_right - .12),
             (x_left + .12, x_left + .12 + lane_width)]
    wood = bpy.data.objects['CBG_D_tower_meandering_stair_treads'].data.materials[0]
    blue = bpy.data.objects['CBG_D_tower_stair_stringers'].data.materials[0]
    pale = bpy.data.objects['CBG_D_tower_stair_slotted_pale_guards'].data.materials[0]
    treads, tread_faces, slots, slot_faces = [], [], [], []

    def packed_box(vertices, faces, lo, hi):
        offset = len(vertices)
        vertices.extend(tuple(lo[i] + (hi[i] - lo[i]) * bit[i] for i in range(3))
                        for bit in CORNERS)
        faces.extend(tuple(offset + i for i in face) for face in BOX_FACES)

    def beam(name, start, end, width, depth, material):
        start, end = Vector(start), Vector(end)
        direction = (end - start).normalized()
        across = Vector((1, 0, 0)) * width / 2
        normal = direction.cross(across.normalized()).normalized() * depth / 2
        points = [tuple(point + a * across + b * normal)
                  for point in (start, end)
                  for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        return mesh_object(name, points, BOX_FACES, material, interior)

    def handrail(name, start, end):
        start, end = Vector(start), Vector(end)
        direction = (end - start).normalized()
        across = Vector((1, 0, 0))
        if abs(direction.dot(across)) > .9:
            across = Vector((0, 1, 0))
        across = (across - direction * across.dot(direction)).normalized()
        normal = direction.cross(across)
        points = [tuple(point + .023 * (across * math.cos(i * math.tau / 8)
                                        + normal * math.sin(i * math.tau / 8)))
                  for point in (start, end) for i in range(8)]
        faces = [tuple(reversed(range(8))), tuple(range(8, 16))]
        faces.extend((i, (i + 1) % 8, (i + 1) % 8 + 8, i + 8) for i in range(8))
        return mesh_object(name, points, faces, frame, interior)

    for flight, (x0, x1) in enumerate(lanes):
        start_y, end_y = (y_rear, landing_end) if flight == 0 else (landing_end, y_rear)
        start_z = base + flight * STEP / 2
        direction = -1 if flight == 0 else 1
        for step in range(14):
            edge_a = start_y + direction * step * going
            edge_b = edge_a + direction * going
            top = start_z + (step + 1) * rise
            packed_box(treads, tread_faces, (x0, min(edge_a, edge_b), top - .12),
                       (x1, max(edge_a, edge_b), top))
        for side, x in enumerate((x0 - .025, x1 + .025)):
            beam(f'upper_stair_stringer_{flight}_{side}', (x, start_y, start_z - .07),
                 (x, end_y, start_z + STEP / 2 - .07), .12, .24, blue)
            handrail(f'upper_stair_handrail_{flight}_{side}', (x, start_y, start_z + 1.05),
                     (x, end_y, start_z + STEP / 2 + 1.05))
            beam(f'upper_stair_guard_base_{flight}_{side}', (x, start_y, start_z + .08),
                 (x, end_y, start_z + STEP / 2 + .08), .06, .13, pale)
            beam(f'upper_stair_guard_cap_{flight}_{side}', (x, start_y, start_z + .995),
                 (x, end_y, start_z + STEP / 2 + .995), .075, .09, pale)
            for strip in range(35):
                fraction = strip / 34
                y = start_y + (end_y - start_y) * fraction
                z = start_z + STEP / 2 * fraction
                packed_box(slots, slot_faces, (x - .035, y - .04, z + .14),
                           (x + .035, y + .04, z + .97))
    mesh_object('upper_stair_treads', treads, tread_faces, wood, interior)
    # The mid landing joins both lanes. The top landing joins the existing
    # academic floor behind the registered well instead of floating at its side.
    mid = base + STEP / 2
    box('upper_stair_mid_landing', (x_left, y_front, mid - .17),
        (x_right, landing_end, mid), slab, interior)
    box('upper_stair_top_landing', (x_left, y_rear, REAR_ROOF - .19),
        (x_right, y_rear + 1.1, REAR_ROOF - .02), slab, interior)
    for strip in range(33):
        x = x_left + (strip + .5) * (x_right - x_left) / 33
        packed_box(slots, slot_faces, (x - .035, y_front - .04, mid + .12),
                   (x + .035, y_front + .04, mid + .98))
    handrail('upper_stair_mid_guard', (x_left, y_front, mid + 1.05),
             (x_right, y_front, mid + 1.05))
    box('upper_stair_mid_guard_base', (x_left, y_front - .04, mid - .005),
        (x_right, y_front + .04, mid + .15), pale, interior)
    box('upper_stair_mid_guard_cap', (x_left, y_front - .04, mid + .96),
        (x_right, y_front + .04, mid + 1.035), pale, interior)
    # The retained upper floor must have a guard at the open well's outer edges.
    for side, x in enumerate((x_left - .04, x_right + .04)):
        handrail(f'upper_stair_floor_guard_{side}', (x, y_front, REAR_ROOF + 1.03),
                 (x, y_rear, REAR_ROOF + 1.03))
        box(f'upper_stair_floor_guard_base_{side}', (x - .04, y_front, REAR_ROOF - .02),
            (x + .04, y_rear, REAR_ROOF + .14), pale, interior)
        box(f'upper_stair_floor_guard_cap_{side}', (x - .04, y_front, REAR_ROOF + .94),
            (x + .04, y_rear, REAR_ROOF + 1.025), pale, interior)
        for strip in range(46):
            y = y_front + (strip + .5) * (y_rear - y_front) / 46
            packed_box(slots, slot_faces, (x - .035, y - .04, REAR_ROOF + .1),
                       (x + .035, y + .04, REAR_ROOF + .96))
    mesh_object('upper_stair_pale_slots', slots, slot_faces, pale, interior)


def apply_cbg_roof_envelope():
    """Create a full roof-envelope candidate; do not silently publish it."""
    assert not any(o.name.startswith(PREFIX) for o in bpy.data.objects), 'Candidate already present'
    local,world=coordinates()
    exterior=bpy.data.collections['CBG_EXTERIOR']
    interior=bpy.data.collections['CBG_PUBLIC_INTERIOR_study']
    before=set(bpy.data.objects)
    originals=sorted([o for o in set(exterior.all_objects)|set(interior.all_objects) if o.type=='MESH' and not o.hide_render],key=lambda o:o.name)
    replacements=[]
    # Preserve the first eight inherited flights exactly. The registered upper
    # well is a different return-stair layout; translating the old ninth flight
    # cannot reproduce its footprint, midpoint landing or floor connection.
    import bmesh
    for name, (count, last) in STAIR_PARTS.items():
        source = bpy.data.objects[name]
        assert len(source.data.vertices) == count * 8
        target = source.copy()
        target.data = source.data.copy()
        target.name = PREFIX + 'connected_' + name
        mesh = bmesh.new()
        mesh.from_mesh(target.data)
        mesh.verts.ensure_lookup_table()
        bmesh.ops.delete(mesh, geom=list(mesh.verts)[(count - last) * 8:], context='VERTS')
        mesh.to_mesh(target.data)
        mesh.free()
        for owner in source.users_collection:
            owner.objects.link(target)
        target['originalObject'] = source.name
        target.hide_render = False
        target.hide_set(False)
        source.hide_render = True
        source.hide_set(True)
        replacements.append(dict(source=name, target=target.name, removedUpperComponents=last))
    for source in originals:
        if source.name in STAIR_PARTS:continue
        glass=any(m and ('glass' in m.name.lower() or m.get('webOpacity',1)<1) for m in source.data.materials)
        roof_cut_height=REAR_ROOF-.01 if glass else REAR_ROOF+.30
        # The registered level12 plan reserves the middle rear volume for the
        # core. Only the terrace end and the photographed setback are lower.
        regions=[((-45.0,ROOF_TERRACE_FRONT_Y,roof_cut_height),(ROOF_TERRACE_END_X,18.0,56.0)),
                 ((CORE_END_X,4.2,roof_cut_height),(9.0,18.0,56.0))]
        # Primary corner columns and the main top beam support the retained
        # canopy. Secondary mullions and the middle floor cannot span the void.
        if 'external_I_columns' not in source.name and 'roof_and_ground_plates' not in source.name and 'red_roof_recess' not in source.name:
            regions.append(((-.5,-2.5,TERRACE-.01 if glass else TERRACE+.40),(7.5,4.2,56.0 if glass else HEIGHT-.38)))
        if any(part in source.name for part in ('tower_floor_plates', 'tower_front_galleries')):
            # A real floor12 opening above both flights, without cutting the
            # level11 entry floor or laying a slab across the walking headroom.
            regions.append(((UPPER_STAIR_X[0] + .03, UPPER_STAIR_Y[0], REAR_ROOF - .30),
                            (UPPER_STAIR_X[1] - .03, UPPER_STAIR_Y[1], REAR_ROOF + .12)))
        selected=[]
        for region in regions:
            pts=[local(source.matrix_world@v.co) for v in source.data.vertices]
            if not any(max(p[i] for p in pts)<=region[0][i] or min(p[i] for p in pts)>=region[1][i] for i in range(3)):
                selected.append(region)
        if selected:
            record=replace_mesh(source,local,world,selected)
            if record:replacements.append(record)
    def mesh_object(name,vertices,faces,material,owner):
        mesh=bpy.data.meshes.new(PREFIX+name);mesh.from_pydata([world(v) for v in vertices],[],faces);mesh.materials.append(material);mesh.update()
        obj=bpy.data.objects.new(mesh.name,mesh);owner.objects.link(obj)
        uv=mesh.uv_layers.new(name='SurfaceUV')
        for face in mesh.polygons:
            pts=[mesh.vertices[i].co for i in face.vertices];u=(pts[1]-pts[0]).normalized();n=(pts[1]-pts[0]).cross(pts[-1]-pts[0]).normalized();v=n.cross(u)
            for loop,p in zip(face.loop_indices,pts):uv.data[loop].uv=((p-pts[0]).dot(u),(p-pts[0]).dot(v))
        return obj
    def box(name,lo,hi,material,owner=exterior):
        return mesh_object(name,[tuple(lo[i]+(hi[i]-lo[i])*bit[i] for i in range(3)) for bit in CORNERS],BOX_FACES,material,owner)
    frame=bpy.data.materials['CBG_D_charcoal_thermal_frames']
    slab=bpy.data.materials['CBG_D_exposed_concrete']
    glass=bpy.data.objects['GLASS181_CBG_NEXT_neutral_end_wall_glazing'].data.materials[0].copy()
    glass.name=PREFIX+'balustrade_glass';glass['webClosedGlazing']=True;glass['webOpacity']=.28
    glass.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=0
    box('end_terrace_deck',(-.5,-1.95,TERRACE+.05),(7.0,4.2,TERRACE+.17),slab,interior)
    box('rear_terrace_deck',(-42,ROOF_TERRACE_FRONT_Y,REAR_ROOF-.08),(ROOF_TERRACE_END_X,14,REAR_ROOF+.04),slab,interior)
    box('end_setback_roof',(-.5,4.2,REAR_ROOF-.08),(7,14,REAR_ROOF+.04),slab,interior)
    # A bridge joins the prior landing and the relocated flight beside the stair,
    # with no slab laid across walking treads.
    box('upper_stair_connection',(-8.60,1.55,TERRACE-.18),(-3.40,2.70,TERRACE-.02),slab,interior)
    add_registered_upper_stair(mesh_object, box, frame, slab, interior)
    box('end_guard',(7.03,-1.85,TERRACE+.22),(7.055,4.10,TERRACE+1.30),glass)
    box('end_guard_shoe',(7.0,-1.85,TERRACE+.15),(7.12,4.10,TERRACE+.24),frame)
    box('end_guard_cap',(7.025,-1.85,TERRACE+1.29),(7.065,4.10,TERRACE+1.32),frame)
    box('side_guard',(-.45,-2.06,TERRACE+.22),(6.92,-2.035,TERRACE+1.30),glass)
    box('side_guard_shoe',(-.45,-2.10,TERRACE+.15),(6.92,-1.99,TERRACE+.24),frame)
    box('rear_roof_guard',(-41.90,14.03,REAR_ROOF+.14),(ROOF_TERRACE_END_X,14.055,REAR_ROOF+1.18),glass)
    box('rear_roof_guard_shoe',(-41.90,14.0,REAR_ROOF+.04),(ROOF_TERRACE_END_X,14.12,REAR_ROOF+.16),frame)
    box('terrace_far_guard',(-42.055,ROOF_TERRACE_FRONT_Y,REAR_ROOF+.14),(-42.03,13.9,REAR_ROOF+1.18),glass)
    box('setback_rear_guard',(-.40,14.03,REAR_ROOF+.14),(6.90,14.055,REAR_ROOF+1.18),glass)
    box('end_roof_guard',(7.03,4.3,REAR_ROOF+.14),(7.055,13.90,REAR_ROOF+1.18),glass)
    # The terrace is outside the upper academic enclosure. New cut surfaces
    # alone would leave that occupied strip open to the garden.
    thermal=glass.copy();thermal.name=PREFIX+'terrace_thermal_glass';thermal['webOpacity']=.82
    for bay in range(8):
        x=-42+bay*(ROOF_TERRACE_END_X+42)/8
        width=(ROOF_TERRACE_END_X+42)/8
        box(f'terrace_thermal_pane_{bay}',(x+.055,ROOF_TERRACE_FRONT_Y-.11,REAR_ROOF+.12),
            (x+width-.055,ROOF_TERRACE_FRONT_Y-.085,HEIGHT-.20),thermal)
        box(f'terrace_thermal_post_{bay}',(x-.035,ROOF_TERRACE_FRONT_Y-.15,REAR_ROOF+.075),
            (x+.035,ROOF_TERRACE_FRONT_Y-.045,HEIGHT-.18),frame)
    box('terrace_thermal_sill',(-42,ROOF_TERRACE_FRONT_Y-.155,REAR_ROOF+.075),
        (ROOF_TERRACE_END_X,ROOF_TERRACE_FRONT_Y-.04,REAR_ROOF+.125),frame)
    box('terrace_thermal_head',(-42,ROOF_TERRACE_FRONT_Y-.155,HEIGHT-.235),
        (ROOF_TERRACE_END_X,ROOF_TERRACE_FRONT_Y-.04,HEIGHT-.18),frame)
    # The design plan shows access from the retained core, with a real opening
    # through its envelope. Door dimensions and the unpictured hardware are
    # deliberately kept as estimates, without adding room contents.
    x=ROOF_TERRACE_END_X
    for name,lo,hi in [
        ('core_terrace_wall_near',(x-.06,ROOF_TERRACE_FRONT_Y,REAR_ROOF+.075),(x+.10,7.35,HEIGHT-.20)),
        ('core_terrace_wall_far',(x-.06,8.75,REAR_ROOF+.075),(x+.10,14,HEIGHT-.20)),
        ('core_terrace_door_head',(x-.06,7.35,REAR_ROOF+2.25),(x+.10,8.75,HEIGHT-.20))]:
        box(name,lo,hi,slab)
    for leaf in range(2):
        y=7.38+leaf*.685
        box(f'core_terrace_door_{leaf}',(x+.01,y,REAR_ROOF+.13),(x+.035,y+.655,REAR_ROOF+2.20),thermal)
        box(f'core_terrace_door_handle_{leaf}',(x-.06,y+.54,REAR_ROOF+.95),(x-.015,y+.57,REAR_ROOF+1.20),frame)
    for y in (7.34,8.03,8.73):
        box('core_door_frame_'+str(y),(x-.07,y,REAR_ROOF+.075),(x+.10,y+.04,REAR_ROOF+2.25),frame)
    box('core_door_threshold',(x-.15,7.35,REAR_ROOF+.04),(x+.13,8.75,REAR_ROOF+.12),slab)
    add_roof_garden(mesh_object,box,slab,frame,exterior)
    # A photographed pale green rooftop screen returns behind the end recess.
    # Its function and absolute elevation remain unknown, so it is a visible
    # envelope study rather than a fabricated plant-room interior.
    screen=glass.copy();screen.name=PREFIX+'pale_green_screen'
    screen.diffuse_color=(.42,.57,.55,1);screen['webOpacity']=.80
    node=screen.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value=screen.diffuse_color
    node.inputs['Roughness'].default_value=.42
    # Joas Souza's built end view shows four rows of translucent screen panels.
    for column in range(4):
        for row in range(4):
            y=5.45+column*1.87;z=REAR_ROOF+.24+row*.885
            box(f'green_screen_{column}_{row}',(-.39,y,z),(-.365,y+1.85,z+.865),screen)
            for side in (0,1):
                yy=y+.06+side*1.72
                box(f'green_screen_clamp_{column}_{row}_{side}',(-.445,yy,z+.405),(-.31,yy+.05,z+.455),frame)
    box('green_screen_base',(-.5,5.4,REAR_ROOF+.15),(-.27,12.95,REAR_ROOF+.23),frame)
    # Twin folded assemblies reproduce visible silhouette and underside panels.
    # Their exact equipment function, materials and dimensions remain unverified.
    metal=frame.copy();metal.name=PREFIX+'folded_assembly_finish'
    metal.diffuse_color=(.29,.32,.33,1)
    node=metal.node_tree.nodes['Principled BSDF'];node.inputs['Base Color'].default_value=metal.diffuse_color;node.inputs['Metallic'].default_value=.3;node.inputs['Roughness'].default_value=.45
    for index,y in enumerate((-.25,1.80)):
        verts=[(-.10,y,48.9),(6.40,y,51.55),(6.40,y+1.75,51.55),(-.10,y+1.75,48.9),
               (-.10,y,49.12),(6.40,y,51.77),(6.40,y+1.75,51.77),(-.10,y+1.75,49.12)]
        mesh_object(f'suspended_{index}_folded_shell',verts,BOX_FACES,metal,exterior)
        box(f'suspended_{index}_front_return',(6.24,y,50.65),(6.42,y+1.75,51.77),metal)
        for rib in range(9):
            x=.10+rib*.69;z=48.9+(x+.1)*2.65/6.5
            box(f'suspended_{index}_underside_rib_{rib}',(x,y-.03,z-.10),(x+.06,y+1.78,z+.02),frame)
    added=[o.name for o in set(bpy.data.objects)-before]
    return dict(status='private-candidate-awaiting-roof-and-circulation-registration',
        addedObjects=added,archivedObjects=[r['source'] for r in replacements],changedObjects=[],replacements=replacements,
        dimensions=dict(top=HEIGHT,openEndFloor=TERRACE,rearRoof=REAR_ROOF,cornerStartX=-.5,roofTerraceEndX=ROOF_TERRACE_END_X,roofTerraceFrontY=ROOF_TERRACE_FRONT_Y,retainedCoreX=[ROOF_TERRACE_END_X,CORE_END_X],upperStairX=UPPER_STAIR_X,upperStairY=UPPER_STAIR_Y,upperStairFlights=2,upperStairTreads=28),
        references=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),captureDate='unknown',
                         role='published2016design-drawing' if ('archdaily_03' in p or '-plan-' in p) else 'built-photograph') for p in SOURCES],
        sourceURL='https://rshp.com/projects/education/lse-centre-building/',
        limitations=['Only overall52.2m height is cited; local dimensions and inherited equal storeys are estimates.',
                     'The rear terrace/core split is proportionally registered from the2016 level12 plan; the published built photograph supports a bounded garden, not an empty full-length roof. Absolute geometry and actual current stair dimensions still require review.',
                     'Suspended assemblies are photo-derived forms; equipment function is not established.',
                     'Current hidden plant, all upper rooms and full internal layout remain unverified.'])
