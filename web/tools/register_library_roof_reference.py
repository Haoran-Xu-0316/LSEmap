"""Register the 2024 LRB roof reference for review before native reconstruction.

No model or public asset is changed. The aerial is oblique, its capture date is
unknown, and fitting four corners exactly does not establish metric accuracy.
Run with the project's existing MachineLearning Python environment.
"""
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'result/blender/stage107'
SOURCE_PDF = ROOT / 'data/collections/library-roof-2024/design-access-statement.pdf'
inspection = json.loads((OUTPUT / 'library-roof-inspection.json').read_text())
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
footprint = next(building for building in site['buildings'] if building['code'] == 'LRB')['rings'][0]

# Coordinates refer to a 1888x1334 display of PDF page 6, not a measured survey.
# Roof and street-level corners have parallax; this is deliberately a review fit.
landmarks = [
    {'name': 'west', 'pixel': [430, 807], 'footprintIndex': 0},
    {'name': 'north', 'pixel': [850, 604], 'footprintIndex': 4},
    {'name': 'east', 'pixel': [1199, 878], 'footprintIndex': 7},
    {'name': 'south', 'pixel': [945, 1090], 'footprintIndex': 11},
]
coefficients, targets = [], []
for landmark in landmarks:
    x, y = landmark['pixel']
    u, v = footprint[landmark['footprintIndex']]
    landmark['nativeWorld'] = [u, v]
    coefficients.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y],
                         [0, 0, 0, x, y, 1, -v*x, -v*y]])
    targets.extend([u, v])
homography = np.append(np.linalg.solve(coefficients, targets), 1).reshape(3, 3)

def project(pixel):
    mapped = homography @ np.array([*pixel, 1.0])
    return mapped[:2] / mapped[2]

shell = next(item for item in inspection if item['name'] == 'LRB_V31_sliced_dome_shell')
native_centre = np.mean(np.array(shell['bounds'])[:, :2], axis=0)
base_centre_pixel = [866, 866]
predicted_centre = project(base_centre_pixel)
centre_error = float(np.linalg.norm(predicted_centre-native_centre))
courtyard_pixels = [[650, 815], [817, 748], [1005, 855], [858, 977]]
roof_deck = next(item for item in inspection if item['name'] == 'LRB_roof_deck_around_atrium')

report = {
    'baselineRelease': 106,
    'sourcePdfSha256': hashlib.sha256(SOURCE_PDF.read_bytes()).hexdigest(),
    'sourcePage': 6,
    'sourceIssueDate': '2024-09-11',
    'photographCaptureDate': None,
    'landmarks': landmarks,
    'homography': homography.tolist(),
    'independentCheck': {'landmark': 'dome base centre', 'pixel': base_centre_pixel,
                         'projectedWorld': predicted_centre.tolist(),
                         'retainedNativeWorld': native_centre.tolist(),
                         'differenceMetres': centre_error},
    'reviewCourtyardOutline': [project(pixel).tolist() for pixel in courtyard_pixels],
    'currentDeckHeight': roof_deck['bounds'][0][2],
    'currentDeckIsSinglePlane': abs(roof_deck['bounds'][1][2]-roof_deck['bounds'][0][2]) < 1e-5,
    'publicationReady': False,
    'nextRequiredEvidence': [
        'Dimensioned roof plan or independently validated roof-level registration',
        'Current placement and dimensions of the heat pumps installed in 2025',
        'Current PV extent after the 2025 roof works',
    ],
    'sources': [
        {'url': 'https://docs.planning.org.uk/20240924/115/SJNKM3RPLBK00/xsfxb5rpke83wljl.pdf',
         'scope': '2024 design/access statement, existing roof photograph and annotated proposed VRF location; proposed unit is not proof of installation'},
        {'url': 'https://www.westminster.gov.uk/sites/default/files/media/documents/All%20-%203%20August%202025.pdf',
         'page': 123, 'reference': '25/03306/FULL',
         'scope': 'Permission granted 18 July 2025 for PV removal and three ASHP units; approval is not an as-built layout'},
        {'url': 'https://info.lse.ac.uk/staff/divisions/estates-division/sustainable-lse/what-we-do/energy',
         'scope': 'LSE confirms the LRB heat-pump project was completed in 2025; does not establish unit placement'},
    ],
    'limits': ['Image landmarks are visual estimates, not surveyed dimensions',
               'Four-corner fit is exact by construction; independent centre mismatch prevents automatic model placement',
               'Native height estimates are retained only as a baseline, not verified against the drawing'],
}
OUTPUT.mkdir(parents=True, exist_ok=True)
(OUTPUT / 'library-roof-registration-review.json').write_text(json.dumps(report, indent=2)+'\n')
print('LIBRARY_ROOF_REVIEW_SAVED', round(centre_error, 3), 'metres centre mismatch; model unchanged')
