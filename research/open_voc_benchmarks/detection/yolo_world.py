from box import box
import yaml
from ultralytics import YOLOWorld
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Tuple, Optional
import torch
import os
from PIL import Image
import time
import json

with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

class YOLOWorldInstanceSegmentation:
    def __init__(self, model_path: str = "yolov8s-worldv2.pt", device = "cuda"):
        self.device = torch.device(device)
        self.model = YOLOWorld(model_path)
        self.classes = []

    def set_classes(self, classes: List[str]):
        self.classes = classes
        self.model.set_classes(classes)

    def segment_image(self, image_path: str, confidence: float = 0.3) -> dict:
        results = self.model(image_path, conf=confidence)
        object = {
            'boxes': [],
            'masks': [],
            'classes': [],
            'confidences': [],
            'class_names': []
        }
        objects = []
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                object['confidences'] = result.boxes.conf.cpu().numpy()
                object['class_ids'] = result.boxes.cls.cpu().numpy().astype(int)
                object['boxes'] = boxes
                objects.append(object)
        return objects

if __name__ == '__main__':
    os.makedirs("results", exist_ok=True)

    model_path = cfg.models.yolo
    image_directory = cfg.sample_dir

    model = YOLOWorldInstanceSegmentation(model_path, cfg.device)
    model.set_classes(cfg.classes)

    timing_results = {}

    for filename in os.listdir(image_directory):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            image_path = os.path.join(image_directory, filename)

            start_time = time.time()

            results = model.segment_image(image_path)

            end_time = time.time()
            processing_time = end_time - start_time
            timing_results[filename] = processing_time

            image = Image.open(image_path)
            fig, ax = plt.subplots(1, figsize=(12, 8))
            ax.imshow(image)

            # Draw rectangles with labels and confidence scores
            for result in results:
                boxes = result.get('boxes', [])
                class_ids = result.get('class_ids', [])
                confidences = result.get('confidences', [])

                for box, class_id, conf in zip(boxes, class_ids, confidences):
                    x1, y1, x2, y2 = box

                    rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                           linewidth=2, edgecolor='red', facecolor='none')
                    ax.add_patch(rect)

                    class_name = model.classes[class_id] if model.classes else str(class_id)
                    label_text = f"{class_name}: {round(conf, 3)}"
                    ax.text(x1, y1-5, label_text, fontsize=10, color='red',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

            ax.axis('off')
            plt.tight_layout()

            output_path = os.path.join("./results", f"yolo_world_{filename}")
            plt.savefig(output_path, bbox_inches='tight', dpi=300)
            print(f"Saved annotated image to: {output_path} (Processing time: {processing_time:.3f}s)")

            plt.close()

    timing_output_path = os.path.join("results", "yolo_world_timing_results.json")
    with open(timing_output_path, 'w') as json_file:
        json.dump(timing_results, json_file, indent=2)
    print(f"Timing results saved to: {timing_output_path}")
