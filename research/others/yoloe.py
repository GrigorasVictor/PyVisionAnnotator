import argparse
import sys
import os
import json
import torch
from ultralytics import YOLOE

def get_args():
    parser = argparse.ArgumentParser(description="YOLO Point Query")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--labels", required=True, help="Comma-separated list of labels to detect")
    parser.add_argument("--model", default="yoloe-26m-seg.pt", help="Path to model weights")
    parser.add_argument("--mode", nargs='+', default=["bbox", "segment"], help="Output mode: bbox, segment")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", help="Device to use")
    parser.add_argument("--conf", type=float, default=0.32, help="Confidence threshold")
    return parser.parse_args()

def main():
    args = get_args()
    if not os.path.exists(args.image):
        print(json.dumps({"error": f"Image not found: {args.image}"}))
        sys.exit(1)
    try:
        model = YOLOE(args.model)

        # Set classes as requested
        labels = [l.strip() for l in args.labels.split(',')]
        model.set_classes(labels)

    except Exception as e:
        print(json.dumps({"error": f"Failed to load model: {str(e)}"}))
        sys.exit(1)

    try:
        results = model.predict(args.image, conf=args.conf, verbose=False, device=args.device)
        result = results[0]
    except Exception as e:
        print(json.dumps({"error": f"Prediction failed: {str(e)}"}))
        sys.exit(1)


    detections = []

    # Process modes
    output_modes = set()
    if args.mode:
        for m in args.mode:
            if m == 'all':
                output_modes.update(['bbox', 'segment'])
            else:
                output_modes.add(m)
    else:
        output_modes.update(['bbox', 'segment'])

    for i, box in enumerate(result.boxes):
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

        label_name = str(cls_id)
        if hasattr(model, 'names'):
            label_name = model.names[cls_id]

        detection = {
            "label": label_name,
            "confidence": conf
        }

        if 'bbox' in output_modes:
            detection["box"] = [float(x1), float(y1), float(x2), float(y2)]

        if 'segment' in output_modes:
            mask_coords = []
            if result.masks is not None:
                try:
                    poly = result.masks.xy[i]
                    if len(poly) > 0:
                        mask_coords = poly.tolist()
                except:
                     mask_coords = []

            if not mask_coords:
                 # usage of box as fallback for mask is sometimes desired
                 mask_coords = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

            detection["coordinates"] = mask_coords

        detections.append(detection)

    print(json.dumps(detections))

if __name__ == "__main__":
    main()
