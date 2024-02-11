import gc
import time
from pathlib import Path

import soundfile
import torch
from intervaltree import IntervalTree
from pyannote.core import Annotation
from transformers import pipeline
from pyannote.audio import Pipeline

device = "cuda:0"
device = torch.device(device)
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

diarize_pipe = Pipeline.from_pretrained("pyannote/speaker-diarization@2.1.1",
                                        use_auth_token="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")
diarize_pipe.to(device)

print("Loaded")


def transcribe(fp: str | Path, word_timestamps=False) -> (dict, float):
    start = time.time()
    output = pipe(str(fp),
                  chunk_length_s=30, batch_size=12,
                  return_timestamps=True, generate_kwargs={"task": "transcribe"})
    gc.collect()
    torch.cuda.empty_cache()
    elapsed = time.time() - start
    return output, elapsed


def diarize(fp: str | Path, num_speakers: int) -> (Annotation, float):
    start = time.time()
    ax, sr = soundfile.read(fp, always_2d=True)  # (time, channels)
    print(f"audio read {time.time() - start:.2f}s")
    print(ax.shape, sr)
    # {"waveform": (channel, time) numpy.ndarray or torch.Tensor, "sample_rate": 44100}
    # Convert to torch tensor
    output: Annotation = diarize_pipe({
        "waveform": torch.tensor(ax.T, device=device, dtype=torch.float32),
        "sample_rate": sr
    }, num_speakers=num_speakers)
    elapsed = time.time() - start
    return output, elapsed


def diarized_transcribe(fp: str | Path, num_speakers: int) -> (Annotation, (float, float)):
    # 1. Diarize, create interval tree
    start = time.time()
    ano, ela = diarize(fp, num_speakers)

    tree = IntervalTree()
    for segment, _, speaker in ano.itertracks(yield_label=True):
        tree[segment.start:segment.end] = speaker

    # 2. Transcribe
    output, elapsed = transcribe(fp)

    # 3. Loop through each chunks and add speaker label
    for chunk in output['chunks']:
        start, end = chunk['timestamp']

        # Get speaker
        speakers = tree[start: end]

        if not speakers:
            continue

        # Choose the speaker with the longest overlapping duration
        longest = max(speakers, key=lambda s: min(s.end, end) - max(s.begin, start))
        chunk['speaker'] = longest.data

    return output, (ela, elapsed)


if __name__ == '__main__':
    # out, ela = diarize("/ws/tmp-whisper/audio/cut.mp3", 2)
    # out: Annotation
    # print(ela)
    # print(out.get_labels())
    print(diarized_transcribe("/ws/tmp-whisper/audio/cut.mp3", num_speakers=2))


