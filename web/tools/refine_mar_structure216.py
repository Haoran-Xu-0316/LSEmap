"""Check Marshall ground controls before coordinated hall/entrance rebuilding.

The published ground plan is a different control set from the old third-floor
outline. Its nine solid column symbols are vector picks, its five-metre scale
is an independent raster pick. A free rigid fit is deliberately more permissive
than a facade-constrained fit: failure even here cannot authorize door placement.
This fixed read-only workflow never saves or changes the campus model.
"""
from pathlib import Path
from itertools import permutations
import hashlib
import json
import math
try:
    import bpy
    import bmesh
    from mathutils import Vector
except ModuleNotFoundError:
    bpy=None
    Vector=None
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v215.blend'
BASE_SHA='b6c726056d7e98dc229e1ac2dc1d01e7be35eb1835a28cd7a6bb88155a9c1a11'
OUT=ROOT/'result/blender/mar-structure216'
SOURCE=ROOT/'data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf'
SOURCE_SHA='d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47'
ORIGIN=Vector((-8.696325894899289,49.33154396120258,0)) if bpy else None
ANGLE=math.radians(22)
U=Vector((math.cos(ANGLE),math.sin(ANGLE),0)) if bpy else None
N=Vector((-U.y,U.x,0)) if bpy else None
# Ground-plan filled structural symbols, exact bounds from pdfplumber page1.
# All nine are controls; no claim that all are the six tree-column types.
SOURCE_COLUMNS=np.array([
 [155.4645,460.6657],[191.0358,460.6659],[226.5768,460.6883],
 [119.8992,496.2350],[191.0338,496.2311],
 [155.4440,531.7707],[191.0404,531.8099],[226.6124,531.8193],
 [191.0104,425.1230],
])
# Source-page.png is a 2970x4200 direct page1 rendering. The black 0/5m
# uprights span x394 to478 in that rendering. One-pixel endpoint uncertainty.
PAGE_WIDTH_POINTS=595.276
PAGE_WIDTH_PIXELS=2970
SCALE_BAR_PIXELS=84
METRES_PER_POINT=5/(SCALE_BAR_PIXELS*PAGE_WIDTH_POINTS/PAGE_WIDTH_PIXELS)


def local(point):
    q=point-ORIGIN
    return [q.dot(U),q.dot(N),point.z]


def components(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();seen=set();parts=[]
    for seed in bm.verts:
        if seed.index in seen:continue
        seen.add(seed.index);pending=[seed];points=[]
        while pending:
            v=pending.pop();points.append(Vector(local(obj.matrix_world@v.co)))
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other.index not in seen:seen.add(other.index);pending.append(other)
        centre=sum(points,Vector())/len(points)
        parts.append({'center':list(centre),'bounds':[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)],'vertices':len(points)})
    bm.free();return parts


