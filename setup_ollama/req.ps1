$models = @(
    "gemma3:12b",
    "qwen2.5vl:7b",
    "llava:13b",
    "minicpm-v:8b",
    "llama3.2-vision:11b"
)

foreach ($model in $models) {
    Write-Host "--- Pulling model: $model ---"
    ollama pull $model
    Write-Host "--- Finished pulling $model ---`n"
}
Write-Host "All models have been pulled."