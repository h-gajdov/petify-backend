"""Record Chrome tabs through the DevTools screencast and encode them with ffmpeg."""

import base64
import json
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import urlopen

import websocket


class ScreencastRecorder:
    def __init__(self, driver, width, height):
        self._width = width - width % 2
        self._height = height - height % 2
        self._frames = []
        self._stopping = threading.Event()
        self._started_at = time.time()

        address = driver.capabilities["goog:chromeOptions"]["debuggerAddress"]
        with urlopen("http://%s/json" % address, timeout=5) as response:
            targets = json.load(response)
        page = next(target for target in targets if target["type"] == "page")
        self._socket = websocket.create_connection(
            page["webSocketDebuggerUrl"], timeout=1, suppress_origin=True
        )
        self._next_id = 0
        self._send("Page.enable")
        self._send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 80,
            "maxWidth": self._width,
            "maxHeight": self._height,
        })
        self._thread = threading.Thread(target=self._receive, daemon=True)
        self._thread.start()

    def _send(self, method, params=None):
        self._next_id += 1
        self._socket.send(json.dumps({"id": self._next_id, "method": method, "params": params or {}}))

    def _receive(self):
        while not self._stopping.is_set():
            try:
                message = json.loads(self._socket.recv())
            except websocket.WebSocketTimeoutException:
                continue
            except (websocket.WebSocketException, OSError):
                return
            if message.get("method") != "Page.screencastFrame":
                continue
            params = message["params"]
            self._frames.append((params["metadata"]["timestamp"], base64.b64decode(params["data"])))
            try:
                self._send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            except (websocket.WebSocketException, OSError):
                return

    def stop(self, driver):
        # Screencast frames trail the page, so finish on the state the test actually ended with.
        try:
            final = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
            self._frames.append((time.time(), base64.b64decode(final["data"])))
        except Exception:
            pass
        ended_at = time.time() + 1
        try:
            self._send("Page.stopScreencast")
        except (websocket.WebSocketException, OSError):
            pass
        self._stopping.set()
        self._thread.join(timeout=5)
        self._socket.close()
        return ended_at

    def save(self, output, ended_at, caption=None, outcome=None):
        if not self._frames:
            return False
        self._frames.sort(key=lambda frame: frame[0])
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="petify-video-") as workdir:
            workdir = Path(workdir)
            lines = []
            for index, (timestamp, data) in enumerate(self._frames):
                frame = workdir / ("%06d.jpg" % index)
                frame.write_bytes(data)
                following = self._frames[index + 1][0] if index + 1 < len(self._frames) else ended_at
                lines.append("file '%s'\nduration %.3f" % (frame.name, max(following - timestamp, 0.04)))
            lines.append("file '%s'" % frame.name)
            (workdir / "frames.txt").write_text("\n".join(lines) + "\n")
            canvas = "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:white" % (
                self._width, self._height, self._width, self._height
            )
            if caption:
                canvas += "," + _caption_filter(workdir, caption, outcome)
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", "frames.txt",
                    "-vf", canvas + ",fps=25", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                    str(output.resolve()),
                ],
                cwd=workdir,
                check=True,
            )
        return True


CAPTION_HEIGHT = 56
CAPTION_FONT = "DejaVu Sans Mono"
OUTCOME_COLORS = {"passed": "0x4ade80", "failed": "0xf87171", "skipped": "0xfacc15"}


def _caption_filter(workdir, caption, outcome):
    # Text goes through files so test names never need ffmpeg filter escaping.
    (workdir / "caption.txt").write_text(caption)
    text = "font='%s':fontsize=24:y=h-%d+(%d-24)/2" % (CAPTION_FONT, CAPTION_HEIGHT, CAPTION_HEIGHT)
    parts = [
        "drawbox=x=0:y=ih-%d:w=iw:h=%d:color=0x111827:t=fill" % (CAPTION_HEIGHT, CAPTION_HEIGHT),
        "drawtext=textfile=caption.txt:%s:x=28:fontcolor=white" % text,
    ]
    if outcome:
        (workdir / "outcome.txt").write_text(outcome.upper())
        parts.append("drawtext=textfile=outcome.txt:%s:x=w-tw-28:fontcolor=%s" % (
            text, OUTCOME_COLORS.get(outcome, "white")
        ))
    return ",".join(parts)


def combine(videos, output):
    if not videos:
        return
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listing:
        for video in videos:
            listing.write("file '%s'\n" % Path(video).resolve())
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", listing.name,
                "-c", "copy", str(output.resolve()),
            ],
            check=True,
        )
    finally:
        Path(listing.name).unlink()


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None
