import yaml
import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
from box import box
import torch
import numpy as np
import random
from sam2.sam2_image_predictor import SAM2ImagePredictor

with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

print(torch.cuda.is_available())

results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

predictor = SAM2ImagePredictor.from_pretrained(cfg.models.facebook.model3)
raw_model_id = cfg.models.facebook.model3
model_name = raw_model_id.split('/')[-1]

timing_data = {}

image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
image_files = [f for f in os.listdir(cfg.sample_dir)
               if f.lower().endswith(image_extensions)]

# Track label assignment index
label_index = 0
class_list = cfg.classes

for image_file in image_files:
    print(f"Processing {image_file}...")

    image_path = os.path.join(cfg.sample_dir, image_file)
    image = Image.open(image_path).convert("RGB")
    image_array = np.array(image)

    start_time = time.time()

    with torch.inference_mode(), torch.autocast(cfg.device, dtype=torch.bfloat16):
        predictor.set_image(image_array)

        # Generate automatic masks using everything mode
        # SAM2 can segment everything without specific prompts
        height, width = image_array.shape[:2]

        # Create a grid of points to prompt segmentation
        grid_size = 32
        point_coords = []
        for y in range(grid_size // 2, height, height // grid_size):
            for x in range(grid_size // 2, width, width // grid_size):
                point_coords.append([x, y])

        point_coords = np.array(point_coords)
        point_labels = np.ones(len(point_coords))

        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True
        )

    # Create visualization
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

    # Process each mask
    for i, (mask, score) in enumerate(zip(masks, scores)):
        if score < 0.5:
            continue
        y_coords, x_coords = np.where(mask)
        if len(y_coords) < 100:
            continue
        label_name = class_list[label_index % len(class_list)]
        label_index += 1
        color = colors[i % len(colors)]
        # Vectorized semi-transparent overlay (faster than per-pixel loop)
        arr = np.array(vis_image)
        alpha = 0.6
        color_arr = np.array(color, dtype=np.float32)
        mask_bool = mask.astype(bool)
        arr[mask_bool] = (alpha * color_arr + (1 - alpha) * arr[mask_bool]).astype(np.uint8)
        vis_image = Image.fromarray(arr)
        draw = ImageDraw.Draw(vis_image)  # refresh after array modification
        cx = int(np.mean(x_coords))
        cy = int(np.mean(y_coords))
        text = f"ID:{i} {label_name}"
        bbox = draw.textbbox((cx, cy), text, font=font)
        draw.rectangle([bbox[0]-2, bbox[1]-2, bbox[2]+2, bbox[3]+2], fill=(0, 0, 0))
        draw.text((cx, cy), text, fill=(255, 255, 255), font=font)

    base_name = os.path.splitext(image_file)[0]
    output_path = os.path.join(results_dir, f"{model_name}_{base_name}_segmented.png")
    vis_image.save(output_path)

    end_time = time.time()
    processing_time = end_time - start_time
    timing_data[image_file] = processing_time

    print(f"Completed {image_file} in {processing_time:.4f}s -> saved: {os.path.basename(output_path)}")

# Save timing data
json_path = os.path.join(results_dir, f'{model_name}_timing.json')
with open(json_path, 'w') as json_file:
    json.dump(timing_data, json_file, indent=2)

print(f"All images processed. Results saved in '{results_dir}' directory.")
