"""Bound sub-centimetre bevel tessellation in temporary browser derivatives.

These named batches were profiled and inspected at production camera distances.
Every authored brick, hole, frame and width remains. Native data and modifier
settings on disk are never changed; the caller restores temporary settings.
"""
OLD_EDGE_BATCHES = frozenset({
    'OLD194_STONE_OLD_V112_retained_Secondary_stone_facades',
    'OLD_V112_retained_D5_windows85_retained_Window_sash_bars',
    'OLD_V112_retained_Window_sash_frames',
    'OLD194_STONE_OLD_V112_retained_Window_stone_reveals',
    'OLD194_STONE_OLD_V112_retained_Window_stone_lintels',
    'OLD194_STONE_OLD_V112_retained_Window_stone_sills',
})
SAW_BRICK_BATCHES = frozenset(f'SAW_NEXT_SCREEN_flush_{index}' for index in range(9))


def budget_web_bevels(objects):
    """Apply a checked one-segment chamfer only to the reviewed edge batches."""
    states = []
    for obj in objects:
        if obj.hide_render:
            continue
        width = .018 if obj.name in OLD_EDGE_BATCHES else .003 if obj.name in SAW_BRICK_BATCHES else None
        if width is None:
            continue
        bevels = [m for m in obj.modifiers if m.type == 'BEVEL']
        assert len(bevels) == 1, 'Reviewed bevel identity changed: ' + obj.name
        bevel = bevels[0]
        assert bevel.segments == 2 and abs(bevel.width - width) < 1e-7, obj.name
        states.append((bevel, bevel.segments))
        bevel.segments = 1
    assert {m.id_data.name for m, _ in states} == OLD_EDGE_BATCHES | SAW_BRICK_BATCHES
    return states


def restore_web_bevels(states):
    for modifier, segments in states:
        modifier.segments = segments
