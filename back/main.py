import os
import threading
import time
import uuid
from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory

import GPUtil
import uvicorn
from fastapi import FastAPI, UploadFile, File
from hypy_utils import write, write_json
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from wp import transcribe, diarized_transcribe

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("/data/private/whisper")
DATA_DIR.mkdir(exist_ok=True)

process_queue = []
processing = ""
start_time = 0
lock = threading.Lock()

app.mount("/result", StaticFiles(directory=DATA_DIR / "transcription"), name="result")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # Generate uuid for the audio file
        audio_id = str(uuid.uuid4())

        # Write to file
        write(DATA_DIR / "audio" / f"{audio_id}.mp3", contents)

        # Add to processing queue
        with lock:
            process_queue.append(audio_id)

        return {"audio_id": audio_id}

    except Exception as e:
        return {"error": str(e)}


@app.get("/progress/{uuid}")
async def progress(uuid: str):
    if Path(DATA_DIR / "transcription" / f"{uuid}.json").exists():
        return {"done": True}

    if processing == uuid:
        # Get load avg, and nvidia load
        lavg = float(open("/proc/loadavg").read().strip().split()[0])
        num_cpus = os.cpu_count()
        nvidia = GPUtil.getGPUs()[0].load
        elapsed = time.time() - start_time

        return {"done": False, "status": f"Processing ({lavg / num_cpus * 100:.0f}% CPU, {nvidia * 100:.0f}% GPU, {elapsed:.0f}s elapsed)"}
    else:
        return {"done": False, "status": f"Queued ({process_queue.index(uuid)} in queue before this one)"}


def process():
    global processing, start_time
    while True:
        time.sleep(0.1)
        with lock:
            if len(process_queue) > 0:
                audio_id = process_queue.pop(0)
                processing = audio_id
                start_time = time.time()
            else:
                continue

        # Start transcription
        output, elapsed = diarized_transcribe(DATA_DIR / "audio" / f"{audio_id}.mp3", num_speakers=2)

        # Write to file
        write_json(DATA_DIR / "transcription" / f"{audio_id}.json", {
            "output": output,
            "elapsed": elapsed
        })

        # Write to timestamped text file
        txt = ""
        last_speaker = None
        for c in output["chunks"]:
            start, end = c['timestamp']
            speaker = c.get('speaker', "SPEAKER_??").replace("SPEAKER_", "Speaker_")

            # Convert seconds to 00:00:00 format
            start = time.strftime('%H:%M:%S', time.gmtime(start))
            if speaker != last_speaker:
                txt += f"\n[{speaker}]\n"
                last_speaker = speaker
            txt += f"{start} [{speaker.replace("Speaker_0", "")}]: {c['text']}\n"

        write(DATA_DIR / "transcription" / f"{audio_id}.txt", txt)

        # Clear processing
        with lock:
            processing = ""
            start_time = 0


if __name__ == '__main__':
    threading.Thread(target=process, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=49585)
    print("Server started")
