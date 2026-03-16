"""
utils/io_handler.py — Export / Import helpers

Functions for persisting annotations as JSON and exporting template formats
such as COCO and YOLO.

JSON schema::

    {
      "filename": "photo.jpg",
      "width": 1920,
      "height": 1080,
      "annotations": [
        {"id": "a1b2c3d4", "x": 10.0, "y": 20.0, "w": 100.0, "h": 50.0},
        ...
      ]
    }

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# -------------------------------------------------------------------- #
#  JSON
# -------------------------------------------------------------------- #
def export_json(
    save_path: str | Path,
    image_filename: str,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
) -> None:
    """Write annotations to a JSON file.

    Args:
        save_path:      Destination file path (will be overwritten).
        image_filename: Original image file name (e.g. ``"photo.jpg"``).
        width:          Image width in pixels.
        height:         Image height in pixels.
        annotations:    List of dicts with keys ``id, x, y, w, h``, optional ``points``.
    """
    payload: dict[str, Any] = {
        "filename": image_filename,
        "width": width,
        "height": height,
        "annotations": annotations, # Pass dicts directly as they are now prepared by to_dict()
    }
    path = Path(save_path)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def import_json(load_path: str | Path) -> tuple[str, int, int, list[dict[str, Any]]]:
    """Read annotations from a JSON file.

    Returns:
        ``(filename, width, height, annotations_list)``
    """
    path = Path(load_path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return (
        data["filename"],
        int(data["width"]),
        int(data["height"]),
        data.get("annotations", []),
    )


def _normalise_label(label: str) -> str:
    text = (label or "").strip()
    return text if text else "object"


def _build_categories(annotations: list[dict[str, Any]]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    labels = sorted({_normalise_label(a.get("label", "")) for a in annotations})
    cat_to_id = {name: idx + 1 for idx, name in enumerate(labels)}
    categories = [{"id": cid, "name": name, "supercategory": "object"} for name, cid in cat_to_id.items()]
    return cat_to_id, categories


def export_coco_template(
    save_path: str | Path,
    image_full_path: str,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
) -> None:
    """Write a minimal single-image COCO annotation template."""
    cat_to_id, categories = _build_categories(annotations)
    coco_annotations: list[dict[str, Any]] = []

    for idx, a in enumerate(annotations, start=1):
        x = float(a.get("x", 0.0))
        y = float(a.get("y", 0.0))
        w = max(0.0, float(a.get("w", 0.0)))
        h = max(0.0, float(a.get("h", 0.0)))

        item: dict[str, Any] = {
            "id": idx,
            "image_id": 1,
            "category_id": cat_to_id[_normalise_label(a.get("label", ""))],
            "bbox": [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
            "area": round(w * h, 2),
            "iscrowd": 0,
        }

        points = a.get("points")
        if isinstance(points, list) and points:
            flat: list[float] = []
            for p in points:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    flat.extend([float(p[0]), float(p[1])])
            if len(flat) >= 6:
                item["segmentation"] = [[round(v, 2) for v in flat]]

        coco_annotations.append(item)

    payload = {
        "images": [{
            "id": 1,
            "file_name": Path(image_full_path).name,
            "width": int(width),
            "height": int(height),
        }],
        "annotations": coco_annotations,
        "categories": categories,
    }
    Path(save_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_yolo_template(
    labels_path: str | Path,
    classes_path: str | Path,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
) -> None:
    """Write YOLO bbox labels and a classes template file."""
    w_img = max(1.0, float(width))
    h_img = max(1.0, float(height))
    cat_to_id, categories = _build_categories(annotations)

    lines: list[str] = []
    for a in annotations:
        x = float(a.get("x", 0.0))
        y = float(a.get("y", 0.0))
        w = max(0.0, float(a.get("w", 0.0)))
        h = max(0.0, float(a.get("h", 0.0)))

        x_center = (x + w / 2.0) / w_img
        y_center = (y + h / 2.0) / h_img
        w_norm = w / w_img
        h_norm = h / h_img
        cls = cat_to_id[_normalise_label(a.get("label", ""))] - 1
        lines.append(f"{cls} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

    Path(labels_path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    class_lines = [c["name"] for c in sorted(categories, key=lambda e: e["id"])]
    Path(classes_path).write_text("\n".join(class_lines) + ("\n" if class_lines else ""), encoding="utf-8")


def export_template_structure(
    output_dir: str | Path,
    image_full_path: str,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
    template: str,
) -> list[str]:
    """Export annotations to a template format (currently COCO and YOLO)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base_name = Path(image_full_path).stem
    key = template.strip().lower()

    if key == "coco":
        path = out / f"{base_name}.coco.json"
        export_coco_template(path, image_full_path, width, height, annotations)
        return [str(path)]

    if key == "yolo":
        labels_path = out / f"{base_name}.txt"
        classes_path = out / "classes.txt"
        export_yolo_template(labels_path, classes_path, width, height, annotations)
        return [str(labels_path), str(classes_path)]

    raise ValueError(f"Unsupported export template: {template}")


def save_dataset_structure(
    output_dir: str | Path,
    image_full_path: str,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
    format: str = "json",
) -> list[str]:
    """Smart export: splits Rect vs Poly and creates subfolders.

    Args:
        output_dir: Root folder to save into (e.g. current image's folder).
        image_full_path: Full absolute path to the image file.
        width: Image width.
        height: Image height.
        annotations: List of annotation dicts.
        format: only "json" is supported.

    Returns:
        List of saved file paths.
    """
    rects = [a for a in annotations if a.get("type", "rect") == "rect"]
    polys = [a for a in annotations if a.get("type") == "poly"]
    masks = [a for a in annotations if a.get("type") == "mask"]

    saved_files = []
    base_name = Path(image_full_path).stem  # e.g. "photo" (no extension)


    if format != "json":
        raise ValueError("save_dataset_structure supports only JSON exports")

    filename_for_save = base_name + ".json"

    out = Path(output_dir)

    # 1. Handle Rectangles
    if rects:
        folder = out / "rectangle"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        export_json(save_path, image_full_path, width, height, rects)
        saved_files.append(str(save_path))

    # 2. Handle Polygons
    if polys:
        folder = out / "poly"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        export_json(save_path, image_full_path, width, height, polys)
        saved_files.append(str(save_path))

    # 3. Handle Masks (AutoSeg)
    if masks:
        folder = out / "mask"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        export_json(save_path, image_full_path, width, height, masks)
        saved_files.append(str(save_path))

    return saved_files

