import os
import threading
import time
import traceback
import uuid
from pathlib import Path
from subprocess import check_call
from tempfile import NamedTemporaryFile
from typing import NamedTuple

import GPUtil
import magic
import uvicorn
from fastapi import FastAPI, UploadFile, File
from hypy_utils import write, write_json
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from wp import diarized_transcribe

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TMP_DIR = Path("/tmp/whisper")
TMP_DIR.mkdir(exist_ok=True)
DATA_DIR = Path("/ws/tmp-whisper")
DATA_DIR.mkdir(exist_ok=True)
MAGIC = magic.Magic(flags=magic.MAGIC_MIME_TYPE)

process_queue = []
processing = ""
start_time = 0
lock = threading.Lock()
errors = {}

app.mount("/result", StaticFiles(directory=DATA_DIR / "transcription"), name="result")


class PendingProcess(NamedTuple):
    audio_id: str
    file: Path


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        contents = await file.read()

        # Get time in YYYY-MM-DD HH:MM:SS format
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{time_str}] Received {file.filename}")

        # Generate uuid for the audio file
        audio_id = str(uuid.uuid4())
        ext = file.filename.split('.')[-1]
        fp = DATA_DIR / "audio" / f"{audio_id}.{ext}"
        write(fp, contents)

        # Add to processing queue
        with lock:
            process_queue.append(PendingProcess(audio_id, fp))

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
    elif uuid in errors:
        return {"done": False, "status": "Error", "error": errors[uuid]}
    else:
        index = 0
        for i, (audio_id, _) in enumerate(process_queue):
            if audio_id == uuid:
                index = i
                break
        return {"done": False, "status": f"Queued ({index} in queue before this one)"}


def process():
    global processing, start_time
    while True:
        time.sleep(0.1)
        with lock:
            if len(process_queue) > 0:
                audio_id, fp = process_queue.pop(0)
                processing = audio_id
                start_time = time.time()
            else:
                continue

        try:
            # Check file magic
            mime = MAGIC.id_buffer(open(fp, "rb").read(2048))
            is_tmp = False

            if mime not in {'audio/mpeg', 'audio/x-wav', 'audio/wav'}:
                print(f"Converting {fp} to mp3")
                mp3_file = TMP_DIR / f"{audio_id}.mp3"

                # Check if file is audio by converting to mp3 (fp) using ffmpeg
                check_call(["ffmpeg", "-i", fp, "-acodec", "mp3", "-y", mp3_file])

                # Set new fp
                fp = mp3_file
                is_tmp = True

            # Start transcription
            output, elapsed = diarized_transcribe(fp, num_speakers=2)

            # Write to file
            write_json(DATA_DIR / "transcription" / f"{audio_id}.json", {
                "output": output,
                "elapsed": elapsed
            })

            # Remove tmp file
            if is_tmp:
                fp.unlink()

        except Exception as e:
            errors[audio_id] = str(e) + "\n\n" + traceback.format_exc()
            print(f"Error processing {audio_id}: {e}")

        # Clear processing
        with lock:
            processing = ""
            start_time = 0


if __name__ == '__main__':
    threading.Thread(target=process, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=49585)
    print("Server started")
