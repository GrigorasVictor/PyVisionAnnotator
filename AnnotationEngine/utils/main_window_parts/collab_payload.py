"""Collaboration payload normalization/build helpers for MainWindow.

Robustly parses incoming backend payloads (wrapper, type aliases, multiple point formats, RLE),
builds outbound payloads (delete/create/update). Key: normalize_collab_annotation_payload,
build_collab_annotation_payload, is_empty_mask_annotation, _normalize_points_payload, _decode_mask_counts.
"""
from __future__ import annotations

import base64
import json
from typing import Any


def _decode_mask_counts(counts: object) -> list[list[float]]:
    payload_data = str(counts or "").strip()
    if not payload_data:
        return []
    try:
        decoded = base64.b64decode(payload_data.encode("ascii"), validate=True)
        parsed = json.loads(decoded.decode("utf-8"))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []

    points: list[list[float]] = []
    for pair in parsed:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            try:
                points.append([float(pair[0]), float(pair[1])])
            except Exception:
                continue
    return points


def _normalize_points_payload(raw_points: object) -> list[list[float]]:
    if not isinstance(raw_points, list):
        return []

    # Accept flattened numeric arrays: [x1, y1, x2, y2, ...]
    if raw_points and all(isinstance(v, (int, float)) for v in raw_points):
        return [[float(raw_points[i]), float(raw_points[i + 1])] for i in range(0, len(raw_points) - 1, 2)]

    out: list[list[float]] = []
    for point in raw_points:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                out.append([float(point[0]), float(point[1])])
            except Exception:
                continue
            continue
        if isinstance(point, dict):
            try:
                out.append([float(point.get("x")), float(point.get("y"))])
            except Exception:
                continue
    return out


def normalize_collab_annotation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, Any] = dict(payload)

    wrapped = normalized.get("annotation")
    if isinstance(wrapped, dict):
        merged = dict(wrapped)
        for key in ("id", "type", "label", "color", "x", "y", "w", "h", "points", "mask"):
            if key not in merged and key in normalized:
                merged[key] = normalized.get(key)
        normalized = merged

    if not normalized.get("id") and normalized.get("annotationId"):
        normalized["id"] = normalized.get("annotationId")

    if not normalized.get("label"):
        normalized["label"] = (
            normalized.get("className")
            or normalized.get("name")
            or normalized.get("category")
            or ""
        )

    if not normalized.get("color"):
        normalized["color"] = (
            normalized.get("colour")
            or normalized.get("hexColor")
            or normalized.get("strokeColor")
            or "#ff3232"
        )

    raw_type = str(normalized.get("type") or "").strip().lower()
    if raw_type in ("bbox", "rectangle", "box"):
        normalized["type"] = "rect"
    elif raw_type in ("segmentation", "seg"):
        normalized["type"] = "mask"

    bbox = normalized.get("bbox")
    if isinstance(bbox, dict):
        if "x" not in normalized and "left" in bbox:
            normalized["x"] = bbox.get("left")
        if "y" not in normalized and "top" in bbox:
            normalized["y"] = bbox.get("top")
        if "w" not in normalized and "width" in bbox:
            normalized["w"] = bbox.get("width")
        if "h" not in normalized and "height" in bbox:
            normalized["h"] = bbox.get("height")

    if str(normalized.get("type") or "") != "mask":
        return normalized

    if not normalized.get("points"):
        normalized["points"] = normalized.get("coordinates")

    mask_obj = normalized.get("mask")
    if isinstance(mask_obj, dict):
        if not normalized.get("points"):
            normalized["points"] = mask_obj.get("points")
        if not normalized.get("points") and str(mask_obj.get("format") or "").lower() == "rle":
            decoded_points = _decode_mask_counts(mask_obj.get("counts"))
            if decoded_points:
                normalized["points"] = decoded_points

    normalized_points = _normalize_points_payload(normalized.get("points"))
    if normalized_points:
        normalized["points"] = normalized_points
        if any(k not in normalized for k in ("x", "y", "w", "h")):
            xs = [p[0] for p in normalized_points]
            ys = [p[1] for p in normalized_points]
            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)
            normalized.setdefault("x", min_x)
            normalized.setdefault("y", min_y)
            normalized.setdefault("w", max(1.0, max_x - min_x))
            normalized.setdefault("h", max(1.0, max_y - min_y))

    return normalized


def is_empty_mask_annotation(payload: dict[str, Any]) -> bool:
    return str(payload.get("type") or "") == "mask" and not payload.get("points")


def build_collab_annotation_payload(manager: Any, event_type: str, ann_id: str) -> dict[str, Any] | None:
    if event_type == "annotation.delete":
        return {"id": ann_id}
    if event_type not in ("annotation.create", "annotation.update"):
        return None

    item = manager.get(ann_id)
    if item is None:
        return None

    payload = item.to_dict() if hasattr(item, "to_dict") else {}
    if not isinstance(payload, dict):
        return None

    payload["id"] = ann_id
    if payload.get("type") == "rect":
        payload["type"] = "bbox"

    if payload.get("type") == "mask":
        points = payload.get("points", [])
        if not isinstance(points, list) or len(points) == 0:
            return None
        payload.pop("mask", None)

    return payload

