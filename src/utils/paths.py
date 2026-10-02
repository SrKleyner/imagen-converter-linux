"""Output path resolution with dedup-suffix strategy.

CO-3: target exists → ``_converted`` suffix.
CO-4: suffixed name also exists → ``_1``, ``_2``, ... (sequential).
BC-2: "single" mode — all outputs land in one folder.
BC-3: "mirror" mode — output tree mirrors input tree relative to common_root.
"""

from __future__ import annotations

import os


def resolve_output_path(
    input_path: str,
    target_ext: str,
    output_dir: str,
    output_mode: str = "single",
    common_root: str | None = None,
) -> str:
    """Compute the output file path, handling name conflicts.

    Parameters
    ----------
    input_path:
        Full path to the input image file.
    target_ext:
        Target extension **including** the dot (e.g. ``".webp"``).
    output_dir:
        Base output directory.
    output_mode:
        ``"single"`` → all files land directly in *output_dir*.
        ``"mirror"`` → relative directory structure preserved beneath *output_dir*.
    common_root:
        Required when *output_mode* is ``"mirror"`` — the deepest common
        ancestor of all inputs.

    Returns
    -------
    str
        A unique output path (may include ``_converted`` or ``_N`` suffix).
    """
    if output_mode == "mirror" and common_root:
        rel = os.path.relpath(input_path, common_root)
        base_dir = os.path.join(output_dir, os.path.dirname(rel))
    else:
        # "single" mode or mirror without common_root
        base_dir = output_dir

    stem, _ = os.path.splitext(os.path.basename(input_path))
    os.makedirs(base_dir, exist_ok=True)

    # First attempt: simple name change
    candidate = os.path.join(base_dir, stem + target_ext)

    # CO-3 / CO-4: conflict resolution
    if not os.path.exists(candidate):
        return candidate

    # Try _converted suffix
    candidate = os.path.join(base_dir, f"{stem}_converted{target_ext}")
    if not os.path.exists(candidate):
        return candidate

    # Sequential suffix: _1, _2, ...
    counter = 1
    while True:
        candidate = os.path.join(base_dir, f"{stem}_converted_{counter}{target_ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1
