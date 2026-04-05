"""
Export / Import helpers for annotations (JSON, COCO, YOLO formats).

Persists annotations as compact JSON (masks encoded as bitset_v1), exports COCO/YOLO templates,
splits Rect/Poly/Mask into subfolders. Key: export_json, import_json, export_coco_template,
export_yolo_template, save_dataset_structure, _encode/_decode_mask_points_bitset_v1.
"""
from __future__ import annotations

import base64
import json
import zlib
from pathlib import Path
from typing import Any


# -------------------------------------------------------------------- #
#  JSON
# -------------------------------------------------------------------- #
_MASK_ENCODING_BITSET_V1 = "bitset_v1"


def _encode_mask_points_bitset_v1(points: list[list[float]]) -> dict[str, Any]:
    """Encode mask points as a compact bitset payload.

    Returns metadata needed to restore legacy ``points`` on import.
    """
    if not points:
        return {
            "mask_encoding": _MASK_ENCODING_BITSET_V1,
            "mask_origin": [0, 0],
            "mask_size": [0, 0],
            "mask_data": "",
        }

    int_points = {(int(round(p[0])), int(round(p[1]))) for p in points if len(p) >= 2}
    if not int_points:
        return {
            "mask_encoding": _MASK_ENCODING_BITSET_V1,
            "mask_origin": [0, 0],
            "mask_size": [0, 0],
            "mask_data": "",
        }

    xs = [p[0] for p in int_points]
    ys = [p[1] for p in int_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) + 1
    height = (max_y - min_y) + 1

    bit_count = width * height
    raw = bytearray((bit_count + 7) // 8)
    for x, y in int_points:
        idx = (y - min_y) * width + (x - min_x)
        raw[idx // 8] |= 1 << (idx % 8)

    compressed = zlib.compress(bytes(raw), level=9)
    encoded = base64.b64encode(compressed).decode("ascii")
    return {
        "mask_encoding": _MASK_ENCODING_BITSET_V1,
        "mask_origin": [min_x, min_y],
        "mask_size": [width, height],
        "mask_data": encoded,
    }


def _decode_mask_points_bitset_v1(annotation: dict[str, Any]) -> list[list[float]]:
    """Decode compact mask payload back to legacy ``points`` format."""
    origin = annotation.get("mask_origin")
    size = annotation.get("mask_size")
    data = annotation.get("mask_data", "")

    if not isinstance(origin, list) or len(origin) != 2:
        raise ValueError("Invalid mask_origin for mask annotation")
    if not isinstance(size, list) or len(size) != 2:
        raise ValueError("Invalid mask_size for mask annotation")

    min_x, min_y = int(origin[0]), int(origin[1])
    width, height = int(size[0]), int(size[1])
    if width <= 0 or height <= 0:
        return []
    if not isinstance(data, str) or not data:
        return []

    compressed = base64.b64decode(data.encode("ascii"))
    raw = zlib.decompress(compressed)

    expected_len = ((width * height) + 7) // 8
    if len(raw) != expected_len:
        raise ValueError("Invalid mask_data length for mask annotation")

    points: list[list[float]] = []
    for idx in range(width * height):
        if raw[idx // 8] & (1 << (idx % 8)):
            x = min_x + (idx % width)
            y = min_y + (idx // width)
            points.append([float(x), float(y)])
    return points


def _prepare_annotations_for_export(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert heavy mask point payloads to compact encoded payloads."""
    prepared: list[dict[str, Any]] = []
    for ann in annotations:
        item = dict(ann)
        if item.get("type") == "mask" and isinstance(item.get("points"), list):
            encoded = _encode_mask_points_bitset_v1(item.get("points", []))
            item.pop("points", None)
            item.update(encoded)
        prepared.append(item)
    return prepared


def _prepare_annotations_for_import(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand compact mask payloads back to legacy point payloads."""
    prepared: list[dict[str, Any]] = []
    for ann in annotations:
        item = dict(ann)
        if (
            item.get("type") == "mask"
            and "points" not in item
            and item.get("mask_encoding") == _MASK_ENCODING_BITSET_V1
        ):
            item["points"] = _decode_mask_points_bitset_v1(item)
        prepared.append(item)
    return prepared


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
        "annotations": _prepare_annotations_for_export(annotations),
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
        _prepare_annotations_for_import(data.get("annotations", [])),
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
    data_yaml_path: str | Path | None,
    width: int,
    height: int,
    annotations: list[dict[str, Any]],
) -> None:
    """Write YOLO bbox labels, classes, and an optional data.yaml template."""
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

    if data_yaml_path is not None:
        data_lines = [
            "# YOLO dataset configuration template",
            "# Update train/val paths to match your dataset layout",
            "path: .",
            "train: images/train",
            "val: images/val",
            f"nc: {len(class_lines)}",
            "names:",
        ]
        if class_lines:
            for idx, name in enumerate(class_lines):
                safe_name = name.replace("\n", " ").replace(":", "-").strip() or f"class_{idx}"
                data_lines.append(f"  {idx}: {safe_name}")
        else:
            data_lines.append("  {}")
        Path(data_yaml_path).write_text("\n".join(data_lines) + "\n", encoding="utf-8")


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
        data_yaml_path = out / "data.yaml"
        export_yolo_template(labels_path, classes_path, data_yaml_path, width, height, annotations)
        return [str(labels_path), str(classes_path), str(data_yaml_path)]

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

