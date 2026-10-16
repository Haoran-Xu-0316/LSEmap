"""SAL continuous public circulation from registered historical built evidence.

Fixed Blender Text Editor authoring, accepted221native is read-only.
"""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v221.blend'
SHA='62b61a56a402120ab5047096113b02e20f85f7957442e39b6262557c151c69cb'
OUT=ROOT/'result/blender/sal-public222'
DATA=ROOT/'data/collections/sal-public222'
PREFIX='SAL222_'
sys.path.insert(0,str(ROOT/'web/tools'))
from integrate_exterior_round194 import object_fingerprint,accepted_fingerprints
from refine_portsmouth_exterior207 import material_fingerprint
import refine_sal_structure221 as prior


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def open_base():
 assert sha(BASE)==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];prior.update()
 assert {o.name:object_fingerprint(o)for o in bpy.data.objects}==accepted_fingerprints(ROOT/'result/blender/stage221',SHA)


def inspect():
 open_base();rows=[]
 for o in bpy.data.collections['SAL_EXTERIOR'].all_objects:
  if o.hide_render:continue
  points=[o.matrix_world@Vector(p)for p in o.bound_box]
  rows.append(dict(name=o.name,type=o.type,materials=[m.name if m else None for m in getattr(o.data,'materials',[])],bounds=[[min(p[i]for p in points),max(p[i]for p in points)]for i in range(3)]))
 (OUT/'inspection.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('SAL222_SOURCE_INSPECTED',len(bpy.data.objects),flush=True)


def inspect_connections():
 from mathutils.bvhtree import BVHTree
 from refine_ksw_exterior195 import connected_parts
 open_base();origin,right,inward,bounds=prior.registration()
 def local(point):
  d=point-origin;return(d.dot(right),d.dot(inward),point.z)
 glass=bpy.data.objects['GLASS181_SAL_Glass_pavilion_glazing'];parts=[]
 for indices in connected_parts(glass.data):
  pts=[local(glass.matrix_world@glass.data.vertices[i].co)for i in indices]
  parts.append(dict(indices=indices,bounds=[[min(p[i]for p in pts),max(p[i]for p in pts)]for i in range(3)]))
 samples=[]
 for name in ['SAL_Secondary_stone_base','SAL_Ground_stone_plinth','SAL184_GLASS181_SAL_NEXT_GLAZING149_retained_frontage_glass','SAL_NEXT_middle_sash_frames','SAL_NEXT_ENVELOPE_retained_sash_bars']:
  obj=bpy.data.objects[name];tree=BVHTree.FromPolygons([obj.matrix_world@v.co for v in obj.data.vertices],[tuple(f.vertices)for f in obj.data.polygons])
  for y in [9.6,12.65,15.70]:
   for z in [.40,1.40,2.40]:
    start=origin+right*(-1.8)+inward*y+Vector((0,0,z));hit=tree.ray_cast(start,-right,4)
    if hit[0]is not None:samples.append(dict(object=name,y=y,z=z,distance=hit[3],point=list(hit[0]),local=local(hit[0])))
 (OUT/'connection-inspection.json').write_text(json.dumps(dict(pavilionParts=parts,portalHits=samples),indent=2)+'\n');print('SAL222_CONNECTIONS_INSPECTED',len(parts),len(samples),flush=True)



PUBLIC='SAL_PUBLIC_INTERIOR222'
SCENE='SAL_PUBLIC_INTERIOR222'
LAYOUT=json.loads((DATA/'plan-layout.json').read_text())
FLOOR=.10
UPPER=4.90
HEIGHT=UPPER-FLOOR


def plan(point):
 s=LAYOUT['uniformScaleMetresPerPoint'];cx,cy=LAYOUT['sourceCentre'];tx,ty=LAYOUT['nativeLocalCentre']
 return tx+(point[0]-cx)*s,ty+(cy-point[1])*s


def local(point):
 origin,right,inward,_=prior.registration();p=point-origin
 return Vector((p.dot(right),p.dot(inward),point.z))


def configure():
 prior.PREFIX=PREFIX;prior.COLLECTION=PUBLIC
 collection=bpy.data.collections.new(PUBLIC);scene=bpy.data.scenes.new(SCENE);scene.collection.children.link(collection)
 bpy.data.scenes['00_CAMPUS_COMPLETE'].collection.children.link(collection)
 return collection,scene


def rect_from_plan(rect):
 a,b=plan(rect[:2]),plan(rect[2:]);return(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))


