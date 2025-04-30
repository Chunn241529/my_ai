import os
import re
import shutil
import threading
import time
from typing import Union
import pygame
from rich.console import Console
from rich.progress import Progress
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

# Import scripts
from cli.functions.subfuncs.file import process_file_read
from cli.functions.chat import Chat
from cli.functions.deepsearch import DeepSearch
from cli.functions.deepthink import DeepThink
from cli.functions.img import ChatImage
from cli.functions.subfuncs.image import *
from cli.functions.subfuncs.music import play_music, add_to_queue, play_next, toggle_loop

console = Console()
prompt_style = Style.from_dict({"": "fg:#ffff99 bold"})
prompt_session = PromptSession("\n>>> ", style=prompt_style, prompt_continuation="")

deep_search_active = False
deep_think_active = False

prefix = "/"
command_deepthink = f"{prefix}deepthink"
command_deepsearch = f"{prefix}deepsearch"
command_bye = f"{prefix}bye"

def delete_pycache(directory):
    """Xóa các thư mục __pycache__ trong thư mục chỉ định và trả về số lượng đã xóa."""
    count = 0
    total_dirs = sum(1 for _ in os.walk(directory))  # Count total directories to scan
    try:
        torch.cuda.empty_cache()
        console.print("[bold green]empty cache CUDA[/bold green]")
        with Progress() as progress:
            task = progress.add_task(
                "[cyan]Scanning and deleting __pycache__...", total=total_dirs
            )
            for root, dirs, files in os.walk(directory):
                for dir in dirs:
                    if dir == "__pycache__":
                        shutil.rmtree(os.path.join(root, dir))
                        count += 1
                        progress.update(
                            task,
                            advance=1,
                            description=f"[cyan]Deleted {count} __pycache__ folders",
                        )
                progress.update(task, advance=1)
    except Exception as e:
        console.print(f"[bold red]Lỗi khi xóa __pycache__: {e}[/bold red]")
    return count

def display_welcome():
    ascii_art = """
╔╦╗┬─┐┬ ┬┌┐┌╔═╗╔═╗╔╦╗
 ║ ├┬┘│ ││││║ ╦╠═╝ ║
 ╩ ┴└─└─┘┘└┘╚═╝╩   ╩
    """
    console.print(ascii_art, style="bold cyan", justify="left")
    console.print("")  # Khoảng cách
    console.print(f"Gõ [bold magenta]{command_bye}[/bold magenta] để thoát.")
    console.print(
        f"Gõ [bold yellow]{command_deepsearch}[/bold yellow] để bật/tắt tìm kiếm sâu."
    )
    console.print(
        f"Gõ [bold green]{command_deepthink}[/bold green] để bật/tắt suy luận sâu."
    )
    console.print(
        f"Gõ [bold green]Tạo ảnh <mô tả>[/bold green] để tạo hình ảnh. [bold yellow]Ví dụ: Tạo ảnh con mèo đang ngủ[/bold yellow]"
    )
    console.print(
        f"Gõ [bold green]@r<file path>[/bold green] để lấy nội dung file. [bold yellow]Ví dụ: Hãy ghi lại nội dung trong @r<readme.md>[/bold yellow]"
    )
    console.print(
        f"Gõ [bold green]@m<song>[/bold green] để phát nhạc (hoặc thêm vào hàng chờ nếu đang phát), [bold green]@m_l[/bold green] để bật/tắt lặp lại."
    )
    console.print("")  # Khoảng cách

def toggle_deep_search() -> None:
    """Bật/tắt chế độ Deep Search"""
    global deep_search_active
    deep_search_active = not deep_search_active
    status = "bật" if deep_search_active else "tắt"
    console.print(f"[bold yellow]Chế độ nghiên cứu sâu đã được {status}.[/bold yellow]")

def toggle_deep_think() -> None:
    """Bật/tắt chế độ Deep Think"""
    global deep_think_active
    deep_think_active = not deep_think_active
    status = "bật" if deep_think_active else "tắt"
    console.print(f"[bold green]Chế độ suy luận sâu đã được {status}.[/bold green]")

