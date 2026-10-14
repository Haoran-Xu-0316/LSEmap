"""Register CBG's architect plan against surrounding GIS buildings.
Run directly with the existing MachineLearning Python. No command-line options.
Only writes result/blender/cbg-georegistration202; does not edit model geometry.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'result/blender/cbg-georegistration202'
OUTPUT.mkdir(parents=True, exist_ok=True)
PLAN = ROOT / 'data/collections/cbg_roof_registration/level12-plan-rshp-2016.jpg'
GIS = ROOT / 'result/blender/site_geometry.json'
site = json.loads(GIS.read_text())
by_code = {building['code']: building for building in site['buildings'] if building['code']}
by_id = {building['id']: building for building in site['buildings']}
# Manually read black outline corners in the full 1700x1201 architect drawing.
# PAN is the GIS code for the drawing's adjacent Tower One.
control_specs = [
    ('OLD', 10, (918, 294), 'east end of long south-facing outline'),
    ('OLD', 12, (106, 294), 'west end of same outline'),
    ('STC', 5, (1080, 280), 'southwest corner'),
    ('STC', 4, (1329, 249), 'southeast corner'),
    ('PAN', 0, (1098, 900), 'Tower One northeast corner'),
    ('PAN', 1, (1077, 1042), 'Tower One east-side bend'),
    ('PAN', 11, (757, 1035), 'Tower One northwest sloping-side junction'),
    ('PAN', 10, (750, 1083), 'Tower One southwest short-edge junction'),
]
pixels = np.array([item[2] for item in control_specs], dtype=float)
worlds = np.array([by_code[code]['rings'][0][index] for code, index, _, _ in control_specs])
flip = np.array([1, -1])  # Image y increases downwards; ENU y increases northwards.

def fit(pixel_points, world_points, fixed_scale=None):
    local = pixel_points * flip
    centered_local = local - local.mean(axis=0)
    centered_world = world_points - world_points.mean(axis=0)
    left, singular, right = np.linalg.svd(centered_local.T @ centered_world)
    rotation = left @ right
    assert np.linalg.det(rotation) > 0.999
    scale = fixed_scale if fixed_scale is not None else singular.sum() / np.sum(centered_local ** 2)
    translation = world_points.mean(axis=0) - scale * local.mean(axis=0) @ rotation
    predicted = scale * local @ rotation + translation
    return scale, rotation, translation, predicted - world_points

true_scale = 20 / 285
free_scale, _, _, free_residuals = fit(pixels, worlds)
scale, rotation, translation, residuals = fit(pixels, worlds, true_scale)

def to_world(points):
    return scale * (np.asarray(points, dtype=float) * flip) @ rotation + translation

def to_pixels(points):
    return (((np.asarray(points) - translation) @ rotation.T) / scale) * flip

column_pixels = np.array([(1399, 668), (1313, 662), (1227, 657), (1141, 652),
                          (1056, 648), (970, 644), (882, 639), (796, 634)])
measured_columns = to_world(column_pixels)
# Straight line through all eight sampled column centres. Symmetric nominal 6m grid.
column_midpoint = measured_columns.mean(axis=0)
_, _, directions = np.linalg.svd(measured_columns - column_midpoint)
direction = directions[0]
if direction @ (measured_columns[0] - measured_columns[-1]) < 0:
    direction *= -1
nominal_columns = column_midpoint + (21 - np.arange(8) * 6)[:, None] * direction
front_axis_nominal_angle = float(np.degrees(np.arctan2(direction[1], direction[0])))
# Front-left G7 to front-right G0 to rear-right to rear-left as visible in the plan.
# This is a design-level outline of canopy/terraces, not a four-corner occupied-room box.
roof_outline_pixels = np.array([(793, 632), (1396, 665), (1368, 924), (766, 858)])
roof_outline = to_world(roof_outline_pixels)
# Southern amenity podium: shared front boundary is the GIS7-storey part's rear edge;
# architect drawing's faint rear corners complete the separate low roof outline.
# This is provisional design geometry, not a surveyed two-storey footprint.
low_roof_outline_pixels = np.array([(239.9, 645.2), (781.6, 721.1), (767, 854), (243, 781)])
low_roof_outline = to_world(low_roof_outline_pixels)
block_outline_pixels = np.array([(276, 425), (977, 425), (977, 568), (886, 568),
                                 (886, 629), (790, 624), (402, 565), (276, 565)])
block_outline = to_world(block_outline_pixels)
leave_one_site_out = {}
for code in ('OLD', 'STC', 'PAN'):
    keep = np.array([item[0] != code for item in control_specs])
    ls, lr, lt, _ = fit(pixels[keep], worlds[keep], true_scale)
    endpoints = ls * (column_pixels[[0, -1]] * flip) @ lr + lt
    leave_one_site_out[code] = {'G0_G7_world': endpoints.tolist(),
                              'endpoint_change_metres': np.linalg.norm(endpoints - measured_columns[[0, -1]], axis=1).tolist()}
controls = []
for spec, world, residual in zip(control_specs, worlds, residuals):
    code, index, pixel, label = spec
    controls.append({'code': code, 'GIS_id': by_code[code]['id'], 'GIS_ring_vertex': index,
                     'feature': label, 'plan_pixel': list(pixel), 'GIS_world': world.tolist(),
                     'residual_world': residual.tolist(), 'residual_metres': float(np.linalg.norm(residual))})
old_origin = np.array([36.96627474, -62.79413750])
old_rotation = np.array([[np.cos(np.radians(58)), -np.sin(np.radians(58))],
                         [np.sin(np.radians(58)), np.cos(np.radians(58))]])
nominal_inherited_local = (nominal_columns - old_origin) @ old_rotation
old_roof = np.array([[-42, -2], [7, -2], [7, 14], [-42, 14]]) @ old_rotation.T + old_origin
old_wing = np.array([[7, -14], [35, -14], [35, 2], [7, 2]]) @ old_rotation.T + old_origin

audit = {
    'status': 'actionable estimated georegistration, independently fitted from non-CBG surroundings',
    'scope': 'output-only registration; no master/model/shared metadata modifications',
    'coordinate_system': site['coordinate_system'],
    'source_role': '2016 architect design drawing plus archived OSM GIS, not surveyed as-built data',
    'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (PLAN, GIS)},
    'source_GIS_retrieved_date': '2026-09-12',
    'scale_bar': {'pixels': [[1220, 1159], [1505, 1159]], 'length_metres': 20, 'metres_per_pixel': true_scale},
    'fixed_true_scale_similarity': {'rotation_image_x_world_angle_degrees': float(np.degrees(np.arctan2(rotation[0, 1], rotation[0, 0]))),
                                    'rotation_row_matrix_after_y_flip': rotation.tolist(), 'translation_world': translation.tolist(),
                                    'rms_metres': float(np.sqrt(np.mean(np.sum(residuals ** 2, axis=1)))),
                                    'max_residual_metres': float(np.linalg.norm(residuals, axis=1).max()), 'controls': controls},
    'free_similarity_crosscheck': {'metres_per_pixel': free_scale, 'scale_bar_difference_percent': (free_scale / true_scale - 1) * 100,
                                   'rms_metres': float(np.sqrt(np.mean(np.sum(free_residuals ** 2, axis=1))))},
    'leave_one_building_out_fixed_scale': leave_one_site_out,
    'column_registration': {'axis_order': 'photo G0 at NE/braced end, G7 at SW/canopy end adjacent low wing',
                            'measured_pixels_G0_to_G7': column_pixels.tolist(), 'measured_world_G0_to_G7': measured_columns.tolist(),
                            'measured_endpoint_length_metres': float(np.linalg.norm(measured_columns[0] - measured_columns[-1])),
                            'nominal_pitch_metres': 6, 'nominal_grid_world_G0_to_G7': nominal_columns.tolist(),
                            'nominal_grid_endpoint_length_metres': 42, 'nominal_grid_midpoint_world': column_midpoint.tolist(),
                            'G7_to_G0_world_angle_degrees': front_axis_nominal_angle,
                            'nominal_grid_in_inherited_local_frame': nominal_inherited_local.tolist(),
                            'nominal_fit_rms_metres': float(np.sqrt(np.mean(np.sum((nominal_columns - measured_columns) ** 2, axis=1))))},
    'tower_roof_design_outline': {'pixel_order': roof_outline_pixels.tolist(), 'world_order': roof_outline.tolist(),
                                 'includes': 'canopy and rear terraces; not a full occupied top-level rectangular solid',
                                 'side_lengths_metres': np.linalg.norm(np.roll(roof_outline, -1, axis=0) - roof_outline, axis=1).tolist()},
    'low_roof_design_outline': {'pixel_order': low_roof_outline_pixels.tolist(), 'world_order': low_roof_outline.tolist(),
                               'role': 'separate southern amenity podium hypothesis; front boundary from shared GIS7-storey rear edge, rear boundary from faint architect plan; not same-height7-storey teaching block'},
    'low_roof_northern_stepped_block': {'pixel_order': block_outline_pixels.tolist(), 'world_order': block_outline.tolist(),
                                      'role': 'faint additional low-roof outline, boundary estimate'},
    'GIS_tower_part': {'id': 'way/766878411', 'building_levels': '13', 'osm_timestamp': '2020-01-27T10:29:38Z',
                       'ring': by_id['way/766878411']['rings'][0], 'rectangle': by_id['way/766878411']['rectangle'],
                       'rectangle_side_lengths_metres': np.linalg.norm(np.roll(np.array(by_id['way/766878411']['rectangle']), -1, axis=0) - np.array(by_id['way/766878411']['rectangle']), axis=1).tolist()},
    'GIS_lower_part': {'id': 'way/766878412', 'properties': by_id['way/766878412']['properties'],
                       'ring': by_id['way/766878412']['rings'][0]},
    'uncertainty': {'recommended_position_allowance_metres': 1.0, 'recommended_roof_trace_allowance_metres': 0.7,
                    'basis': 'Fixed-scale external fit RMS0.294m,max0.573m; manual raster marks about3-5px; GIS cartographic error unquantified; design/as-built drift unquantified. 1m is working model tolerance, not survey confidence interval.'},
    'finding': 'The inherited tower/low-wing placement is reversed in world coordinates. The49m OSM edge belongs to the southwestern lower wing. The independent42m tower grid is northeastern and matches the GIS building:levels13 part.',
    'rebuild_recommendation': 'Use the registered nominal42m grid and world outline to place tower. Register low wing separately from design low-roof outline/GIS low part. Recompute all tower facade/roof/stair coordinates from the shared new frame; do not retain x7 junction or merely shorten the inherited49m tower.',
}
(OUTPUT / 'registration.json').write_text(json.dumps(audit, indent=2) + '\n')

fig, ax = plt.subplots(figsize=(17, 12))
ax.imshow(Image.open(PLAN), alpha=0.80, cmap='gray')
styles = [('OLD', '#3a739f'), ('STC', '#3a739f'), ('PAN', '#3a739f')]
for code, color in styles:
    polygon = np.array(by_code[code]['rings'][0]); polygon = np.vstack([polygon, polygon[0]])
    projected = to_pixels(polygon)
    ax.plot(*projected.T, color=color, linewidth=1.3, label='GIS surroundings' if code == 'OLD' else None)
for polygon, color, label in [(np.array(by_id['way/766878411']['rings'][0]), '#9d33bb', 'GIS 13-storey tower part'),
                               (np.array(by_id['way/766878412']['rings'][0]), '#387a4a', 'GIS lower part'),
                               (old_roof, '#df4939', 'Inherited tower, wrong wing'),
                               (old_wing, '#ec986a', 'Inherited low wing'),
                               (roof_outline, '#151515', 'Registered design roof'),
                               (low_roof_outline, '#6f9693', 'Separate amenity podium estimate')]:
    polygon = np.vstack([polygon, polygon[0]]); projected = to_pixels(polygon)
    ax.plot(*projected.T, color=color, linewidth=2, label=label)
for index, (pixel, spec) in enumerate(zip(pixels, control_specs)):
    ax.scatter(*pixel, c='#17689d', s=30)
    ax.text(pixel[0]+8, pixel[1]-7, f'{spec[0]}:{spec[1]}', color='#17689d', fontsize=9)
npix = to_pixels(nominal_columns)
ax.plot(*npix.T, 'o-', color='#145aad', linewidth=3, markersize=6, label='Nominal 7 x 6m tower grid')
for index, point in enumerate(npix):
    ax.text(point[0], point[1]-16, f'G{index}', color='#145aad', fontsize=11, ha='center')
ax.set_title('CBG independent external-control registration | fixed scale RMS 0.294m | 42m tower grid', fontsize=14)
ax.set_xlim(0, 1650); ax.set_ylim(1105, 0); ax.set_aspect('equal')
ax.legend(loc='upper left', fontsize=9, framealpha=0.95)
ax.set_xlabel('Architect drawing pixel x'); ax.set_ylabel('Architect drawing pixel y')
fig.tight_layout(); fig.savefig(OUTPUT / 'registration-overlay.png', dpi=140); plt.close(fig)
# Discard intermediate identification image; final overlay supersedes it.
(OUTPUT / 'gis-identification.png').unlink(missing_ok=True)
print(json.dumps({'fixed_rms': audit['fixed_true_scale_similarity']['rms_metres'],
                  'nominal_columns': nominal_columns.tolist(),
                  'tower_roof': roof_outline.tolist(),
                  'direction': front_axis_nominal_angle,
                  'inherited_local': nominal_inherited_local.tolist()}, indent=2))
# Compact placement contract for the rebuilding agent. x increases towards SW;
# y increases towards SE/rear, so the public NW facade is at y=0.
origin = nominal_columns[-1]
x_unit = -direction
y_unit = np.array([-x_unit[1], x_unit[0]])
frame_matrix = np.column_stack([x_unit, y_unit])

def frame_local(world_points):
    return (np.asarray(world_points) - origin) @ frame_matrix

old_landmarks = json.loads((ROOT / 'data/collections/cbg_roof_registration/registration.json').read_text())['registration']['landmarks']
landmarks = {name: {'pixel': record['pixel'], 'world': to_world([record['pixel']])[0].tolist(),
                    'local': frame_local(to_world([record['pixel']]))[0].tolist()}
             for name, record in old_landmarks.items()}
low_gis = np.array(by_id['way/766878412']['rings'][0])
low_local = frame_local(low_gis)
amenity_local = frame_local(low_roof_outline)
mapping = {
    'frame': {'origin_G7_SW_world': origin.tolist(), 'x_unit_SW': x_unit.tolist(), 'y_unit_SE_rear': y_unit.tolist(),
              'rotation_degrees': float(np.degrees(np.arctan2(x_unit[1], x_unit[0])) % 360),
              'tower_axis_x_G0_to_G7': np.arange(-42, 1, 6).tolist(), 'tower_front_y': 0,
              'public_square_side': 'negative y / NW', 'rear_TowerOne_side': 'positive y / SE',
              'formula': 'world=origin+x*x_unit+y*y_unit; z unchanged'},
    'legacy_frame_compatible_transform': {'G7_local': [7, -2],
                                        'translation_world': (origin - frame_matrix @ np.array([7, -2])).tolist(),
                                        'rotation_degrees': float(np.degrees(np.arctan2(x_unit[1], x_unit[0])) % 360),
                                        'tower_axis_x_G0_to_G7': np.arange(-35, 8, 6).tolist(),
                                        'instruction': 'This is an alternate frame ONLY: shift every compact-frame local point by[7,-2]before using translation.'},
    'tower': {'nominal_axes_world': nominal_columns.tolist(), 'nominal_length_metres': 42,
              'design_roof_envelope_local': frame_local(roof_outline).tolist(),
              'GIS_13storey_part_id': 'way/766878411', 'GIS_tower_polygon_local': frame_local(np.array(by_id['way/766878411']['rings'][0])).tolist(),
              'depth_estimate_metres': {'SW_end': 15.94, 'NE_end': 18.26, 'GIS_rectangle': 19.16},
              'depth_role': 'overall roof/canopy/terrace envelope; transverse9m frame module is not full depth',
              'highest_front_zones_x': {'office_G0_G4': [-42, -18], 'upper_circulation_G4_G6': [-18, -6], 'open_canopy_G6_G7': [-6, 0]},
              'traced_roof_landmarks_local': landmarks},
    'houghton_teaching_block': {'GIS_part_id': 'way/766878412', 'GIS_levels': 7,
                                'GIS_polygon_local': low_local.tolist(),
                                'bounds_local': {'x': [float(low_local[:,0].min()), float(low_local[:,0].max())],
                                                 'y': [float(low_local[:,1].min()), float(low_local[:,1].max())]},
                                'design_northern_stepped_outline_local': frame_local(block_outline).tolist(),
                                'note': 'GIS7levels can mean ground plus6upperfloors; floor-count source interpretation must be reconciled. 28m inherited wing is not supported: about49m outer front span.'},
    'southern_amenity_podium': {'GIS_part_id': None, 'provisional_polygon_local': amenity_local.tolist(),
                               'provisional_polygon_world': low_roof_outline.tolist(),
                               'bounds_local': {'x': [float(amenity_local[:,0].min()), float(amenity_local[:,0].max())],
                                                'y': [float(amenity_local[:,1].min()), float(amenity_local[:,1].max())]},
                               'front_shared_GIS_edge': {'low_part_vertex_indices': [3, 2], 'world': [low_gis[3].tolist(), low_gis[2].tolist()]},
                               'source_role': '2016 architect faint podium perimeter and shared GISlowpart edge; podium not encoded as separatepart in archivedGIS',
                               'height_role': 'separate low podium; this registration does not establish2storeyheight. Parent existing built evidence supplies height.'},
    'placement_tolerance_metres': 1.0,
    'registration_fixed_scale_rms_metres': float(np.sqrt(np.mean(np.sum(residuals ** 2, axis=1)))),
    'registration_fixed_scale_max_metres': float(np.linalg.norm(residuals, axis=1).max()),
    'leave_one_site_out_max_endpoint_change_metres': max(max(record['endpoint_change_metres']) for record in leave_one_site_out.values()),
}
(OUTPUT / 'rebuild-mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
