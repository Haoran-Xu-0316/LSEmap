"""Quiet, source-linked stone palettes for two already modelled paved spaces.

Call in the loaded native scene. Existing setts/slabs and grain dimensions remain
unchanged. Author colour is linear RGB; both native ramp endpoints and browser
surface descriptors therefore receive the same corrected palette. Reference
photographs guide appearance, not measured reflectance or2026 site condition.
"""
import bpy

TARGETS={'Houghton':'SITE167_Houghton_paving_with_cover_openings','Watkins':'SITE_V47_John_Watkins_Plaza'}
PALETTES={'Houghton':{'slab':(.18,.195,.188),'edge':(.245,.245,.222),'grout':(.073,.079,.075)},
          'Watkins':{'slab':(.245,.253,.238),'edge':(.263,.256,.233),'grout':(.105,.110,.103)}}


def _role(material):
    for role in ('grout','slab','edge'):
        if material.name.startswith('SITE_V47_'+role):return role
    raise AssertionError('Unexpected surface material '+material.name)


def apply_street_surface172():
    objects={label:bpy.data.objects[name] for label,name in TARGETS.items()}
    if all(obj.get('surfacePalette172')==label for label,obj in objects.items()):
        assert all(mat.get('surfacePalette172')==label for label,obj in objects.items() for mat in obj.data.materials)
        return {'alreadyApplied':True,'addedObjects':[],'archivedObjects':[],'changedObjects':[],'changedMaterials':[]}
    assert all(not obj.get('surfacePalette172') for obj in objects.values()), 'Partial palette application'
    changed=[];preserved=[];detail=[]
    for label,obj in objects.items():
        originals=list(obj.data.materials)
        for index,original in enumerate(originals):
            role=_role(original)
            factor=1
            if role=='slab':factor=.95+.025*int(original.name.rsplit('_',1)[1])
            elif role=='edge':factor=.98+.02*int(original.name.rsplit('_',1)[1])
            colour=tuple(c*factor for c in PALETTES[label][role])
            material=original.copy();material.name=f'SITE172_{original.name}_{label}'
            material.diffuse_color=(*colour,1)
            shader=material.node_tree.nodes['Principled BSDF']
            shader.inputs['Base Color'].default_value=(*colour,1)
            for node in material.node_tree.nodes:
                if node.type=='VALTORGB':
                    node.color_ramp.elements[0].color=(*(c*.96 for c in colour),1)
                    node.color_ramp.elements[-1].color=(*(c*1.025 for c in colour),1)
            material['surfacePalette172']=label
            material['sourceMaterial']=original.name
            material['scope']='Photo-estimated paving colour; geometry and procedural grain scale retained'
            obj.data.materials[index]=material
            changed.append(material.name);preserved.append(original.name)
            detail.append({'object':obj.name,'slot':index,'role':role,'source':original.name,'owned':material.name,'linearColor':list(colour)})
        obj['surfacePalette172']=label
    return {'alreadyApplied':False,'addedObjects':[],'archivedObjects':[],
            'changedObjects':list(TARGETS.values()),'changedMaterials':changed,'preservedSourceMaterials':sorted(set(preserved)),
            'materialBindings':detail,
            'references':['data/collections/public-realm-2026/user-references/reference-09.png','data/collections/streets/derived/review_public_realm_pdf_page14.png'],
            'limitations':['Photos have different illumination; palette values are visual estimates, not measured stone reflectance.',
                           'Houghton paver dimensions0.30×0.15m and John Watkins courses are retained estimates.',
                           'Official public-realm site photographs date2021; no current2026 renovation claim.']}
