import argparse
import sys
import os
import json
import torch
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
import logging

# Suppress warnings
logging.getLogger("transformers").setLevel(logging.ERROR)

def get_args():
    parser = argparse.ArgumentParser(description="Mask2Former Point Query")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--point", help="Point of interest x,y (e.g. 100,200)")
    parser.add_argument("--all", action="store_true", help="Return all predicted segments")
    parser.add_argument("--model", default="facebook/mask2former-swin-large-coco-panoptic", help="HuggingFace model ID")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", help="Device to use (cuda/cpu)")
    return parser.parse_args()

def main():
    args = get_args()

    # Parse point
    px = py = None
    if not args.all:
        if not args.point:
            print(json.dumps({"error": "Missing --point. Use --point x,y or --all."}))
            sys.exit(1)
        try:
            if ',' in args.point:
                px, py = map(int, args.point.split(','))
            else:
                px, py = map(int, args.point.split())
        except ValueError:
            print(json.dumps({"error": "Invalid point format. Use x,y"}))
            sys.exit(1)

    if not os.path.exists(args.image):
        print(json.dumps({"error": f"Image not found: {args.image}"}))
        sys.exit(1)

    # Load resources
    try:
        processor = AutoImageProcessor.from_pretrained(args.model)
        model = Mask2FormerForUniversalSegmentation.from_pretrained(args.model)
        model.to(args.device)
    except Exception as e:
        print(json.dumps({"error": f"Failed to load model: {str(e)}"}))
        sys.exit(1)

    # Load and process image
    try:
        image = Image.open(args.image).convert("RGB")
        width, height = image.size

        # Check point bounds
        if not args.all and not (0 <= px < width and 0 <= py < height):
             print(json.dumps({"error": f"Point {px},{py} out of bounds ({width}x{height})"}))
             sys.exit(1)

        inputs = processor(images=image, return_tensors="pt")
        inputs = {k: v.to(args.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        result = processor.post_process_panoptic_segmentation(
            outputs,
            target_sizes=[image.size[::-1]],
            label_ids_to_fuse=[]
        )[0]
    except Exception as e:
        print(json.dumps({"error": f"Processing failed: {str(e)}"}))
        sys.exit(1)

    predicted_panoptic_map = result["segmentation"].cpu().numpy()
    segments_info = result["segments_info"]
    id2label = model.config.id2label

    if args.all:
        detections = []
        for segment in segments_info:
            segment_id = segment["id"]
            if segment_id == 0:
                continue

            y_coords, x_coords = np.where(predicted_panoptic_map == segment_id)
            if len(x_coords) == 0:
                continue

            label_id = segment.get("label_id")
            label_name = id2label.get(label_id, f"unknown_{label_id}")
            pixels = np.column_stack((x_coords, y_coords)).tolist()

            detections.append({
                "label": label_name,
                "id": int(segment_id),
                "coordinates": pixels,
                "bbox": [
                    int(np.min(x_coords)),
                    int(np.min(y_coords)),
                    int(np.max(x_coords)),
                    int(np.max(y_coords)),
                ],
            })

        print(json.dumps(detections))
        return

    # Query point
    segment_id = predicted_panoptic_map[py, px]

    if segment_id == 0:
        # Background
        print(json.dumps({
            "label": "background",
            "id": 0,
            "coordinates": []
        }))
        return

    # Find segment info
    label_name = "unknown"
    for segment in segments_info:
        if segment["id"] == segment_id:
            label_id = segment["label_id"]
            label_name = id2label.get(label_id, f"unknown_{label_id}")
            break

    # Get coordinates (all pixels for this segment)
    # Using numpy to find indices
    y_coords, x_coords = np.where(predicted_panoptic_map == segment_id)

    # Pack as list of [x, y]
    # This can be large, consider simplifying if needed
    pixels = np.column_stack((x_coords, y_coords)).tolist()

    output = {
        "label": label_name,
        "id": int(segment_id),
        "point_queried": [px, py],
        "coordinates": pixels,
        "bbox": [int(np.min(x_coords)), int(np.min(y_coords)), int(np.max(x_coords)), int(np.max(y_coords))]
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()

