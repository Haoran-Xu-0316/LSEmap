"""Measure the MAR north opening mismatch before changing upper-wing geometry.

Run in Blender's Text Editor. This reads the current source and records evidence
only. Two retained outer podium windows anchor the photo's horizontal mapping;
upper opening edge picks are approximate and are not surveyed dimensions.
"""
from pathlib import Path
import json
import hashlib
import bpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mathutils.bvhtree import BVHTree
from refine_mar_exterior174 import world, N

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v187.blend'
PHOTO = ROOT / 'data/建筑图片/MAR_Marshall Building/01_建筑实拍/architecture_round5_MAR_mar_kane_02.jpg'
OUTPUT = ROOT / 'result/blender/mar-north-alignment'


def audit_north_alignment():
    source_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(MODEL))
    scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
    bpy.context.window.scene = scene
    for layer in scene.view_layers:
        layer.update()
    visible = set()

    def collect(collection):
        if collection.hide_render:
            return
        visible.update(obj for obj in collection.objects if not obj.hide_render)
        for child in collection.children:
            collect(child)

    collect(scene.collection)
    trees = []
    for obj in visible:
        if obj.type != 'MESH' or not obj.name.startswith('MAR') or not obj.data.polygons:
            continue
        tree = BVHTree.FromPolygons(
            [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
            [tuple(face.vertices) for face in obj.data.polygons],
        )
        trees.append((obj.name, tree))

    # Looking south, image-right is decreasing localX, as confirmed by the
    # existing two outer windows. A missing third window is not a fit anchor.
    anchors = [dict(photoX=143.0, localX=19.5), dict(photoX=1065.0, localX=-25.9)]
    slope = (anchors[1]['localX'] - anchors[0]['localX']) / (anchors[1]['photoX'] - anchors[0]['photoX'])
    intercept = anchors[0]['localX'] - slope * anchors[0]['photoX']
    opening_photo_pixels = [373.0, 639.0]
    opening_local = sorted(intercept + slope * pixel for pixel in opening_photo_pixels)
    rows = []
    for height in [25.2, 28.1, 31.1]:
        samples = []
        for step in range(217):
            x = -30 + step * .25
            hits = []
            # Start behind the screen fins, looking only through the depth band
            # containing the registered front office wall. This does not assert
            # that an empty band is an unobstructed full-depth courtyard.
            for name, tree in trees:
                point, normal, face, distance = tree.ray_cast(world(x, 19.0, height), -N, .6)
                if point is not None:
                    hits.append((distance, name))
            samples.append(dict(x=x, firstHit=min(hits) if hits else None))
        empty = [sample['x'] for sample in samples if sample['firstHit'] is None]
        runs = []
        for x in empty:
            if not runs or x - runs[-1][-1] > .251:
                runs.append([x])
            else:
                runs[-1].append(x)
        rows.append(dict(height=height, emptyIntervals=[[r[0], r[-1]] for r in runs if len(r)>2], samples=samples))
    report = dict(
        sourceModel=str(MODEL.relative_to(ROOT)), sourceModelSha256=source_hash,
        sourcePhoto=str(PHOTO.relative_to(ROOT)), photoSha256=hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
        sourceURL='https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/',
        captureDate='unknown', photoWidth=1200, anchors=anchors,
        photoOpeningPixels=opening_photo_pixels, estimatedPhotoOpeningLocalX=opening_local,
        photoToLocalSlope=slope, photoToLocalIntercept=intercept,
        nativeFrontWallDepthBand=[18.4,19.0], rows=rows,
        limitations=[
            'Opening-edge picks have roughly10pixel uncertainty; perspective and recess parallax introduce additional unmeasured error.',
            'The two anchors constrain a horizontal comparison only, not a complete camera or facade homography.',
            'The architect-published third-floor plan is not a roof plan and does not prove upper-wing heights or depths.',
            'No native meshes, materials, public assets or deployment changed by this audit.',
        ],
    )
    assert hashlib.sha256(MODEL.read_bytes()).hexdigest() == source_hash
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'alignment.json').write_text(json.dumps(report, indent=2) + '\n')
    print('MAR_NORTH_ALIGNMENT', opening_local, [(row['height'], row['emptyIntervals']) for row in rows])


if __name__ == '__main__':
    audit_north_alignment()
