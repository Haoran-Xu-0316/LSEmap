"""Recheck LRB plan registration before changing the coupled atrium structure.

Read-only calibration. Guide landmarks are approximate selections on the
1500px archived render, not surveyed control points.
"""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage38'
OUT.mkdir(parents=True,exist_ok=True)
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
lrb=next(b for b in site['buildings'] if b['code']=='LRB')
ring=np.array(lrb['rings'][0])
# The north corner is rounded: its correspondence has greater uncertainty.
landmarks=[('west',125,416,0),('north',862,62,4),('east',1364,414,7),('south',866,1032,11)]
plan=np.array([[x,y,1] for _,x,y,_ in landmarks],dtype=float)
world=np.array([ring[index] for *_,index in landmarks])
transform=np.linalg.lstsq(plan,world,rcond=None)[0]
residuals=np.linalg.norm(plan@transform-world,axis=1)
leave_one_out=[]
for i in range(len(plan)):
 keep=[j for j in range(len(plan)) if i!=j]
 t=np.linalg.lstsq(plan[keep],world[keep],rcond=None)[0]
 leave_one_out.append(float(np.linalg.norm(plan[i]@t-world[i])))
# Independent readings from G, first and fourth floor renderings.
centres=np.array([[833,453],[828,454],[826,451]],dtype=float)
centre_world=np.c_[centres,np.ones(len(centres))]@transform
native=np.array(lrb['center'])+[-2,3]
mean=centre_world.mean(axis=0)
report={
 'source':'data/documents/library_floor_plans.pdf',
 'sourceSha256':hashlib.sha256((ROOT/'data/documents/library_floor_plans.pdf').read_bytes()).hexdigest(),
 'referenceRenders':['data/previews/library_floor_plans_p3.png','data/previews/library_floor_plans_p4.png','data/previews/library_floor_plans_p7.png'],
 'landmarks':[{'name':name,'pixel':[x,y],'gisRingIndex':index,'world':world[i].tolist(),
              'fitResidualMetres':float(residuals[i]),'leaveOneOutErrorMetres':leave_one_out[i]}
              for i,(name,x,y,index) in enumerate(landmarks)],
 'pixelToWorldAffine':transform.tolist(),
 'nativeAtriumCentre':native.tolist(), 'guideCentresPixels':centres.tolist(),
 'guideCentresWorld':centre_world.tolist(), 'meanGuideCentre':mean.tolist(),
 'suggestedTranslation':(mean-native).tolist(), 'translationMagnitudeMetres':float(np.linalg.norm(mean-native)),
 'interpretation':'Plan registration supports an eastward displacement; exact translation is approximate, especially at the rounded north corner.',
 'coupledComponents':['spiral slab and guards','floor openings and slab edges','columns and braces',
  'lift assembly','landing links','roof opening and dome','nearby shelves and reading furniture'],
 'additionalFinding':'The guide G and upper-floor opening outlines are not represented by one shared circular hole. Confirm each opening boundary before moving the core.',
 'decision':'Do not translate the core alone. Rebuild opening boundaries with fixed perimeter, then test furniture and landing clearance. Current edition37 geometry unchanged.',
 'limitations':['Diagram-to-GIS fit is not a measured survey','Centre picks are manual readings',
 'Diagram white areas require photographic cross-check before treating them as voids']}
(OUT/'library-plan-registration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['meanGuideCentre','suggestedTranslation','translationMagnitudeMetres']},ensure_ascii=False))
print('Fit residuals',residuals.tolist(),'leave-one-out',leave_one_out)
