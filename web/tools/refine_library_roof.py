"""Reconstruct LRB's north-facing sliced dome from the archived aerial.

Run in Blender's Text Editor. Dimensions are visual estimates, not a survey.
The 2024/25 roof heat-pump installation is documented but not reconstructed:
no current photograph establishes its geometry or equipment positions.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import shutil
import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage31'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v30.blend'))

def fingerprint(obj):
    vertices = array.array('f', [0]) * (3 * len(obj.data.vertices))
    obj.data.vertices.foreach_get('co', vertices)
    indices = array.array('i', [0]) * len(obj.data.loops)
    obj.data.loops.foreach_get('vertex_index', indices)
    return hashlib.sha256(vertices.tobytes() + indices.tobytes()).hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects if o.type == 'MESH'}
collection = bpy.data.collections['LRB_EXTERIOR']
removed = ['LRB_roof_lightwell_white_funnel', 'LRB_roof_oculus_ring',
           'LRB_roof_oculus_glazing', 'LRB_roof_triangular_lattice']
for name in removed:
    obj = bpy.data.objects.get(name)
    assert obj and obj.name in collection.objects, name
    bpy.data.objects.remove(obj, do_unlink=True)
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
centre = next(b['center'] for b in site['buildings'] if b['code'] == 'LRB')
origin = Vector((centre[0] - 2, centre[1] + 3, 23))
radius, height = 9.8, 9.0
# X east, Y north. The north-facing aperture follows z + y = 10 locally.
cut_height = 10.0

def material(name, colour, roughness, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*colour, 1)
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = mat.diffuse_color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return mat

shell_mat = material('LRB_V31_light_metal_roof', (.57, .59, .59), .49, .35)
seam_mat = material('LRB_V31_roof_seams', (.26, .28, .29), .5, .4)
glass_mat = material('LRB_V31_north_roof_glass', (.27, .38, .42), .13)
glass_mat['webOpacity'] = .58
glass_mat.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value = .8

created = []
def mesh(name, vertices, faces, mat, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(origin + Vector(v)) for v in vertices], [], faces)
    data.materials.append(mat)
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj['sharedInteriorRoof'] = True
    obj['source_status'] = 'Photographic silhouette reconstruction; metric dimensions estimated'
    for face in data.polygons:
        face.use_smooth = smooth
    created.append(name)
    return obj

# An ellipsoidal cap keeps a curved crown, unlike the previous truncated cone.
segments, rings = 128, 48
vertices = [(0, 0, height)]
for row in range(1, rings + 1):
    theta = row * math.pi / (2 * rings)
    for i in range(segments):
        phi = i * 2 * math.pi / segments
        vertices.append((radius * math.sin(theta) * math.cos(phi),
                         radius * math.sin(theta) * math.sin(phi), height * math.cos(theta)))
faces = [(0, 1+i, 1+(i+1) % segments) for i in range(segments)]
for row in range(rings - 1):
    first = 1 + row * segments
    for i in range(segments):
        nxt = (i + 1) % segments
        faces.append((first+i, first+segments+i, first+segments+nxt, first+nxt))
shell = mesh('LRB_V31_sliced_dome_shell', vertices, faces, shell_mat, True)
bm = bmesh.new()
bm.from_mesh(shell.data)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
    plane_co=origin+Vector((0, 0, cut_height)), plane_no=Vector((0, 1, 1)),
    clear_outer=True, dist=1e-6)
boundary = [v.co-origin for v in bm.verts if abs((v.co-origin).y+(v.co-origin).z-cut_height)<1e-4]
bm.to_mesh(shell.data)
bm.free()
assert len(boundary) > 50
# Order the cut perimeter in its own plane to form the north-facing glass aperture.
centre_cut = sum(boundary, Vector()) / len(boundary)
u, v = Vector((1,0,0)), Vector((0,-1,1)).normalized()
boundary.sort(key=lambda p: math.atan2((p-centre_cut).dot(v), (p-centre_cut).dot(u)))
mesh('LRB_V31_north_aperture_glass', [centre_cut]+boundary,
     [(0, i+1, (i+1)%len(boundary)+1) for i in range(len(boundary))], glass_mat)

seam_vertices, seam_faces = [], []
def tube(a, b, thickness):
    direction = b-a
    if direction.length < 1e-5:
        return
    normal = direction.normalized()
    reference = Vector((0,0,1)) if abs(normal.z)<.95 else Vector((1,0,0))
    axis = normal.cross(reference).normalized()
    other = normal.cross(axis)
    start = len(seam_vertices)
    for point in (a,b):
        for i in range(6):
            seam_vertices.append(point+thickness*(axis*math.cos(i*math.pi/3)+other*math.sin(i*math.pi/3)))
    seam_faces.extend((start+i,start+(i+1)%6,start+(i+1)%6+6,start+i+6) for i in range(6))

# Standing seams follow the curvature and stop at the aperture boundary.
for i in range(32):
    phi = 2*math.pi*i/32
    points = [Vector(((radius+.075)*math.sin(j*math.pi/192)*math.cos(phi),
                      (radius+.075)*math.sin(j*math.pi/192)*math.sin(phi),
                      (height+.075)*math.cos(j*math.pi/192))) for j in range(97)]
    for a,b in zip(points,points[1:]):
        da,db = a.y+a.z-cut_height,b.y+b.z-cut_height
        if da>0 and db>0:
            continue
        if (da>0)!=(db>0):
            cut = a+(b-a)*da/(da-db)
            if da>0: a=cut
            else: b=cut
        tube(a,b,.035)
for a,b in zip(boundary,boundary[1:]+boundary[:1]): tube(a,b,.08)
# Thin framing within the glazed cut, clipped against its measured polygon.
for x in [-6,-3,0,3,6]:
    crossings=[]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):
        if (a.x<=x<b.x) or (b.x<=x<a.x):crossings.append(a+(b-a)*(x-a.x)/(b.x-a.x))
    if len(crossings)==2:tube(*crossings,.04)
mesh('LRB_V31_dome_standing_seams_and_frame',seam_vertices,seam_faces,seam_mat,True)

after = {o.name:fingerprint(o) for o in bpy.data.objects if o.type=='MESH'}
assert all(after[name]==value for name,value in before.items() if name not in removed)
for name in ['room-studies.json','room-spaces.json','building-review.json']:
    shutil.copyfile(ROOT/'result/blender/stage30'/name, OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v31.blend'))
(OUT/'library-roof-audit.json').write_text(json.dumps({
    'reference':'data/collections/library_round5/photos/LRB_5ea4100c9303.jpg',
    'descriptionSource':'https://www.lse.ac.uk/library/about/history-of-lse-library',
    'recentChangeSource':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Organisation/LSE-Estates-Annual-Report-2024-25.pdf',
    'removed':removed,'created':created,'unchangedMeshes':len(before)-len(removed),
    'estimates':{'radius':radius,'height':height,'baseHeight':23,'cutPlane':'local y+z=10, north-facing'},
    'limitations':'Roof silhouette only. Dimensions estimated. Current heat-pump arrangement and perimeter roof remain unverified. Interiors unchanged.'
},indent=2)+'\n')
print('LIBRARY_ROOF_COMPLETE',created)
