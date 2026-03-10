"""
utils/io_handler.py — Export / Import helpers

Functions for persisting annotations as JSON and CSV files.

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

CSV columns::

    filename, id, x, y, w, h
"""
from __future__ import annotations

import csv
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


# -------------------------------------------------------------------- #
#  CSV
# -------------------------------------------------------------------- #
def export_csv(
    save_path: str | Path,
    image_filename: str,
    annotations: list[dict[str, Any]],
) -> None:
    """Write annotations to a CSV file.

    Columns: ``filename, id, type, label, color, x, y, w, h, points``

    Args:
        save_path:      Destination CSV path.
        image_filename: Image file name repeated on every row.
        annotations:    List of dicts.
    """
    path = Path(save_path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["filename", "id", "type", "label", "color", "x", "y", "w", "h", "points"])
        for a in annotations:
            points_str = json.dumps(a.get("points", [])) if "points" in a else ""
            writer.writerow([
                image_filename,
                a.get("id", ""),
                a.get("type", "rect"),
                a.get("label", ""),
                a.get("color", "#ff3232"),
                a["x"],
                a["y"],
                a["w"],
                a["h"],
                points_str,
            ])


def import_csv(load_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Read annotations from a CSV file, grouped by filename.

    Returns:
        ``{filename: [{"id", "type", "x", "y", "w", "h", "points"}, ...]}``
    """
    path = Path(load_path)
    result: dict[str, list[dict[str, Any]]] = {}
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            fname = row["filename"]
            points_str = row.get("points", "")
            points = json.loads(points_str) if points_str else []

            entry = {
                "id": row.get("id", ""),
                "type": row.get("type", "rect"),
                "label": row.get("label", ""),
                "color": row.get("color", "#ff3232"),
                "x": float(row["x"]),
                "y": float(row["y"]),
                "w": float(row["w"]),
                "h": float(row["h"]),
                "points": points,
            }
            result.setdefault(fname, []).append(entry)
    return result


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
        format: "json" or "csv".

    Returns:
        List of saved file paths.
    """
    rects = [a for a in annotations if a.get("type", "rect") == "rect"]
    polys = [a for a in annotations if a.get("type") == "poly"]
    masks = [a for a in annotations if a.get("type") == "mask"]

    saved_files = []
    base_name = Path(image_full_path).stem  # e.g. "photo" (no extension)


    filename_for_save = base_name + "." + format

    out = Path(output_dir)

    # 1. Handle Rectangles
    if rects:
        folder = out / "rectangle"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        if format == "json":
            export_json(save_path, image_full_path, width, height, rects)
        else:
            export_csv(save_path, image_full_path, rects)
        saved_files.append(str(save_path))

    # 2. Handle Polygons
    if polys:
        folder = out / "poly"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        if format == "json":
            export_json(save_path, image_full_path, width, height, polys)
        else:
            export_csv(save_path, image_full_path, polys)
        saved_files.append(str(save_path))

    # 3. Handle Masks (AutoSeg)
    if masks:
        folder = out / "mask"
        folder.mkdir(parents=True, exist_ok=True)
        save_path = folder / filename_for_save

        if format == "json":
            export_json(save_path, image_full_path, width, height, masks)
        else:
            export_csv(save_path, image_full_path, masks)
        saved_files.append(str(save_path))

    return saved_files

