import logging
import os
import platform
import time
import queue
import re
import threading
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live



# Giả định các module này đã được định nghĩa
from cli.functions.subfuncs.commands import *
from cli.functions.subfuncs.file import *
from cli.functions.subfuncs.generate import *
from cli.functions.subfuncs.image import genImage  # Import genImge từ image.py

console = Console()

# Suppress all logging from sentence_transformers and datasets
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("datasets").setLevel(logging.ERROR)


class ChatImage:
    def __init__(self, initial_query: str):
        self.initial_query = initial_query
        self.refresh_second = 10
        self.vertical_overflow = "ellipsis"
        os.environ["JAX_PLATFORM_NAME"] = "cpu"


    def generate_image_in_thread(self, prompt, result_queue):
        """Chạy genImge trong một luồng riêng và đặt kết quả vào queue."""
        try:
            image_paths = genImage(prompt)
            image_path = image_paths if isinstance(image_paths, str) else image_paths[0]
            if not image_path or not os.path.exists(image_path):
                raise ValueError(f"Đường dẫn ảnh không hợp lệ: {image_path}")
            result_queue.put(("success", image_path))
        except Exception as e:
            error_msg = f"Lỗi trong generate_image_in_thread: {str(e)}"
            console.print(f"[bold red]{error_msg}[/bold red]")
            result_queue.put(("error", str(e)))

    def open_image(self, file_path):
        try:
            system = platform.system()
            if system == "Linux":
                os.system(f"xdg-open {file_path}")
            elif system == "Windows":
                os.system(f"start {file_path}")
            elif system == "Darwin":
                os.system(f"open {file_path}")
        except Exception:
            pass  # Không hiển thị lỗi khi mở ảnh thất bại

    def chat_image(self) -> str:
        with Live(
            Markdown("\nĐang tạo prompt...🖌️\n"),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
            analys_stream = image_chat_(query=self.initial_query)
            analys = ""
            for part in analys_stream:
                if part:
                    analys += part
                    live.update(Markdown(f"\n{analys}"))

            # Tạo prompt dựa trên description từ retrieve_prompts
            prompt_sd = generate_image(
                query=analys,  # Sử dụng description thay vì initial_query
            )
            generate_prompt = ""
            for part in prompt_sd:
                if part is not None:
                    generate_prompt += part

        result_queue = queue.Queue()
        image_thread = threading.Thread(
            target=self.generate_image_in_thread,
            args=(generate_prompt, result_queue),
        )
        image_thread.start()

        console.print("\n")
        image_path = ""
        error_msg = ""

        while image_thread.is_alive():
            try:
                result_type, result = result_queue.get(block=True, timeout=0.5)
                if result_type == "success":
                    image_path = result
                else:
                    error_msg = f"Lỗi khi tạo ảnh: {result}"
                break
            except queue.Empty:
                time.sleep(0.1)

        if not image_path and not error_msg:
            try:
                result_type, result = result_queue.get(block=False)
                if result_type == "success":
                    image_path = result
                else:
                    error_msg = f"Lỗi khi tạo ảnh: {result}"
            except queue.Empty:
                error_msg = "Lỗi: Không nhận được kết quả từ quá trình tạo ảnh."

        if image_path and not os.path.exists(image_path):
            error_msg = f"Đường dẫn ảnh {image_path} không tồn tại."
            image_path = ""

        if error_msg:
            live.update(Markdown(f"\n{error_msg}"))
            console.print(f"[bold red]{error_msg}[/bold red]")
            return error_msg

        if image_path:
            live.update("")

            self.open_image(image_path)
            console.clear()


    def run_chat_image(self) -> str:
        final_answer = self.chat_image()
        return f"\n{final_answer}"
