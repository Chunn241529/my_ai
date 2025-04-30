import threading
import time
import re
import os
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import pygame
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from typing import List

# Giả định các module này đã được định nghĩa
from cli.functions.subfuncs.commands import *
from cli.functions.subfuncs.file import *
from cli.functions.subfuncs.generate import *
from cli.functions.subfuncs.tts import run_viettts_synthesis
from cli.functions.subfuncs.music import play_music
from utils.helper.web_utils import *

console = Console()

# Khởi tạo pygame mixer
pygame.mixer.init()

class Chat:
    def __init__(self, initial_query: str):
        self.initial_query = initial_query
        self.history_analys: List[str] = []
        self.refresh_second = 10
        self.vertical_overflow = "ellipsis"
        self.only_url = extract_url_from_input(self.initial_query) or ""
        os.environ["JAX_PLATFORM_NAME"] = "cpu"
        # Lock để đồng bộ giữa TTS và music
        self.audio_lock = threading.Lock()

    # def extract_url_from_input(self, input_text: str) -> str:
    #     """Trích xuất URL đầu tiên từ chuỗi đầu vào của người dùng."""
    #     URL_PATTERN = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*"
    #     match = re.search(URL_PATTERN, input_text)
    #     return match.group(0) if match else ""

    # def extract_image_path(self, input_text: str) -> str:
    #     """Trích xuất đường dẫn file ảnh từ chuỗi đầu vào, hỗ trợ Windows, Linux, macOS."""
    #     IMAGE_PATH_PATTERN = r"(?:(?:[a-zA-Z]:[\\/])|\/)?[\w\-\.\/\\]*(?:[\w\-]+\.(?:jpg|jpeg|png|gif|bmp|webp))"
    #     match = re.search(IMAGE_PATH_PATTERN, input_text, re.IGNORECASE)
    #     return match.group(0) if match else ""

    # def extract_image_url(self, input_text: str) -> str:
    #     """Trích xuất URL ảnh đầu tiên từ chuỗi đầu vào của người dùng."""
    #     IMAGE_URL_PATTERN = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*\.(?:jpg|jpeg|png|gif|bmp|webp)"
    #     match = re.search(IMAGE_URL_PATTERN, input_text, re.IGNORECASE)
    #     return match.group(0) if match else ""

    def fallback_search(self, query: str) -> str:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=2)
            return (
                "\n".join([r["body"] for r in results])
                if results
                else "Không tìm thấy thông tin bổ sung."
            )

    def extract_content(self, url: str = None, snippet: str = "") -> str:
        if not url:
            url = self.only_url
        if not url:
            return "Không có URL để phân tích. Tôi sẽ dựa vào thông tin khác nếu có."
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            tags_to_extract = ["p", "h1", "h2", "h3", "a", "span", "table", "textarea"]
            content_parts = [
                tag.get_text(strip=True)
                for tag in soup.find_all(tags_to_extract)
                if tag.get_text(strip=True)
            ]
            return f"Snippet: {snippet}\n" + "\n".join(content_parts)
        except requests.RequestException as e:
            return (
                f"Không thể truy cập {url}: {str(e)}. Tôi sẽ thử tìm thông tin bổ sung."
            )

    def play_speech(self, file_path):
        """Phát file âm thanh TTS với lock để tránh chồng chéo."""
        with self.audio_lock:
            try:
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            except Exception as e:
                console.print(f"[bold red]Lỗi khi phát TTS: {e}[/bold red]")

    def chat(self) -> str:
        """Tổng hợp các câu trả lời đã thu thập."""


        image_path = extract_image_path(self.initial_query) or ""
        image_url = extract_image_url(self.initial_query) or ""

        content = extract_content(self.only_url) or ""

        if any(
            keyword in content.lower()
            for keyword in [
                "đăng nhập",
                "sign in",
                "không thể truy cập",
                "Forbidden",
                "404 Not Found",
                "Connection Refused",
            ]
        ):
            fallback = self.fallback_search(self.only_url)
            content += f"\nThông tin bổ sung từ tìm kiếm: {fallback}"

        with Live(
            Markdown("Chờ xíu...🖐️"),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
            summary_stream = chat(
                query=self.initial_query, url=self.only_url, image_path=image_path, url_image=image_url ,content=content
            )

            final_answer = ""
            for part in summary_stream:
                if part is not None:
                    final_answer += part
                    live.update(Markdown(f"\n{final_answer}"))

            # # Xử lý TTS
            # output_file = "assets/infore/clip.wav"
            # word_count = len(final_answer.split())
            # tts_thread = None
            # if word_count <= 500:
            #     if not pygame.mixer.music.get_busy():
            #         success = run_viettts_synthesis(text=final_answer, output=output_file)
            #         if success:
            #             tts_thread = threading.Thread(
            #                 target=self.play_speech, args=(output_file,), daemon=True
            #             )
            #             tts_thread.start()
            #     else:
            #         console.print("")


        self.history_analys.append(final_answer)
        # return final_answer, tts_thread
        return final_answer

    def extract_music_url(self, query: str) -> str:
        """Trích xuất URL nhạc từ query."""
        music_pattern = r"@m<([^>]+)>"  # Biểu thức chính quy để tìm @m<tên bài hát>
        match = re.search(music_pattern, query)
        return match.group(1).strip() if match else ""

    def run_chat(self) -> str:
        # final_answer, tts_thread = self.chat()
        final_answer= self.chat()
        self.history_analys.clear()
        return f"\n{final_answer}"
