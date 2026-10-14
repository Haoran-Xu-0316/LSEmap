"""Check retained street coverage and removal of duplicate road surfaces."""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/street-network198'


def verify_network():
    audit=json.loads((OUT/'native-road-audit.json').read_text())
    plan=json.loads((OUT/'surface-plan.json').read_text())
    components=json.loads((OUT/'audit.json').read_text())
    source=[]
    for road in audit['roads']:
        if road['name'] not in plan['sourceObjects']: continue
        for face in road['faces']:
            points=[road['vertices'][index] for index in face]
            if all(abs(point[2]-.024)<1e-5 for point in points):
                polygon=Polygon([point[:2] for point in points])
                if polygon.area>1e-9: source.append(polygon)
    original=unary_union(source)
    retained=unary_union([Polygon(part['outer'],part['holes']) for part in plan['polygons']])
    triangles=[Polygon(points) for points in plan['triangles']]
    actual=unary_union(triangles)
    assert len(source)==397 and len(plan['sourceObjects'])==138
    assert original.hausdorff_distance(retained)<.0001
    assert original.symmetric_difference(retained).area<.3
    assert actual.symmetric_difference(retained).area<1e-5
    assert abs(sum(triangle.area for triangle in triangles)-actual.area)<1e-5
    assert sum(p.area for p in source)-original.area>6500
    assert sum(len(p.interiors) for p in actual.geoms)==23
    for part in actual.geoms:
        for hole in part.interiors:
            assert not actual.covers(Polygon(hole).representative_point())
    assert components['verification']['componentReopened'] and components['verification']['allEdgesManifold']
    result=dict(verified=True,sourceObjects=138,sourceStrips=397,retainedHoles=23,
                duplicateAreaBeforeM2=sum(p.area for p in source)-original.area,
                duplicateAreaAfterM2=sum(t.area for t in triangles)-actual.area,
                boundaryMaximumDeviationMetres=original.hausdorff_distance(actual),
                retainedUnionAreaM2=actual.area)
    (OUT/'coverage-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    verify_network()
