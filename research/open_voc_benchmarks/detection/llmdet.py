import torch
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
from box import box
import yaml
import time
import json

# Load configuration
with open('config.yaml', 'r', encoding='utf8') as ymlfile:
    cfg = box.Box(yaml.safe_load(ymlfile))

print(f'Cuda available: {torch.cuda.is_available()}')

os.makedirs("results", exist_ok=True)

# prepare processor and model
model_id = cfg.models.llmdet
device = cfg.device if torch.cuda.is_available() else "cpu"
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

text_labels = [cfg.classes]
timing_results = {}

image_directory = cfg.sample_dir
for filename in os.listdir(image_directory):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        image_path = os.path.join(image_directory, filename)

        start_time = time.time()

        image_ex = Image.open(image_path)
        inputs = processor(images=image_ex, text=text_labels, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        results = processor.post_process_grounded_object_detection(
            outputs,
            threshold=0.4,
            target_sizes=[(image_ex.height, image_ex.width)]
        )

        end_time = time.time()
        processing_time = end_time - start_time
        timing_results[filename] = processing_time

        result = results[0]
        fig, ax = plt.subplots(1, figsize=(12, 8))
        ax.imshow(image_ex)

        # draw rectangles with labels and confidence scores
        for box, score, labels in zip(result["boxes"], result["scores"], result["labels"]):
            box = [round(x, 2) for x in box.tolist()]
            x1, y1, x2, y2 = box

            rect = patches.Rectangle((x1, y1), x2-x1, y2-y1,
                                   linewidth=2, edgecolor='red', facecolor='none')
            ax.add_patch(rect)

            label_text = f"{labels}: {round(score.item(), 3)}"
            ax.text(x1, y1-5, label_text, fontsize=10, color='red',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        ax.axis('off')
        plt.tight_layout()

        output_path = os.path.join("./results", f"llmdet_{filename}")
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        print(f"Saved annotated image to: {output_path} (Processing time: {processing_time:.3f}s)")

        plt.close()

timing_output_path = os.path.join("results", "llmdet_timing_results.json")
with open(timing_output_path, 'w') as json_file:
    json.dump(timing_results, json_file, indent=2)
print(f"Timing results saved to: {timing_output_path}")
