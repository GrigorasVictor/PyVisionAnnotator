import yaml
import os
import json
import time
from PIL import Image
from box import box
import torch
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

# Load configuration
with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

device = cfg.device if torch.cuda.is_available() else 'cpu'
print(f"Device: {device}")

results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

# Load Model
model_name = cfg.models.briaai.model1
print(f"Loading model: {model_name}")
model = AutoModelForImageSegmentation.from_pretrained(model_name, trust_remote_code=True)
model.to(device)
model.eval()

# Data settings
image_size = (1024, 1024)
transform_image = transforms.Compose([
    transforms.Resize(image_size),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

timing_data = {}

image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
image_files = [f for f in os.listdir(cfg.sample_dir)
               if f.lower().endswith(image_extensions)]

for image_file in image_files:
    print(f"Processing {image_file}...")

    image_path = os.path.join(cfg.sample_dir, image_file)
    image = Image.open(image_path)

    # Ensure RGB for model input
    input_image_rgb = image.convert("RGB")

    start_time = time.time()

    input_tensor = transform_image(input_image_rgb).unsqueeze(0).to(device)

    # Prediction
    with torch.no_grad():
        preds = model(input_tensor)[-1].sigmoid().cpu()

    pred = preds[0].squeeze()
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(image.size)

    # Create result image with transparency
    if image.mode != 'RGBA':
        result_image = image.convert('RGBA')
    else:
        result_image = image.copy()

    result_image.putalpha(mask)

    # Save result
    base_name = os.path.splitext(image_file)[0]
    output_filename = f"RMBG-2.0_{base_name}_no_bg.png"
    output_path = os.path.join(results_dir, output_filename)
    result_image.save(output_path)

    end_time = time.time()
    processing_time = end_time - start_time
    timing_data[image_file] = processing_time

    print(f"Completed {image_file} in {processing_time:.4f}s -> saved: {output_filename}")

# Save timing data
json_path = os.path.join(results_dir, 'RMBG-2.0_timing.json')
with open(json_path, 'w') as json_file:
    json.dump(timing_data, json_file, indent=2)

print(f"All images processed. Results saved in '{results_dir}' directory.")
