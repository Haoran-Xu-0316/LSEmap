"""Audit the existing paved pedestrian network against archived centre lines.

Fixed project paths. The first pass exports visible native ground faces only;
no guessed route width or future public-realm scheme is introduced.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'result/blender/LSE_campus_detailed_v198.blend'
SHA='b45a6a433f350226beecfd201457420d86b2d253796098f86ff5417d5752b27e'
OUT=ROOT/'result/blender/pedestrian-network199'

def audit_native():
 import bpy
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
 rows=[]
 for obj in scene.objects:
  if obj.type!='MESH' or obj.hide_render or obj.hide_get():continue
  if not (obj.name.startswith('SITE194_') or obj.name in ['SITE173_Houghton_New_Inn_flush_paving_join','SITE_V114_Globe_continuous_paving']):continue
  verts=[list(obj.matrix_world@v.co) for v in obj.data.vertices]
  # Include upper pedestrian faces and adjacent surface contexts, not buildings.
  faces=[]
  for p in obj.data.polygons:
   points=[verts[i] for i in p.vertices]
   if len(points)>=3 and max(v[2] for v in points)-min(v[2] for v in points)<.002 and -.02<=points[0][2]<=.15:
    material=obj.data.materials[p.material_index] if len(obj.data.materials)>p.material_index else None
    faces.append(dict(vertices=list(p.vertices),material=material.name if material else None,z=points[0][2]))
  if faces:rows.append(dict(name=obj.name,vertices=verts,faces=faces,collections=[c.name for c in obj.users_collection]))
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'native-ground.json').write_text(json.dumps(dict(baselineSha256=SHA,objects=rows),indent=2)+'\n')
 assert hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA
 print('PEDESTRIAN199_AUDITED',len(rows),flush=True)


def review_coverage():
 """Measure existing coverage; centre lines never justify wider street polygons."""
 from shapely.geometry import Polygon,LineString
 from shapely.ops import unary_union
 record=json.loads((OUT/'native-ground.json').read_text())
 assert record['baselineSha256']==SHA
 targets={o['name']:o for o in record['objects'] if o['name'].startswith('SITE194_') or o['name']=='SITE173_Houghton_New_Inn_flush_paving_join' or o['name']=='SITE_V114_Globe_continuous_paving'}
 footprints={};top_faces={};rows=[]
 for name,obj in targets.items():
  planes={}
  for face in obj['faces']:
   points=[obj['vertices'][i] for i in face['vertices']]
   if max(p[2] for p in points)-min(p[2] for p in points)>1e-6:continue
   polygon=Polygon([p[:2] for p in points])
   if polygon.area<=1e-9:continue
   planes.setdefault(round(face['z'],3),[]).append(polygon)
  footprint=unary_union([p for z,polygons in planes.items() if z>=.039 for p in polygons])
  footprints[name]=footprint
  top_faces[name]={z:unary_union(polygons) for z,polygons in planes.items()}
  rows.append(dict(name=name,coveredAreaM2=footprint.area,components=len(footprint.geoms) if hasattr(footprint,'geoms') else 1,
                   sameHeightAdditiveExcessAreaM2={str(z):sum(p.area for p in polygons)-unary_union(polygons).area for z,polygons in planes.items()}))
 union=unary_union(list(footprints.values()));streets=[]
 for source in json.loads((ROOT/'data/collections/public-realm-2026/mapped-streets.json').read_text())['roads']:
  name=source['properties']['name']
  if source['geometry']['type']!='LineString' or name not in ['Houghton Street','Clare Market','Sheffield Street','John Watkins Plaza']:continue
  line=LineString(source['geometry']['coordinates']);missing=line.difference(union.buffer(.001))
  streets.append(dict(name=name,osmId=source['id'],lengthM=line.length,missingCentrelineLengthM=missing.length))
 assert all(row['missingCentrelineLengthM']<1e-6 for row in streets)
 globe=top_faces['SITE_V114_Globe_continuous_paving'];sheffield=top_faces['SITE194_SITE_V47_Sheffield_Street']
 coplanar=sheffield[.05].intersection(globe[.05]);visible_seams=coplanar.difference(globe[.052])
 report=dict(version=199,baseline=str(BASE.relative_to(ROOT)),baselineSha256=SHA,targetCollection='00_SITE',
  status='read-only-no-supported-major-footprint-change',componentPath=None,componentSha256=None,addedObjects=[],archivedObjects=[],
  nativeSurfaceAudit=rows,mappedRouteCoverage=streets,totalReviewedCentrelineLengthM=sum(s['lengthM'] for s in streets),
  existingIssues=dict(globeSheffieldUnderlyingCoplanarAreaM2=coplanar.area,globeSheffieldPotentialVisibleSeamAreaM2=visible_seams.area,
   disposition='No speculative resurfacing. Globe tiles sit2mm above the retained Sheffield surface. The potential same-height exposed seam area is0.0192m2; underlying paving is not a missing route. Retain for a focused source/renderer audit rather than cutting a large hole in the working surface.'),
  references=['data/collections/public-realm-2026/mapped-streets.json','data/collections/public-realm-2026/user-references/reference-09.png','data/collections/public-realm-2026/user-references/reference-05.png','data/collections/streets/coverage.json','data/collections/streets/raw/public_realm_strategy_2022.pdf','web/tools/refine_street_connections194.py'],
  decision='Do not add guessed widths or replacement patches: all9 mapped line segments are already covered, and the two native194 joins remain. Existing paver colours and low-level path footprints remain unchanged.',
  limitations=['Centreline coverage proves no missing centreline only. It does not validate full kerb width, wheelchair clearance, building thresholds or current2026 site measurements.',
   '2021 photographs in the2022 public-realm strategy and user photographs have uneven viewpoint coverage; no current measured kerb outline can be derived.',
   'Small same-plane additive overlaps remain within the retained detailed paver meshes; their area alone cannot distinguish coincident triangles from intentional bevel/edge construction. No geometry was removed from that ambiguous evidence.',
   '198 asphalt road union and all23holes are untouched. No change to buildings, vegetation, materials, UVs, public catalogue or runtime.'],
  verification=dict(baselineSha256Unchanged=hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA,noNativeSave=True,noComponentCreated=True))
 assert report['verification']['baselineSha256Unchanged']
 (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PEDESTRIAN199_COVERAGE',len(streets),report['totalReviewedCentrelineLengthM'],flush=True)


if __name__=='__main__':
 try:
  import bpy
 except ImportError:
  review_coverage()
 else:
  audit_native()
