"""Render a captioned walkthrough from real, dated public UI screenshots."""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps


SCENES = (
    ("overview.jpg", "Save a pool or mint to a local watchlist.",
     "The public feed is a recorded snapshot; stale data stays visible."),
    ("workflow.jpg", "Follow readiness, migration evidence and watchlist activity.",
     "A threshold indicator is not a forecast or permission to trade."),
    ("detail.jpg", "Inspect the finalized transaction and its raw evidence.",
     "Each result retains its source, slot, identity and classification."),
    ("quotes.jpg", "Compare exact-input arithmetic against the pinned Meteora SDK.",
     "Supported captured states only; this does not establish fills or profit."),
    ("pilot.jpg", "Read the versioned JSON feed from your own application.",
     "I am continuing development and inviting independent developer feedback."),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshots", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path,
                        default=Path("C:/Windows/Fonts/segoeui.ttf"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(args.font), 25)
    small = ImageFont.truetype(str(args.font), 18)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="dbc-walkthrough-") as temporary:
        directory = Path(temporary)
        segments = []
        for index, (filename, title, detail) in enumerate(SCENES):
            source = Image.open(args.screenshots / filename).convert("RGB")
            frame = Image.new("RGB", (1280, 840), "#f5f7f6")
            fitted = ImageOps.contain(source, (1280, 720))
            frame.paste(fitted, ((1280-fitted.width)//2, (720-fitted.height)//2))
            draw = ImageDraw.Draw(frame)
            draw.rectangle((0, 720, 1280, 840), fill="#142822")
            for text, selected_font in ((title, font), (detail, small)):
                if draw.textlength(text, font=selected_font) > 1220:
                    raise ValueError("Caption exceeds the fixed frame")
            draw.text((28, 732), title, font=font, fill="white")
            draw.text((28, 769), detail, font=small, fill="#dcebe5")
            draw.text((28, 807),
                      f"{index+1}/5  |  Public UI screenshots, 16 October 2026  |  Post-submission progress",
                      font=small, fill="#b9cec3")
            still = directory / f"scene-{index}.png"
            frame.save(still)
            if index == 0:
                frame.save(args.output.with_suffix(".jpg"), quality=92)
            segment = directory / f"scene-{index}.mp4"
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                            "-loop", "1", "-i", str(still), "-t", "12", "-r", "24",
                            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                            "-pix_fmt", "yuv420p", "-an", str(segment)], check=True)
            segments.append(segment)
        listing = directory / "segments.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments),
                           encoding="utf-8")
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                        "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-c", "copy", "-movflags", "+faststart", str(args.output)], check=True)
    reader = imageio_ffmpeg.read_frames(str(args.output), pix_fmt="rgb24")
    metadata = next(reader)
    first = next(reader)
    reader.close()
    if metadata["size"] != (1280, 840) or abs(metadata["duration"]-60) > .2:
        raise ValueError(f"Unexpected media metadata: {metadata}")
    if len(set(first)) < 64:
        raise ValueError("Rendered first frame is blank")
    print(json.dumps({"output": str(args.output), "duration": metadata["duration"],
                      "size": metadata["size"], "bytes": args.output.stat().st_size,
                      "voice": False, "source": "dated public UI screenshots"}))


if __name__ == "__main__":
    main()
