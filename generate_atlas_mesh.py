import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import zoom
from skimage.measure import marching_cubes

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "static/models/atlas.nii"
OUTPUT = ROOT / "static/models/atlas_mesh.js"


def build_affine_for_downsampled(img, target_shape):
    orig_shape = np.array(img.shape[:3], dtype=float)
    target_shape = np.array(target_shape, dtype=float)
    scale = orig_shape / target_shape
    new_aff = img.affine.copy()
    new_aff[:3, :3] = img.affine[:3, :3] @ np.diag(scale)
    return new_aff


def surface_from_mask(mask, affine):
    verts, faces, _, _ = marching_cubes(mask.astype(np.float32), level=0.5)
    if len(verts) == 0 or len(faces) == 0:
        return {"vertices": [], "faces": []}

    world = np.hstack([verts, np.ones((len(verts), 1), dtype=float)]) @ affine.T
    vertices = world[:, :3].astype(float).ravel().tolist()
    faces = faces.astype(int).ravel().tolist()
    return {"vertices": vertices, "faces": faces}


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Atlas file not found: {INPUT}")

    img = nib.load(str(INPUT))
    mask = img.get_fdata() > 0.5

    factor = 0.2
    target_shape = tuple(max(1, int(s * factor)) for s in mask.shape)
    resampled = zoom(mask.astype(np.float32), [a / b for a, b in zip(target_shape, mask.shape)], order=1)
    affine = build_affine_for_downsampled(img, target_shape)

    brain_surface = surface_from_mask(resampled, affine)
    mesh = {
        "name": "atlas_nii_surface",
        "left": brain_surface,
        "right": brain_surface,
    }

    if not mesh["left"]["vertices"] or not mesh["right"]["vertices"]:
        raise RuntimeError("Generated mesh is empty; atlas may be too sparse or not a binary mask.")

    js = (
        "window.ATLAS_MESH = "
        + json.dumps(mesh, separators=(",", ":"), ensure_ascii=False)
        + ";\n"
    )
    OUTPUT.write_text(js, encoding="utf-8")
    print(f"Wrote atlas mesh: {OUTPUT}")
    print(f"Left vertices={len(mesh['left']['vertices']) // 3}, faces={len(mesh['left']['faces']) // 3}")
    print(f"Right vertices={len(mesh['right']['vertices']) // 3}, faces={len(mesh['right']['faces']) // 3}")


if __name__ == "__main__":
    main()