def path_rectangles(points,width):
 result=[]
 for a,b in zip(points,points[1:]):
  if abs(a[0]-b[0])<1e-5:result.append((a[0]-width/2,min(a[1],b[1])-width/2,a[0]+width/2,max(a[1],b[1])+width/2))
  else:result.append((min(a[0],b[0])-width/2,a[1]-width/2,max(a[0],b[0])+width/2,a[1]+width/2))
 return result


def floor_mesh(name,rectangles,bottom,top,material):
 """Exact rectangle union in a planar grid, retaining only its exterior shell."""
 import bmesh
 xs=sorted(set(round(r[i],6)for r in rectangles for i in [0,2]));ys=sorted(set(round(r[i],6)for r in rectangles for i in [1,3]));active=set()
 for i in range(len(xs)-1):
  for j in range(len(ys)-1):
   x=(xs[i]+xs[i+1])/2;y=(ys[j]+ys[j+1])/2
   if any(r[0]-1e-6<x<r[2]+1e-6 and r[1]-1e-6<y<r[3]+1e-6 for r in rectangles):active.add((i,j))
 verts=[];faces=[];lookup={}
 def index(i,j,k):
  key=(i,j,k)
  if key not in lookup:lookup[key]=len(verts);verts.append(prior.world(xs[i],ys[j],bottom if k==0 else top))
  return lookup[key]
 for i,j in sorted(active):
  a,b,c,d=[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
  faces.extend([tuple(index(*q,0)for q in [d,c,b,a]),tuple(index(*q,1)for q in [a,b,c,d])])
  for neighbour,edge in [((i,j-1),(a,b)),((i+1,j),(b,c)),((i,j+1),(c,d)),((i-1,j),(d,a))]:
   if neighbour not in active:faces.append(tuple(index(*q,k)for q,k in [(edge[0],0),(edge[1],0),(edge[1],1),(edge[0],1)]))
 mesh=bpy.data.meshes.new(PREFIX+name);mesh.from_pydata(verts,[],faces);mesh.materials.append(material);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.dissolve_limit(bm,angle_limit=.00001,verts=list(bm.verts),edges=list(bm.edges),delimit={'MATERIAL'});bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
 obj=bpy.data.objects.new(mesh.name,mesh);bpy.data.collections[PUBLIC].objects.link(obj);obj['destinationCollection']=PUBLIC;obj['publicLevel']='LG'if top<1 else'G'
 return obj


def make_tool(doors):
 batch=prior.Batch('door_cutting_tool',bpy.data.materials['SAL_Portland_stone'])
 for door in doors:
  y=door['localCentre'][1];half=door['openingWidth']/2;batch.box((-5.2,y-half,.075),(-2.0,y+half,2.83))
 return batch.finish()


def trim_originals(tool):
 from mathutils.bvhtree import BVHTree
 cutter=BVHTree.FromPolygons([tool.matrix_world@v.co for v in tool.data.vertices],[tuple(f.vertices)for f in tool.data.polygons]);owned=[];archived=[];records=[]
 for source in list(bpy.data.collections['SAL_EXTERIOR'].all_objects):
  if source.type!='MESH'or source.hide_render:continue
  if source.name.startswith('SAL221_')or'pavilion'in source.name.lower():continue
  tree=BVHTree.FromPolygons([source.matrix_world@v.co for v in source.data.vertices],[tuple(f.vertices)for f in source.data.polygons])
  if not tree.overlap(cutter):continue
  clone=source.copy();clone.data=source.data.copy();clone.name=PREFIX+'opened_'+source.name;clone.data.name=clone.name;clone['originalObject']=source.name;clone['destinationCollection']=PUBLIC
  bpy.data.collections[PUBLIC].objects.link(clone);clone.hide_render=False;clone.hide_set(False)
  bpy.context.view_layer.objects.active=clone;modifier=clone.modifiers.new('Three documented historical LG side portals','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=tool;clone.modifiers.move(len(clone.modifiers)-1,0)
  bpy.ops.object.modifier_apply(modifier=modifier.name)
  source.hide_render=True;source.hide_set(True);owned.append(clone);archived.append(source.name)
  records.append(dict(original=source.name,replacement=clone.name,beforePolygons=len(source.data.polygons),afterPolygons=len(clone.data.polygons),beforeTriangles=sum(len(f.vertices)-2 for f in source.data.polygons),afterTriangles=sum(len(f.vertices)-2 for f in clone.data.polygons),scope='Only three plan-supported doorway cutters; original full object, materials and UV archived intact'))
 assert'SAL_Secondary_stone_base'in archived
 return owned,archived,records


def stair_flight(batch,x0,x1,y0,direction,z0,risers,rise,tread):
 # Closed extruded stair profile with a sloped underside, not intersecting boxes.
 top=[(y0,z0)]
 for i in range(risers):
  top.extend([(y0+direction*i*tread,z0+(i+1)*rise),(y0+direction*(i+1)*tread,z0+(i+1)*rise)])
 polygon=top+[(y0+direction*risers*tread,z0+risers*rise-.20),(y0,z0-.20)]
 n=len(polygon);points=[(x,y,z)for x in [x0,x1]for y,z in polygon]
 faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
 batch.solid(points,faces)


def build():
 plaster=prior.material('plaster',(.77,.76,.72),.7)
 oak=prior.material('public_floor_oak',(.49,.37,.23),.63)
 stone=prior.material('stair_stone',(.51,.50,.47),.69)
 iron=prior.material('stair_iron',(.034,.036,.037),.39,.12)
 glass=bpy.data.materials['GLASS181_shell_SAL_Entrance_clear_glass']
 frame=prior.material('passage_white_frame',(.79,.79,.76),.45)
 batches={name:prior.Batch(name,mat)for name,mat in [('passage_glass',glass),('passage_frame',frame),('portal_liners',plaster),('LG_partitions',plaster),('G_partitions',plaster),('known_landing_cores',plaster),('main_stairs',stone),('stair_handrails',iron)]}
 doors=[]
 for row in LAYOUT['doors']:
  xy=plan(row['sourceCentre']);width=(row['sourceOpening'][1]-row['sourceOpening'][0])*LAYOUT['uniformScaleMetresPerPoint'];doors.append(dict(sourceCentre=row['sourceCentre'],localCentre=xy,openingWidth=width,clearWidth=width-.14,threshold=.10,head=2.83))
 # Reconstruct only plan-white public corridors and the documented open right lobby.
 internal=[rect_from_plan(r)for r in LAYOUT['publicFloorRectangles']]
 branches=[]
 for index,door in enumerate(doors):
  y=door['localCentre'][1];half=door['openingWidth']/2;branches.append((-5.22,y-half,-2.31,y+half))
  if index<2:branches+=path_rectangles([(-4.7,y),plan([440,door['sourceCentre'][1]])],1.8)
  else:branches+=path_rectangles([plan([499.611,429.482]),plan([486,429.482]),plan([486,445]),plan([440,445])],1.8)
 end=plan([499.611,335.654])[1];outer=[(-2.31,2.70,2.31,end)]
 internal+=branches
 # Ground-floor (G) plan is a pure translation of the same two stair cores.
 upper_rects=[rect_from_plan(r)for r in [[421.3,262.5,444.6,435.5],[128.8,435.7,498.4,455.3],[128.8,241.8,498.4,262.5],[128.8,262.5,151.7,435.7]]]
 stair_records=[];LG_pads=[];G_pads=[]
 for index,raw in enumerate([[151.912,381.387,185.3,434.864],[388.176,381.387,421.564,434.864]]):
  x0,yfront,x1,yback=rect_from_plan(raw);width=x1-x0;approach=1.1;tread=.31;risers=13;rise=HEIGHT/(risers*2);run=risers*tread;landing=yback-(yfront+approach+run);assert 1.0<landing<1.4
  flight_width=(width-.52)/2;y0=yfront+approach;y1=y0+run
  stair_flight(batches['main_stairs'],x0,x0+flight_width,y0,1,FLOOR,risers,rise,tread)
  stair_flight(batches['main_stairs'],x1-flight_width,x1,y1,-1,FLOOR+HEIGHT/2,risers,rise,tread)
  batches['main_stairs'].box((x0,y1,FLOOR+HEIGHT/2-.20),(x1,yback,FLOOR+HEIGHT/2))
  LG_pads.append((x0,yfront-.20,x1,y0));G_pads.append((x0,yfront-.20,x1,y0))
  # Landing piers give the mid-platform an actual load path to the shared floor.
  for x in [x0+.09,x1-.09]:batches['main_stairs'].box((x-.08,yback-.18,FLOOR),(x+.08,yback,FLOOR+HEIGHT/2-.20))
  rail=batches['stair_handrails']
  for side,(xl,xr,ystart,sign,zstart)in enumerate([(x0,x0+flight_width,y0,1,FLOOR),(x1-flight_width,x1,y1,-1,FLOOR+HEIGHT/2)]):
   for x in [xl+.045,xr-.045]:
    rail.beam((x,ystart,zstart+rise+1.0),(x,ystart+sign*run,zstart+HEIGHT/2+1.0),.035)
    for i in [0,3,6,9,12]:
     y=ystart+sign*(i+.5)*tread;z=zstart+(i+1)*rise;rail.column(x,y,z,z+1.0,.013,8)
  rail.beam((x0+.045,yback-.045,FLOOR+HEIGHT/2+1.0),(x1-.045,yback-.045,FLOOR+HEIGHT/2+1.0),.035)
  for x in [x0+.045,(x0+x1)/2,x1-.045]:rail.column(x,yback-.045,FLOOR+HEIGHT/2,FLOOR+HEIGHT/2+1.0,.013,8)
  # Upper arrival guards the first-flight opening while leaving the return flight clear.
  guard_x1=x1-flight_width-.045
  rail.beam((x0+.045,y0-.025,UPPER+1.0),(guard_x1,y0-.025,UPPER+1.0),.035)
  for x in [x0+.045,(x0+.045+guard_x1)/2,guard_x1]:rail.column(x,y0-.025,UPPER,UPPER+1.0,.013,8)
  samples=[]
  for side,x,ystart,sign,zstart in [(0,x0+flight_width/2,y0,1,FLOOR),(1,x1-flight_width/2,y1,-1,FLOOR+HEIGHT/2)]:
   for i in range(risers):samples.append(dict(flight=side,step=i+1,point=[x,ystart+sign*(i+.5)*tread,zstart+(i+1)*rise]))
  stair_records.append(dict(core=index,sourcePlanBox=raw,localBounds=[x0,yfront,x1,yback],risersPerFlight=risers,rise=rise,tread=tread,flightWidth=flight_width,midLandingDepth=landing,steps=samples))
 internal+=LG_pads
 floors=[floor_mesh('LG_public_floor',internal,.0,FLOOR,oak),floor_mesh('passage_floor',outer,.0,FLOOR,bpy.data.materials['SAL221_warm_grey_limestone_floor'])]
 # A single shared upper deck forms LG ceilings and the corresponding G public slab.
 upper=floor_mesh('G_public_deck',internal+upper_rects+G_pads,UPPER-.35,UPPER,oak);upper.data.materials.append(plaster)
 for face in upper.data.polygons:
  if face.normal.z<.5:face.material_index=1
 floors.append(upper)
 # The new side passage continues the old floor seam and inherited roof datum.
 glass_batch=batches['passage_glass'];glow=2.75;ghigh=end
 glass_batch.box((2.3275,glow,.10),(2.3725,ghigh,3.25))
 intervals=[(door['localCentre'][1]-door['openingWidth']/2,door['localCentre'][1]+door['openingWidth']/2)for door in doors];cursor=glow
 for lo,hi in sorted(intervals):
  if lo>cursor:glass_batch.box((-2.3725,cursor,.10),(-2.3275,lo,3.25))
  glass_batch.box((-2.3725,lo,2.83),(-2.3275,hi,3.25));cursor=hi
 if cursor<ghigh:glass_batch.box((-2.3725,cursor,.10),(-2.3275,ghigh,3.25))
 glass_batch.box((-2.3275,glow,3.26),(2.3275,ghigh,3.34))
 f=batches['passage_frame']
 for x in [-2.29,2.29]:
  f.box((x-.045,glow,3.20),(x+.045,ghigh,3.29))
  for y in [5.5,11.,17.8,ghigh-.08]:f.column(x,y,FLOOR,3.26,.055,10)
 for y in [5.5,11.,17.8,ghigh-.08]:f.box((-2.29,y-.035,3.20),(2.29,y+.035,3.27))
 for door in doors:
  y=door['localCentre'][1];half=door['openingWidth']/2
  for yy in [y-half,y+half]:batches['portal_liners'].box((-3.60,yy-.035,FLOOR),(-2.30,yy+.035,2.83))
  batches['portal_liners'].box((-3.60,y-half,2.83),(-2.30,y+half,2.93))
 # Only boundaries actually drawn on the historical plans; no unseen room fit-out.
 for name,segments,z0,z1 in [('LG_partitions',LAYOUT['planRoomBoundarySegments'],FLOOR,UPPER-.35),('G_partitions',[[[151.5,263.1],[151.5,381.4]],[[421.0,263.1],[421.0,381.0]],[[444.9,273.1],[444.9,411.3]],[[128.5,262.5],[128.5,435.7]]],UPPER,UPPER+3.45)]:
  for a,b in segments:
   a,b=plan(a),plan(b);batches[name].box((min(a[0],b[0])-.07,min(a[1],b[1])-.07,z0),(max(a[0],b[0])+.07,max(a[1],b[1])+.07,z1))
 for raw in LAYOUT['planKnownCoreRectangles']:
  x0,y0,x1,y1=rect_from_plan(raw);batches['known_landing_cores'].box((x0,y0,FLOOR),(x1,y1,UPPER-.35))
 owned=floors+[batch.finish()for batch in batches.values()]
 for obj in owned:obj['destinationCollection']=PUBLIC;obj['scope']='2015plan-registered continuousLG/Gpublic circulation, source age and dimensional estimates explicit; no unseen room interiors'
 tool=make_tool(doors);replacements,archived,cut_records=trim_originals(tool);mesh=tool.data;bpy.data.objects.remove(tool,do_unlink=True);bpy.data.meshes.remove(mesh);owned+=replacements
 return owned,archived,dict(doors=doors,stairCores=stair_records,passageEnd=end,lowerGroundDatum=FLOOR,groundDatum=UPPER,uniformSourceScale=LAYOUT['uniformScaleMetresPerPoint'],exteriorReplacements=cut_records),[obj.name for obj in replacements]+[PREFIX+'passage_floor',PREFIX+'passage_glass',PREFIX+'passage_frame',PREFIX+'portal_liners']


def shared_objects(archived):
 names=['SAL_Glass_pavilion_dark_frame','SAL_Glass_pavilion_name_fascia','SAL_Glass_pavilion_LSE_sign','SAL_Pavilion_name','SAL_Pavilion_LSE','GLASS181_SAL_Glass_pavilion_door_glass','GLASS181_SAL_Glass_pavilion_glazing','GLASS181_SAL_Glass_pavilion_roof']+[name for name in bpy.data.objects.keys()if name.startswith('SAL221_')]
 rows=[]
 for name in names:
  obj=bpy.data.objects[name];assert name not in archived and not obj.hide_render;assert obj.parent is None and not obj.constraints
  rows.append(dict(name=name,parent=None,constraints=[],matrixWorld=[list(row)for row in obj.matrix_world]))
 return names,rows


def geometry_tree(owned,shared,include_glass=False):
 from mathutils.bvhtree import BVHTree
 objects=list({o.name:o for o in list(owned)+[bpy.data.objects[n]for n in shared]}.values());vertices=[];faces=[];owners=[]
 for obj in objects:
  if obj.type!='MESH'or obj.hide_render:continue
  if not include_glass and any(m and ('glass'in m.name.lower()or'glazing'in m.name.lower())for m in obj.data.materials):continue
  offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(offset+i for i in face.vertices)for face in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 return BVHTree.FromPolygons(vertices,faces),owners


def verify(owned,shared,dimensions):
 tree,owners=geometry_tree(owned,shared,False);origin,right,inward,_=prior.registration();portal_rows=[]
 # Include every still-visible SAL surface and every new frame, not only the cut wall.
 full=[o for o in bpy.data.collections['SAL_EXTERIOR'].all_objects if not o.hide_render]+list(owned)
 # Original glass panels are solid here; the three real openings also clear glass.
 all_tree,all_owners=geometry_tree(full,[],True)
 for index,door in enumerate(dimensions['doors']):
  y=door['localCentre'][1]
  for offset in [-.55,0,.55]:
   for z in [.35,1.4,2.5]:
    hit=all_tree.ray_cast(prior.world(.20,y+offset,z),-right,5.3)
    assert hit[0]is None,('Blocked real side portal',index,offset,z,all_owners[hit[2]]if hit[2]is not None else None,hit)
    portal_rows.append(dict(door=index,depthOffset=offset,height=z,widthMetres=5.3,anyOpaqueOrGlassHit=False))
 floor_rows=[]
 route=[[(0,2.60),(0,dimensions['passageEnd']-.25)]]
 route += [[plan(a),plan(b)]for a,b in LAYOUT['routeSegments']]
 route += [[(-.7,d['localCentre'][1]),(-5.0,d['localCentre'][1])]for d in dimensions['doors']]
 for level in [FLOOR,UPPER]:
  for index,segment in enumerate(route if level==FLOOR else route[1:5]):
   a,b=map(Vector,segment);length=(b-a).length;count=max(2,int(length/.7)+1)
   for i in range(count+1):
    point=a.lerp(b,i/count);hit=tree.ray_cast(prior.world(point.x,point.y,level+.25),Vector((0,0,-1)),.40)
    assert hit[0]is not None and abs(hit[0].z-level)<.01,('Unsupported public route',level,index,list(point),hit)
    floor_rows.append(dict(level=level,path=index,position=list(point),support=owners[hit[2]],height=hit[0].z))
 # Literal saved stair treads, 2m vertical head clearance, and common floor arrivals.
 stairs=[]
 for core in dimensions['stairCores']:
  for step in core['steps']:
   x,y,z=step['point'];hit=tree.ray_cast(prior.world(x,y,z+.025),Vector((0,0,-1)),.06)
   assert hit[0]is not None and abs(hit[0].z-z)<.005,('Missing literal tread',step,hit)
   head=tree.ray_cast(prior.world(x,y,z+.025),Vector((0,0,1)),1.975)
   assert head[0]is None,('Low head clearance',step,owners[head[2]]if head[2]is not None else None,head)
   stairs.append(dict(core=core['core'],flight=step['flight'],step=step['step'],actualTreadHeight=hit[0].z,headClearanceMetres=2.0))
 guard_tree,guard_owners=geometry_tree([o for o in owned if o.name!=PREFIX+'stair_handrails'],shared,False);guard_rows=[]
 for core in dimensions['stairCores']:
  x0,yfront,x1,yback=core['localBounds'];guard_x1=x1-core['flightWidth']-.045
  for label,points,z in [('mid',[(x,yback-.045)for x in [x0+.045,(x0+x1)/2,x1-.045]],FLOOR+HEIGHT/2),('G',[(x,yfront+1.1-.025)for x in [x0+.045,(x0+.045+guard_x1)/2,guard_x1]],UPPER)]:
   for x,y in points:
    hit=guard_tree.ray_cast(prior.world(x,y,z+.025),Vector((0,0,-1)),.06)
    assert hit[0]is not None and abs(hit[0].z-z)<.005,('Unsupported landing guard',core['core'],label,x,y,z,hit)
    guard_rows.append(dict(core=core['core'],level=label,foot=[x,y,z],support=guard_owners[hit[2]],actualSupportHeight=hit[0].z))
 return dict(landingGuardSupportProbes=guard_rows,realSidePortalRays=portal_rows,continuousFloorRouteProbes=floor_rows,literalTreadAndHeadroomProbes=stairs,graph='Old pavilion -> extended side passage ->3actual openings ->LGcontinuous common loop ->2Ustairs ->Gcommon loop',limitations='Historic wayfinding registration and inherited4.8mstorey height; optical/structural details estimated, no contemporary surveyed whole-interior claim')


def render_views(label,owned,shared):
 import math
 scene=bpy.data.scenes.new(PREFIX+'REVIEW_'+label);collection=bpy.data.collections[PUBLIC];scene.collection.children.link(collection);bpy.context.window.scene=scene
 world=bpy.data.worlds.new(scene.name);world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.82,.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8;scene.world=world
 ld=bpy.data.lights.new(scene.name,'SUN');ld.energy=2;ld.angle=.14;sun=bpy.data.objects.new(scene.name+'_sun',ld);scene.collection.objects.link(sun);sun.rotation_euler=(.5,-.5,-.1)
 cd=bpy.data.cameras.new(scene.name);camera=bpy.data.objects.new(scene.name+'_camera',cd);scene.collection.objects.link(camera);scene.camera=camera;cd.clip_end=300
 scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 views=[]
 for name,position,target,ortho in [('connected-entry',(.7,5.0,1.75),(-3.5,13.5,1.65),None),('LG-stairs',(*plan([396,449]),1.75),(*plan([396,393]),2.50),None),('G-corridor',(*plan([404,447]),6.45),(*plan([440,350]),5.90),None),('public-cutaway',(-22,-19,41),(-26,18,1.9),66)]:
  hidden=[obj for obj in owned if obj.get('originalObject')and obj.get('originalObject')!='SAL_Secondary_stone_base']
  for obj in hidden:obj.hide_render=True
  if ortho:
   for obj in owned:
    if obj.name in [PREFIX+'G_public_deck',PREFIX+'G_partitions']:hidden.append(obj);obj.hide_render=True
   cd.type='ORTHO';cd.ortho_scale=ortho
  else:cd.type='PERSP';cd.lens=23
  camera.location=prior.world(*position);focus=prior.world(*target);camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
  views.append(dict(name=name,position=list(camera.location),target=list(focus),orthographicScale=ortho,fov=math.degrees(2*math.atan(36*900/1200/(2*23)))if ortho is None else None,hiddenForCutaway=[o.name for o in hidden]))
  for obj in hidden:obj.hide_render=False
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for obj in [camera,sun]:bpy.data.objects.remove(obj,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.worlds.remove(world);bpy.data.cameras.remove(cd);bpy.data.lights.remove(ld);prior.update()
 return views


def ownership(owned,public_names,exterior):
 collection=bpy.data.collections[PUBLIC]
 for obj in owned:
  if obj.name in public_names and obj.name not in collection.objects:collection.objects.link(obj)
  if obj.name not in public_names and obj.name in collection.objects:collection.objects.unlink(obj)
  if obj.name in exterior and obj.name not in bpy.data.collections['SAL_EXTERIOR'].objects:bpy.data.collections['SAL_EXTERIOR'].objects.link(obj)


def run():
 open_base();originals={o.name:object_fingerprint(o)for o in bpy.data.objects};material_states={m.name:material_fingerprint(m)for m in bpy.data.materials};modifiers={o.name:prior.stable_modifiers(o)for o in bpy.data.objects};rooms=prior.rooms_state();visibility={o.name:o.hide_render for o in bpy.data.objects};original_collections={o.name:sorted(c.name for c in o.users_collection)for o in bpy.data.objects};assert len(originals)==7651 and len(rooms)==19
 collection,scene=configure();owned,archived,dimensions,exterior=build();print('SAL222_BUILT',len(owned),archived,flush=True);shared,dependencies=shared_objects(archived);public_names=[o.name for o in owned if not o.get('originalObject')or o.get('originalObject')=='SAL_Secondary_stone_base'];assert set(public_names)|set(exterior)==set(o.name for o in owned);ownership(owned,public_names,exterior)
 for name in shared:collection.objects.link(bpy.data.objects[name])
 prior.update();checks=verify(owned,shared,dimensions);cameras=render_views('after',owned,shared)
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items());assert all(prior.stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert prior.rooms_state()==rooms
 fingerprints={o.name:object_fingerprint(o)for o in owned};bindings={o.name:[m.name if m else None for m in o.data.materials]for o in owned};component=OUT/'component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];prior.update();assert{obj.name:object_fingerprint(obj)for obj in bpy.data.objects}==accepted_fingerprints(ROOT/'result/blender/stage221',SHA)
 collection,scene=configure()
 with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(fingerprints)
 for obj in dst.objects:
  for i,name in enumerate(bindings[obj.name]):obj.data.materials[i]=bpy.data.materials[name]if name else None
  collection.objects.link(obj)
 ownership(dst.objects,public_names,exterior)
 for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
 for name in shared:collection.objects.link(bpy.data.objects[name])
 prior.update();assert verify(dst.objects,shared,dimensions)==checks
 assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all(object_fingerprint(bpy.data.objects[n])==v for n,v in fingerprints.items());assert all(material_fingerprint(bpy.data.materials[n])==v for n,v in material_states.items());assert all(prior.stable_modifiers(bpy.data.objects[n])==v for n,v in modifiers.items());assert prior.rooms_state()==rooms
 for name,old in original_collections.items():assert sorted(c.name for c in bpy.data.objects[name].users_collection)==sorted(old+([PUBLIC]if name in shared else[]))
 assert all(bpy.data.objects[n].hide_render==(True if n in archived else v)for n,v in visibility.items())
 for row in dependencies:assert [list(r)for r in bpy.data.objects[row['name']].matrix_world]==row['matrixWorld']
 verification=dict(savedComponentReopened=True,independentAcceptedObjectsVerified=len(originals),allOriginalMaterialNodesVerified=len(material_states),allOriginalModifiersVerified=len(modifiers),sourceGeometryUVTransformBindingsUnchanged=True,roomCollectionsPreserved=len(rooms),roomUniqueObjectsPreserved=len(set(n for r in rooms for n in r['objects'])),allOldRoomAndClassroomMembershipsPreserved=True,sourceCollectionsPreservedExceptExplicitPublicSharing=True,sharedObjectsHaveNoParentOrConstraints=True,sharedWorldMatricesExact=True,originalClassroomCollection='SAL_PUBLIC_INTERIOR_study',originalClassroomObjects=34,realPortalRays=len(checks['realSidePortalRays']),publicFloorProbes=len(checks['continuousFloorRouteProbes']),treadAndHeadroomProbes=len(checks['literalTreadAndHeadroomProbes']),landingGuardSupportProbes=len(checks['landingGuardSupportProbes']),addedObjectTriangles=sum(len(f.vertices)-2 for o in dst.objects for f in o.data.polygons),replacementOriginalTriangles=sum(r['beforeTriangles']for r in dimensions['exteriorReplacements']),incrementalTriangles=sum(len(f.vertices)-2 for o in dst.objects for f in o.data.polygons)-sum(r['beforeTriangles']for r in dimensions['exteriorReplacements']),nativeBaselineUnchanged=sha(BASE)==SHA)
 references=[]
 for path in ['data/collections/sal-public222/brismes2015.pdf','data/collections/interiors/originals/2012-32LIF.pdf','data/collections/library_round5/photos/SAL_afc16a916259.jpg','data/collections/library_round5/photos/SAL_6fc777f9f01e.jpg','data/collections/library_round5/photos/SAL_28f6b43c9977.jpg']:
  p=ROOT/path;references.append(dict(path=path,sha256=sha(p),stage='2015publishedG/LGwayfinding plan, not scale survey'if'brismes'in path else'2012built project context; photograph capture date unspecified',distribution='Reference only, not public texture'))
 report=dict(version=222,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,componentPath=str(component.relative_to(ROOT)),componentSha256=sha(component),targetCollection=PUBLIC,destinationCollection=PUBLIC,collectionSpec=dict(kind='public-interior',name=PUBLIC,scene=SCENE),addedObjects=list(fingerprints),archivedObjects=archived,changedObjects=[],addedFingerprints=fingerprints,replacementMaterialBindings=bindings,sharedObjects=shared,sharedDependencies=dependencies,exteriorObjects=exterior,publicObjects=public_names,publicPresentation='Public scene linkspublicObjects+sharedObjects. SAL_EXTERIORlinksexteriorObjects. Campus keeps both groups visible; full merged upper facade batches are excluded from public scene.',originalClassroom=dict(collection='SAL_PUBLIC_INTERIOR_study',objects=34,unchanged=True),scope='Continuous historical public entrance passage,3actualLGside openings, plan-white commonLGcirculation,2Ustairs andGcommon loop. Public geometry shares native world registration and existing pavilion; no independent miniature room.',dimensions=dimensions,checks=checks,verification=verification,references=references,sourceRegistration=LAYOUT,cameras=cameras,publicSections=[dict(id='LG',label='LG入口与公共环廊',objects=[n for n in public_names if n not in [PREFIX+'G_public_deck',PREFIX+'G_partitions']]+shared,cutawayHiddenObjects=[PREFIX+'G_public_deck',PREFIX+'G_partitions'],view=dict(position=[cameras[1]['position'][0],cameras[1]['position'][2],-cameras[1]['position'][1]],target=[cameras[1]['target'][0],cameras[1]['target'][2],-cameras[1]['target'][1]],fov=cameras[1]['fov'])),dict(id='G',label='G公共环廊与主梯到达',objects=[PREFIX+'G_public_deck',PREFIX+'G_partitions',PREFIX+'main_stairs',PREFIX+'stair_handrails'],view=dict(position=[cameras[2]['position'][0],cameras[2]['position'][2],-cameras[2]['position'][1]],target=[cameras[2]['target'][0],cameras[2]['target'][2],-cameras[2]['target'][1]],fov=cameras[2]['fov']))],publicView=dict(position=[cameras[1]['position'][0],cameras[1]['position'][2],-cameras[1]['position'][1]],target=[cameras[1]['target'][0],cameras[1]['target'][2],-cameras[1]['target'][1]],fov=cameras[1]['fov']),limitations=['2015wayfinding plans are schematic historical route evidence, not a measured survey. OSM registration and source proportional fit are estimates; no2026complete current interior claim.','2026planning index listsEXISTINGplans but document download links requirerecaptcha and return404; no proposed works or unread2026drawing used.','NativeLG/Gfloor datum and4.8mstorey height inherited, stair13+13riserspercore,31cmtread, handrails, wall heights and finishes are modelling estimates.','Unpictured rooms, precise lift doors/cars, fully continuous lift shafts, complete upper floors andBlevelcafe/learning void remain unbuilt.','Only plan-known public-facing room boundaries are represented; closed landings/core volumes are not invented room interiors.','Reference photographs are not redistributed or embedded as public textures; fine ornamental historic balustrade is simplified.'])
 report['sourceManifest']='data/collections/sal-public222/sources.json'
 report['publicViewSuggestion']=dict(coordinateSystem='Web: nativeX,nativeZ,-nativeY',interiorView=report['publicView'],interiorDisplayMaxZ=8.4,interiorSections=[dict(id='LG',label='LG入口与公共环廊',minHeight=-.05,maxHeight=4.54,scope='2015示意图支持的连续LG公共环廊、三处侧向门洞与两座主梯。G楼板作剖切隐藏。'),dict(id='G',label='G公共环廊与主梯到达',minHeight=4.55,maxHeight=8.4,scope='2015示意图支持的G公共环廊及主梯到达，不含未见房间。')],gallerySuggestions=[dict(name='sal-lg-stairs',label='LG公共主梯',sectionId='LG',view=report['publicSections'][0]['view']),dict(name='sal-g-corridor',label='G公共环廊',sectionId='G',view=report['publicSections'][1]['view']),dict(name='sal-connected-entry',label='入口亭与公共通廊',sectionId='LG',view=dict(position=[cameras[0]['position'][0],cameras[0]['position'][2],-cameras[0]['position'][1]],target=[cameras[0]['target'][0],cameras[0]['target'][2],-cameras[0]['target'][1]],fov=cameras[0]['fov']))])
 (OUT/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('SAL222_COMPONENT_REOPENED',len(owned),len(archived),verification,flush=True)


if __name__=='__main__':run()
