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
from functions.chat import Chat
from functions.subfuncs.commands import process_shutdown_command
from functions.subfuncs.file import process_file_read
from functions.subfuncs.image import *
from functions.deepsearch import DeepSearch
from functions.deepthink import DeepThink

console = Console()
prompt_style = Style.from_dict({"": "fg:#ffff99 bold"})
prompt_session = PromptSession("\n>>> ", style=prompt_style, prompt_continuation="")

deep_search_active = False
deep_think_active = False

prefix="/"
command_deepthink = f"{prefix}dt"
command_deepsearch = f"{prefix}ds"
command_bye= f"{prefix}bye"

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
    console.print(f"Gõ [bold magenta]{command_bye}[/bold magenta] để thoát.")
    console.print(f"Gõ [bold yellow]{command_deepsearch}on[/bold yellow] để bật tìm kiếm sâu, [bold yellow]{command_deepsearch}off[/bold yellow] để tắt.")
    console.print(f"Gõ [bold green]{command_deepthink}on[/bold green] để bật suy luận sâu, [bold green]{command_deepthink}off[/bold green] để tắt.")
    console.print("")  # Khoảng cách


def toggle_deep_search(state: bool) -> None:
    """Bật/tắt chế độ Deep Search"""
    global deep_search_active
    deep_search_active = state

    status = "bật" if state else "tắt"
    console.print(f"[bold yellow]Chế độ Deep Search đang được {status}.[/bold yellow]")

def toggle_deep_think(state: bool) -> None:
    """Bật/tắt chế độ Deep Think"""
    global deep_think_active
    deep_think_active = state

    status = "bật" if state else "tắt"
    console.print(f"[bold green]Chế độ Deep Think đang được {status}.[/bold green]")

def main():
    global deep_search_active, deep_think_active  # Sử dụng biến toàn cục

    while True:
        try:
            user_input = prompt_session.prompt()
            console.print("\n")
            if user_input.lower() == f"{command_bye}":
                break

            # Xử lý toggle cho Deep Search
            if user_input.lower() == f"{command_deepsearch}on":
                console.clear()
                display_welcome()   
                toggle_deep_search(True)
                continue
            elif user_input.lower() == f"{command_deepsearch}off":
                console.clear()
                display_welcome() 
                toggle_deep_search(False)
                continue

            # Xử lý toggle cho Deep Think
            elif user_input.lower() == f"{command_deepthink}on":
                console.clear()
                display_welcome() 
                toggle_deep_think(True)
                continue
            elif user_input.lower() == f"{command_deepthink}off":
                console.clear()
                display_welcome() 
                toggle_deep_think(False)
                continue

            # Xử lý đầu vào dựa trên chế độ
            if deep_search_active:
                _ = process_file_read(user_input)
                deep_search = DeepSearch(_)
                full_response = deep_search.run()
                console.print("\n\n")
                toggle_deep_search(deep_search_active)
            elif deep_think_active:
                _ = process_file_read(user_input)
                deep_think = DeepThink(_)
                full_response = deep_think.run_think()
                console.print("\n\n")
                toggle_deep_think(deep_think_active)
            else:
                _ = process_file_read(user_input)
                chat = Chat(_)
                full_response = chat.run_chat()
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