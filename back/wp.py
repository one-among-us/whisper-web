import time
from pathlib import Path

import torch
from transformers import pipeline

device = "cuda:0"
dtype = torch.float16
MODEL = "/data/Datasets/whisper"

pipe = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-large-v3",
    torch_dtype=torch.float16,
    device="cuda",
    return_timestamps=True,
    model_kwargs={"use_flash_attention_2": True},
)

print("Loaded")


def transcribe(fp: str | Path):
    start = time.time()
    output = pipe(str(fp),
                  chunk_length_s=30, batch_size=24,
                  return_timestamps=True, generate_kwargs={"task": "transcribe"})
    elapsed = time.time() - start
    return output, elapsed



