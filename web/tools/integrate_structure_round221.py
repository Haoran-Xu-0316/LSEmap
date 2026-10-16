"""Integrate the verified library connections and SAL entrance from accepted220.

The SAW feasibility candidate remains rejected. Original meshes and materials
are retained; only ten explicit library replacements change visibility.
"""
from pathlib import Path
import hashlib
import json
import sys
import bpy
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from integrate_exterior_round194 import integrate, update_scene, verify_saved_model

def use_current_library_in_native_views():
    """Select one library generation per view without destroying its archive.

    Excluding the old collection in these two view layers keeps its intact
    archival objects and collection ownership while preventing double geometry.
    The dedicated source review remains available in its original scene.
    """
    current = bpy.data.collections['LRB_PUBLIC_INTERIOR168_study']
    old_name = 'LRB_PUBLIC_INTERIOR_study'
    # Keep a dedicated evaluable source scene. Excluding every owning view
    # would leave parented source matrices unevaluated after a file reopen.
    archive_name = 'ARCHIVE_LRB_PUBLIC_PRE221'
    archive = bpy.data.scenes.get(archive_name) or bpy.data.scenes.new(archive_name)
    if old_name not in archive.collection.children:
        archive.collection.children.link(bpy.data.collections[old_name])
    routing = []
    def matching_layers(layer):
        found = [layer] if layer.name == old_name else []
        for child in layer.children:
            found += matching_layers(child)
        return found
    for name in ['00_CAMPUS_COMPLETE', '04_LRB_DETAIL_REVIEW']:
        scene = bpy.data.scenes[name]
        if current.name not in scene.collection.children:
            scene.collection.children.link(current)
        for layer in scene.view_layers:
            old_layers = matching_layers(layer.layer_collection)
            assert len(old_layers) == 1, (name, layer.name, len(old_layers))
            old_layers[0].exclude = True
            layer.update()
            assert all(not o.visible_get(view_layer=layer) for o in bpy.data.collections[old_name].all_objects)
            assert all(o.visible_get(view_layer=layer) for o in current.all_objects if not o.hide_render)
            routing.append(dict(scene=name, viewLayer=layer.name, excludedArchive=old_name,
                                publicCollection=current.name, visibleCurrentObjects=sum(not o.hide_render for o in current.all_objects)))
    update_scene()
    destination = ROOT / 'result/blender/LSE_campus_detailed_v221.blend'
    proof = ROOT / 'result/blender/stage221'
    record = json.loads((proof / 'building-refinement.json').read_text())
    intermediate_sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    record['librarySourceArchiveScene'] = archive_name
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    record['sourceModelSha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
    record['libraryNativeViewRouting'] = routing
    (proof / 'building-refinement.json').write_text(json.dumps(record, indent=2) + '\n')
    verify_saved_model(destination=destination, proof=proof)
    backup = destination.with_suffix('.blend1')
    if backup.exists():
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == intermediate_sha
        backup.unlink()
    print('LIBRARY221_NATIVE_CURRENT_VIEWS', routing, flush=True)


if __name__ == '__main__':
    integrate(
        base=ROOT / 'result/blender/LSE_campus_detailed_v220.blend',
        destination=ROOT / 'result/blender/LSE_campus_detailed_v221.blend',
        proof=ROOT / 'result/blender/stage221', version=221,
        baseline_proof=ROOT / 'result/blender/stage220',
        reports=[
            ('LRB', 'result/blender/lrb-structure221/audit.json', 'LRB_PUBLIC_INTERIOR168_study'),
            ('SAL', 'result/blender/sal-structure221/audit.json', 'SAL_EXTERIOR'),
        ],
        scope='Coordinate six estimated library ramp/gallery joins and their finish/supports, and add photo-supported SAL public-entry pavilion structure, reception and gates. Preserve all prior source objects, material nodes, room assets, street geometry and exterior glazing. SAW stair feasibility is not accepted construction.',
    )
    use_current_library_in_native_views()
