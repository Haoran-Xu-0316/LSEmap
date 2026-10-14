"""Dissolve duplicate coplanar road strips into a continuous native road network.

Run in the existing Python environment to prepare the geometric plan from the
read-only road audit, then open this file in Blender to create its component.
No widths, traffic rules or new routes are inferred. Original objects remain
available for archival by the normal complete-campus integration workflow.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'result/blender/LSE_campus_detailed_v197.blend'
OUT = ROOT/'result/blender/street-network198'
NAME = 'SITE198_Continuous_asphalt_road_network'
SHA = '5a225f1d5227e0b173bc93d9ba4aa5da1e539ec73b003f31ea575ccea807d854'


def prepare_plan():
    from shapely import constrained_delaunay_triangles, orient_polygons, set_precision
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    audit=json.loads((OUT/'native-road-audit.json').read_text())
    assert audit['baselineSha256']==SHA
    sources=[row for row in audit['roads'] if row['materials']==['Road asphalt']]
    polygons=[]
    for row in sources:
        assert row['collections']==['00_SITE'], row['name']
        for face in row['faces']:
            points=[row['vertices'][index] for index in face]
            if all(abs(point[2]-.024)<1e-5 for point in points):
                polygon=Polygon([point[:2] for point in points])
                if polygon.area>1e-9: polygons.append(polygon)
    original=unary_union(polygons)
    # A sub-millimetre computational grid avoids floating sliver triangles at
    # old strip intersections. It does not change the estimated street layout.
    footprint=orient_polygons(set_precision(original,.0001))
    parts=list(footprint.geoms)
    triangles=list(constrained_delaunay_triangles(footprint).geoms)
    assert footprint.is_valid and len(parts)==2
    assert sum(len(part.interiors) for part in parts)==23
    assert original.hausdorff_distance(footprint)<.0001
    assert original.symmetric_difference(footprint).area<.3
    assert abs(sum(t.area for t in triangles)-footprint.area)<1e-5
    plan=dict(baselineSha256=SHA,sourceObjects=[row['name'] for row in sources],
              sourceTopFaces=len(polygons),sourceAdditiveAreaM2=sum(p.area for p in polygons),
              retainedFootprintAreaM2=original.area,redundantCoplanarAreaM2=sum(p.area for p in polygons)-original.area,
              boundaryToleranceMetres=.0001,boundaryMaximumDeviationMetres=original.hausdorff_distance(footprint),
              symmetricDifferenceAreaM2=original.symmetric_difference(footprint).area,holes=23,connectedParts=2,
              top=.024,bottom=0,
              polygons=[dict(outer=list(part.exterior.coords)[:-1],holes=[list(ring.coords)[:-1] for ring in part.interiors]) for part in parts],
              triangles=[list(triangle.exterior.coords)[:-1] for triangle in triangles])
    (OUT/'surface-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print('STREET198_PLAN',len(sources),len(triangles),plan['redundantCoplanarAreaM2'],flush=True)


def build_component():
    import bpy
    import bmesh
    from integrate_exterior_round194 import object_fingerprint
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
    plan=json.loads((OUT/'surface-plan.json').read_text())
    assert plan['baselineSha256']==SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
    before={obj.name:object_fingerprint(obj) for obj in bpy.data.objects}
    vertices=[];faces=[];indices={}
    def vertex(point,z):
        key=(round(point[0],4),round(point[1],4),z)
        if key not in indices:indices[key]=len(vertices);vertices.append(key)
        return indices[key]
    for triangle in plan['triangles']:
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(triangle,triangle[1:]+triangle[:1]))
        ordered=triangle if area>0 else list(reversed(triangle))
        faces.append(tuple(vertex(p,plan['top']) for p in ordered))
        faces.append(tuple(vertex(p,plan['bottom']) for p in reversed(ordered)))
    for polygon in plan['polygons']:
        for ring in [polygon['outer'],*polygon['holes']]:
            for a,b in zip(ring,ring[1:]+ring[:1]):
                faces.append((vertex(a,plan['bottom']),vertex(b,plan['bottom']),vertex(b,plan['top']),vertex(a,plan['top'])))
    mesh=bpy.data.meshes.new(NAME+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
    mesh.materials.append(bpy.data.materials['Road asphalt'])
    uv=mesh.uv_layers.new(name='MetricUV')
    for loop in mesh.loops:uv.data[loop.index].uv=mesh.vertices[loop.vertex_index].co.xy
    obj=bpy.data.objects.new(NAME,mesh);bpy.data.collections['00_SITE'].objects.link(obj)
    obj['roadSurfaceScope']='Union of existing coplanar asphalt strips; no route or width changes.23 existing holes retained.'
    obj['roadSourceObjectCount']=len(plan['sourceObjects'])
    bm=bmesh.new();bm.from_mesh(mesh)
    assert all(edge.is_manifold for edge in bm.edges)
    assert all(face.calc_area()>1e-12 for face in bm.faces)
    volume=bm.calc_volume(signed=True);bm.free()
    assert volume>0
    for name,fingerprint in before.items():assert object_fingerprint(bpy.data.objects[name])==fingerprint,name
    component=OUT/'street-network198-component.blend'
    bpy.data.libraries.write(str(component),{obj},fake_user=True,compress=True)
    report=dict(version=198,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,
                componentPath=str(component.relative_to(ROOT)),componentSha256=hashlib.sha256(component.read_bytes()).hexdigest(),
                targetCollection='00_SITE',addedObjects=[NAME],archivedObjects=plan['sourceObjects'],changedObjects=[],
                network={key:plan[key] for key in ['sourceTopFaces','sourceAdditiveAreaM2','retainedFootprintAreaM2','redundantCoplanarAreaM2','boundaryMaximumDeviationMetres','symmetricDifferenceAreaM2','holes','connectedParts']},
                vertices=len(vertices),faces=len(faces),originalsVerified=len(before),signedVolume=volume,
                scope='Replace138 batched overlapping road objects with one watertight network at the original height; preserve approximate road widths, boundary,23 holes and all non-road geometry.',
                limitations='Archived source road widths and topology remain schematic. This removes duplicate surfaces, not an as-built traffic or kerb survey.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component),link=False) as (source,target):target.objects=[NAME]
    obj=target.objects[0];bpy.context.scene.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    assert bm.calc_volume(signed=True)>0;bm.free()
    report['verification']=dict(componentReopened=True,allEdgesManifold=True,positiveClosedVolume=True,originalGeometryUVsBindingsPreserved=True,
                                baselineSha256Unchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA)
    assert report['verification']['baselineSha256Unchanged']
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('STREET198_COMPONENT',len(vertices),len(faces),flush=True)


if __name__=='__main__':
    try:
        import bpy
    except ImportError:
        prepare_plan()
    else:
        import sys
        sys.path.insert(0,str(ROOT/'web/tools'))
        build_component()