def display_typing_effect(message: str, delay: Union[int, float]):
    for i in range(len(message) + 1):
        console.print(f"[bold yellow]{message[:i]}[/bold yellow]", end="\r")
        time.sleep(0.01)
    time.sleep(delay)
    for i in range(len(message), -1, -1):
        console.print(
            f"[bold yellow]{message[:i]}[/bold yellow]" + " " * (len(message) - i),
            end="\r",
        )
        time.sleep(0.01)

def extract_music_command(query: str):
    """Trích xuất lệnh nhạc từ query."""
    play_pattern = r"@m<([^>]+)>"  # Phát nhạc hoặc thêm vào hàng chờ
    loop_pattern = r"@m_l"  # Bật/tắt lặp lại

    if re.match(loop_pattern, query):
        return "loop", None
    match_play = re.search(play_pattern, query)
    if match_play:
        return "play", match_play.group(1).strip()
    return None, query

def main():
    global deep_search_active, deep_think_active
    pygame.mixer.init()  # Khởi tạo mixer để kiểm tra trạng thái nhạc
    console.clear()
    display_welcome()

    # Thread để kiểm tra và phát bài tiếp theo
    def music_monitor():
        while True:
            pygame.time.Clock().tick(10)  # Giới hạn tốc độ vòng lặp
            play_next()  # Kiểm tra và phát bài tiếp theo khi cần
            time.sleep(0.1)  # Giảm tải CPU

    music_thread = threading.Thread(target=music_monitor, daemon=True)
    music_thread.start()

    while True:
        try:
            user_input = prompt_session.prompt()
            while not user_input.strip():
                console.print("\n")
                display_typing_effect("Vui lòng nhập nội dung, không để trống!", 0.5)
                console.clear()
                display_welcome()
                user_input = prompt_session.prompt()

            console.print("\n")
            if user_input.lower() == f"{command_bye}":
                pygame.mixer.music.stop()  # Dừng nhạc trước khi thoát
                break

            if user_input.lower() == f"{command_deepsearch}":
                console.clear()
                display_welcome()
                toggle_deep_search()
                continue
            elif user_input.lower() == f"{command_deepthink}":
                console.clear()
                display_welcome()
                toggle_deep_think()
                continue

            # Xử lý lệnh nhạc
            command, value = extract_music_command(user_input)
            if command == "play" and value:
                if pygame.mixer.music.get_busy():  # Nếu đang phát nhạc
                    add_to_queue(value)
                else:  # Nếu không có nhạc đang phát
                    play_music(value)
                continue
            elif command == "loop":
                toggle_loop()
                continue

            # Xử lý đầu vào dựa trên chế độ
            if user_input.lower().startswith("tạo ảnh") or user_input.lower().startswith("tạo hình ảnh"):
                console.clear()
                # Extract the description after the trigger
                if user_input.lower().startswith("tạo ảnh"):
                    description = user_input[7:].strip() if len(user_input) > 7 else ""
                else:  # "tạo hình ảnh"
                    description = user_input[12:].strip() if len(user_input) > 12 else ""
                if not description:
                    console.print("[bold red]Vui lòng cung cấp mô tả cho hình ảnh![/bold red]")
                    continue
                _ = process_file_read(description)
                gen_img = ChatImage(_)
                full_response = gen_img.run_chat_image()
                console.print("\n\n")
            elif deep_search_active:
                console.clear()
                _ = process_file_read(user_input)
                deep_search = DeepSearch(_)
                full_response = deep_search.run()
                console.print("\n\n")
            elif deep_think_active:
                console.clear()
                _ = process_file_read(user_input)
                deep_think = DeepThink(_)
                full_response = deep_think.run_think()
                console.print("\n\n")
            else:
                console.clear()
                _ = process_file_read(user_input)
                chat = Chat(_)
                full_response = chat.run_chat()

        except Exception as e:
            console.print(f"[bold red]Đã xảy ra lỗi: {e}[/bold red]")

if __name__ == "__main__":
    import os

    os.environ["JAX_PLATFORM_NAME"] = "cpu"  # Buộc J tendenza dùng CPU
    cache_count = delete_pycache(os.getcwd())

    if cache_count > 0:
        console.print(
            f"[bold green]Đã xóa {cache_count} thư mục __pycache__.[/bold green]"
        )
    else:
        console.print("[bold green]Không tìm thấy __pycache__ để xóa.[/bold green]")
    time.sleep(0.5)
    main()
