from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime
from typing import Optional, Tuple, Dict

import yt_dlp


class YouTubeIngestor:
    def __init__(self, output_dir: str = "data/uploads/subtitles") -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/live/)([^&\n?#]+)",
            r"youtube\.com/watch\?.*v=([^&\n?#]+)",
            r"youtu\.be/([^&\n?#]+)",
            r"youtube\.com/live/([^&\n?#]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
            return url
        return None

    def fetch_raw_text(self, video_id: str) -> Tuple[str, Dict[str, str]]:
        url = f"https://www.youtube.com/watch?v={video_id}"
        info = self._extract_info(url)
        raw_vtt, lang = self._download_best_subtitles(info, video_id)
        clean_text = self._clean_subtitle_text(raw_vtt)
        metadata = self._build_metadata(info, lang)
        return clean_text, metadata

    def _extract_info(self, url: str) -> dict:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitlesformat": "vtt",
            "subtitleslangs": ["ru", "en"],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _download_best_subtitles(self, info: dict, video_id: str) -> Tuple[str, str]:
        subtitles = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}

        for lang in ["ru", "en"]:
            entry = subtitles.get(lang) or auto.get(lang)
            if not entry:
                continue
            url = self._pick_subtitle_url(entry)
            if url:
                raw = self._download_text(url)
                return raw, lang

        # fallback: any available subtitles
        for source in (subtitles, auto):
            for lang, entry in source.items():
                url = self._pick_subtitle_url(entry)
                if url:
                    raw = self._download_text(url)
                    return raw, lang

        raise RuntimeError("No subtitles found for video")

    def _pick_subtitle_url(self, entries: list) -> Optional[str]:
        if not entries:
            return None
        # prefer vtt
        for item in entries:
            if item.get("ext") == "vtt" and item.get("url"):
                return item["url"]
        return entries[0].get("url")

    def _download_text(self, url: str) -> str:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="ignore")

    def _build_metadata(self, info: dict, language: str) -> Dict[str, str]:
        title = info.get("title", "")
        channel = info.get("uploader") or info.get("channel") or ""
        upload_date = info.get("upload_date", "")
        published_date = ""
        if upload_date and len(upload_date) == 8:
            published_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        return {
            "title": title,
            "channel": channel,
            "language": language,
            "published_date": published_date,
        }

    def _clean_subtitle_text(self, raw_vtt: str) -> str:
        if not raw_vtt:
            return ""
        lines = raw_vtt.splitlines()
        cleaned_lines = []
        last_line = ""
        timecode_re = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("WEBVTT"):
                continue
            if "-->" in line or timecode_re.search(line):
                continue
            if line.isdigit():
                continue
            line = re.sub(r"<[^>]+>", "", line)
            line = line.strip()
            if not line:
                continue
            if line == last_line:
                continue
            cleaned_lines.append(line)
            last_line = line

        text = " ".join(cleaned_lines)
        text = re.sub(r"\s+", " ", text).strip()
        return text
