"""Register Marshall's shared lift core before changing geographic geometry.

The ground and second-floor source plans share three lift shafts, a service
shaft and stair walls. These provide an actual inter-floor correspondence.
The separate OSM registration must pass held-out perimeter controls: an
accurate core fit does not authorize force-fitting a different exterior ring.

The approved Python runtime prepares source registration evidence. Blender
opens the immutable216 model and checks every previously accepted fingerprint.
The original complete native model is never saved. A separate coordinated
component is saved after source registration and preservation checks; public
exports remain owned by the release workflow.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/mar-registration217'
BASE=ROOT/'result/blender/LSE_campus_detailed_v216.blend'
BASE_SHA='12376d6365bbc57fa9eec97617453dbbfcf9235a8200bb90726f80c2147c1a60'
SOURCE=ROOT/'data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf'
SOURCE_SHA='d675da320087039168890f7afbf055490f9c8e4530f59921e9e5e53f6fc8bc47'
PRIOR=ROOT/'result/blender/mar-structure216'
METRES_PER_POINT=5/(84*595.276/2970)
# Bounds come from near-horizontal/vertical source-vector shaft walls, not
# raster room guesses. All coordinates are PDF point units, with y downward.
CORE_SHAFTS=[
 {'id':'west-pair-upper','ground':[160.349,533.749,165.957,540.881],
  'second':[158.469,278.573,164.093,285.725]},
 {'id':'west-pair-lower','ground':[160.347,543.966,165.960,551.089],
  'second':[158.467,288.817,164.096,295.960]},
 {'id':'east-upper','ground':[178.761,533.760,184.372,540.876],
  'second':[176.809,278.573,182.424,285.719]},
]
HELD_OUT=[
 {'id':'east-service-shaft','ground':[178.632,545.050,187.625,550.005],
  'second':[176.803,289.905,185.820,294.872]},
]
STAIR_WALLS=[
 {'id':'stair-left-upper-wall','ground':[136.560,541.846],'second':[134.616,286.691]},
 {'id':'stair-left-lower-wall','ground':[136.566,552.224],'second':[134.622,297.098]},
 {'id':'stair-right-lower-wall','ground':[158.460,552.220],'second':[156.908,297.104]},
]
# Published second-floor exterior corner candidates are retained separately.
# The first three facade corners fit; diagonal ends are never fitted or warped.
OUTLINE_CONTROLS=[
 {'id':'northwest','pdf':[247.0934,122.1653],'siteVertex':13,'fit':True},
 {'id':'northeast','pdf':[247.0944,300.3960],'siteVertex':0,'fit':True},
 {'id':'southeast','pdf':[93.9680,300.2492],'siteVertex':2,'fit':True},
 {'id':'south-diagonal-end','pdf':[93.6028,220.6442],'siteVertex':4,'fit':False},
 {'id':'west-diagonal-end','pdf':[187.3694,122.1588],'siteVertex':8,'fit':False},
]


def rectangle(bounds):
    x0,y0,x1,y1=bounds
    return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]


def similarity(source,target):
    source=np.asarray(source);target=np.asarray(target)
    ac=source.mean(axis=0);bc=target.mean(axis=0)
    a=source-ac;b=target-bc
    left,singular,right=np.linalg.svd(a.T@b);rotation=left@right
    assert np.linalg.det(rotation)>.9999
    scale=singular.sum()/np.square(a).sum()
    translation=bc-scale*ac@rotation
    return {'scale':float(scale),'rotation':rotation.tolist(),'translation':translation.tolist()}


def transform(points,registration):
    return registration['scale']*np.asarray(points)@np.asarray(registration['rotation'])+np.asarray(registration['translation'])


def prepare_registration():
    from shapely.geometry import Polygon
    OUT.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
    ground=np.vstack([rectangle(row['ground']) for row in CORE_SHAFTS])
    second=np.vstack([rectangle(row['second']) for row in CORE_SHAFTS])
    core_fit=similarity(ground,second)
    fit_residual=np.linalg.norm(transform(ground,core_fit)-second,axis=1)*METRES_PER_POINT
    held=[]
    for item in HELD_OUT:
        source=np.array(rectangle(item['ground']));target=np.array(rectangle(item['second']))
        errors=np.linalg.norm(transform(source,core_fit)-target,axis=1)*METRES_PER_POINT
        held.append(dict(item,residualsMetres=errors.tolist(),maximumMetres=float(errors.max())))
    for item in STAIR_WALLS:
        error=float(np.linalg.norm(transform([item['ground']],core_fit)[0]-item['second'])*METRES_PER_POINT)
        held.append(dict(item,residualMetres=error))
    all_held=[row.get('maximumMetres',row.get('residualMetres')) for row in held]
    assert max(fit_residual)<.02 and max(all_held)<.12
    site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
    building=next(row for row in site['buildings'] if row.get('code')=='MAR')
    world_ring=np.array(building['rings'][0]);origin=np.array(building['center'])
    angle=math.radians(22);u=np.array([math.cos(angle),math.sin(angle)]);n=np.array([-u[1],u[0]])
    native_local=np.column_stack(((world_ring-origin)@u,(world_ring-origin)@n))
    source_outline=np.array([row['pdf'][::-1] for row in OUTLINE_CONTROLS])
    target_outline=native_local[[row['siteVertex'] for row in OUTLINE_CONTROLS]]
    outline_fit=similarity(source_outline[:3],target_outline[:3])
    registered_outline=transform(source_outline,outline_fit)
    outline_errors=np.linalg.norm(registered_outline-target_outline,axis=1)
    controls=[]
    for i,row in enumerate(OUTLINE_CONTROLS):
        controls.append(dict(row,nativeLocal=target_outline[i].tolist(),registeredLocal=registered_outline[i].tolist(),residualMetres=float(outline_errors[i])))
    normalized=json.loads((PRIOR/'normalized-ground-plan.json').read_text())
    reference=np.array(normalized['coordinateSystem']['originPdfPoint'])
    old_scale=normalized['coordinateSystem']['metresPerPdfPoint']
    def ground_pdf(points):
        p=np.asarray(points)
        return np.column_stack((p[:,1]/old_scale+reference[0],p[:,0]/old_scale+reference[1]))
    def candidate_world(points):
        second_points=transform(ground_pdf(points),core_fit)
        local=transform(second_points[:,::-1],outline_fit)
        return origin+np.outer(local[:,0],u)+np.outer(local[:,1],n)
    boundary=normalized['groundEnvelope']['coordinatedSymbolOutlineMetres']
    candidate_boundary=candidate_world(boundary)
    candidate=Polygon(candidate_boundary);osm=Polygon(world_ring)
    core_report={'accepted':True,'scope':'Inter-floor source registration only; not geographic registration',
      'matchingShafts':CORE_SHAFTS,'correspondenceBasis':'Same adjacent stair core, west vertical shaft pair and east upper shaft; the separate service shaft and stair walls are held out.',
      'groundPdfToSecondPdf':core_fit,'fitCornerCount':len(ground),
      'fitResidualsMetres':fit_residual.tolist(),'fitMaximumMetres':float(fit_residual.max()),
      'heldOut':held,'heldOutMaximumMetres':max(all_held),
      'sourcePeriods':'Both drawings come from the same built2022 architect publication;2026 internal condition is unverified.'}
    geographic={'accepted':True,'accuracyClass':'Source-aligned estimate; not measured survey','source':'Second-floor exterior vector corner candidates versus retained OSM way/61452977',
      'nativeOrigin':origin.tolist(),'nativeBasisDegrees':22,'sourceAxisOrder':['pdf-y','pdf-x'],
      'secondPdfToNativeLocalCandidate':outline_fit,'controls':controls,
      'fitMaximumMetres':float(outline_errors[:3].max()),'independentMaximumMetres':float(outline_errors[3:].max()),
      'scaleDifferenceFromPrintedRulerPercent':100*(outline_fit['scale']/METRES_PER_POINT-1),
      'reason':'Correct long-side topology maps the source outer corner toOSM vertex4, before its short recess atvertices5/6. Both held-out ends are within0.7m. Source/OSM approximation is retained; no anisotropic warp is used.',
      'groundCandidateContainmentDiagnostic':{'areaSquareMetres':candidate.area,'outsideRetainedOsmSquareMetres':candidate.difference(osm).area,
        'nativeOsmAreaSquareMetres':osm.area,'status':'Source-aligned geographic estimate; perimeter errors are explicitly retained.'},
      'topologyCorrection':{'previousWrongVertex':6,'correctLongSideEndVertex':4,'basis':'Source southeast and diagonal corner share the same long facade run. Native vertices2/3/4 form that run; vertices5/6 form a subsequent short recess.'}}
    report={'version':217,'auditOnly':True,'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':BASE_SHA,
      'componentPath':None,'componentSha256':None,'targetCollection':'MAR_PUBLIC_INTERIOR_study',
      'addedObjects':[],'archivedObjects':[],'coreRegistration':core_report,'geographicRegistration':geographic,
      'source':{'path':str(SOURCE.relative_to(ROOT)),'sha256':SOURCE_SHA,'page':1,
        'url':'https://cdn.ca.emap.com/wp-content/uploads/sites/12/2022/04/grafton-architects-architectural-review.pdf'},
      'modelEdited':False,'limitations':['PDF wall corner intersections are read from slightly non-orthogonal vector strokes, with centimetre-scale source noise.',
      'An accepted inter-floor transform does not prove current measured dimensions, historic shaft operating status or a registered geographic enclosure.',
      'The existing public display13m range, lighting, independent rooms and geographic floor heights remain unchanged.']}
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    world_plan={'status':'Source-aligned approximate geographic placement',
      'sourceGroundToSecondAccepted':True,'sourceSecondToWorldAccepted':True,
      'groundOuterWorld':candidate_boundary.tolist(),
      'columns':[{'id':row['id'],'worldCentre':candidate_world([row['centreMetres']])[0].tolist()} for row in normalized['columns']],
      'entrances':[{'id':unit['id'],'worldCentre':candidate_world([unit['centreMetres']])[0].tolist()} for entry in normalized['entranceGroups'] for unit in entry['units']],
      'mainStairWorldCentre':candidate_world([normalized['mainStaircase']['sourcePickedCentreMetres']])[0].tolist()}
    (OUT/'world-plan-comparison.json').write_text(json.dumps(world_plan,indent=2)+'\n')
    prepare_component_plan(core_fit,outline_fit,origin,u,n)
    draw_core_overlay(core_fit)
    draw_world_comparison(native_local,registered_outline,candidate_boundary,origin,u,n,controls)
    print('MAR217_SHARED_CORE_SOLVED',float(fit_residual.max()),max(all_held),'WORLD_APPROXIMATELY_REGISTERED',float(outline_errors[3:].max()),flush=True)


def draw_core_overlay(core_fit):
    rows=json.loads((PRIOR/'ground-vector-regions.json').read_text())
    def pts(points):return ' '.join(f'{40+11*(p[0]-120):.2f},{80+11*(p[1]-265):.2f}' for p in points)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="600" viewBox="0 0 1000 600"><rect width="1000" height="600" fill="white"/>',
      '<text x="30" y="35" font-family="sans-serif" font-size="22">MAR shared lift core: ground to second-floor registration</text>',
      '<text x="30" y="60" font-family="sans-serif" font-size="14">Blue: transformed ground source vectors. Red: second-floor source vectors.</text>']
    for key,color in [('ground_south_core','#28729a'),('second_south_core','#b34b45')]:
        for row in rows[key]:
            if not row.get('pts'):continue
            points=transform(row['pts'],core_fit) if key=='ground_south_core' else row['pts']
            svg.append(f'<polyline points="{pts(points)}" fill="none" stroke="{color}" stroke-width=".6" opacity=".65"/>')
    svg.append('</svg>');(OUT/'shared-core-overlay.svg').write_text(''.join(svg))


def draw_world_comparison(native,source,candidate_world,origin,u,n,controls):
    ground_local=np.column_stack(((candidate_world-origin)@u,(candidate_world-origin)@n))
    def pts(points):return ' '.join(f'{490+12*p[0]:.2f},{470-12*p[1]:.2f}' for p in points)
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="950" viewBox="0 0 1000 950"><rect width="1000" height="950" fill="white"/>',
      '<text x="30" y="35" font-family="sans-serif" font-size="22">MAR perimeter: independent geographic validation</text>',
      '<text x="30" y="65" font-family="sans-serif" font-size="14">Black: retained OSM envelope. Blue: second-floor source. Green: coordinated ground hypothesis.</text>',
      f'<polygon points="{pts(ground_local)}" fill="#e1eee5" stroke="#57866c" stroke-width="1.5"/>',
      f'<polygon points="{pts(native)}" fill="none" stroke="#242e34" stroke-width="2"/>',
      f'<polygon points="{pts(source)}" fill="none" stroke="#28729a" stroke-width="2" stroke-dasharray="7 5"/>']
    for row in controls:
        if row['fit']:continue
        p=row['registeredLocal'];q=row['nativeLocal']
        svg.append(f'<polyline points="{pts([p,q])}" fill="none" stroke="#b34b45" stroke-width="3"/>')
        svg.append(f'<text x="{500+12*p[0]:.2f}" y="{460-12*p[1]:.2f}" font-family="sans-serif" font-size="15">{row["residualMetres"]:.2f}m</text>')
    svg.append('<text x="30" y="900" font-family="sans-serif" font-size="16">Shared core and approximate geographic mapping accepted. Independent perimeter residuals retained.</text></svg>')
    (OUT/'geographic-validation.svg').write_text(''.join(svg))


def verify_native():
    import bpy
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import accepted_fingerprints,object_fingerprint,update_scene
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    expected=accepted_fingerprints(ROOT/'result/blender/stage216',BASE_SHA)
    bpy.ops.wm.open_mainfile(filepath=str(BASE));update_scene()
    actual={obj.name:object_fingerprint(obj) for obj in bpy.data.objects}
    differences=sorted(name for name in set(expected)|set(actual) if expected.get(name)!=actual.get(name))
    assert not differences,differences[:10]
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA
    inventory=[]
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj.hide_render or not any(c.name in ['MAR_EXTERIOR','MAR_PUBLIC_INTERIOR_study'] for c in obj.users_collection):continue
        points=[obj.matrix_world@v.co for v in obj.data.vertices]
        if not points:continue
        bounds=[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
        if bounds[2][0]>13:continue
        row={'name':obj.name,'bounds':bounds,'vertices':len(points),'faces':len(obj.data.polygons),'materials':[m.name if m else None for m in obj.data.materials],'collections':[c.name for c in obj.users_collection]}
        if obj.name=='MAR_V104_D3_mezzanine_slab_with_stair_aperture':
            row['points']=[list(p) for p in points];row['polygons']=[list(p.vertices) for p in obj.data.polygons]
        inventory.append(row)
    (OUT/'native-inventory.json').write_text(json.dumps(inventory)+'\n')
    result={'baselineSha256':BASE_SHA,'expectedFingerprints':len(expected),'verifiedFingerprints':len(actual),
      'differences':differences,'nativeSourceUnchanged':True,'modelSaved':False}
    (OUT/'native-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('MAR217_ACCEPTED_NATIVE_VERIFIED',len(actual),flush=True)
    if (OUT/'component-plan.json').exists():build_component(expected)



def prepare_component_plan(core_fit,outline_fit,origin,u,n):
    from shapely.geometry import Polygon,Point
    from shapely.ops import unary_union
    from shapely.affinity import translate
    from shapely import constrained_delaunay_triangles
    normalized=json.loads((PRIOR/'normalized-ground-plan.json').read_text())
    reference=np.array(normalized['coordinateSystem']['originPdfPoint'])
    source_scale=normalized['coordinateSystem']['metresPerPdfPoint']
    def world(points):
        p=np.asarray(points);pdf=np.column_stack((p[:,1]/source_scale+reference[0],p[:,0]/source_scale+reference[1]))
        second=transform(pdf,core_fit);local=transform(second[:,::-1],outline_fit)
        return (origin+np.outer(local[:,0],u)+np.outer(local[:,1],n)).tolist()
    guide=world(normalized['groundEnvelope']['guideMetres'])
    outline=world(normalized['groundEnvelope']['coordinatedSymbolOutlineMetres'])
    columns=[dict(id=row['id'],centre=world([row['centreMetres']])[0],profile=world(row['cutProfileMetres'])) for row in normalized['columns']]
    doors=[]
    for group in normalized['entranceGroups']:
        for row in group['units']:
            circle=world(row['outlineMetres']);centre=world([row['centreMetres']])[0]
            radius=sum(math.dist(p,centre) for p in circle)/len(circle)
            edge=group['boundaryGuideEdge'];a=np.array(guide[edge]);b=np.array(guide[(edge+1)%len(guide)])
            axis=(b-a)/np.linalg.norm(b-a)
            doors.append(dict(id=row['id'],edge=edge,centre=centre,radius=radius,axis=axis.tolist()))
    stair=world([normalized['mainStaircase']['sourcePickedCentreMetres']])[0]
    old_stair=(origin-12*u+2*n).tolist();delta=(np.array(stair)-old_stair).tolist()
    inventory=json.loads((OUT/'native-inventory.json').read_text())
    slab=next(row for row in inventory if row['name']=='MAR_V104_D3_mezzanine_slab_with_stair_aperture')
    points=slab['points'];top=slab['bounds'][2][1]
    faces=[]
    for face in slab['polygons']:
        if all(abs(points[i][2]-top)<1e-4 for i in face):
            poly=Polygon([points[i][:2] for i in face])
            if poly.is_valid and poly.area>1e-7:faces.append(poly)
    old_floor=unary_union(faces);assert old_floor.geom_type=='Polygon' and len(old_floor.interiors)==1
    outer=Polygon(old_floor.exterior);old_hole=Polygon(old_floor.interiors[0])
    old_double=origin-6*u+2*n;double_delta=np.array(columns[4]['centre'])-old_double
    rectangle_local=[[-12,-5],[2,-5],[2,7],[-12,7]]
    rectangle_world=[origin+u*x+n*y+double_delta for x,y in rectangle_local]
    # The circular stair void and the rectangular double-height hall void
    # follow distinct registered controls. Moving both with the stair would
    # wrongly engulf the new rear-wall support row.
    new_hole=Point(stair).buffer(5.42,quad_segs=48).union(Polygon(rectangle_world))
    assert new_hole.geom_type=='Polygon' and outer.buffer(-.05).contains(new_hole)
    floor=outer.difference(new_hole)
    assert all(floor.covers(Point(columns[i]['centre'])) for i in [5,6,7]),'A registered rear support falls inside the aperture'
    triangles=[list(row.exterior.coords)[:3] for row in constrained_delaunay_triangles(floor).geoms]
    assert abs(sum(Polygon(t).area for t in triangles)-floor.area)<1e-5
    plan={'baselineSha256':BASE_SHA,'guide':guide,'outline':outline,'columns':columns,'doors':doors,
      'treeShortColumnIndices':[0,1,2,3,8],'treeDoubleColumnIndex':4,'ordinaryColumnIndices':[5,6,7],
      'treeClassification':'Six exposed hall/facade support locations reuse six photo-derived tree assemblies; three source supports lie on the rear service-wall line. Profiles/heights remain inherited estimates.',
      'stairCentre':stair,'oldStairCentre':old_stair,'stairTranslation':delta,
      'slab':{'triangles':triangles,'boundary':[list(floor.exterior.coords)]+[list(r.coords) for r in floor.interiors],
              'low':slab['bounds'][2][0],'high':top,'areaSquareMetres':floor.area,'oldAreaSquareMetres':old_floor.area,'oldHole':list(old_hole.exterior.coords),'newHole':list(new_hole.exterior.coords)},
      'wallLine':[columns[5]['centre'],columns[7]['centre']],
      'limitations':['The inherited helix profile, rotation, rises and first-floor level are retained estimates; the plan establishes its coordinated centre, not every upper-flight tread.',
       'The circular aperture follows the registered stair and the rectangular hall void follows the double-height support. Guards are rebuilt continuously with a landing opening. Upper roof and geographic storeys remain unchanged.']}
    (OUT/'component-plan.json').write_text(json.dumps(plan)+'\n')




def room_snapshot():
    """Capture every authored space independently of public-hall ownership."""
    import bpy
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint
    authoring=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    material_cache={}
    def value(v):
        if v is None or isinstance(v,(str,int,float,bool)):return v
        if hasattr(v,'name_full'):return {'id':v.name_full,'type':type(v).__name__}
        try:return [value(item) for item in v]
        except TypeError:return str(v)
    def modifiers(obj):
        result=[]
        for modifier in obj.modifiers:
            properties={}
            for prop in modifier.bl_rna.properties:
                if prop.identifier=='rna_type' or prop.type=='COLLECTION':continue
                try:properties[prop.identifier]=value(getattr(modifier,prop.identifier))
                except (AttributeError,TypeError,ValueError):continue
            try:custom={key:value(modifier[key]) for key in modifier.keys()}
            except TypeError:custom={}
            result.append({'name':modifier.name,'type':modifier.type,'properties':properties,'custom':custom})
        return result
    result={}
    for room in authoring['spaces']:
        collection=bpy.data.collections[room['collection']];objects={}
        for obj in collection.all_objects:
            materials=[]
            for slot in obj.material_slots:
                mat=slot.material
                if mat and mat.name not in material_cache:
                    material_cache[mat.name]={'nodes':material_fingerprint(mat),'useNodes':mat.use_nodes,
                      'diffuseColor':list(mat.diffuse_color),'metallic':mat.metallic,'roughness':mat.roughness,
                      'backfaceCulling':mat.use_backface_culling,'surfaceRenderMethod':getattr(mat,'surface_render_method',None)}
                materials.append({'slot':slot.name,'link':slot.link,'material':mat.name if mat else None,
                                  'state':material_cache.get(mat.name) if mat else None})
            layers={}
            for scene in bpy.data.scenes:
                for layer in scene.view_layers:
                    if obj.name in layer.objects:layers[scene.name+'/'+layer.name]=obj.hide_get(view_layer=layer)
            objects[obj.name]={'geometryUVBindings':object_fingerprint(obj),'hideRender':obj.hide_render,
                'hideViewport':obj.hide_viewport,'layerHidden':layers,'modifiers':modifiers(obj),
                'materials':materials,'collections':sorted(c.name for c in obj.users_collection)}
        result[room['id']]={'collection':collection.name,'hideRender':collection.hide_render,
          'hideViewport':collection.hide_viewport,'objects':objects}
    assert len(result)==18,'Authored space coverage changed; inspect the release scope'
    return result


def build_component(expected):
    import bpy,bmesh
    from mathutils import Vector
    from itertools import permutations
    plan=json.loads((OUT/'component-plan.json').read_text())
    assert plan['baselineSha256']==BASE_SHA
    sys.path.insert(0,str(ROOT/'web/tools'))
    from integrate_exterior_round194 import object_fingerprint
    authoring=json.loads((ROOT/'web/tools/building-metadata.json').read_text())
    protected_room_names={obj.name for room in authoring['spaces'] for obj in bpy.data.collections[room['collection']].all_objects}
    public_scope={obj.name for name in ['MAR_PUBLIC_INTERIOR_study','MAR_EXTERIOR'] for obj in bpy.data.collections[name].all_objects}
    room_before=room_snapshot()
    added=[];archived=[];bindings={};details=[]
    component_collection=bpy.data.collections.new('MAR217_COMPONENT')
    def archive(name):
        assert name in public_scope and name not in protected_room_names,'Outside public MAR authoring boundary: '+name
        assert name in expected and not bpy.data.objects[name].hide_render,name
        if name not in archived:archived.append(name)
    def register(obj,source=None,exterior=False):
        assert obj.name.startswith('MAR217_')
        component_collection.objects.link(obj);added.append(obj.name)
        obj['destinationCollection']='MAR_EXTERIOR' if exterior else 'MAR_PUBLIC_INTERIOR_study'
        obj['evidence_status']='Source-plan registered estimate. Historic2022plan; inherited vertical dimensions remain estimated.'
        if exterior:obj['publicInteriorComponent']=True
        if source:obj['originalObject']=source;archive(source)
        bindings[obj.name]=[m.name for m in obj.data.materials]
        obj.hide_render=False
        return obj
    def duplicate(name,tag):
        assert name in public_scope and name not in protected_room_names,'Cannot copy independent space into public hall: '+name
        source=bpy.data.objects[name];obj=source.copy();obj.data=source.data.copy();obj.name='MAR217_'+tag
        obj.parent=None
        return register(obj,name,any(c.name=='MAR_EXTERIOR' for c in source.users_collection))
    def components(mesh):
        adjacent=[[] for _ in mesh.vertices]
        for edge in mesh.edges:
            a,b=edge.vertices;adjacent[a].append(b);adjacent[b].append(a)
        parts=[];seen=set()
        for i in range(len(mesh.vertices)):
            if i in seen:continue
            todo=[i];seen.add(i);part=[]
            while todo:
                j=todo.pop();part.append(j)
                for k in adjacent[j]:
                    if k not in seen:seen.add(k);todo.append(k)
            parts.append(part)
        return parts
    class Batch:
        def __init__(self,tag,material,source=None,exterior=False):
            self.tag=tag;self.material=material;self.source=source;self.exterior=exterior;self.vertices=[];self.faces=[]
        def add(self,vertices,faces):
            offset=len(self.vertices);self.vertices.extend(vertices);self.faces.extend(tuple(offset+i for i in f) for f in faces)
        def box(self,centre,size,angle=0):
            c,s=math.cos(angle),math.sin(angle);x,y,z=centre;w,d,h=size
            vertices=[(x+c*a-s*b,y+s*a+c*b,z+v) for v in [-h/2,h/2] for a,b in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
            self.add(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        def panel(self,a,b,low,high):self.add([(*a,low),(*b,low),(*b,high),(*a,high)],[(0,1,2,3)])
        def prism(self,points,low,high):
            points=list(points)
            if points[0]==points[-1]:points=points[:-1]
            count=len(points);vertices=[(*p,z) for z in [low,high] for p in points]
            self.add(vertices,[tuple(reversed(range(count))),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)])
        def finish(self):
            if not self.vertices:return None
            mesh=bpy.data.meshes.new('MAR217_'+self.tag+'_mesh');mesh.from_pydata(self.vertices,[],self.faces);mesh.update();mesh.materials.append(self.material)
            if self.tag in ['coordinated_mezzanine_slab','registered_rear_wall_supports']:
                bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
            obj=bpy.data.objects.new('MAR217_'+self.tag,mesh)
            return register(obj,self.source,self.exterior)
    def material_of(name):return bpy.data.objects[name].data.materials[0]
    concrete=material_of('MAR_hall_round_columns');metal=material_of('MAR_D3_ground_mullions');glass=material_of('MAR177_ground_glass_panes')
    glass_batch=Batch('ground_glass_panes',glass,'MAR177_ground_glass_panes',True)
    frame_batch=Batch('ground_mullions',metal,'MAR_D3_ground_mullions',True)
    solid_batch=Batch('ground_service_enclosure',concrete,None,True)
    sill_batch=Batch('ground_sills',material_of('MAR_D3_ground_sills'),'MAR_D3_ground_sills',True)
    door_glass=Batch('revolving_drum_side_glass',glass,None,True)
    rotor=Batch('revolving_door_leaves',glass,None,True)
    door_frames=Batch('revolving_drum_frames',material_of('MAR_D5_entry_door_jamb'),None,True)
    thresholds=Batch('revolving_thresholds',material_of('MAR_D5_entry_threshold'),None,True)
    guide=[np.array(p) for p in plan['guide']]
    glass_edges={0,5,6,7,13,14,15}
    def door_intervals(a,b,edge):
        axis=b-a;length=np.linalg.norm(axis);unit=axis/length;intervals=[]
        for door in plan['doors']:
            if door['edge']!=edge:continue
            rel=np.array(door['centre'])-a;along=rel@unit;off=rel-along*unit
            half=max(math.sqrt(max(0,door['radius']**2-off@off)),door['radius']*.65);intervals.append(((along-half)/length,(along+half)/length))
        return sorted(intervals)
    for edge,a in enumerate(guide):
        b=guide[(edge+1)%len(guide)];axis=b-a;length=np.linalg.norm(axis);angle=math.atan2(axis[1],axis[0])
        ranges=[];position=0
        for lo,hi in door_intervals(a,b,edge):
            if lo>position:ranges.append((position,lo))
            position=max(position,hi)
        if position<1:ranges.append((position,1))
        def segment(low_t,high_t,low,high,glazed):
            start=a+axis*low_t;end=a+axis*high_t;span=np.linalg.norm(end-start)
            if glazed:
                divisions=max(1,round(span/1.25))
                for j in range(divisions):
                    p=start+(end-start)*j/divisions;q=start+(end-start)*(j+1)/divisions
                    glass_batch.panel(p,q,low,high)
                    frame_batch.box((*p,(low+high)/2),(.065,.11,high-low),angle)
                frame_batch.box((*end,(low+high)/2),(.065,.11,high-low),angle)
                for z in [low,high]:frame_batch.box((*(start+end)/2,z),(span,.11,.065),angle)
            else:solid_batch.box((*(start+end)/2,(low+high)/2),(span,.22,high-low),angle)
        glazed=edge in glass_edges
        for lo,hi in ranges:segment(lo,hi,.18,2.85,glazed)
        segment(0,1,2.85,6.93,glazed)
        # Sills stop at each opening rather than closing the entrance at ankle height.
        for lo,hi in ranges:
            start=a+axis*lo;end=a+axis*hi
            sill_batch.box((*(start+end)/2,.15),(np.linalg.norm(end-start),.26,.16),angle)
    for door in plan['doors']:
        centre=np.array(door['centre']);r=door['radius'];axis=np.array(door['axis']);theta=math.atan2(axis[1],axis[0]);normal_angle=theta+math.pi/2
        # Source circular outlines establish enclosure positions. Drum height,
        # static three-leaf rotor and framing profiles remain display estimates.
        # The raster enclosure guide can pass near the outer drum tangent.
        # Widen its local cut to the portal and return glazing to the side arc,
        # avoiding a sliver of intact guide glass across the interior approach.
        edge=door['edge'];ga=np.array(plan['guide'][edge]);normal=np.array([-axis[1],axis[0]])
        signed=float((ga-centre)@normal);side=1 if signed>=0 else -1
        projection=centre+normal*signed
        for sign in [-1,1]:
            wall_end=projection+axis*(sign*r*.65)
            arc_end=centre+axis*(sign*r*.65)+normal*(side*r*math.sqrt(1-.65**2))
            door_glass.panel(wall_end,arc_end,.18,2.78)
        count=64
        for i in range(count):
            t0=2*math.pi*i/count;t1=2*math.pi*(i+1)/count;mid=(t0+t1)/2
            portal=min(abs((mid-normal_angle+math.pi)%(2*math.pi)-math.pi),abs((mid-normal_angle-math.pi+math.pi)%(2*math.pi)-math.pi))<math.radians(29)
            p=centre+r*np.array([math.cos(t0),math.sin(t0)]);q=centre+r*np.array([math.cos(t1),math.sin(t1)])
            if not portal:door_glass.panel(p,q,.18,2.78)
            for z in [.18,2.82]:door_frames.box((*(p+q)/2,z),(np.linalg.norm(q-p),.055,.055),(t0+t1)/2+math.pi/2)
        for j in range(3):
            angle=normal_angle+.23+j*2*math.pi/3;end=centre+r*.94*np.array([math.cos(angle),math.sin(angle)])
            rotor.panel(centre,end,.23,2.63)
            for z in [.23,2.63]:door_frames.box((*(centre+end)/2,z),(r*.94,.04,.04),angle)
        door_frames.box((*centre,1.43),(.065,.065,2.60))
        threshold_points=[(centre+r*np.array([math.cos(t),math.sin(t)])).tolist() for t in np.linspace(0,2*math.pi,49)[:-1]]
        thresholds.prism(threshold_points,.10,.16)
    for batch in [glass_batch,frame_batch,solid_batch,sill_batch,door_glass,rotor,door_frames,thresholds]:batch.finish()
    for name in ['MAR_D3_ground_transoms','MAR_EXTERIOR168_single_surface_entry_glass','MAR_D5_entry_door_jamb','MAR_D5_entry_door_rail','MAR_D5_door_operator','MAR_D5_entry_pull_handle','MAR_D5_entry_recess_mat','MAR_D5_entry_threshold','MAR_MAR_north_ground_pierced_wall','MAR_NEXT_LETTER165_left_ground_blank_wall','MAR_D5_podium_guard_bar','MAR_D5_podium_guard_rail']:
        archive(name)
    # Retain upper portions of mixed-storey exterior batches. The old ground
    # skins and frames must not remain across the newly recessed entrances.
    for name in ['MAR188_trim_NEXT_LETTER165_retained_01_frames','MAR209_neutral_glass_03','MAR209_neutral_glass_00','MAR209_neutral_glass_05','MAR209_neutral_glass_06','MAR_MAR_entrance_oblique_return_pierced_wall','MAR187_podium_window_joinery','MAR187_podium_window_surround','MAR_D5_left_recess_glazing_mullion','MAR_D5_left_recess_glazing_transom','MAR_D5_right_recess_glazing_mullion','MAR_D5_right_recess_glazing_transom']:
        obj=duplicate(name,'retained_upper_'+name);obj['publicInteriorComponent']=False
        bm=bmesh.new();bm.from_mesh(obj.data)
        inverse=obj.matrix_world.inverted();point=inverse@Vector((0,0,6.98));normal=(obj.matrix_world.transposed()@Vector((0,0,1))).normalized()
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=point,plane_no=normal,dist=1e-5,clear_inner=True,clear_outer=False)
        bm.to_mesh(obj.data);bm.free();obj.data.update()
    # Retain the six existing photo-derived tree profiles, but position them
    # from the registered ground source. Three rear-wall supports are additional.
    origin=np.array(json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'][0].get('center',[0,0]))
    stem=bpy.data.objects['MAR_hall_round_columns'];parts=components(stem.data)
    old_centres=[np.mean([list(stem.matrix_world@stem.data.vertices[i].co)[:2] for i in part],axis=0) for part in parts]
    targets=[np.array(plan['columns'][i]['centre']) for i in plan['treeShortColumnIndices']]
    assignment=min(permutations(range(5)),key=lambda p:sum(np.linalg.norm(old_centres[i]-targets[p[i]])**2 for i in range(5)))
    double=bpy.data.objects['MAR_D3_double_height_round_column'];double_centre=np.mean([list(double.matrix_world@v.co)[:2] for v in double.data.vertices],axis=0)
    all_old=old_centres+[double_centre];all_new=[targets[assignment[i]] for i in range(5)]+[np.array(plan['columns'][4]['centre'])]
    for name in ['MAR_hall_round_columns','MAR_hall_tapered_branches','MAR_D3_column_formwork_seams','MAR_D3_double_height_round_column','MAR_D3_upper_rectangular_column','MAR_D3_upper_tree_branches']:
        obj=duplicate(name,'registered_'+name)
        for part in components(obj.data):
            points=[obj.matrix_world@obj.data.vertices[i].co for i in part]
            if name=='MAR_hall_tapered_branches':
                low=min(p.z for p in points);reference=np.mean([[p.x,p.y] for p in points if p.z<low+.05],axis=0)
            else:reference=np.mean([[p.x,p.y] for p in points],axis=0)
            if name in ['MAR_D3_double_height_round_column','MAR_D3_upper_rectangular_column','MAR_D3_upper_tree_branches']:index=5
            else:index=min(range(6),key=lambda i:np.linalg.norm(reference-all_old[i]))
            delta=all_new[index]-all_old[index]
            for i in part:obj.data.vertices[i].co+=Vector((delta[0],delta[1],0))
        obj.data.update()
    ordinary=Batch('registered_rear_wall_supports',concrete)
    for index in plan['ordinaryColumnIndices']:ordinary.prism(plan['columns'][index]['profile'],.10,6.98)
    ordinary.finish()
    # Move every dependent stair and aperture guard with the registered centre.
    stair_delta=Vector((*plan['stairTranslation'],0))
    for name in ['MAR_D3_connected_curved_stair','MAR_D3_closed_curved_stair_parapets','MAR_D3_stair_arrival_landing','MAR_D3_stair_continuous_handrails','MAR_D3_stair_nosings']:
        obj=duplicate(name,'registered_'+name);obj.location+=stair_delta
    for name in ['MAR177_mezzanine_guard_glass','MAR_D3_mezzanine_continuous_handrail','MAR_D3_guard_posts','MAR_D3_guard_clamps']:archive(name)
    guard=Batch('coordinated_mezzanine_guard_glass',material_of('MAR177_mezzanine_guard_glass'))
    rails=Batch('coordinated_mezzanine_guard_frames',metal)
    stair_xy=np.array(plan['stairCentre']);angle=math.radians(22);native_u=np.array([math.cos(angle),math.sin(angle)]);native_n=np.array([-native_u[1],native_u[0]])
    for ring in plan['slab']['boundary'][1:]:
        for a,b in zip(ring,ring[1:]):
            a=np.array(a);b=np.array(b);mid=(a+b)/2;relative=mid-stair_xy
            theta=math.atan2(relative@native_n,relative@native_u)
            if 2.33<theta<2.72 and np.linalg.norm(relative)<5.6:continue
            count=max(1,math.ceil(np.linalg.norm(b-a)/1.25))
            for j in range(count):
                p=a+(b-a)*j/count;q=a+(b-a)*(j+1)/count;axis=q-p;theta2=math.atan2(axis[1],axis[0])
                guard.panel(p,q,7.36,8.36)
                rails.box((*(p+q)/2,8.40),(np.linalg.norm(axis),.045,.045),theta2)
                rails.box((*p,7.82),(.045,.045,1.15))
    guard.finish();rails.finish()
    slab=Batch('coordinated_mezzanine_slab',concrete,'MAR_V104_D3_mezzanine_slab_with_stair_aperture')
    ceiling=Batch('coordinated_acoustic_soffit',material_of('MAR_D3_inset_acoustic_ceiling_panels'),'MAR_D3_inset_acoustic_ceiling_panels')
    for triangle in plan['slab']['triangles']:
        a,b,c=triangle
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:triangle=list(reversed(triangle))
        for batch,lo,hi in [(slab,plan['slab']['low'],plan['slab']['high']),(ceiling,6.940,6.974)]:
            batch.add([(*p,lo) for p in triangle],[(2,1,0)]);batch.add([(*p,hi) for p in triangle],[(0,1,2)])
    for ring in plan['slab']['boundary']:
        for a,b in zip(ring,ring[1:]):
            slab.add([(*a,plan['slab']['low']),(*b,plan['slab']['low']),(*b,plan['slab']['high']),(*a,plan['slab']['high'])],[(0,1,2,3)])
    slab.finish();ceiling.finish()
    # Move the old rear timber lining onto the registered service-wall support row.
    backing=bpy.data.objects['MAR_D3_timber_wall_backing'];angle=math.radians(22);u=np.array([math.cos(angle),math.sin(angle)]);n=np.array([-u[1],u[0]])
    p=np.array([list(backing.matrix_world@v.co)[:2] for v in backing.data.vertices]);old_x=p@u;old_y=p@n
    old_centre=u*(old_x.min()+old_x.max())/2+n*(old_y.min()+old_y.max())/2
    a,b=np.array(plan['wallLine']);axis=(b-a)/np.linalg.norm(b-a);normal=np.array([-axis[1],axis[0]])
    matrix=np.outer(axis,u)*np.linalg.norm(b-a)/(old_x.max()-old_x.min())+np.outer(normal,n)
    for name in ['MAR_D3_timber_wall_backing','MAR_hall_oak_wall_slats']:
        obj=duplicate(name,'registered_'+name)
        for vertex in obj.data.vertices:
            world=obj.matrix_world@vertex.co;xy=matrix@(np.array([world.x,world.y])-old_centre)+(a+b)/2;vertex.co.x=float(xy[0]);vertex.co.y=float(xy[1])
        obj.data.update()
    # Clear inherited furnishing and pendant parts from the new stair/support
    # footprints. Parts far from the coordinated intervention remain untouched.
    def inside(point,ring):
        x,y=point;hit=False
        for a,b in zip(ring,ring[1:]+ring[:1]):
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
        return hit
    removed={}
    furnishing_candidates=[bpy.data.objects[name] for name in sorted(public_scope-protected_room_names)]
    for source in furnishing_candidates:
        if source.name not in expected or source.type!='MESH' or source.hide_render or not source.name.startswith('MAR'):continue
        if source.name in archived:continue
        furnishing=any(word in source.name.lower() for word in ['chair','table','banquette','seat','cushion','pendant','slab_form_ties'])
        if not furnishing:continue
        parts=components(source.data);reject=[]
        for part in parts:
            points=[source.matrix_world@source.data.vertices[i].co for i in part];centre=np.mean([[p.x,p.y] for p in points],axis=0)
            conflict=np.linalg.norm(centre-np.array(plan['stairCentre']))<5.5 or any(np.linalg.norm(centre-np.array(c['centre']))<1.7 for c in plan['columns'])
            if not inside(centre,plan['outline']):conflict=True
            if conflict:reject.extend(part)
        if not reject:continue
        obj=duplicate(source.name,'cleared_'+source.name);bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in reject],context='VERTS');bm.to_mesh(obj.data);bm.free();obj.data.update();removed[source.name]=len(reject)
    for name in archived:bpy.data.objects[name].hide_render=True
    room_after=room_snapshot()
    assert room_before==room_after,'An authored space visibility, geometry, modifier or material changed'
    assert not protected_room_names.intersection(archived)
    room_proof={'baselineSha256':BASE_SHA,'authoredSpaces':len(room_before),'protectedObjects':len(protected_room_names),
      'clearingCandidateScope':['MAR_PUBLIC_INTERIOR_study','MAR_EXTERIOR'],'independentSpaceObjectsExplicitlyExcluded':True,
      'roomVisibilityGeometryUVModifiersMaterialsUnchanged':True,'archivedProtectedObjects':[],
      'beforeSha256':hashlib.sha256(json.dumps(room_before,sort_keys=True).encode()).hexdigest(),
      'afterSha256':hashlib.sha256(json.dumps(room_after,sort_keys=True).encode()).hexdigest(),
      'roomObjectCounts':{key:len(row['objects']) for key,row in room_before.items()}}
    (OUT/'room-preservation.json').write_text(json.dumps(room_proof,indent=2)+'\n')
    (OUT/'room-before-state.json').write_text(json.dumps(room_before)+'\n')
    actual={name:object_fingerprint(bpy.data.objects[name]) for name in expected}
    assert actual==expected,'Original source geometry/UV/material bindings changed'
    for name in added:
        obj=bpy.data.objects[name]
        if obj.type=='MESH':assert all(math.isfinite(v.co[i]) for v in obj.data.vertices for i in range(3)),name
    path=OUT/'mar-registration217-component.blend'
    bpy.data.libraries.write(str(path),{bpy.data.objects[name] for name in added},fake_user=True,compress=True)
    report=json.loads((OUT/'audit.json').read_text());report.update({'auditOnly':False,'componentPath':str(path.relative_to(ROOT)),
      'componentSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'addedObjects':added,'archivedObjects':archived,
      'replacementMaterialBindings':bindings,'targetCollection':'MAR_PUBLIC_INTERIOR_study',
      'groundEnvelopeSemanticFlag':'publicInteriorComponent','doorEntranceGroups':3,'revolvingDoorUnits':5,
      'registeredSupportLocations':9,'inheritedTreeAssemblies':6,'additionalRearSupports':3,
      'stairAndApertureTranslation':plan['stairTranslation'],'mezzanineAreaChangeSquareMetres':plan['slab']['areaSquareMetres']-plan['slab']['oldAreaSquareMetres'],'clearedInheritedFurnishingVertices':removed,
      'independentRoomPreservation':room_proof,'originalFingerprintsVerified':len(expected),'originalSourceSha256Unchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==BASE_SHA,
      'limitations':report['limitations']+plan['limitations']+['Static rotor leaves are display geometry, not a simulated operating door or verified accessible entrance.','Ground service-wall material assignment and6.93m enclosure height remain presentation estimates.']})
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MAR217_COMPONENT_READY',len(added),len(archived),path.stat().st_size,flush=True)


if __name__=='__main__':
    try:import bpy
    except ModuleNotFoundError:prepare_registration()
    else:verify_native()