def best_rigid_fit(source,target,scale,fixed_source=None):
    """Enumerate every injective six-of-nine assignment, no forced correspondence."""
    free_count=len(target)-(0 if fixed_source is None else 1)
    indices=np.asarray(list(permutations(range(len(source)),free_count)))
    candidates=source[indices]*scale
    if fixed_source is not None:
        fixed=np.broadcast_to(np.asarray(fixed_source)*scale,(len(indices),1,2))
        candidates=np.concatenate((candidates,fixed),axis=1)
    ac=candidates.mean(axis=1);bc=target.mean(axis=0)
    a=candidates-ac[:,None,:];b=target-bc
    covariance=np.einsum('nki,kj->nij',a,b)
    left,_,right=np.linalg.svd(covariance)
    rotation=left@right
    positive=np.linalg.det(rotation)>.99999
    registered=np.einsum('nki,nij->nkj',a,rotation)+bc
    errors=np.linalg.norm(registered-target,axis=2)
    rms=np.sqrt(np.mean(errors**2,axis=1));rms[~positive]=np.inf
    best=int(np.argmin(rms))
    return {'assignment':indices[best].tolist(),'rotation':rotation[best].tolist(),
            'translation':(bc-ac[best]@rotation[best]).tolist(),'registered':registered[best].tolist(),
            'residuals':errors[best].tolist(),'rms':float(rms[best]),'maximum':float(errors[best].max()),
            'assignmentsEvaluated':len(indices)}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    vector_candidates=json.loads((OUT/'vector-candidates.json').read_text())
    extracted=np.array([[(r['x0']+r['x1'])/2,(r['top']+r['bottom'])/2] for r in vector_candidates])
    assert all(np.linalg.norm(extracted-point,axis=1).min()<.001 for point in SOURCE_COLUMNS)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    controls=[]
    for name in ['MAR_hall_round_columns','MAR_D3_double_height_round_column']:
        for component in components(bpy.data.objects[name]):
            component['object']=name;controls.append(component)
    assert len(controls)==6
    target=np.array([c['center'][:2] for c in controls])
    stair=bpy.data.objects['MAR_D3_connected_curved_stair']
    stair_points=np.array([local(stair.matrix_world@v.co)[:2] for v in stair.data.vertices])
    # The inherited builder centres its stair near(-12,2). Outer-ring vertices
    # are separated from the inner ring by2.8m, allowing an independent circle fit.
    outer=stair_points[np.linalg.norm(stair_points-np.array([-12,2]),axis=1)>4.9]
    coefficients=np.linalg.lstsq(np.column_stack((2*outer,np.ones(len(outer)))),np.sum(outer**2,axis=1),rcond=None)[0]
    stair_center=coefficients[:2]
    stair_radius=float(np.sqrt(coefficients[2]+sum(stair_center**2)))
    stair_radial_error=float(np.max(np.abs(np.linalg.norm(outer-stair_center,axis=1)-stair_radius)))
    # Swap PDF axes into the known plan orientation. Translation and rotation
    # remain free, so this fit is not a ground-plan-to-street registration.
    source=SOURCE_COLUMNS[:,::-1]
    fit=best_rigid_fit(source,target,METRES_PER_POINT)
    source_stair=[155.46,496.23]
    joint_fit=best_rigid_fit(source,np.vstack((target,stair_center)),METRES_PER_POINT,fixed_source=source_stair[::-1])
    # Bound the raster ruler uncertainty by one pixel at each endpoint.
    tolerance_fits=[]
    for pixels in [82,86]:
        scale=5/(pixels*PAGE_WIDTH_POINTS/PAGE_WIDTH_PIXELS)
        candidate=best_rigid_fit(source,target,scale)
        tolerance_fits.append({'barPixels':pixels,'metresPerPoint':scale,'rms':candidate['rms'],'maximum':candidate['maximum']})
    rows=[]
    for i,control in enumerate(controls):
        j=fit['assignment'][i]
        rows.append({'native':control,'sourceColumnIndex':j,'sourcePdfPoint':SOURCE_COLUMNS[j].tolist(),
                     'registeredBestCase':fit['registered'][i],'residualMetres':fit['residuals'][i]})
    glass=bpy.data.objects['MAR177_ground_glass_panes']
    material_names=[m.name if m else None for m in glass.data.materials]
    report={'version':216,'auditOnly':True,'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':BASE_SHA,
      'componentPath':None,'componentSha256':None,'addedObjects':[],'archivedObjects':[],
      'targetCollection':'MAR_PUBLIC_INTERIOR_study','nativeSourceUnchanged':True,
      'newControlSet':{'source':'Built2022 ground-floor plan, page1, solid structural column symbols',
       'sourcePath':str(SOURCE.relative_to(ROOT)),'sourceSha256':SOURCE_SHA,
       'sourceUrl':'https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf',
       'sourcePeriod':'Published built2022 plans; not proof of2026 internal conditions.',
       'evidenceFiles':['vector-candidates.json','source-ground.png','source-scale.png','column-control-comparison.svg'],
       'sourceColumnsPdfPoints':SOURCE_COLUMNS.tolist(),'sourceSymbolCount':9,
       'nativeCylinderCount':6,'symbolTypeLimitation':'Nine structural cut symbols are not identified as nine tree columns; contractor six-tree count does not define every ground support.',
       'scale':{'metresPerPdfPoint':METRES_PER_POINT,'printedLengthMetres':5,'sourcePageWidthPoints':PAGE_WIDTH_POINTS,
        'sourcePageWidthPixels':PAGE_WIDTH_PIXELS,'rulerSpanPixels':SCALE_BAR_PIXELS,'rulerEndpointUncertaintyPixels':1}},
      'bestCaseRigidMetricFit':fit,
      'jointColumnAndStairFit':{'fit':joint_fit,'nativeStairCentre':stair_center.tolist(),
       'nativeStairOuterRadius':stair_radius,'nativeCircleMaxResidual':stair_radial_error,
       'sourceStairPdfPoint':source_stair,'sourceStairPickUncertaintyPdfPoints':.2,
       'sourcePickBasis':'Raster centre of the helical stair, coincident with an unoccupied grid intersection; not a vector circle or survey dimension.'},
      'rulerUncertaintyFits':tolerance_fits,'controls':rows,
      'registrationAccepted':False,
      'reason':'Even the globally enumerated best six-of-nine assignment at the independently printed metric scale fails to align existing ground supports. This unconstrained fit is only a lower bound: it does not fit facade corners, street controls, stair landing or the missing recessed entrance boundary.',
      'consequences':[
       'The inherited six photo-estimated round supports cannot serve as six verified ground registration anchors.',
       'Registering the published plan to existing supports would warp the source; placing five drums using that fit would perpetuate a different hall.',
       'The entire ground glass boundary and related public hall support/stair layout need coordinated plan registration before door replacement.'
      ],
      'nextConcreteSource':{'sourceAlreadyAvailable':'Same architect-authored PDF, ground and second-floor plans and sectionAA',
       'requiredWork':'Trace the full ground envelope and projected portico column line, then connect both plans through matching lift/stair cores and the published scale. Register that coordinated multi-floor geometry against independently identifiable street/facade endpoints; do not fit the nine symbols to the old guessed supports.',
       'ifStreetTieRemainsAmbiguous':'Obtain an architect/Estates georeferenced ground survey or controlled facade/portico dimensions. A photograph alone does not give metric plan control.'},
      'preserved':{'nativeObjects':len(bpy.data.objects),'groundGlassMaterials':material_names,
       'originalGeometry':True,'uv':True,'materialNodes':True,'publicMaxZ13ExportPolicy':True,'independentRooms':True},
      'limitations':['Printed ruler is a raster measurement with stated uncertainty; PDF column centres use vector symbol bounds.',
       'A minimum fit mismatch is evidence against using inherited supports as registration controls, not an accepted correspondence of each support.',
       'No model edit, export or publication is authorized by this audit alone.']}
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    def xy(p):return f'{480+11*p[0]:.2f},{480-11*p[1]:.2f}'
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="900" viewBox="0 0 1000 900">',
         '<rect width="1000" height="900" fill="white"/>',
         '<text x="35" y="40" font-family="sans-serif" font-size="22">MAR ground structure: permissive best-case rigid fit</text>',
         '<text x="35" y="70" font-family="sans-serif" font-size="15">Black: six inherited round supports. Blue: six selected published structural controls.</text>']
    for row in rows:
        a=row['native']['center'];b=row['registeredBestCase']
        ax,ay=xy(a).split(',');bx,by=xy(b).split(',')
        svg.extend([f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#a8433b" stroke-width="2"/>',
          f'<circle cx="{ax}" cy="{ay}" r="8" fill="none" stroke="#222" stroke-width="2"/>',
          f'<circle cx="{bx}" cy="{by}" r="6" fill="#28729a"/>',
          f'<text x="{float(ax)+12}" y="{ay}" font-family="sans-serif" font-size="14">{row["residualMetres"]:.2f}m</text>'])
    svg.extend([f'<text x="35" y="800" font-family="sans-serif" font-size="17">RMS {fit["rms"]:.2f}m; maximum {fit["maximum"]:.2f}m. No accepted ground registration.</text>',
      '<text x="35" y="835" font-family="sans-serif" font-size="14">All 60,480 assignments evaluated at independently printed scale; free translation/rotation.</text>','</svg>'])
    (OUT/'column-control-comparison.svg').write_text(''.join(svg))
    print('MAR216_NEW_GROUND_CONTROL_AUDIT',fit['rms'],fit['maximum'],flush=True)




