"""Extend the native LRB study with six source-supported public floor zones.

Open this file in Blender's Text Editor and run it. Coordinates, furniture
sizes and counts are visual estimates, not surveyed or operational layouts.
Existing geometry is retained byte-for-byte; room walls are not invented.
"""
from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage21/library'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'render').mkdir(exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v20.blend'))
collection = bpy.data.collections['LRB_PUBLIC_INTERIOR_study']
originals = list(bpy.data.objects)

def fingerprint(objects):
    digest = hashlib.sha256()
    for obj in sorted(objects, key=lambda item: item.name):
        digest.update(obj.name.encode())
        digest.update(array.array('f', [v for row in obj.matrix_world for v in row]).tobytes())
        if obj.type == 'MESH':
            vertices = array.array('f', [0]) * (len(obj.data.vertices) * 3)
            obj.data.vertices.foreach_get('co', vertices)
            digest.update(vertices.tobytes())
    return digest.hexdigest()

before = fingerprint(originals)
site = json.loads((ROOT / 'result/blender/site_geometry.json').read_text())
if isinstance(site, dict) and 'buildings' in site:
    site = site['buildings']
if isinstance(site, list):
    footprint = next(item for item in site if item['code'] == 'LRB')['rings'][0]
else:
    footprint = site['LRB']['rings'][0]
CENTER = (69.63215041268096, 13.996751978703918)
PALETTE = {'oak': (.52,.37,.20), 'frame': (.60,.62,.60), 'seat': (.12,.29,.36),
           'steel': (.13,.17,.19), 'screen': (.07,.10,.12), 'desk': (.77,.76,.67),
           'book_blue': (.14,.28,.36), 'book_red': (.40,.15,.12),
           'book_cream': (.65,.59,.43), 'book_green': (.24,.33,.23)}
materials.clear()
for key, color in PALETTE.items():
    material = bpy.data.materials.new('LRB_V21_' + key)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*color,1)
    material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
    materials[key] = material

def plan_point(point, lower_ground=False):
    # LG has a different image framing. Normalise its four outer landmarks
    # approximately to the upper-plan frame before applying the same GIS fit.
    x, y = point
    if lower_ground:
        x = 125 + (x - 34) * (1360-125)/(1410-34)
        y = 63 + (y - 53) * (1032-63)/(964-53)
    return (.0719063418*x - .0000220201874*y + 15.6175472,
            -.00119674917*x - .0704995938*y + 46.1506280)

def inside(point, polygon):
    x,y = point; result = False
    for i, (ax,ay) in enumerate(polygon):
        bx,by = polygon[i-1]
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            result = not result
    return result

def rotated(x,y,angle):
    c,s = math.cos(angle), math.sin(angle)
    return c*x-s*y, s*x+c*y

