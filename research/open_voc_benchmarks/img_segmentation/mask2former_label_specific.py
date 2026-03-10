import yaml
import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
from box import box
from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation
import torch
import numpy as np
import random

with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

print(torch.cuda.is_available())

results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

processor = AutoImageProcessor.from_pretrained(cfg.models.facebook.model1)
model = Mask2FormerForUniversalSegmentation.from_pretrained(cfg.models.facebook.model1)

model = model.to(cfg.device)
model_name = cfg.models.facebook.model1.split('/')[-1]

timing_data = {}

image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
image_files = [f for f in os.listdir(cfg.sample_dir)
               if f.lower().endswith(image_extensions)]

for image_file in image_files:
    print(f"Processing {image_file}...")

    image_path = os.path.join(cfg.sample_dir, image_file)
    image = Image.open(image_path)

    start_time = time.time()

    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(cfg.device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    # model predicts class_queries_logits of shape `(batch_size, num_queries)`
    # and masks_queries_logits of shape `(batch_size, num_queries, height, width)`
    class_queries_logits = outputs.class_queries_logits
    masks_queries_logits = outputs.masks_queries_logits

    # you can pass them to processor for postprocessing
    result = processor.post_process_panoptic_segmentation(
        outputs,
        target_sizes=[image.size[::-1]],
        label_ids_to_fuse=[]
    )[0]
    predicted_panoptic_map = result["segmentation"]
    segments_info = result["segments_info"]

    # Get label names from model config
    id2label = model.config.id2label

    # Get target classes from config (same as llmdet)
    target_classes = [cls.lower() for cls in cfg.classes]

    # convert to an image and apply custom color mapping
    segmentation_array = predicted_panoptic_map.cpu().numpy()

    # Create a filtered segmentation array
    filtered_segmentation = np.zeros_like(segmentation_array)
    valid_segments = {}

    for segment in segments_info:
        segment_id = segment["id"]
        label_id = segment["label_id"]
        label_name = id2label.get(label_id, f"unknown_{label_id}")

        # Filter by target classes from config
        if label_name.lower() in target_classes:
            segment_mask = segmentation_array == segment_id
            filtered_segmentation[segment_mask] = segment_id
            valid_segments[segment_id] = {
                "label_id": label_id,
                "label_name": label_name
            }

    unique_ids = np.unique(filtered_segmentation)
    unique_ids = unique_ids[unique_ids != 0]  # Remove background

    height, width = filtered_segmentation.shape
    colored_image = np.zeros((height, width, 3), dtype=np.uint8)

    # Set background to red
    background_mask = filtered_segmentation == 0
    colored_image[background_mask] = [255, 0, 0]  # Red background

    random.seed(42)

    for i, segment_id in enumerate(unique_ids):
        segment_mask = filtered_segmentation == segment_id

        if i == 0:  # first detection is purple base
            colored_image[segment_mask] = [128, 0, 128]
        else:
            # generate random color variations for other detections
            r = random.randint(100, 255)
            g = random.randint(50, 200)
            b = random.randint(100, 255)
            colored_image[segment_mask] = [r, g, b]

    segmented_image = Image.fromarray(colored_image)
    draw = ImageDraw.Draw(segmented_image)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    for segment_id in unique_ids:
        segment_mask = filtered_segmentation == segment_id
        y_coords, x_coords = np.where(segment_mask)

        if len(y_coords) > 0:
            center_y = int(np.mean(y_coords))
            center_x = int(np.mean(x_coords))

            # Get label info
            segment_info = valid_segments[segment_id]
            label_name = segment_info["label_name"]

            # Create text with ID and label name
            text_id = f"ID: {segment_id}"
            text_label = f"{label_name}"

            # Draw ID text
            draw.text((center_x-1, center_y-11), text_id, fill="black", font=font_small)
            draw.text((center_x+1, center_y-11), text_id, fill="black", font=font_small)
            draw.text((center_x-1, center_y-9), text_id, fill="black", font=font_small)
            draw.text((center_x+1, center_y-9), text_id, fill="black", font=font_small)
            draw.text((center_x, center_y-10), text_id, fill="white", font=font_small)

            # Draw label name text
            draw.text((center_x-1, center_y+4), text_label, fill="black", font=font)
            draw.text((center_x+1, center_y+4), text_label, fill="black", font=font)
            draw.text((center_x-1, center_y+6), text_label, fill="black", font=font)
            draw.text((center_x+1, center_y+6), text_label, fill="black", font=font)
            draw.text((center_x, center_y+5), text_label, fill="white", font=font)

    base_name = os.path.splitext(image_file)[0]
    segmented_image_path = os.path.join(results_dir, f"{model_name}_label_specific_{base_name}.png")
    segmented_image.save(segmented_image_path)

    end_time = time.time()
    processing_time = end_time - start_time

    timing_data[image_file] = processing_time

    print(f"Completed {image_file} in {processing_time:.4f} seconds")

json_path = os.path.join(results_dir, f'facebook_timing.json')
with open(json_path, 'w') as json_file:
    json.dump(timing_data, json_file, indent=2)

print(f"All images processed. Results saved in '{results_dir}' directory.")
