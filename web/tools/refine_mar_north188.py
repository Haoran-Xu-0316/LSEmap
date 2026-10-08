"""Candidate north envelope registered to MAR's built front photograph.

The opening shifts approximately10.25m in the retained local coordinates.
Front walls, recessed side walls and their roof plates are rebuilt together.
This component alone is not release-ready: roof terrace continuity and complete
upper-wing registration still require review. Recess clearance passes
the separate saved-component verification.
No files are opened or saved here. All original meshes remain archived intact.
"""
import bpy
from mathutils import Vector
from refine_mar_exterior174 import world, local
from refine_mar_podium187 import box

SOURCES = [
    'MAR_NEXT_ENVELOPE_north_three_row_walls',
    'MAR_EXTERIOR168_north_screen_dielectric_glass',
    'MAR_NEXT_ENVELOPE_north_three_row_frames',
    'MAR_D5_north115_roof',
]
NAMES = ['MAR188_north_walls', 'MAR188_north_glass', 'MAR188_north_frames', 'MAR188_north_roofs',
         'MAR188_middle_walls', 'MAR188_middle_glass', 'MAR188_middle_frames']
MIDDLE_SOURCE = 'MAR_V115_retained_MAR_north_middle_wall_pierced_wall'
OPENING = (-4.95, 8.25)
FRONT_ROWS = [(24, 26.2), (27, 29.2), (30, 32.2)]
RETURN_ROWS = [(24, 27.55), (28.65, 32.2)]


def trim_inherited_recess(collection):
    """Subtract the relocated court from inherited meshes, interpolating corner UVs."""
    outline=[(-4.95,21.16),(-4.95,8.8),(1.75,3.5),(8.25,16),(8.25,21.16)]
    planes=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        normal=Vector((a[1]-b[1],b[0]-a[0],0))
        planes.append((normal,-normal.dot(Vector((*a,0)))+.06*normal.length))
    planes.extend([(Vector((0,0,1)),-12.801),(Vector((0,0,-1)),32.851)])

    # Replace the middle front as a complete wall/window system, including its
    # old glazing and joinery, while keeping the projecting concrete fins.
    front=[(Vector((1,0,0)),30.061),(Vector((-1,0,0)),24.061),
           (Vector((0,1,0)),-18.20),(Vector((0,-1,0)),19.12),
           (Vector((0,0,1)),-12.801),(Vector((0,0,-1)),23.3991)]
    regions=[planes,front]

    def split(polygon,normal,offset,sign):
        output=[]
        for a,b in zip(polygon,polygon[1:]+polygon[:1]):
            da=sign*(normal.dot(a[0])+offset)
            db=sign*(normal.dot(b[0])+offset)
            if da>=-1e-7:output.append(a)
            if (da>1e-7 and db<-1e-7)or(da<-1e-7 and db>1e-7):
                t=da/(da-db)
                output.append((a[0].lerp(b[0],t),[u.lerp(v,t)for u,v in zip(a[1],b[1])]))
        return output if len(output)>=3 else []

    def subtract(polygon,region):
        retained=[]
        for normal,offset in region:
            if not polygon:break
            distances=[normal.dot(p[0])+offset for p in polygon]
            if min(distances)>=-1e-7:continue
            outside=split(polygon,normal,offset,-1)
            if outside:retained.append(outside)
            polygon=split(polygon,normal,offset,1)
        return retained

    records=[]
    visible=set()
    def collect(group):
        if group.hide_render:return
        visible.update(obj for obj in group.objects if not obj.hide_render)
        for child in group.children:collect(child)
    collect(bpy.context.scene.collection)
    building=next(group for group in bpy.data.collections['02_LSE_BUILDINGS'].children if group.name.startswith('MAR_'))
    visible.intersection_update(building.all_objects)
    sources=sorted([obj for obj in visible if obj.type=='MESH' and not obj.name.startswith('MAR188_')],key=lambda obj:obj.name)
    for source in sources:
        if any(token in source.name for token in ['upper_screen_shafts','upper_screen_hammerheads','north115_fin','north_screen_horizontal_edges']):continue
        mesh=source.data
        if not mesh.vertices or not mesh.polygons:continue
        mesh.calc_loop_triangles()
        triangles={}
        for triangle in mesh.loop_triangles:triangles.setdefault(triangle.polygon_index,[]).append(triangle)
        points=[local(source.matrix_world@vertex.co)for vertex in mesh.vertices]
        if all(any(max(normal.dot(point)+offset for point in points)<=1e-7 for normal,offset in region)for region in regions):continue
        vertices,faces,indices,smoothing=[],[],[],[]
        uv_values=[[]for layer in mesh.uv_layers]
        changed=0

        def polygon(loops):
            return [(points[mesh.loops[i].vertex_index],[Vector(layer.data[i].uv)for layer in mesh.uv_layers])for i in loops]

        def append(poly,face):
            offset=len(vertices);vertices.extend(p[0]for p in poly)
            faces.append(tuple(range(offset,offset+len(poly))))
            indices.append(face.material_index);smoothing.append(face.use_smooth)
            for j,values in enumerate(uv_values):values.extend(p[1][j]for p in poly)

        for face in mesh.polygons:
            poly=polygon(face.loop_indices)
            if all(any(max(normal.dot(p[0])+offset for p in poly)<=1e-7 for normal,offset in region)for region in regions):
                append(poly,face);continue
            changed+=1
            for triangle in triangles[face.index]:
                pieces=[polygon(triangle.loops)]
                for region in regions:pieces=[part for piece in pieces for part in subtract(piece,region)]
                for retained in pieces:append(retained,face)
        if not changed:continue
        name='MAR188_trim_'+source.name.removeprefix('MAR_')
        replacement=source.copy();replacement.data=bpy.data.meshes.new(name)
        inverse=source.matrix_world.inverted()
        replacement.data.from_pydata([inverse@world(*p)for p in vertices],[],faces)
        for material in mesh.materials:replacement.data.materials.append(material)
        for face,index,smooth in zip(replacement.data.polygons,indices,smoothing):face.material_index=index;face.use_smooth=smooth
        for layer,values in zip(mesh.uv_layers,uv_values):
            uv=replacement.data.uv_layers.new(name=layer.name)
            for corner,value in zip(uv.data,values):corner.uv=value
            uv.active_render=layer.active_render
        replacement.data.update();replacement.name=name
        for owner in source.users_collection:owner.objects.link(replacement)
        replacement.hide_render=False;replacement.hide_set(False)
        source.hide_render=True;source.hide_set(True)
        records.append(dict(source=source.name,target=replacement.name,intersectingSourceFaces=changed))
    return records