def build_normalized_ground_plan():
    """Publish coordinated two-dimensional source geometry, not a guessed model."""
    from shapely.geometry import Polygon,Point,LineString
    from shapely.ops import unary_union
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    regions=json.loads((OUT/'ground-vector-regions.json').read_text())
    candidates=json.loads((OUT/'vector-candidates.json').read_text())
    reference=SOURCE_COLUMNS[4]
    pixel_per_point=PAGE_WIDTH_PIXELS/PAGE_WIDTH_POINTS
    def normalized(point):
        return [(point[1]-reference[1])*METRES_PER_POINT,(point[0]-reference[0])*METRES_PER_POINT]
    def from_crop(point):
        return [(point[0]+380)/pixel_per_point,(point[1]+1760)/pixel_per_point]
    def normalize_crop(point):return normalized(from_crop(point))
    # Trace the actual ground enclosure, including the three recessed entrance
    # faces. It is deliberately distinct from roof/portico and site boundaries.
    # Solid wall thickness and the separate external stair are not inferred.
    boundary_pixels=[(473,252),(557,330),(635,251),(635,193),(848,193),(848,449),
      (761,537),(849,631),(849,995),(221,995),(221,985),(125,985),(125,798),
      (215,711),(106,619),(151,573)]
    boundary=[normalize_crop(p) for p in boundary_pixels]
    base=Polygon(boundary)
    assert base.is_valid and base.area>100
    columns=[]
    for i,point in enumerate(SOURCE_COLUMNS):
        row=min(candidates,key=lambda r:np.linalg.norm(np.array([(r['x0']+r['x1'])/2,(r['top']+r['bottom'])/2])-point))
        points=[normalized(p) for p in row['pts']]
        columns.append({'id':f'column-{i+1:02d}','sourcePdfCentre':point.tolist(),
          'centreMetres':normalized(point),'cutProfileMetres':points,
          'areaSquareMetres':Polygon(points).area,
          'evidence':'Exact vector filled cut profile from the published ground plan; tree/ordinary support type unassigned.'})
    door_specs=[('entrance-a','ground_entrance_a',[(177.5784,406.1615),(182.3047,410.8925)],0),
                ('entrance-b','ground_entrance_b',[(104.1958,485.6598),(108.9194,490.3942)],13),
                ('entrance-c','ground_entrance_c',[(239.9626,470.1416)],6)]
    entrances=[];door_polygons=[]
    for group,region,centres,edge in door_specs:
        units=[]
        for i,centre in enumerate(centres):
            possible=[r for r in regions[region] if r['object_type']=='curve' and len(r.get('pts') or [])>=50]
            row=min(possible,key=lambda r:np.linalg.norm(np.array([(r['x0']+r['x1'])/2,(r['top']+r['bottom'])/2])-centre))
            exact=[(row['x0']+row['x1'])/2,(row['top']+row['bottom'])/2]
            assert np.linalg.norm(np.array(exact)-centre)<.02
            points=[normalized(p) for p in row['pts']]
            disk=Polygon(points)
            assert disk.is_valid and disk.area>1
            door_polygons.append(disk)
            units.append({'id':f'{group}-{i+1}','sourcePdfCentre':exact,'centreMetres':normalized(exact),
              'outlineMetres':points,'symbolDiameterMetres':[(row['x1']-row['x0'])*METRES_PER_POINT,(row['bottom']-row['top'])*METRES_PER_POINT],
              'distanceFromEnvelopeGuideMetres':disk.centroid.distance(LineString([boundary[edge],boundary[(edge+1)%len(boundary)]])),
              'type':'Circular revolving-door plan symbol; actual leaf/glazing thickness and clear opening are not established.'})
        entrances.append({'id':group,'boundaryGuideEdge':edge,'units':units,
          'adjacentFacetsMetres':[boundary[(edge-1)%len(boundary)],boundary[edge],boundary[(edge+1)%len(boundary)],boundary[(edge+2)%len(boundary)]],
          'requiredWallOperation':'Replace the guide interval with the published circular opening profile as one coordinated enclosure; do not retain an intact glass panel across the door.'})
    # This union is a source-plan outline only. It neither raises a3D cylinder
    # nor asserts operating clearances, accessible leaves or measured thickness.
    coordinated=unary_union([base]+door_polygons)
    assert coordinated.geom_type=='Polygon' and coordinated.is_valid
    def linework(rows,normalizer):
        result=[];seen=set()
        for row in rows:
            if not row.get('pts'):continue
            path=[normalizer(p) for p in row['pts']]
            key=tuple((round(p[0],2),round(p[1],2)) for p in path)
            reverse=tuple(reversed(key))
            if key in seen or reverse in seen:continue
            seen.add(key);result.append(path)
        return result
    staircase=linework(regions['ground_stair'],normalized)
    ground_core=linework(regions['ground_south_core'],normalized)
    second_core=linework(regions['second_south_core'],lambda p:[p[0]*METRES_PER_POINT,-p[1]*METRES_PER_POINT])
    site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    mar=next(b for b in site['buildings'] if b.get('code')=='MAR')
    native=Polygon(mar['rings'][0])
    def metrics(poly):
        hull=poly.convex_hull
        return {'areaSquareMetres':poly.area,'perimeterMetres':poly.length,
                'convexHullAreaSquareMetres':hull.area,'convexHullAreaRatio':poly.area/hull.area,
                'deepestVertexRecessFromHullMetres':max(Point(p).distance(hull.boundary) for p in poly.exterior.coords)}
    report={
      'version':216,'kind':'Coordinated ground source plan, not georeferenced as-built mesh',
      'source':{'url':'https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf',
                'path':str(SOURCE.relative_to(ROOT)),'sha256':SOURCE_SHA,'page':1,'period':'Built2022 publication; current2026 condition unverified'},
      'coordinateSystem':{'units':'metres','originPdfPoint':reference.tolist(),'x':'Increasing source PDF downward coordinate',
                          'y':'Increasing source PDF rightward coordinate','metresPerPdfPoint':METRES_PER_POINT,
                          'scaleRulerEndpointUncertaintyPixels':1,'metresPerPointRangeForTwoEndpointErrors':[5/(86*PAGE_WIDTH_POINTS/PAGE_WIDTH_PIXELS),5/(82*PAGE_WIDTH_POINTS/PAGE_WIDTH_PIXELS)],
                          'geographicTransform':None,'groundCropPixelOffset':[380,1760],'groundRasterPixelsPerPdfPoint':pixel_per_point},
      'quality':{'columns':'Exact source vector polygons','entranceOutlines':'Exact source vector circular-symbol polygons',
                 'staircase':'Source vector linework, retained without inventing a tread count, slope or upper landing',
                 'enclosureGuide':'Raster digitization at approximately0.06m per pixel; estimated2pixel pick uncertainty, plus printed ruler uncertainty',
                 'roomsAndWallThickness':'Not reconstructed or inferred'},
      'groundEnvelope':{'guidePixels':boundary_pixels,'guideMetres':boundary,'guideClosed':True,
         'coordinatedSymbolOutlineMetres':[list(p) for p in coordinated.exterior.coords],
         'areaAndShape':metrics(coordinated),
         'boundaryEdges':[{'id':i,'a':boundary[i],'b':boundary[(i+1)%len(boundary)],
                           'role':next((e['id'] for e in entrances if e['boundaryGuideEdge']==i),'solid-or-glazed-enclosure-guide-unassigned')} for i in range(len(boundary))]},
      'columns':columns,'entranceGroups':entrances,
      'mainStaircase':{'sourceRegionPdf':[137,479,174,511],'lineworkMetres':staircase,
         'sourcePickedCentreMetres':normalized([155.46,496.23]),'pickUncertaintyMetres':.2*METRES_PER_POINT,
         'heightAndLanding':'Unassigned; sectionAA and upper-level connection must be solved before3D construction.'},
      'coreComparison':{'groundSourceRegionPdf':[120,530,188,556],'groundLineworkMetres':ground_core,
         'secondFloorSourceRegionPdf':[115,265,190,310],'secondFloorLineworkMetricPageFrame':second_core,
         'acceptedMatchingCoreCorners':[],'registrationAccepted':False,
         'finding':'Both source regions are extracted. Shaft identities and corresponding outer corners are not yet established, so no translation or floor alignment is asserted from look-alike rectangles.'},
      'osmComparison':{'sourceId':mar['id'],'nativeWorldRing':mar['rings'][0],'nativeOutlineMetrics':metrics(native),
         'mappingAccepted':False,
         'inconsistentEdges':[{'sourceEdge':e['boundaryGuideEdge'],'sourceGroup':e['id'],
          'finding':'Recessed ground entrance facet with revolving circular openings has no equivalent identified on the retained upper-envelope OSM ring. The ring is not a ground-glazing control.'} for e in entrances],
         'finding':'The OSM outline and the ground enclosure represent different physical boundaries. Similarity, centre alignment or outline minimization does not establish geographic correspondence.'},
      'readyForNextStep':['Use this complete coordinated ground-source geometry instead of the inherited six-column estimate.',
         'Resolve matching lift/stair core corners in the extracted ground and second-floor regions; keep the portico/street boundary distinct from the ground enclosure.',
         'Tie at least two facade/street endpoints plus an independent third control before replacing the geographic model.'],
      'modelEdited':False,'nativeSha256Preserved':hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA}
    (OUT/'normalized-ground-plan.json').write_text(json.dumps(report,indent=2)+'\n')
    def drawing(points):return ' '.join(f'{460+14*p[0]:.2f},{500-14*p[1]:.2f}' for p in points)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">',
      '<rect width="1000" height="1000" fill="white"/>',
      '<text x="35" y="40" font-family="sans-serif" font-size="24">MAR coordinated ground source plan</text>',
      '<text x="35" y="68" font-family="sans-serif" font-size="14">Built2022 ground plan. Metric source frame; geographic placement remains unverified.</text>',
      f'<polygon points="{drawing(coordinated.exterior.coords)}" fill="#f5f1e8" stroke="#303d43" stroke-width="2"/>']
    for path in staircase:svg.append(f'<polyline points="{drawing(path)}" fill="none" stroke="#687d86" stroke-width=".65"/>')
    for column in columns:svg.append(f'<polygon points="{drawing(column["cutProfileMetres"])}" fill="#303d43"/>')
    for entry in entrances:
        for unit in entry['units']:
            svg.append(f'<polygon points="{drawing(unit["outlineMetres"])}" fill="#d4e7ed" stroke="#28729a" stroke-width="1.5"/>')
            x,y=unit['centreMetres'];svg.append(f'<text x="{460+14*x+14:.2f}" y="{500-14*y:.2f}" font-family="sans-serif" font-size="12">{unit["id"]}</text>')
    svg.extend(['<line x1="50" y1="905" x2="120" y2="905" stroke="#222" stroke-width="5"/>',
       '<text x="50" y="930" font-family="sans-serif" font-size="15">5m</text>',
       '<text x="35" y="970" font-family="sans-serif" font-size="13">Boundary: raster guide. Columns, circular door symbols and stair linework: source vectors. No3D heights inferred.</text>','</svg>'])
    (OUT/'normalized-ground-plan.svg').write_text(''.join(svg))
    print('MAR216_COORDINATED_GROUND_PLAN',coordinated.area,len(columns),sum(len(e['units']) for e in entrances),len(staircase))


if __name__=='__main__':
    if bpy:main()
    else:build_normalized_ground_plan()
