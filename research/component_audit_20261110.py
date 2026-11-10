"""Synthetic-only binary-mask topology and source-protection diagnostics.

No HST image or observational detection claim. Uses 4-neighbour connectivity.
"""
from collections import deque
from math import isfinite


def components(mask):
    """Return sorted 4-connected component areas of a rectangular binary mask."""
    if not mask or not mask[0] or any(len(row) != len(mask[0]) for row in mask):
        raise ValueError("mask must be nonempty and rectangular")
    h, w = len(mask), len(mask[0])
    seen = set()
    areas = []
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or (y, x) in seen:
                continue
            q = deque([(y, x)])
            seen.add((y, x))
            area = 0
            while q:
                cy, cx = q.popleft()
                area += 1
                for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny][nx] and (ny,nx) not in seen:
                        seen.add((ny,nx))
                        q.append((ny,nx))
            areas.append(area)
    return sorted(areas, reverse=True)


def protected_mask_cost(predicted, truth, source_core, core_weight=5.0):
    """Cost = missed CR pixels + false masked background + weighted core loss.

    Each pixel belongs to one of three mutually exclusive classes:
    true cosmic ray, source core (non-CR), or other background.
    """
    if not isfinite(core_weight) or core_weight < 0:
        raise ValueError("core_weight must be finite and nonnegative")
    if not predicted or not predicted[0]:
        raise ValueError("empty mask")
    shape = (len(predicted), len(predicted[0]))
    for grid in (predicted, truth, source_core):
        if len(grid) != shape[0] or any(len(row) != shape[1] for row in grid):
            raise ValueError("mask shapes differ")
    missed = false_background = false_core = 0
    for p_row, t_row, c_row in zip(predicted, truth, source_core):
        for p, t, c in zip(p_row, t_row, c_row):
            if t and c:
                raise ValueError("source-core and cosmic-ray truth overlap")
            missed += int(bool(t) and not bool(p))
            false_core += int(bool(p) and bool(c))
            false_background += int(bool(p) and not bool(t) and not bool(c))
    return {
        "missed_cr": missed,
        "false_background": false_background,
        "false_core": false_core,
        "weighted_cost": missed + false_background + core_weight * false_core,
    }
