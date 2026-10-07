"""SAW historical upper-stair connection and retained-structure review.

The 2014 guide supports a central curved upper connection. Its registration
uses the retained opening and estimated dimensions, while side cores stay unbuilt.
The callable adds one scoped connection; file opening and saving belong to assembly.
"""
from pathlib import Path
import hashlib
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT = Path(__file__).resolve().parents[2]
COLLECTION = 'SAW_PUBLIC_INTERIOR_study'
STAIRS = 'SAW_spiral_stair_treads'
GUIDE = 'data/documents/saw_occupants_guide_2014.pdf'
SOURCE_URL = 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/SAW/Final-Web-version-of-Occupants-Guide.pdf'


def review_saw_structure171():
    """Report actual retained circulation gaps without inventing missing geometry."""
    collection = bpy.data.collections[COLLECTION]
    def descendants(parent):
        return [parent] + [item for child in parent.children for item in descendants(child)]
    assert collection in descendants(bpy.data.scenes['00_CAMPUS_COMPLETE'].collection)
    floors = sorted((o for o in collection.all_objects if o.name.startswith('SAW_SAW_floor_')), key=lambda o: float(o.name.rsplit('_', 1)[1]))
    stairs = bpy.data.objects[STAIRS]
    assert len(floors) == 7 and len(stairs.data.vertices) == 128 * 8
    trees = [(o.name, BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])) for o in floors]
    probes = []
    for index in range(128):
        points = [stairs.matrix_world @ v.co for v in stairs.data.vertices[index * 8:index * 8 + 8]]
        center = sum(points, Vector()) / 8
        center.z = max(p.z for p in points) + .001
        hits = []
        for name, tree in trees:
            hit = tree.ray_cast(center, Vector((0, 0, 1)), 30)
            if hit[0] is not None:
                hits.append(dict(floor=name, distance=hit[3]))
        probes.append(dict(tread=index, point=list(center), nearestFloorAbove=min(hits, key=lambda x: x['distance']) if hits else None))
    return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[],
        status='reviewed-structure-gaps-recorded-no-fabricated-replacement', productionInteriorCollection=COLLECTION,
        floorDatums=[float(o.name.rsplit('_', 1)[1]) for o in floors], retainedSpiralTreads=128,
        retainedSpiralTop=max((stairs.matrix_world @ v.co).z for v in stairs.data.vertices), floorClearanceProbes=probes,
        references=[dict(file=GUIDE, sha256=hashlib.sha256((ROOT / GUIDE).read_bytes()).hexdigest(), sourceURL=SOURCE_URL, publicationYear=2014, inspectedPages=[26,27,28,29,30], captureDate='Plan publication 2014; current condition unverified')],
        findings=[
            'Seven public floor sheets represent ground through sixth floor, but share a retained generic envelope; official upper-floor diagrams differ in setback and circulation.',
            'Retained continuous spiral stops at about14.30m while two upper sheets remain at18.0m and21.9m; no connected upper stair reconstruction is present.',
            '2014 guide pages26-30 show varying central stair outlines and independent side stair/lift cores; one repeated helix does not certify their built arrangement.',
            'Existing Denning and Three Tuns models are separate room studies, not complete registered floors.'],
        limitations=[
            'No new furniture, structure or exterior added. Original geometry, UV, transforms and materials retained.',
            'Plan pages are historical occupants diagrams without current measured registration. Exact core alignment, stair rise and changed use remain unverified.',
            'Per-tread upward rays report only existing floor-sheet intersections, not a whole-building collision or safety certificate.',
            'Do not fill upper levels by extending the generic helix or assume the existing floor sheets are exact as-built plans.'])

# Historical topology supported by the central curved stair on guide pages26/27.
# Registration reuses the retained public-stair axis; dimensions are estimates.
OWN_COLLECTION = 'SAW_STRUCTURE171_historical_upper_connection'
OWN_NAMES = ['SAW171_fifth_to_sixth_curved_treads', 'SAW171_upper_stair_landings', 'SAW171_upper_stair_guards']
CENTER = (-61.67495, 13.33058)
LOWER_Z, UPPER_Z = 18.0, 21.9
INNER_RADIUS, OUTER_RADIUS, STEP_COUNT = 1.05, 2.88, 26