class Floor:
    def __init__(self, floor_id, index, label, scope):
        self.id, self.index, self.z = floor_id, index, .32 + 4*index
        self.label, self.scope, self.groups = label, scope, {}
        self.occupied, self.counts = [], {'stackModules':0,'readingTables':0,'chairs':0,'computers':0}
        self.zones = []
    def box(self, family, material, center, size, angle=0):
        key = family + '_' + material
        if key not in self.groups:
            group = Geometry('LRB', self.id + '_' + key, material)
            group.name = 'LRB_V21_' + self.id + '_' + key
            group.collection = collection
            self.groups[key] = group
        self.groups[key].box(center, size, angle)
    def valid(self, x,y, width, depth, angle, polygon):
        # Entire furniture envelope must stay in the diagram zone and native
        # footprint. The generous inner radius preserves atrium circulation.
        corners = [(x+dx,y+dy) for dx,dy in [rotated(sx*width/2,sy*depth/2,angle)
                    for sx in [-1,1] for sy in [-1,1]]]
        for px,py in corners:
            if not inside((px,py), polygon) or not inside((px,py), footprint): return False
            if math.hypot(px-CENTER[0],py-CENTER[1]) < 14: return False
        if abs(y-CENTER[1]) < 2.3 and CENTER[0]+8 < x < CENTER[0]+21: return False
        xmin,xmax = min(p[0] for p in corners),max(p[0] for p in corners)
        ymin,ymax = min(p[1] for p in corners),max(p[1] for p in corners)
        obstacles = list(self.occupied)
        if 1 <= self.index <= 4:
            for ox in [-16,-13,13,16]:
                for oy in [-9,-4,1,6,11]:
                    obstacles.append((CENTER[0]+ox-.9,CENTER[0]+ox+.9,
                                      CENTER[1]+oy-1.45,CENTER[1]+oy+1.45))
        if any(xmin < b and xmax > a and ymin < d and ymax > c for a,b,c,d in obstacles): return False
        self.occupied.append((xmin-.12,xmax+.12,ymin-.12,ymax+.12))
        return True
    def chair(self,x,y,angle):
        def p(dx,dy,dz):
            rx,ry=rotated(dx,dy,angle); return (x+rx,y+ry,self.z+dz)
        self.box('seating','seat',p(0,0,.46),(.46,.44,.075),angle)
        self.box('seating','seat',p(0,.20,.73),(.46,.065,.46),angle)
        for dx in [-.18,.18]:
            for dy in [-.16,.16]: self.box('chair_legs','steel',p(dx,dy,.23),(.035,.035,.43),angle)
        self.counts['chairs'] += 1
    def table(self,x,y,angle,computer=False,group=False):
        width, depth = (2.4,1.1) if group else (1.6,.75)
        self.box('reading_tables','desk',(x,y,self.z+.76),(width,depth,.06),angle)
        for dx in [-width/2+.16,width/2-.16]:
            for dy in [-depth/2+.12,depth/2-.12]:
                rx,ry=rotated(dx,dy,angle)
                self.box('table_legs','steel',(x+rx,y+ry,self.z+.37),(.045,.045,.72),angle)
        positions = [(-.65,-.91),(.65,-.91),(-.65,.91),(.65,.91)] if group else [(0,-.76)]
        for dx,dy in positions:
            rx,ry=rotated(dx,dy,angle); self.chair(x+rx,y+ry,angle+(math.pi if dy<0 else 0))
        if computer:
            self.box('computer_monitor','screen',(x,y,self.z+1.12),(.52,.06,.33),angle)
            self.box('computer_stand','steel',(x,y,self.z+.90),(.06,.08,.24),angle)
            rx,ry=rotated(0,-.2,angle)
            self.box('keyboard','screen',(x+rx,y+ry,self.z+.808),(.43,.14,.025),angle)
            self.counts['computers'] += 1
        self.counts['readingTables'] += 1
    def stack(self,x,y,angle,seed):
        def p(dx,dy,dz):
            rx,ry=rotated(dx,dy,angle); return (x+rx,y+ry,self.z+dz)
        for dx in [-1.45,1.45]: self.box('stack_ends','frame',p(dx,0,1.03),(.07,.66,2.06),angle)
        self.box('stack_back','frame',p(0,0,1.04),(2.83,.035,2.04),angle)
        for level in range(5):
            height=.16+level*.38
            self.box('stack_shelves','frame',p(0,0,height),(2.87,.66,.04),angle)
            for side in [-1,1]:
                for i in range(12):
                    material = ['book_blue','book_red','book_cream','book_green'][(i+seed+level)%4]
                    book_height=.24+.018*((i+level)%4)
                    self.box('books',material,p(-1.30+i*.225,side*.185,height+.02+book_height/2),(.18,.26,book_height),angle)
        self.counts['stackModules'] += 1
    def zone(self,label,pixels,kind,angle_degrees=-39,lg=False):
        polygon=[plan_point(p,lg) for p in pixels]
        angle=math.radians(angle_degrees)
        local=[rotated(x,y,-angle) for x,y in polygon]
        if kind=='stacks': width,depth,stepx,stepy=3.05,.82,4.25,2.55
        elif kind=='group': width,depth,stepx,stepy=2.9,2.9,4.05,4.05
        else: width,depth,stepx,stepy=1.95,2.0,2.65,3.15
        start=dict(self.counts); yi=min(y for x,y in local)+depth/2+.2; seed=0
        while yi < max(y for x,y in local):
            xi=min(x for x,y in local)+width/2+.2
            while xi < max(x for x,y in local):
                x,y=rotated(xi,yi,angle)
                if self.valid(x,y,width,depth,angle,polygon):
                    if kind=='stacks': self.stack(x,y,angle,seed)
                    else: self.table(x,y,angle,kind=='computers',kind=='group')
                    seed+=1
                xi+=stepx
            yi+=stepy
        self.zones.append({'label':label,'kind':kind,'planPolygonPixels':pixels,'worldPolygon':polygon,
                           'addedCounts':{k:self.counts[k]-start[k] for k in start}})
    def finish(self):
        for geometry in self.groups.values():
            obj=geometry.finish()
            obj['floorId']=self.id
            obj['scope']='Official floor-guide functional zones; estimated furniture, not measured room geometry'
            obj['source']='data/documents/library_floor_plans.pdf, page '+str(self.index+2)
            # Thousands of book edges do not need export-time subdivision.
            for modifier in list(obj.modifiers): obj.modifiers.remove(modifier)
        return [{'name':g.name,'collection':collection.name} for g in self.groups.values()]

