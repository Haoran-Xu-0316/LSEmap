"""Build CBG's photographed open top end and stepped roof as a private candidate.

Apply to an already loaded campus. This module never opens, saves or publishes a
file. Coordinates and the relocated upper stair connection are estimates; the
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
SOURCES = [
    'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_05.jpg',
    'data/collections/campus_photos_round2/images/CBG/CBG_cbg_joas_12.jpg',
    'data/collections/exteriors/images/cbg_archdaily_033.jpg',
    'data/collections/exteriors/images/cbg_archdaily_034.jpg',
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


def apply_cbg_roof_envelope():
    """Create a full roof-envelope candidate; do not silently publish it."""
    assert not any(o.name.startswith(PREFIX) for o in bpy.data.objects), 'Candidate already present'
    local,world=coordinates()
    exterior=bpy.data.collections['CBG_EXTERIOR']
    interior=bpy.data.collections['CBG_PUBLIC_INTERIOR_study']
    before=set(bpy.data.objects)
    originals=sorted([o for o in set(exterior.all_objects)|set(interior.all_objects) if o.type=='MESH' and not o.hide_render],key=lambda o:o.name)
    replacements=[]
    # Relocate the last estimated stair as a whole flight, never crop individual
    # steps to manufacture a void. The new connection remains subject to review.
    for name,(count,last) in STAIR_PARTS.items():
        source=bpy.data.objects[name]
        assert len(source.data.vertices)==count*8
        target=source.copy();target.data=source.data.copy();target.name=PREFIX+'connected_'+name
        inverse=source.matrix_world.inverted()
        for vertex in target.data.vertices[(count-last)*8:]:
            point=local(source.matrix_world@vertex.co);point.x-=4.65
            vertex.co=inverse@world(point)
        for owner in source.users_collection:owner.objects.link(target)
        target['originalObject']=source.name
        target.hide_render=False;target.hide_set(False);source.hide_render=True;source.hide_set(True)
        replacements.append(dict(source=name,target=target.name,wholeFlightShiftX=-4.65))
    for source in originals:
        if source.name in STAIR_PARTS:continue
        glass=any(m and ('glass' in m.name.lower() or m.get('webOpacity',1)<1) for m in source.data.materials)
        regions=[((-45.0,4.2,REAR_ROOF-.01 if glass else REAR_ROOF+.30),(9.0,18.0,56.0))]
        # Primary corner columns and the main top beam support the retained
        # canopy. Secondary mullions and the middle floor cannot span the void.
        if 'external_I_columns' not in source.name and 'roof_and_ground_plates' not in source.name and 'red_roof_recess' not in source.name:
            regions.append(((-.5,-2.5,TERRACE-.01 if glass else TERRACE+.40),(7.5,4.2,56.0 if glass else HEIGHT-.38)))
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
    box('rear_terrace_deck',(-42,4.2,REAR_ROOF+.02),(7,14,REAR_ROOF+.08),slab,interior)
    # A bridge joins the prior landing and the relocated flight beside the stair,
    # with no slab laid across walking treads.
    box('upper_stair_connection',(-9.25,1.55,TERRACE-.10),(-3.40,2.45,TERRACE+.04),slab,interior)
    box('end_guard',(7.03,-1.85,TERRACE+.22),(7.055,4.10,TERRACE+1.30),glass)
    box('end_guard_shoe',(7.0,-1.85,TERRACE+.15),(7.12,4.10,TERRACE+.24),frame)
    box('end_guard_cap',(7.025,-1.85,TERRACE+1.29),(7.065,4.10,TERRACE+1.32),frame)
    box('side_guard',(-.45,-2.06,TERRACE+.22),(6.92,-2.035,TERRACE+1.30),glass)
    box('side_guard_shoe',(-.45,-2.10,TERRACE+.15),(6.92,-1.99,TERRACE+.24),frame)
    box('rear_roof_guard',(-41.90,14.03,REAR_ROOF+.14),(6.90,14.055,REAR_ROOF+1.18),glass)
    box('rear_roof_guard_shoe',(-41.90,14.0,REAR_ROOF+.07),(6.90,14.12,REAR_ROOF+.16),frame)
    box('end_roof_guard',(7.03,4.3,REAR_ROOF+.14),(7.055,13.90,REAR_ROOF+1.18),glass)
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
        dimensions=dict(top=HEIGHT,openEndFloor=TERRACE,rearRoof=REAR_ROOF,cornerStartX=-.5,rearStartY=4.2),
        references=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),captureDate='unknown',
                         role='published2016design-section' if 'archdaily_03' in p else 'built-photograph') for p in SOURCES],
        sourceURL='https://rshp.com/projects/education/lse-centre-building/',
        limitations=['Only overall52.2m height is cited; local dimensions and inherited equal storeys are estimates.',
                     'Whole rear-roof extent and upper-stair relocation require registered review before integration.',
                     'Suspended assemblies are photo-derived forms; equipment function is not established.',
                     'Current hidden plant, all upper rooms and full internal layout remain unverified.'])