def restore_recess_floor_infill():
    """Recover only floor fragments removed by the former court, with original UVs.

    The inherited upper-front setback at y18.20 stays open. Four retained floor
    datums are included; the podium and roof terraces remain separate.
    """
    def planes(outline):
        result=[]
        for a,b in zip(outline,outline[1:]+outline[:1]):
            normal=Vector((a[1]-b[1],b[0]-a[0],0))
            result.append((normal,-normal.dot(Vector((*a,0)))+.06*normal.length))
        return result
    old=planes([(-15.2,21.16),(-15.2,8.8),(-8.5,3.5),(-2,16),(-2,21.16)])
    new=planes([(-4.95,21.16),(-4.95,8.8),(1.75,3.5),(8.25,16),(8.25,21.16)])
    def clip(poly,plane,sign=1):
        normal,offset=plane;output=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=sign*(normal.dot(a[0])+offset);db=sign*(normal.dot(b[0])+offset)
            if da>=-1e-7:output.append(a)
            if (da>1e-7 and db<-1e-7)or(da<-1e-7 and db>1e-7):
                t=da/(da-db)
                output.append((a[0].lerp(b[0],t),[u.lerp(v,t)for u,v in zip(a[1],b[1])]))
        return output if len(output)>=3 else []
    records=[]
    for way in ['1376078543','1376078544']:
        for height in ['17.5','21.9','26.2','30.5']:
            source=bpy.data.objects[f'MAR_MAR_floor_way/{way}_{height}']
            retained=bpy.data.objects[f'MAR_V115_retained_MAR_floor_way/{way}_{height}']
            mesh=source.data;mesh.calc_loop_triangles()
            vertices=[];faces=[];indices=[];uvs=[[]for layer in mesh.uv_layers]
            for triangle in mesh.loop_triangles:
                poly=[(local(source.matrix_world@mesh.vertices[mesh.loops[i].vertex_index].co),
                       [Vector(layer.data[i].uv)for layer in mesh.uv_layers])for i in triangle.loops]
                cut_planes=old+([(Vector((0,-1,0)),18.20)]if float(height)>23.399 else [])
                for plane in cut_planes:
                    poly=clip(poly,plane)
                    if not poly:break
                pieces=[]
                for plane in new:
                    if not poly:break
                    outside=clip(poly,plane,-1)
                    if outside:pieces.append(outside)
                    poly=clip(poly,plane)
                for piece in pieces:
                    area=sum((piece[i][0]-piece[0][0]).cross(piece[i+1][0]-piece[0][0]).length/2 for i in range(1,len(piece)-1))
                    if area<1e-8:continue
                    offset=len(vertices);vertices.extend(world(*v[0])for v in piece)
                    faces.append(tuple(range(offset,len(vertices))));indices.append(mesh.polygons[triangle.polygon_index].material_index)
                    for j,values in enumerate(uvs):values.extend(v[1][j]for v in piece)
            assert faces,source.name
            name=f'MAR188_floor_infill_{way}_{height}'
            result=bpy.data.meshes.new(name);result.from_pydata(vertices,[],faces)
            for material in mesh.materials:result.materials.append(material)
            for face,index in zip(result.polygons,indices):face.material_index=index
            for layer,values in zip(mesh.uv_layers,uvs):
                target=result.uv_layers.new(name=layer.name)
                for corner,value in zip(target.data,values):corner.uv=value
                target.active_render=layer.active_render
            result.update();obj=bpy.data.objects.new(name,result)
            for owner in retained.users_collection:owner.objects.link(obj)
            obj['candidateOnly']=True
            records.append(dict(source=source.name,ownerSource=retained.name,target=obj.name,faces=len(faces)))
    return records