floors=[]
f=Floor('LG',0,'LG层：电脑与政府出版物','官方LG导览图支持电脑、分组学习与政府出版物区域；家具为估算。沿用既有最低层，地下绝对高程尚未校准。');floors.append(f)
f.zone('PC与Mac学习区',[(605,497),(794,637),(680,783),(493,621)],'computers',-39,True)
f.zone('政府出版物与历史统计',[(1010,500),(1230,616),(1010,839),(850,705)],'stacks',-39,True)
f.zone('分组学习',[(335,459),(488,327),(704,482),(610,583)],'group',-39,True)
f=Floor('G',1,'G层：LSE LIFE学习区','依据官方G层导览图补充LSE LIFE开放学习工作区；未重建服务柜台与封闭房间，保留原有估算家具。');floors.append(f)
for number,polygon in enumerate([[(935,162),(1150,280),(1050,432),(890,323)],[(1150,280),(1270,357),(1160,560),(1050,432)],[(1020,500),(1150,612),(1000,770),(903,641)],[(898,684),(1000,770),(866,1008),(747,906)]],1):
    f.zone('LSE LIFE Workspace '+str(number),polygon,'group',-39)
SW=[(420,390),(758,658),(655,802),(310,503)]
SE=[(990,480),(1115,569),(893,844),(776,750)]
NW=[(561,276),(818,154),(874,291),(619,405)]
READ_SW=[(177,416),(280,343),(651,822),(613,846),(204,493)]
READ_SE=[(1180,595),(1213,621),(880,993),(759,905),(780,866),(878,937)]
for index,identifier,label,swlabel,selabel in [(2,'1','1层：主要藏书与课程藏书','主要藏书JX–ZZ','课程藏书A–Z'),(3,'2','2层：经济类藏书与期刊','主要藏书HF–JV','主要藏书HB–HF'),(4,'3','3层：社会科学藏书与期刊','主要藏书F–HA及期刊A–HT','主要藏书A–F')]:
    f=Floor(identifier,index,label,'官方导览图支持藏书、期刊与阅览区域；新增可浏览书架和座席，数量与尺寸估算，未构造无依据的封闭房间。');floors.append(f)
    f.zone(swlabel,SW,'stacks')
    f.zone(selabel,SE,'stacks')
    f.zone('临John Watkins Plaza安静阅览',READ_SW,'reading')
    f.zone('临Grange Court安静阅览',READ_SE,'reading',49)
    if identifier=='1':
        f.zone('分组学习桌区',[(525,230),(850,86),(894,169),(867,309),(658,395)],'group',25)
        f.zone('研究生安静阅览',[(976,334),(1115,254),(1197,355),(1095,482)],'reading',-39)
    else:
        f.zone('期刊与统计资料' if identifier=='2' else '期刊HT–JZ及专题馆藏',NW,'stacks',25)
        f.zone('临Portugal Street安静阅览',[(540,234),(826,95),(862,147),(575,282)],'reading',25)
        f.zone('东北安静阅览',[(960,217),(1108,301),(1136,363),(1061,387),(955,300)],'reading',-39)
f=Floor('4',5,'4层：专题阅览与分组学习','依据官方4层图补充本科生、研究生、Women’s Library阅览与分组学习区域；不推断PhD Academy、保密资料室或5层员工空间。');floors.append(f)
f.zone('本科生安静阅览',[(538,226),(760,119),(804,249),(751,290),(591,342)],'reading',25)
f.zone('Women’s Library阅览',[(796,102),(887,100),(1094,256),(1027,349),(900,273),(810,267)],'reading',-39)
f.zone('研究生安静阅览',[(600,548),(753,677),(654,839),(476,696)],'reading',-39)
f.zone('分组学习',[(889,651),(1031,751),(911,911),(763,858)],'group',-39)
added=[]
for floor in floors: added.extend(floor.finish())
assert before==fingerprint(originals), 'An original object was changed'
assert all(f.counts['readingTables']+f.counts['stackModules']>0 for f in floors)
sections=[{'id':f.id,'label':f.label,'minHeight':round(f.z-.34,2),'maxHeight':22.90 if f.id=='4' else round(f.z+3.60,2),
           'camera':[112,-45,f.z+54],'target':[72,6,f.z+.55],'scope':f.scope} for f in floors]
