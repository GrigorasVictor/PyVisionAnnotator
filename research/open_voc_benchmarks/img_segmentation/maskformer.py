import yaml
import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
from box import box
from transformers import MaskFormerImageProcessor, MaskFormerForInstanceSegmentation
import torch
import numpy as np
import random

with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

print(torch.cuda.is_available())

results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

processor = MaskFormerImageProcessor.from_pretrained(cfg.models.facebook.model2)
model = MaskFormerForInstanceSegmentation.from_pretrained(cfg.models.facebook.model2)

model = model.to(cfg.device)
model_name = cfg.models.facebook.model2.split('/')[-1]

timing_data = {}

image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
image_files = [f for f in os.listdir(cfg.sample_dir)
               if f.lower().endswith(image_extensions)]

for image_file in image_files:
    print(f"Processing {image_file}...")

    image_path = os.path.join(cfg.sample_dir, image_file)
    image = Image.open(image_path).convert("RGB")

    start_time = time.time()

    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(cfg.device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    result = processor.post_process_panoptic_segmentation(
        outputs,
        target_sizes=[image.size[::-1]],
        label_ids_to_fuse=[]
    )[0]
    predicted_panoptic_map = result["segmentation"]
    segments_info = result["segments_info"]

    id2label = model.config.id2label
    segmentation_array = predicted_panoptic_map.cpu().numpy()

    # Get segment info
    valid_segments = {}
    for segment in segments_info:
        segment_id = segment.get("id")
        label_id = segment.get("label_id")
        label_name = id2label.get(label_id, f"unknown_{label_id}")
        valid_segments[segment_id] = {
            "label_name": label_name
        }

    unique_ids = np.unique(segmentation_array)
    unique_ids = unique_ids[unique_ids != 0]  # remove background

    height, width = segmentation_array.shape

    # Create visualization image (copy original)
    vis_image = image.copy()
    draw = ImageDraw.Draw(vis_image)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Generate colors for segments
    random.seed(42)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
              (255, 0, 255), (0, 255, 255), (128, 0, 128), (255, 165, 0)]

    for i, segment_id in enumerate(unique_ids):
        if segment_id not in valid_segments:
            continue

        label_name = valid_segments[segment_id]["label_name"]

        # Get mask
        segment_mask = segmentation_array == segment_id
        y_coords, x_coords = np.where(segment_mask)

        if len(y_coords) < 10:  # Skip tiny segments
            continue

        # Get color
        color = colors[i % len(colors)]

        # Fill mask area with color
        for y, x in zip(y_coords, x_coords):
            vis_image.putpixel((x, y), color)

        # Calculate centroid for text
        cx = int(np.mean(x_coords))
        cy = int(np.mean(y_coords))

        # Draw label and ID
        text = f"{label_name} #{segment_id}"

        # Black background for text readability
        bbox = draw.textbbox((cx, cy), text, font=font)
        draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=(0, 0, 0))
        draw.text((cx, cy), text, fill=(255, 255, 255), font=font)

    # Save result
    base_name = os.path.splitext(image_file)[0]
    output_path = os.path.join(results_dir, f"{model_name}_{base_name}_segmented.png")
    vis_image.save(output_path)

    end_time = time.time()
    processing_time = end_time - start_time
    timing_data[image_file] = processing_time

    print(f"Completed {image_file} in {processing_time:.4f}s -> saved: {os.path.basename(output_path)}")

# Save timing data
json_path = os.path.join(results_dir, f'maskformer_timing.json')
with open(json_path, 'w') as json_file:
    json.dump(timing_data, json_file, indent=2)

print(f"All images processed. Results saved in '{results_dir}' directory.")
