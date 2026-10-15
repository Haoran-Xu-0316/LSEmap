"""Check SAL flank height controls in the archived OSM data, without model writes.

Run in the established MachineLearning environment. Fixed paths and explicit
building identity prevent a neighbouring building's levels from becoming SAL
height controls. A single whole-building level tag cannot determine flank rows.
"""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, shape

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/sal-exterior215'
BASE = ROOT / 'result/blender/LSE_campus_detailed_v214.blend'
EXPECTED_SHA = '58d38dabb75db4fed63d79e1e26ad46da5c7ba809567ab074c70329f9b4880a6'
SITE = ROOT / 'result/blender/site_geometry.json'
RAW = ROOT / 'data/collections/streets/raw/osm_map.osm'
DERIVED = ROOT / 'data/collections/streets/derived/buildings.geojson'
PHOTO = ROOT / 'data/collections/library_round5/photos/SAL_5b39324ea103.jpg'
HEIGHT_FIELDS = ['building:levels', 'roof:levels', 'height', 'min_height',
                 'building:min_level', 'roof:height', 'building:part']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tags(element):
    return {item.attrib['k']: item.attrib['v'] for item in element.findall('tag')}


def main():
    sources = [BASE, SITE, RAW, DERIVED, PHOTO]
    original_hashes = {str(path.relative_to(ROOT)): sha(path) for path in sources}
    assert original_hashes[str(BASE.relative_to(ROOT))] == EXPECTED_SHA
    site = json.loads(SITE.read_text())
    native_sal = next(item for item in site['buildings'] if item.get('code') == 'SAL')
    raw = ET.parse(RAW).getroot()
    nodes = {n.attrib['id']: (float(n.attrib['lon']), float(n.attrib['lat']))
             for n in raw.findall('node')}
    ways = {w.attrib['id']: w for w in raw.findall('way')}
    sal_way = ways['61452981']

    def geometry(way):
        references = [n.attrib['ref'] for n in way.findall('nd')]
        if not all(reference in nodes for reference in references):
            return None
        coordinates = [nodes[reference] for reference in references]
        if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
            return None
        polygon = Polygon(coordinates)
        return polygon if polygon.is_valid else polygon.buffer(0)

    sal_polygon = geometry(sal_way)
    assert sal_polygon is not None
    data = json.loads(DERIVED.read_text())
    derived_sal = next(f for f in data['features'] if f.get('id') == 'way/61452981')
    assert sal_polygon.equals(shape(derived_sal['geometry']))
    nearby = []
    overlapping_parts = []
    all_parts = 0
    closed_parts = 0
    # Approximate ten-metre margin used solely to inventory neighbours.
    # Positive polygon overlap against the actual SAL outline is exact in the
    # source coordinates; no height or building membership is inferred.
    margin = .0001
    for identity, way in ways.items():
        properties = tags(way)
        is_part = 'building:part' in properties
        all_parts += int(is_part)
        if not ('building' in properties or is_part):
            continue
        polygon = geometry(way)
        if polygon is None:
            continue
        closed_parts += int(is_part)
        overlap = polygon.intersection(sal_polygon).area
        positive_overlap = overlap > 1e-14
        if polygon.intersects(sal_polygon.buffer(margin)):
            record = {'id': 'way/' + identity,
                      'name': properties.get('name', properties.get('addr:housename')),
                      'housenumber': properties.get('addr:housenumber'),
                      'controls': {field: properties.get(field) for field in HEIGHT_FIELDS},
                      'overlapFractionOfSal': overlap / sal_polygon.area,
                      'positiveOverlap': positive_overlap,
                      'touchesSal': polygon.touches(sal_polygon)}
            nearby.append(record)
            if is_part and positive_overlap:
                overlapping_parts.append(record)
    memberships = [{'id': 'relation/' + r.attrib['id'], 'tags': tags(r),
                    'members': [m.attrib for m in r.findall('member')]}
                   for r in raw.findall('relation')
                   if any(m.attrib['type'] == 'way' and m.attrib['ref'] == '61452981'
                          for m in r.findall('member'))]
    derived_parts = [f for f in data['features']
                     if 'building:part' in f.get('properties', {})
                     and shape(f['geometry']).intersection(sal_polygon).area > 1e-14]
    assert not overlapping_parts and not derived_parts and not memberships
    ring = native_sal['rings'][0]
    angle = math.radians(24.35)
    local = lambda p: [-p[0]*math.cos(angle)-p[1]*math.sin(angle),
                       -p[0]*math.sin(angle)+p[1]*math.cos(angle)]
    blocks = []
    for edge in [0, 2, 4]:
        start, end = ring[edge], ring[edge + 1]
        length = math.dist(start, end)
        blocks.append({'edge': edge, 'lengthM': length,
                       'startLocal': local(start), 'endLocal': local(end),
                       'inheritedEstimatedBayCount': max(1, round(length / 3.65)),
                       'blockSpecificHeight': None, 'blockSpecificLevels': None})
    assert [b['inheritedEstimatedBayCount'] for b in blocks] == [2, 7, 2]
    assert {str(path.relative_to(ROOT)): sha(path) for path in sources} == original_hashes
    report = {
        'code': 'SAL', 'version': 215, 'decision': 'no-differentiating-height-controls',
        'baseline': str(BASE.relative_to(ROOT)), 'baselineSha256': EXPECTED_SHA,
        'targetCollection': 'SAL_EXTERIOR', 'componentPath': None,
        'componentSha256': None, 'addedObjects': [], 'archivedObjects': [],
        'changedObjects': [], 'integrationRequired': False,
        'sourceSha256': original_hashes,
        'salIdentity': {'id': 'way/61452981', 'rawWayAttributes': sal_way.attrib,
                        'rawTags': tags(sal_way),
                        'derivedHeightControls': {f: derived_sal['properties'].get(f)
                                                  for f in HEIGHT_FIELDS},
                        'siteHeightControls': {f: native_sal['properties'].get(f)
                                               for f in HEIGHT_FIELDS},
                        'rawDerivedFootprintEqual': True,
                        'siteProjectedAreaM2': native_sal['area'],
                        'rawOutlineVertexCountExcludingClosure':
                            len(sal_way.findall('nd')) - 1},
        'partInventory': {'rawBuildingPartWays': all_parts,
                          'rawClosedBuildingPartPolygons': closed_parts,
                          'rawPartsWithPositiveSalOverlap': len(overlapping_parts),
                          'derivedPartsWithPositiveSalOverlap': len(derived_parts),
                          'salRelationMemberships': memberships},
        'nearbyBuildingControls': nearby, 'nativeFlankOutlineSegments': blocks,
        'conclusion': 'Only a whole-building building:levels=6 tag is available. '
                      'No SAL building-part polygons, per-block levels, height, '
                      'roof:levels or roof:height resolve the flank. The 2/7/2 '
                      'bay sequence comes from outline lengths divided by an '
                      'assumed3.65m spacing; it is not mapped window evidence.',
        'photoCrossCheck': {'file': str(PHOTO.relative_to(ROOT)), 'sha256': sha(PHOTO),
                           'url': 'https://www.jesticowhiles.com/wp-content/uploads/2024/01/2393_N32926_high.jpg',
                           'status': 'Existing completed-building photo, capture date unknown; reviewed in SAL214.',
                           'result': 'The photograph cannot supply missing block heights without independent registration. Existing near-dark and middle-pale frames are already implemented; no repeated palette correction.'},
        'limitations': ['ArchivedOSM snapshot was retrieved2026-09-12; this is a local control audit, not a refreshed current survey.',
                        'Neighbour35Lincoln\'sInnFields way/1335918466 has seven levels, but belongs to a distinct building and supplies no SAL-part height.',
                        'Whole-building six levels cannot be converted to six exposed window rows or distributed among the three flank segments.',
                        'No differentiating control exists, so no proposed correction or new rendering is warranted.'],
        'verification': {'baselineFileShaUnchanged': True, 'sourceFilesUnchanged': True,
                         'blenderStarted': False, 'nativeModelWritten': False,
                         'newRenderCreated': False,
                         'originalGeometryUVMaterialNodesRoomsPreserved': 'No native file was opened for writing; identical baseline file SHA verified before and after.'}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'decision': report['decision'], 'parts': report['partInventory'],
                      'baySequence': [b['inheritedEstimatedBayCount'] for b in blocks],
                      'baselineShaUnchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