def apply_mar_north188():
    if all(bpy.data.objects.get(name) for name in NAMES):
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    assert not any(bpy.data.objects.get(name) for name in NAMES), 'Partial MAR188 component'
    originals = [bpy.data.objects[name] for name in SOURCES]
    assert all(not obj.hide_render for obj in originals)
    collection = bpy.data.collections['MAR_EXTERIOR']
    batches = {kind: [] for kind in ['wall', 'glass', 'frame', 'roof','middle_wall','middle_glass','middle_frame']}
    windows = []

    def wall(start, end, columns, rows, label, lower=23.4, upper=32.65, prefix=""):
        start, end = Vector(start), Vector(end)
        axis = (end - start).normalized()
        normal = Vector((axis.y, -axis.x))
        length = (end - start).length

        def point(x, z, depth=0):
            xy = start + axis * x + normal * depth
            return (xy.x, xy.y, z)

        def quad(kind, x0, x1, z0, z1, depth=0, reverse=False):
            vertices = [point(x0, z0, depth), point(x1, z0, depth), point(x1, z1, depth), point(x0, z1, depth)]
            batches[prefix+kind].append(list(reversed(vertices)) if reverse else vertices)

        cuts = []
        for column in range(columns):
            centre = (column + .5) * length / columns
            width = min(1.45, length / columns - .5)
            for bottom, top in rows:
                cuts.append((centre - width / 2, centre + width / 2, bottom, top))
        xs = sorted({0, length, *[value for cut in cuts for value in cut[:2]]})
        zs = sorted({lower, upper, *[value for cut in cuts for value in cut[2:]]})
        occupied = set()
        for i in range(len(xs)-1):
            for j in range(len(zs)-1):
                x, z = (xs[i]+xs[i+1])/2, (zs[j]+zs[j+1])/2
                if not any(a < x < c and b < z < d for a,c,b,d in cuts):
                    occupied.add((i,j))
        for i,j in sorted(occupied):
            a,c = xs[i:i+2]
            b,d = zs[j:j+2]
            quad('wall',a,c,b,d)
            quad('wall',a,c,b,d,-.1,True)
            # Only external and aperture boundaries get returns; no internal caps.
            if (i-1,j) not in occupied:
                batches[prefix+'wall'].append([point(a,b),point(a,d),point(a,d,-.1),point(a,b,-.1)])
            if (i+1,j) not in occupied:
                batches[prefix+'wall'].append([point(c,d),point(c,b),point(c,b,-.1),point(c,d,-.1)])
            if (i,j-1) not in occupied:
                batches[prefix+'wall'].append([point(a,b),point(a,b,-.1),point(c,b,-.1),point(c,b)])
            if (i,j+1) not in occupied:
                batches[prefix+'wall'].append([point(c,d),point(c,d,-.1),point(a,d,-.1),point(a,d)])
        for a,c,b,d in cuts:
            quad('glass',a+.02,c-.02,b+.02,d-.02,-.12)
            for x in [a,c]:
                quad('frame',x-.025,x+.025,b,d,-.09)
            for z in [b,d]:
                quad('frame',a,c,z-.025,z+.025,-.09)
            z = b+(d-b)*.52
            quad('frame',a,c,z-.018,z+.018,-.08)
            windows.append(dict(wall=label,centre=point((a+c)/2,(b+d)/2,-.12),normal=list(normal)))

    left, right = OPENING
    # Retain the previous total15front columns and floor datums, redistributing
    # columns at a comparable pitch over the photo-registered solid spans.
    wall((left,18.8),(-30,18.8),9,FRONT_ROWS,'west-front')
    wall((24,18.8),(right,18.8),6,FRONT_ROWS,'east-front')
    wall((left,8.8),(left,18.8),3,RETURN_ROWS,'west-return')
    wall((right,18.8),(right,16),1,RETURN_ROWS,'east-return')
    wall((right,16),(1.75,3.5),4,RETURN_ROWS,'diagonal-return')
    wall((1.75,3.5),(left,8.8),3,RETURN_ROWS,'west-diagonal-return')
    for a,c in [(-30,left),(right,24)]:
        batches['roof'].extend(box(a,c,8.8,18.8,32.78,32.85))

    middle_rows=[(14.7,17.7),(18.9,21.9)]
    for start,end,columns,label in [
        ((left,18.9),(-30,18.9),9,'west-front'),
        ((24,18.9),(right,18.9),6,'east-front'),
        ((left,8.8),(left,18.9),3,'west-return'),
        ((right,18.9),(right,16),1,'east-return'),
        ((right,16),(1.75,3.5),4,'diagonal-return'),
        ((1.75,3.5),(left,8.8),3,'west-diagonal-return')]:
        wall(start,end,columns,middle_rows,'middle-'+label,12.8,23.399,'middle_')

    materials = [original.data.materials[0] for original in originals]
    materials[1] = materials[1].copy()
    materials[1].name = 'MAR188_retained_dielectric_glass'
    middle_glass=bpy.data.objects['MAR174_retained_loggia_12'].data.materials[0].copy()
    middle_glass.name='MAR188_middle_retained_dielectric_glass'
    materials.extend([bpy.data.objects[MIDDLE_SOURCE].data.materials[0],middle_glass,
                      bpy.data.objects['MAR_NEXT_LETTER165_retained_01_frames'].data.materials[0]])
    for name,kind,material in zip(NAMES,batches,materials):
        vertices,faces = [],[]
        for quad in batches[kind]:
            offset=len(vertices)
            vertices.extend(world(*point) for point in quad)
            faces.append(tuple(range(offset,offset+len(quad))))
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(vertices,[],faces)
        mesh.materials.append(material)
        uv=mesh.uv_layers.new(name='Metric')
        for face in mesh.polygons:
            for loop in face.loop_indices:
                vertex=vertices[mesh.loops[loop].vertex_index]
                uv.data[loop].uv=(vertex.x,vertex.z)
        mesh.update()
        obj=bpy.data.objects.new(name,mesh)
        collection.objects.link(obj)
        obj['candidateOnly']=True
    for original in originals:
        original.hide_render=True
        original.hide_set(True)
    bpy.data.objects[MIDDLE_SOURCE].hide_render=True
    bpy.data.objects[MIDDLE_SOURCE].hide_set(True)
    trims=trim_inherited_recess(collection)
    floors=restore_recess_floor_infill()
    return dict(
        alreadyApplied=False,addedObjects=NAMES+[r['target']for r in trims]+[r['target']for r in floors],archivedObjects=SOURCES+[MIDDLE_SOURCE]+[r['source']for r in trims],changedObjects=[],trimRecords=trims,floorInfillRecords=floors,
        openingLocalX=list(OPENING),windowProbes=windows,frontColumns=[9,6],
        releaseReady=False,
        limitations=[
            'Photo registration is approximate; opening edges are not surveyed dimensions.',
            'Previous floor datums, window width and total front column count retained as estimates.',
            'Side-wall depth and diagonal termination inherited then shifted; full upper-wing plan not verified.',
            'Middle and upper inherited meshes trimmed with corner UV interpolation; roof-terrace continuity still requires review.',
            'Do not integrate or deploy before roof-terrace continuity and whole-building visual review are resolved.',
        ],
    )