def apply_saw_structure171():
    """Add one historical upper-floor curved connection, without changing source."""
    import math
    import bmesh
    if OWN_COLLECTION in bpy.data.collections:
        assert all(name in bpy.data.objects for name in OWN_NAMES)
        return dict(alreadyApplied=True, addedObjects=[], archivedObjects=[], changedObjects=[])
    report = review_saw_structure171()
    collection = bpy.data.collections.new(OWN_COLLECTION)
    bpy.data.collections[COLLECTION].children.link(collection)
    collection['evidence'] = '2014 occupants guide pages26/27: central upper curved stair'
    collection['registration'] = 'Retained central stair axis; radius/angles/treads estimated, not surveyed'
    mats = []
    for name, color in [('SAW171_historical_concrete',(.49,.49,.45,1)), ('SAW171_historical_dark_guard',(.075,.079,.075,1))]:
        material = bpy.data.materials.new(name);material.diffuse_color=color;material.use_nodes=True
        shader=material.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=color;shader.inputs['Roughness'].default_value=.68
        mats.append(material)
    groups = [([],[]),([],[]),([],[])]
    def solid(group, footprint, bottom, top):
        vertices,faces=groups[group];start=len(vertices);n=len(footprint)
        vertices.extend([(x,y,z)for z in (bottom,top)for x,y in footprint])
        faces.extend([tuple(start+i for i in reversed(range(n))),tuple(start+n+i for i in range(n))])
        faces.extend((start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i)for i in range(n))
    def point(radius,theta):return CENTER[0]+radius*math.cos(theta),CENTER[1]+radius*math.sin(theta)
    start_angle=math.radians(-70);sweep=math.pi
    for i in range(STEP_COUNT):
        a=start_angle+sweep*i/STEP_COUNT;b=start_angle+sweep*(i+1)/STEP_COUNT
        z=LOWER_Z+(UPPER_Z-LOWER_Z)*(i+1)/STEP_COUNT
        solid(0,[point(INNER_RADIUS,a),point(OUTER_RADIUS,a),point(OUTER_RADIUS,b),point(INNER_RADIUS,b)],z-.11,z)
        # Single curved vertical guard along the outer edge, batched by tread.
        solid(2,[point(OUTER_RADIUS+.018,a),point(OUTER_RADIUS+.07,a),point(OUTER_RADIUS+.07,b),point(OUTER_RADIUS+.018,b)],z+.005,z+1.05)
    registration=[]
    for datum,theta,floor_name in [(LOWER_Z,start_angle,'SAW_SAW_floor_18.0'),(UPPER_Z,start_angle+sweep,'SAW_SAW_floor_21.9')]:
        floor=bpy.data.objects[floor_name]
        tree=BVHTree.FromPolygons([floor.matrix_world@v.co for v in floor.data.vertices],[tuple(p.vertices)for p in floor.data.polygons])
        # Fixed angular width preserves a clear arc landing at each opening edge.
        # Place landings adjacent to flights, never over the final tread.
        angle_a,angle_b=(theta-.36,theta-.0003)if datum==LOWER_Z else(theta+.0003,theta+.36)
        distances=[]
        angles=[angle_a+(angle_b-angle_a)*i/60 for i in range(61)]
        for angle in angles:
            radius=OUTER_RADIUS
            while radius<10:
                x,y=point(radius,angle)
                if tree.ray_cast(Vector((x,y,datum+.1)),Vector((0,0,-1)),.2)[0] is not None:break
                radius+=.002
            assert radius<10,'Could not register landing against retained floor edge'
            distances.append(radius)
        edges=[r-.003 for r in distances]
        assert min(edges)>OUTER_RADIUS
        # Follow the actual opening boundary with a3mm seam, not a short
        # rectangular bridge that would leave a half-metre centerline gap.
        footprint=[point(INNER_RADIUS,angle_a)]+[point(r,a)for r,a in zip(edges,angles)]+[point(INNER_RADIUS,angle_b)]
        solid(1,footprint,datum-.12,datum)
        registration.append(dict(floor=floor_name,datum=datum,angle=theta,landingOuterRadii=edges,firstFloorDistances=distances))
    for index,(name,(verts,faces)) in enumerate(zip(OWN_NAMES,groups)):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        uv=mesh.uv_layers.new(name='MetricUV')
        for loop in mesh.loops:
            v=mesh.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x,v.y)
        mesh.materials.append(mats[1 if index==2 else 0])
        obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
        obj['evidenceYear']=2014;obj['dimensions']='Estimated from retained opening; not measured';obj['sourceURL']=SOURCE_URL
    return dict(alreadyApplied=False,addedObjects=OWN_NAMES[:],archivedObjects=[],changedObjects=[],
        historicalStudy=True,sourceYear=2014,registration=registration,estimatedStepCount=STEP_COUNT,
        scope='One fifth-to-sixth central curved connection. Lower stair and all floor sheets unchanged.',
        limitations=report['limitations'][1:]+['Only relative central upper-stair topology is evidenced; detailed starting angles, radius, step count, guards and retained vertical datums are estimates.','Fourth-to-fifth and side stair/lift cores remain incomplete; no2026 as-built or complete interior claim.'])
