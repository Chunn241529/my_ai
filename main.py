import os
import shutil
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

# Import scripts
from functions.subfuncs.commands import process_shutdown_command
from functions.subfuncs.file import process_file_read
from functions.subfuncs.image import *
from functions.deepsearch import DeepSearch
from functions.deepthink import DeepThink
from functions.generate import query_ollama

# Khởi tạo console từ Rich
console = Console()

# Định nghĩa style cho prompt với màu vàng nhạt
prompt_style = Style.from_dict({"": "fg:#ffff99 bold"})

# Khởi tạo PromptSession với style
prompt_session = PromptSession("\n>>> ", style=prompt_style, prompt_continuation="")

# Biến trạng thái cho các chế độ
deep_search_active = False
deep_think_active = False

def delete_pycache(directory):
    """Xóa các thư mục __pycache__ trong thư mục chỉ định và trả về số lượng đã xóa."""
    count = 0
    try:
        for root, dirs, files in os.walk(directory):
            for dir in dirs:
                if dir == "__pycache__":
                    shutil.rmtree(os.path.join(root, dir))
                    count += 1
    except Exception as e:
        console.print(f"[bold red]Lỗi khi xóa __pycache__: {e}[/bold red]")
    return count

def display_welcome():
    ascii_art = """
╔╦╗┬─┐┬ ┬┌┐┌╔═╗╔═╗╔╦╗  ╔═╗╦  ╦
 ║ ├┬┘│ ││││║ ╦╠═╝ ║   ║  ║  ║
 ╩ ┴└─└─┘┘└┘╚═╝╩   ╩   ╚═╝╩═╝╩
    """
    console.print(ascii_art, style="bold cyan", justify="left")
    console.print("")  # Khoảng cách
    console.print("Gõ [bold magenta]!bye[/bold magenta] để thoát.")
    console.print("Gõ [bold yellow]!ds_on[/bold yellow] để bật tìm kiếm sâu, [bold yellow]!ds_off[/bold yellow] để tắt.")
    console.print("Gõ [bold green]!dt_on[/bold green] để bật suy luận sâu, [bold green]!dt_off[/bold green] để tắt.")
    console.print("")  # Khoảng cách

def main():
    global deep_search_active, deep_think_active  # Sử dụng biến toàn cục

    while True:
        try:
            user_input = prompt_session.prompt()
            console.print("\n")
            if user_input.lower() == "!bye":
                break

            # Xử lý toggle cho Deep Search
            if user_input.lower() == "!ds_on":
                deep_search_active = True
                console.clear()
                display_welcome()
                console.print("[bold yellow]Chế độ Deep Search đã được bật.[/bold yellow]")
                continue
            elif user_input.lower() == "!ds_off":
                deep_search_active = False
                console.clear()
                display_welcome()
                console.print("[bold yellow]Chế độ Deep Search đã được tắt.[/bold yellow]")
                continue

            # Xử lý toggle cho Deep Think
            elif user_input.lower() == "!dt_on":
                deep_think_active = True
                console.clear()
                display_welcome()
                console.print("[bold green]Chế độ Deep Think đã được bật.[/bold green]")
                continue
            elif user_input.lower() == "!dt_off":
                deep_think_active = False
                console.clear()
                display_welcome()
                console.print("[bold green]Chế độ Deep Think đã được tắt.[/bold green]")
                continue

            # Xử lý đầu vào dựa trên chế độ
            if deep_search_active:
                deep_search = DeepSearch(user_input)
                full_response = deep_search.run()
            elif deep_think_active:
                deep_think = DeepThink(user_input)
                full_response = deep_think.run_think()
            else:
                user_input = process_file_read(user_input)
                response_stream = query_ollama(user_input)
                status_text = "Chờ xíu...\n"
                with Live(
                    Markdown(status_text),
                    refresh_per_second=10,
                    console=console,
                    vertical_overflow="visible",
                ) as live:
                    full_response = ""
                    for part in response_stream:
                        if part is not None:
                            full_response += part
                            live.update(Markdown(f"\n{full_response}"))
                console.print("\n\n")
                process_shutdown_command(full_response)

        except Exception as e:
            console.print(f"[bold red]Đã xảy ra lỗi: {e}[/bold red]")

if __name__ == "__main__":
    cache_count = delete_pycache(os.getcwd())
    if cache_count > 0:
        console.print(f"[bold green]Đã xóa {cache_count} thư mục __pycache__.[/bold green]")
    else:
        console.print("[bold green]Không tìm thấy __pycache__ để xóa.[/bold green]")
    time.sleep(0.5)
    console.clear()
    display_welcome()
    main()