manifest={'stage':21,'baseline':'result/blender/LSE_campus_detailed_v20.blend',
 'output':'result/blender/stage21/library/refined.blend',
 'buildings':[{'code':'LRB','status':'six-public-floor-zone-extension','changes':['保留既有中庭、螺旋坡道、地板与所有家具','按LG、G、1、2、3、4六层官方功能分区扩展书架与阅览空间'],
 'sources':[{'path':'data/documents/library_floor_plans.pdf','pages':[2,3,4,5,6,7]}, {'path':'result/blender/site_geometry.json'}, {'path':'code/blender/agents/atria/build_atria.py'}],
 'limitations':['层高沿用原模型每层4米，非测绘高程；LG位于Z0.32，地下绝对高程未校准','官方图四角拟合残差约0.6–1.1米；图中中庭中心与原模型相差约5.3米，保留原中庭，仅估算外围功能区','家具形态、尺寸、数量和通道宽度为展示估算；不等于当前实景或疏散依据','保留原模型通用书架，因此局部现有家具可能不对应导览图功能；新增家具已避让','未重建教学室、办公室、厕所、封闭小房间或5层员工空间'],
 'addedObjects':added,'interiorSections':sections,
 'interiorSectionScope':'LG、G、1、2、3、4共6个公共楼层依照官方导览图分配功能区，沿用原模型相对层级估算；LG地下绝对高程尚未校准，中庭与平面位置存在偏差，外围区域定位及家具尺寸、数量均为估算，非完整实测布局。',
 'floors':[{'id':f.id,'floorZ':f.z,'zRange':[round(f.z-.32,2),round(f.z+3.60,2)],'counts':f.counts,'zones':f.zones} for f in floors]}],
 'qa':{'originalObjectCount':len(originals),'originalFingerprintBefore':before,'originalFingerprintAfter':fingerprint(originals),
       'newMeshObjects':len(added),'placementChecks':'Every furniture envelope inside its functional-zone polygon and GIS footprint; native atrium radius14m excluded; existing shelf envelopes excluded on G/1/2/3; east landing corridor reserved'}}
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'refined.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('LIBRARY_MANIFEST', [(f.id,f.counts) for f in floors], flush=True)

# Render temporary per-floor cutaways without changing the saved native study.
# Batched original meshes span six levels; select only faces inside each Z band.
scene=bpy.data.scenes.new('LRB_V21_QA_only')
bpy.context.window.scene=scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.studiolight_rotate_z=.35
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('LRB_V21_QA_world')
scene.world.color=(.82,.84,.86)
scene.render.resolution_x=1500;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard'
camera=bpy.data.objects.new('LRB_V21_QA_camera',bpy.data.cameras.new('LRB_V21_QA_camera'))
scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=100
source_objects=[obj for obj in collection.all_objects if obj.type=='MESH']
for floor,section in zip(floors,sections):
    temporary=[]
    low,high=section['minHeight'],section['maxHeight']
    for original in source_objects:
        coordinates=[original.matrix_world@v.co for v in original.data.vertices]
        faces=[];material_indices=[]
        for polygon in original.data.polygons:
            if all(low-.001 <= coordinates[i].z <= high+.001 for i in polygon.vertices):
                faces.append(tuple(polygon.vertices));material_indices.append(polygon.material_index)
        if not faces: continue
        mesh=bpy.data.meshes.new('QA_cutaway');mesh.from_pydata(coordinates,[],faces)
        for material in original.data.materials: mesh.materials.append(material)
        for polygon,index in zip(mesh.polygons,material_indices):polygon.material_index=index
        obj=bpy.data.objects.new('QA_cutaway',mesh);scene.collection.objects.link(obj);temporary.append(obj)
    camera.location=(112,-45,floor.z+70)
    camera.rotation_euler=(Vector((72,6,floor.z))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'render'/('LRB_'+floor.id+'.png'))
    bpy.ops.render.render(write_still=True)
    for obj in temporary:
        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
manifest['qa']['renderPaths']=['result/blender/stage21/library/render/LRB_'+f.id+'.png' for f in floors]
manifest['qa']['renderedFloorCount']=len(floors)
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('LIBRARY_BUILD_DONE',flush=True)
