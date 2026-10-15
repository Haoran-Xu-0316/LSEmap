"""Read-only review of SAW's historic main stair and twin-lift relationship.

The accepted217 complete native is never saved or changed. This review keeps
registered source sections and rejected feasibility evidence. It deliberately
writes no Blender component: the fourth-to-fifth joint is not resolved by the
available two-dimensional drawings. Fixed configuration, no command-line API.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw-circulation218'
BASE=ROOT/'result/blender/LSE_campus_detailed_v217.blend'
BASE_SHA='daac71eaf581c94e544fe7098e51f897273223a981bd8f1b4b637d56d4469423'
FLOORS=ROOT/'result/blender/saw-floors216'
PDF=ROOT/'data/documents/saw_occupants_guide_2014.pdf'
AR=ROOT/'data/collections/saw-circulation217/architectural-review-2014.pdf'
LEVELS=[0.,3.45,8.1,11.1,14.1,18.,21.9]
ANCHORS=np.array([[-65.223399,-15.905616],[-84.252182,28.425],[-55.301,36.609104]])
DIAGNOSTIC_GUARD_INSET=.25
CLEARANCE=2.1
# Explicit source-line correspondence, not an accepted construction sequence.
# Each row pairs visible portions of two adjacent plans in the same registered
# source coordinate system. Publication drawing cuts can truncate a line; a
# line span must not automatically be treated as a measured clear stair width.
SOURCE_GROUPS=[
 [(32,[3803,3804,3806,3807,3808]),(31,[3329,3330,3331,3332,3333])],
 [(31,[1416,1417,1418,1419,1420,1421,1422]),(30,[6011,6010,6006,6005,5979,5978,5977,5976])],
 [(30,[5989,5988,5987,5985,5984,5983,5982,5981]),(30,[5996,5997,5998]),(29,[1761,1760,1759,1758,1757,1756])],
 [(29,[4701,4702,4703,4704,4705,4708,4707,4706,4709,4710]),(28,[1220,1219,1218])],
 [(28,[2288,2289,2290,2291,2292]),(28,[2282,2281]),(27,[2949,2948,2952,2950,2951])],
 [(27,[2941,2940,2939,2938,2937,2936,2935,2934]),(26,[8226,8227,8225,8224,8223,8222,8221,8210,8211])],
]

def write_json(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def world(points):
    p=np.array(points);a,b,c=ANCHORS
    return a+(p[:,0:1]-145)/1200*(b-a)+(p[:,1:2]-400)/785*(c-b)

def ground_pixels(points):
    matrix=np.column_stack(((ANCHORS[1]-ANCHORS[0])/1200,(ANCHORS[2]-ANCHORS[1])/785))
    return (np.asarray(points)-ANCHORS[0])@np.linalg.inv(matrix).T+np.array([145,400])

def extract_source_lines():
    """Reuse cached PDF vectors; parse the seven source pages only if missing."""
    path=OUT/'source-lines.json'
    if path.exists():return json.loads(path.read_text())
    import pdfplumber
    wanted={page:{index for groups in SOURCE_GROUPS for source_page,indices in groups if source_page==page for index in indices} for page in range(26,33)}
    records={}
    with pdfplumber.open(PDF) as document:
        for number in range(26,33):
            page=document.pages[number-1];factor=1501/page.width;lines=[]
            for index,row in enumerate(page.lines):
                if index in wanted[number]:
                    lines.append({'index':index,'pts':row['pts'],'color':row.get('stroking_color'),'linewidth':row.get('linewidth')})
            records[str(number)]={'pageSize':[page.width,page.height],'lines':lines}
    write_json('source-lines.json',records)
    return records

def source_sections():
    lines=extract_source_lines();registration=json.loads((FLOORS/'registration.json').read_text());result=[]
    for flight,groups in enumerate(SOURCE_GROUPS):
        row=[];last=None
        for page,indices in groups:
            raw={line['index']:line for line in lines[str(page)]['lines']};r=registration[str(page)]
            factor=1501/lines[str(page)]['pageSize'][0];sections=[];proof=[]
            for index in indices:
                pdf=np.asarray(raw[index]['pts']);registered=(pdf@np.asarray(r['matrix'])+np.asarray(r['offset']))*factor
                q=world(registered)
                if last is not None and np.linalg.norm(last[0]-q[1])+np.linalg.norm(last[1]-q[0])<np.linalg.norm(last[0]-q[0])+np.linalg.norm(last[1]-q[1]):q=q[::-1]
                last=q;sections.append(q)
                proof.append({'sourcePage':page,'sourceLineIndex':index,'pdfEndpoints':pdf.tolist(),
                  'registeredGroundPagePixelEndpoints':registered.tolist(),'worldEndpoints':q.tolist(),
                  'worldMidpoint':q.mean(0).tolist(),'publishedLineSpanMetres':float(np.linalg.norm(q[1]-q[0]))})
            row.append({'page':page,'indices':indices,'sections':sections,'proof':proof})
        result.append(row)
    write_json('source-section-correspondence.json',{'baselineSha256':BASE_SHA,'coordinateSystem':'Blender X east, Y north, Z up; XY source coordinates only',
      'registrationSource':'result/blender/saw-floors216/registration.json','registrationScope':'Twelve common dual-lift interior corners; retained estimated geographic affine mapping',
      'sourceGuideSha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),'maxInterfloorFitResidualPdfPoints':max(r['maxResidualPdfPoints'] for r in registration.values()),
      'acceptedStairCorrespondence':False,'flights':[{'flight':f,'fromLevel':f,'toLevel':f+1,'sourceGroups':[{'page':g['page'],'sourceLineIndices':g['indices'],'sections':g['proof']} for g in groups]}for f,groups in enumerate(result)],
      'limitations':['Visible riser-line ends may be clipped by drawing breaks. Their spans are evidence, not surveyed clear widths.',
        'The adjacent-page sequence and equal-rise feasibility assumptions are not accepted construction geometry.','Geographic transform and all storey heights remain inherited estimates.']})
    return result,registration

def candidate_surfaces(groups):
    """Reject a full-source candidate before allowing any native authoring.

    A continuous normal inset of the visible side boundary is included solely
    to test whether a broad concrete parapet could explain the discrepancy.
    Its0.25m thickness is a diagnostic estimate, never a source measurement.
    """
    from shapely.geometry import Polygon,MultiPoint
    surfaces=[]
    for flight,source in enumerate(groups):
        rows=[g['sections'] for g in source];clearances=[]
        for stations in rows:
            start,end=stations[0],stations[-1];u=stations[1].mean(0)-start.mean(0);u/=np.linalg.norm(u)
            v=end.mean(0)-stations[-2].mean(0);v/=np.linalg.norm(v)
            extended=[start-u*.8]+stations+[end+v*.8]
            body=Polygon([q[0] for q in extended]+[q[1] for q in reversed(extended)])
            assert body.is_valid
            clearances.append(body.buffer(-DIAGNOSTIC_GUARD_INSET,join_style=2))
        intervals=sum(len(row)-1 for row in rows);rise=(LEVELS[flight+1]-LEVELS[flight])/intervals;step=0
        for group,stations in enumerate(rows):
            for index,(a,b) in enumerate(zip(stations,stations[1:])):
                poly=Polygon([a[0],a[1],b[1],b[0]]);assert poly.is_valid
                poly=poly.intersection(clearances[group]);assert poly.geom_type=='Polygon'
                step+=1;top=LEVELS[flight]+rise*step
                surfaces.append({'flight':flight,'group':group,'step':step,'kind':'diagnostic_tread_interval',
                  'sourcePage':source[group]['page'],'sourceLines':source[group]['indices'][index:index+2],
                  'top':top,'bottom':top-rise+.002,'ring':list(poly.exterior.coords)[:-1]})
            if group<len(rows)-1:
                poly=MultiPoint(np.concatenate([stations[-1],rows[group+1][0]])).convex_hull;top=LEVELS[flight]+rise*step
                surfaces.append({'flight':flight,'group':group,'kind':'unaccepted_convex_join','top':top,'bottom':top-.18,'ring':list(poly.exterior.coords)[:-1]})
    return surfaces

def analyze(surfaces,registration):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    vectors=json.loads((FLOORS/'vectors.json').read_text());factor=1501/vectors['32']['pageSize'][0]
    cabins=[Polygon(world(np.array(next(c for c in vectors['32']['candidates'] if c['index']==index)['pts'][:-1])*factor)) for index in registration['32']['sourceControlCurveIndices']]
    lifts=unary_union(cabins);conflicts=[];lift_conflicts=[];outside=[]
    for index,a in enumerate(surfaces):
        p=Polygon(a['ring']);overlap=p.intersection(lifts).area
        if overlap>1e-4:lift_conflicts.append({'surface':index,'overlapSquareMetres':overlap})
        contour=Polygon(world(registration[str(31-a['flight'])]['groundPagePixelOutline']))
        area=p.difference(contour).area
        if area>.01:outside.append({'surface':index,'flight':a['flight'],'top':a['top'],'areaSquareMetres':area})
        for other_index,b in enumerate(surfaces[index+1:],index+1):
            q=Polygon(b['ring']);area=p.intersection(q).area
            if area<.001:continue
            low,high=sorted([a,b],key=lambda r:r['top']);gap=high['bottom']-low['top']
            if gap<CLEARANCE:conflicts.append({'surfaceA':index,'surfaceB':other_index,'flightA':a['flight'],'flightB':b['flight'],
              'kindA':a['kind'],'kindB':b['kind'],'gapMetres':gap,'overlapSquareMetres':area})
    treads=[a for a in surfaces if a['kind']=='diagnostic_tread_interval'];changes=[]
    for a in treads:
        poly=Polygon(a['ring']);cuts=[]
        for b in treads:
            if a is b or b['top']<=a['top']+.001 or b['bottom']-a['top']>=2.25:continue
            if a['flight']==b['flight'] and abs(a['step']-b['step'])<=1:continue
            q=Polygon(b['ring'])
            if poly.intersection(q).area>.001:cuts.append(q.buffer(.003,join_style=2))
        if cuts:
            proposed=poly.difference(unary_union(cuts))
            changes.append({'flight':a['flight'],'step':a['step'],'sourcePage':a['sourcePage'],'sourceLines':a['sourceLines'],
              'removedAreaSquareMetres':poly.area-proposed.area,'maximumPlanChangeMetres':poly.hausdorff_distance(proposed),
              'remainingGeometryType':proposed.geom_type,'originalCentroidRetained':proposed.covers(poly.centroid),
              'implemented':False,'reason':'No independent source justifies this corner cut. Concrete-side-boundary offset does not resolve it.'})
    report={'diagnosticSurfaceCount':len(surfaces),'diagnosticTreadIntervals':len(treads),'diagnosticConvexJoins':len(surfaces)-len(treads),
      'assumedHeights':'Equal rise per selected source interval, inherited storey datums. Diagnostic assumption, not an accepted riser schedule.',
      'diagnosticParapetInsetMetres':DIAGNOSTIC_GUARD_INSET,'clearanceThresholdMetres':CLEARANCE,
      'liftConflicts':lift_conflicts,'crossFlightConflicts':[r for r in conflicts if r['flightA']!=r['flightB']],
      'sameFlightConflicts':[r for r in conflicts if r['flightA']==r['flightB']],
      'upperFloorProjectionOutside':outside,'boundaryAcceptance':False,
      'boundaryCaveat':'A lower half-flight outside the upper-floor projection is not automatically a facade collision. The actual tapered envelope and native facade/headroom have not been validated.',
      'unimplementedWinderChange':changes,'surfaces':surfaces,'liftPolygons':[list(p.exterior.coords) for p in cabins]}
    write_json('station-feasibility.json',report)
    return report

def figures(groups,report):
    from PIL import Image,ImageDraw
    from shapely.geometry import Polygon
    registration=json.loads((FLOORS/'registration.json').read_text());vectors=json.loads((FLOORS/'vectors.json').read_text())
    contact=Image.new('RGB',(1800,800),'white')
    for flight,source in enumerate(groups):
        page=source[0]['page'];im=Image.open(ROOT/f'data/previews/saw_occupants_guide_2014_p{page}.png').convert('RGB')
        r=registration[str(page)];factor=1501/vectors[str(page)]['pageSize'][0];inverse=np.linalg.inv(r['matrix']);off=-np.asarray(r['offset'])*factor@inverse
        im=im.transform(im.size,Image.Transform.AFFINE,(inverse[0,0],inverse[1,0],off[0],inverse[0,1],inverse[1,1],off[1]),Image.Resampling.BICUBIC)
        d=ImageDraw.Draw(im)
        for k,g in enumerate(source):
            color=['#0069ad','#da6a00','#7a328c'][k]
            centres=[]
            for q in g['sections']:
                pts=ground_pixels(q);d.line([tuple(p)for p in pts],fill=color,width=3);centres.append(tuple(pts.mean(0)))
            d.line(centres,fill=color,width=3)
        im=im.crop((480,420,890,650)).resize((590,331),Image.Resampling.LANCZOS);x=(flight%3)*600;y=(flight//3)*400
        contact.paste(im,(x,y+60));ImageDraw.Draw(contact).text((x+8,y+10),f'{flight} to {flight+1}; pages '+','.join(str(g['page'])for g in source),fill='black')
        ImageDraw.Draw(contact).text((x+8,y+30),'Source sections only; stair correspondence NOT accepted',fill='#b00000')
    contact.save(OUT/'source-sections-proof.png')
    image=Image.new('RGB',(1300,950),'white');d=ImageDraw.Draw(image)
    focus=[item for item in report['surfaces']if item['flight']==4 and item['group']>0 and item['kind']=='diagnostic_tread_interval']
    all_points=np.concatenate([ground_pixels(item['ring']) for item in focus]);low=all_points.min(0);high=all_points.max(0)
    scale=min(1100/(high[0]-low[0]),680/(high[1]-low[1]))
    def project(ring):return [tuple((np.array(p)-low)*scale+[100,90]) for p in ground_pixels(ring)]
    d.text((20,15),'4 to 5: source28 lower portion and source27 fan; not an accepted joint',fill='black')
    f4=[s for s in report['surfaces'] if s['flight']==4 and s['kind']=='diagnostic_tread_interval']
    for item in f4:
        if item['group']==0:continue
        color='#0069ad' if item['sourcePage']==28 else '#da6a00'
        d.polygon(project(item['ring']),outline=color,width=4)
    for a in f4:
        for b in f4:
            if a['sourcePage']==b['sourcePage'] or a['top']>=b['top']:continue
            geometry=Polygon(a['ring']).intersection(Polygon(b['ring']))
            if geometry.area>.001 and geometry.geom_type=='Polygon':d.polygon(project(list(geometry.exterior.coords)),fill='#d60000')
    change=report['unimplementedWinderChange'][0]
    d.text((20,850),'Blue: page28. Orange: page27. Red: incompatible source corner under the diagnostic heights.',fill='black')
    d.text((20,875),f'Removing it would change the lower corner by {change['maximumPlanChangeMetres']:.6f}m; NOT implemented.',fill='#b00000')
    image.save(OUT/'fourth-fifth-joint-difference.png')

def review():
    groups,registration=source_sections();surfaces=candidate_surfaces(groups);report=analyze(surfaces,registration);figures(groups,report)
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    retained=json.loads((OUT/'accepted-native-surfaces.json').read_text())
    assert retained['baselineSha256']==BASE_SHA
    stairs=next(row for row in retained['objects']if row['name']=='SAW173_registered_main_treads')
    vertices=np.asarray(stairs['vertices']);top_faces={}
    for triangle in stairs['triangles']:
        points=vertices[triangle]
        if np.ptp(points[:,2])<1e-5 and np.cross(points[1]-points[0],points[2]-points[0])[2]>0:
            poly=Polygon(points[:,:2])
            if poly.area>1e-9:top_faces.setdefault(round(float(points[:,2].mean()),6),[]).append(poly)
    cabins=unary_union([Polygon(ring)for ring in report['liftPolygons']]);native_conflicts=[]
    for height,parts in top_faces.items():
        overlap=unary_union(parts).intersection(cabins).area
        if overlap>1e-5:native_conflicts.append({'top':height,'overlapSquareMetres':overlap})
    native_proof={'baselineSha256':BASE_SHA,'actualTreadCount':len(top_faces),'conflictingTreads':len(native_conflicts),
      'summedTreadCabinOverlapM2':sum(r['overlapSquareMetres']for r in native_conflicts),'conflicts':native_conflicts,
      'scope':'Current217 actual retained native tread top faces against the same registered historical two-cabin polygons. No stair change authored.'}
    assert native_proof['actualTreadCount']==146 and native_proof['conflictingTreads']==38
    write_json('retained-native-conflicts.json',native_proof)
    write_json('audit.json',{'version':218,'status':'not_accepted_no_component','auditOnly':True,'baselinePath':str(BASE.relative_to(ROOT)),
      'baselineSha256':BASE_SHA,'addedObjects':[],'archivedObjects':[],'changedObjects':[],
      'retainedNativeConflictProof':'retained-native-conflicts.json',
      'retainedNative':'217 main stair remains active and unchanged. Its previously identified38 tread/lift conflicts remain unresolved.',
      'sourceFiles':[str(PDF.relative_to(ROOT)),str(AR.relative_to(ROOT))],
      'sourceSha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [PDF,AR]},
      'inheritedEstimatedStoreyDatums':LEVELS,'sourceRegistrationMaxResidualPdfPoints':max(r['maxResidualPdfPoints']for r in registration.values()),
      'sourceSectionCorrespondence':'source-section-correspondence.json','feasibilityProof':'station-feasibility.json',
      'diagnosticLiftConflictCount':len(report['liftConflicts']),'diagnosticCrossFlightConflictCount':len(report['crossFlightConflicts']),
      'diagnosticSameFlightConflictCount':len(report['sameFlightConflicts']),'boundaryAccepted':False,
      'winderCornerChangeRequiredButNotImplemented':report['unimplementedWinderChange'],
      'sourceModelAndRoomPreservation':'native-preservation.json',
      'acceptanceCaveat':'Zero lift/cross-flight overlap applies only to the rejected diagnostic geometry, not a corrected native component. Same-flight joins and envelope are not accepted.',
      'requiredNextEvidence':'An architect-issued main-stair fourth/fifth plan/detail or a reliably registered built photograph showing the inside winder and intermediate platform. The2014 guide and low-resolution AR scan do not resolve the contradictory corner.',
      'limitations':['The published sectionBB supports the relative storey sequence, without reliable absolute vertical dimensions. No height changes were made.',
        'The0.25m parapet thickness and interval rise allocation are diagnostic estimates. No guessed0.232m trim was authored.',
        'Native floor apertures, landing support, facade intersections, guards and G-to-sixth connectivity remain unmodified and unaccepted for this218 proposal.']})
    print('SAWCIRC218_REVIEW_NOT_ACCEPTED',len(report['sameFlightConflicts']),report['unimplementedWinderChange'][0]['maximumPlanChangeMetres'],flush=True)

def native():
    import bpy
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint,update_scene
    from refine_mar_registration217 import room_snapshot
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    expected=accepted_fingerprints(ROOT/'result/blender/stage217',BASE_SHA)
    bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];update_scene()
    assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==expected
    before=room_snapshot();protected={name for room in before.values()for name in room['objects']};assert len(protected)==623
    records=[]
    for obj in bpy.data.collections['SAW_PUBLIC_INTERIOR_study'].all_objects:
        if obj.type!='MESH' or obj.hide_render:continue
        if not(obj.name.startswith(('SAW173','SAWFLOOR216'))or obj.name=='SAW_SAW_floor_0'):continue
        obj.data.calc_loop_triangles();records.append({'name':obj.name,'vertices':[list(obj.matrix_world@v.co)for v in obj.data.vertices],
          'triangles':[list(t.vertices)for t in obj.data.loop_triangles],'materials':[m.name if m else None for m in obj.data.materials]})
    assert room_snapshot()==before
    assert {name:object_fingerprint(bpy.data.objects[name])for name in expected}==expected
    write_json('accepted-native-surfaces.json',{'baselineSha256':BASE_SHA,'objects':records,'acceptedFingerprints':len(expected)})
    write_json('native-preservation.json',{'baselineSha256':BASE_SHA,'acceptedFingerprints':len(expected),'authoredSpaces':len(before),'protectedObjects':len(protected),
      'beforeSha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),'afterSha256':hashlib.sha256(json.dumps(room_snapshot(),sort_keys=True).encode()).hexdigest(),
      'roomObjectCounts':{key:len(row['objects'])for key,row in before.items()},'roomVisibilityGeometryUVModifiersMaterialsUnchanged':True,
      'scope':'Read-only extraction. No native object or collection was edited, archived or hidden. No complete native or component was saved.'})
    print('SAWCIRC218_READ_ONLY_NATIVE_VERIFIED',len(expected),len(protected),flush=True)

if __name__=='__main__':
    try:import bpy
    except ModuleNotFoundError:review()
    else:native()
