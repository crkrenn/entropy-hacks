#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "yt-dlp>=2026.1.0",
# ]
# ///

import argparse
import re
import sys
from pathlib import Path

import yt_dlp


def strip_vtt(vtt_text: str) -> str:
    lines = []
    for line in vtt_text.splitlines():
        line = line.strip()

        if not line:
            continue
        if line == "WEBVTT":
            continue
        if "-->" in line:
            continue
        if line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if re.fullmatch(r"\d+", line):
            continue

        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)

    cleaned = []
    for line in lines:
        if not cleaned or cleaned[-1] != line:
            cleaned.append(line)

    return "\n".join(cleaned) + "\n"


def choose_caption(info: dict, lang: str) -> tuple[str, bool]:
    """Return (url, is_auto_caption)."""
    for source_name, is_auto in [
        ("subtitles", False),
        ("automatic_captions", True),
    ]:
        captions = info.get(source_name) or {}

        candidates = []
        if lang in captions:
            candidates.append(lang)

        candidates.extend(
            k for k in captions
            if k.startswith(lang + "-")
        )

        for key in candidates:
            formats = captions[key]

            for fmt in formats:
                if fmt.get("ext") == "vtt" and fmt.get("url"):
                    return fmt["url"], is_auto

            for fmt in formats:
                if fmt.get("url"):
                    return fmt["url"], is_auto

    raise RuntimeError(
        f"No captions found for language '{lang}'."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download YouTube captions as plain text."
    )
    parser.add_argument(
        "url",
        help="YouTube video URL",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Caption language (default: en)",
    )
    parser.add_argument(
        "--out",
        default="captions.txt",
        help="Output text file",
    )

    args = parser.parse_args()

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(args.url, download=False)

        caption_url, is_auto = choose_caption(
            info,
            args.lang,
        )

        vtt_text = (
            ydl.urlopen(caption_url)
            .read()
            .decode("utf-8", errors="replace")
        )

    text = strip_vtt(vtt_text)
    Path(args.out).write_text(text, encoding="utf-8")

    source = (
        "auto-generated captions"
        if is_auto
        else "manual closed captions"
    )

    print(f"Wrote {args.out} from {source}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
