"""Read-only177 review: existing plaza surface supported, drains unregistered.

The2008 photograph shows a local pale sloped boundary besideLAK. The2021
strategy describes a low wall but neither source supplies a reliable complete
boundary or drain registration. Do not infer hidden drainage or whole terraces.
No new mesh, material, collection, file, visibility or property is created.
"""
import bpy

SOURCE_URL='https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf'
PHOTO_URL='https://www.geograph.org.uk/photo/668683'
REQUIRED=('SITE_V47_John_Watkins_Plaza','SITE174_John_Watkins_Plaza_picnic_seating','LRB_NEXT_PLAZA155_steel')


def apply_library_environment177():
    assert all(bpy.data.objects.get(name) for name in REQUIRED),'Expected retained176 plaza surface, pavilion and seating missing'
    return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[],
            'reviewOnly':True,'reviewScope':'John Watkins Plaza andLRB entrance external ground; no verified new geometry from available records',
            'sourceURL':SOURCE_URL,'photoURL':PHOTO_URL,
            'referenceDates':['2008-01-23Geograph photograph','2021-08-31strategy photograph within2022publication'],
            'unresolved':['Precise visibleLAK-side sloped low-boundary endpoint and cross-section; historical persistence not confirmed',
                          'Library entrance ground drain/utility opening positions not identified in supplied photos or official plan',
                          'No complete terrace outline or surveyed level change supported'],
            'retainedObjects':list(REQUIRED),
            'cameraSuggestions':{'overall':{'position':[19,3.1,-14],'target':[46,1.2,10],'fov':64},
                                 'entranceGround':{'position':[39,2.2,4],'target':[56,0.6,17],'fov':54}},
            'cameraCoordinates':'Three local metres(x east,y up,z south); suggestions require production-render framing acceptance'}
