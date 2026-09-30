"""Prepare edition46 stone courses and mapped street-object placements.
Dimensions are estimates; existing photographs establish the street character.
"""
from pathlib import Path
import json, math
from shapely import affinity, constrained_delaunay_triangles
from shapely.geometry import Polygon, Point, box, shape
from shapely.ops import unary_union, substring

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'result/blender/stage46'
OUT.mkdir(parents=True,exist_ok=True)
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text())
old=json.loads((ROOT/'result/blender/stage44/paving-plan.json').read_text())
buildings=unary_union([Polygon(b['rings'][0],b['rings'][1:]).buffer(0) for b in site['buildings'] if b['rings']]).buffer(.04)

def polygons(value):
    if value.is_empty:return []
    if value.geom_type=='Polygon':return [value]
    return [p for item in value.geoms for p in polygons(item)]

def triangles(value):
    result=[list(t.exterior.coords)[:3] for p in polygons(value) for t in constrained_delaunay_triangles(p).geoms if t.area>1e-10]
    assert abs(sum(Polygon(t).area for t in result)-value.area)<1e-6
    return result

def course(value,shade):
    inset=value.buffer(-.003)
    if inset.is_empty:inset=value
    bevel = [[(x,y,.047+.003*min(1,Point(x,y).distance(value.boundary)/.003)) for x,y in tri] for tri in triangles(value.difference(inset))]
    return {'top':triangles(inset),'bevel':bevel,'shade':shade}

used=Polygon();records=[]
for record in old['records']:
    street=record['street'];angle=record['angle']
    region=unary_union([Polygon(t) for t in record['base']])
    # Fill the former slivers beside narrow centreline-based surfaces.
    region=region.buffer(.80,join_style=2).difference(buildings).difference(used).buffer(0)
    used=unary_union([used,region])
    local=affinity.rotate(region,-angle,origin=(0,0));interior=local.buffer(-.19)
    xmin,ymin,xmax,ymax=local.bounds
    length,width=(.60,.30) if street=='Portsmouth Street' else (.90,.60)
    tiles=[]
    for row in range(math.floor(ymin/width),math.ceil(ymax/width)):
        shift=.5*length*(row%2)
        for col in range(math.floor((xmin-shift)/length),math.ceil((xmax-shift)/length)):
            x,y=col*length+shift,row*width
            tile=box(x+.003,y+.003,x+length-.003,y+width-.003).intersection(interior)
            if tile.area<.003:continue
            tiles.append(course(affinity.rotate(tile,angle,origin=(0,0)),(row*73856093^col*19349663)%5))
    band=region.difference(affinity.rotate(interior,angle,origin=(0,0)));borders=[]
    for poly in polygons(region):
        for ring in [poly.exterior,*poly.interiors]:
            line=ring
            for i in range(math.ceil(line.length/.60)):
                segment=substring(line,i*.60+.003,min((i+1)*.60-.003,line.length))
                stone=segment.buffer(.20,cap_style=2,join_style=2).intersection(band)
                if stone.area>.001:borders.append(course(stone,i%2))
    records.append({'street':street,'area':region.area,'base':triangles(region),'tiles':tiles,'borders':borders,'angle':angle,'rings':[list(p.exterior.coords) for p in polygons(region)]})

# The OSM archive locates objects independently of their visual interpretation.
def ecef(longitude,latitude):
    lo,la=map(math.radians,(longitude,latitude));n=6378137/math.sqrt(1-.00669437999014*math.sin(la)**2)
    return (n*math.cos(la)*math.cos(lo),n*math.cos(la)*math.sin(lo),n*(1-.00669437999014)*math.sin(la))
origin=ecef(-.1167,51.5146)
lon,lat=map(math.radians,(-.1167,51.5146))
def metric(point):
    xyz=ecef(*point);dx,dy,dz=[a-b for a,b in zip(xyz,origin)]
    return (-math.sin(lon)*dx+math.cos(lon)*dy,-math.sin(lat)*math.cos(lon)*dx-math.sin(lat)*math.sin(lon)*dy+math.cos(lat)*dz)
objects=[]
for filename in ['greenspace','street_objects']:
    for f in json.loads((ROOT/f'data/collections/streets/derived/{filename}.geojson').read_text())['features']:
        if f['geometry']['type']!='Point':continue
        p=f['properties'];kind='tree' if p.get('natural')=='tree' else 'bollard' if p.get('barrier')=='bollard' else 'cycle' if p.get('amenity')=='bicycle_parking' else None
        if not kind:continue
        xy=metric(f['geometry']['coordinates']);point=Point(xy)
        radius=.65 if kind=='tree' else .25 if kind=='bollard' else .70
        if not used.buffer(-radius).covers(point) or point.distance(Point(-48.9262,-20.3711))<3:continue
        objects.append({'kind':kind,'xy':xy,'osmId':f.get('id'),'scope':'Archived OSM position; dimensions estimated'})
# Drainage is confirmed in the completed Portsmouth scheme; these six locations are illustrative.
port=next(r for r in records if r['street']=='Portsmouth Street')
region=unary_union([Polygon(t) for t in port['base']]);local=affinity.rotate(region,-port['angle'],origin=(0,0))
lo,_,hi,_=local.bounds;gullies=[]
for i in range(6):
    x=lo+(hi-lo)*(i+1)/7
    cut=local.intersection(box(x-.32,-1000,x+.32,1000))
    if cut.is_empty:continue
    _,bottom,_,top=cut.bounds
    point=affinity.rotate(Point(x,bottom+.7),port['angle'],origin=(0,0))
    if region.buffer(-.36).covers(point):gullies.append({'xy':[point.x,point.y],'angle':port['angle']})
# Cut real openings so flush grilles do not fight the underlying paving faces.
openings = [Point(item['xy']).buffer(.70) for item in objects if item['kind']=='tree']
for item in gullies:
    x,y=item['xy'];opening=box(x-.302,y-.212,x+.302,y+.212)
    openings.append(affinity.rotate(opening,item['angle'],origin=(x,y)))
openings=unary_union(openings)
for record in records:
    for component in ['tiles','borders']:
        clipped=[]
        for tile in record[component]:
            surface=unary_union([Polygon([(p[0],p[1]) for p in tri]) for tri in tile['top']+tile['bevel']])
            cut=surface.difference(openings)
            if cut.area>.00001:clipped.append(course(cut,tile['shade']))
        record[component]=clipped
assert used.intersection(buildings).area<1e-6
payload={'records':records,'objects':objects,'gullies':gullies,'buildingOverlapArea':used.intersection(buildings).area,'limitations':['Stone courses and added surface widths estimated from existing street photographs','Mapped trees and furniture use archived OSM locations, not a current survey','Portsmouth gully locations illustrative; completion source confirms drainage works but no located plans','Existing seven bench centres retained; bench construction estimated','No future Portugal Street landscape added']}
(OUT/'street-plan.json').write_text(json.dumps(payload,separators=(',',':')))
print('STREET_PLAN',sum(len(r['tiles']) for r in records),'pavers',len(objects),'mapped objects',len(gullies),'gullies')
