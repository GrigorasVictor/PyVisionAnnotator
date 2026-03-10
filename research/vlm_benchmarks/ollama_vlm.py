import os
import ollama
import re

models = ['gemma3:12b', 'qwen2.5vl:7b', 'llava:13b', 'minicpm-v:8b', 'llama3.2-vision:11b']
#models = ['gemma3:12b']

result_name = 'ollama_vlm_results.md'
promt = "Respond to the following questions, strictly adhering to the format 'Q: <question> \nA: <answer>'.\n NO OTHER TEXT"
questions = """What is happening in this image?
    Describe the relationships between the objects.
    Where is the person located?
    What time of day is it?
    What might happen next in the scene?"""

samples_dir = 'samples'

# rename the files in the samples directory to sample_1, sample_2, etc.
for idx, filename in enumerate(os.listdir(samples_dir), 1):
    old_path = os.path.join(samples_dir, filename)
    if os.path.isfile(old_path) and not filename.startswith('sample_'):
        ext = os.path.splitext(filename)[1]
        new_name = f"sample_{idx}{ext}"
        new_path = os.path.join(samples_dir, new_name)
        os.rename(old_path, new_path)

# making the .md file by iteratng through the samples directory and running the models on each image
with open(result_name, 'w') as f:
    f.write("# VLM Benchmark Results\n\n")
    for idx, filename in enumerate(sorted(os.listdir(samples_dir)), 1):
        f.write(f'## Analysis of `{filename}`\n\n')

        image_path = os.path.join(samples_dir, filename).replace('\\', '/')
        f.write(f'![{filename}]({image_path})\n\n')

        for model in models:
            print(f'Analyzing `{filename}` with model `{model}`...')

            response = ollama.chat(
                model=model,
                messages=[
                    {
                        'role': 'user',
                        'content': f'{promt}\n Questions: {questions}',
                        'images': [os.path.join(samples_dir, filename)]
                    },
                ],
                options={
                    'num_gpu': 100
                }
            )
            # remove the entire <think>...<./think> section
            summary = (re.sub(r'<think\s*>.*?</think\s*>', '', response['message']['content'], flags=re.DOTALL)
                       .replace('*', '')
                       .replace('```json', '')
                       .replace('```', '')
                       .strip())

            f.write(f"### Response from `{model}`\n\n")
            qa_pairs = re.split(r'\n?Q:', summary)
            for pair in qa_pairs:
                if not pair.strip():
                    continue
                parts = re.split(r'\n\s*A:', pair, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    question = parts[0].strip()
                    answer = parts[1].strip().replace('\n', ' ')
                    f.write(f"* **{question}**\n{answer}\n\n")
                else:
                    f.write(f"{pair.strip()}\n\n")