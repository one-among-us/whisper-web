import gc
import time
from pathlib import Path

import os
import soundfile
import torch
from intervaltree import IntervalTree
from pyannote.core import Annotation
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel

device = "cuda:0"
device_obj = torch.device(device)
dtype = torch.float16
HF_TOKEN = os.getenv("HF_TOKEN")

# Initialize faster-whisper
fw_model = WhisperModel("large-v3", device="cuda", compute_type="float16")

diarize_pipe = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token=HF_TOKEN
)
diarize_pipe.to(device_obj)

print("Loaded")


def transcribe(fp: str | Path, task="transcribe") -> tuple[dict, float]:
    start = time.time()
    segments, info = fw_model.transcribe(
        str(fp), 
        beam_size=5, 
        task=task, 
        vad_filter=True, 
        initial_prompt="English and Mandarin Chinese mixed conversation."
    )
    
    chunks = []
    for segment in segments:
        chunks.append({
            'timestamp': (segment.start, segment.end),
            'text': segment.text
        })
    
    output = {
        'text': "".join([c['text'] for c in chunks]),
        'chunks': chunks
    }

    gc.collect()
    torch.cuda.empty_cache()
    elapsed = time.time() - start
    return output, elapsed


def diarize(fp: str | Path, num_speakers: int) -> tuple[any, float]:
    start = time.time()
    ax, sr = soundfile.read(fp, always_2d=True)
    # Convert to torch tensor
    output = diarize_pipe({
        "waveform": torch.tensor(ax.T, device=device_obj, dtype=torch.float32),
        "sample_rate": sr
    }, num_speakers=num_speakers)
    elapsed = time.time() - start
    return output, elapsed


def diarized_transcribe(fp: str | Path, num_speakers: int, task="transcribe") -> tuple[dict, tuple[float, float]]:
    # 1. Diarize, create interval tree
    output, ela = diarize(fp, num_speakers)

    tree = IntervalTree()
    # Support both new community-1 API and legacy API
    diarization = getattr(output, 'speaker_diarization', None)
    
    if diarization is not None:
        # New community-1 API
        for turn, speaker in diarization:
            tree[turn.start:turn.end] = speaker
    else:
        # Legacy 3.1 API
        for segment, _, speaker in output.itertracks(yield_label=True):
            tree[segment.start:segment.end] = speaker

    # 2. Transcribe
    output, elapsed = transcribe(fp, task=task)

    # 3. Loop through each chunks and add speaker label
    for chunk in output['chunks']:
        start_t, end_t = chunk['timestamp']

        # Get speaker
        speakers = tree[start_t: end_t]

        if not speakers:
            continue

        # Choose the speaker with the longest overlapping duration
        longest = max(speakers, key=lambda s: min(s.end, end_t) - max(s.begin, start_t))
        chunk['speaker'] = longest.data

    return output, (ela, elapsed)


if __name__ == '__main__':
    # Test
    import sys
    if len(sys.argv) > 1:
        print(diarized_transcribe(sys.argv[1], num_speakers=2))
