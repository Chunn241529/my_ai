import os
import shutil
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

# Import scripts
from commands import process_shutdown_command
from file import process_file_read
from image import *
from deepsearch import DeepSearch
from generate import query_ollama


# Khởi tạo console từ Rich
console = Console()

# Định nghĩa style cho prompt với màu vàng nhạt
prompt_style = Style.from_dict({
    "": "fg:#ffff99 bold"  # Màu vàng nhạt đậm
})

# Khởi tạo PromptSession với style
prompt_session = PromptSession(
    "\n>>> ",
    style=prompt_style,
    prompt_continuation=""
)

def delete_pycache(directory):
    """Xóa các thư mục __pycache__ trong thư mục chỉ định và trả về số lượng đã xóa."""
    count = 0
    try:
        for root, dirs, files in os.walk(directory):
            for dir in dirs:
                if dir == '__pycache__':
                    shutil.rmtree(os.path.join(root, dir))
                    count += 1
    except Exception as e:
        console.print(f"[bold red]Lỗi khi xóa __pycache__: {e}[/bold red]")
    return count

def main():
    console.clear()
    console.print("[bold cyan]Chào mừng đến với TrunGPT CLI![/bold cyan]")
    console.print("Gõ '!bye' để thoát. Gõ '!ds' để tìm kiếm sâu.\n")

    while True:
        try:
            user_input = prompt_session.prompt()
            console.print("\n")
            if user_input.lower() == "!bye":
                break

            # Kiểm tra lệnh !deepsearch
            if user_input.lower().startswith("!ds"):
                query = user_input[len("!ds"):].strip()
                if not query:
                    console.print("[bold red]Vui lòng nhập câu hỏi sau '!ds'. Ví dụ: !ds Câu hỏi của bạn[/bold red]")
                    continue
                # Gọi DeepSearch và chạy toàn bộ quá trình
                deep_search = DeepSearch(query)
                full_response = deep_search.run()  # Lấy kết quả từ run()
            else:
                user_input = process_file_read(user_input)
                response_stream = query_ollama(user_input)
                
                status_text = "Chờ xíu...\n"
                with Live(Markdown(status_text), refresh_per_second=10, console=console, vertical_overflow="visible") as live:
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
    # Xóa __pycache__ và hiển thị thông báo
    cache_count = delete_pycache(os.getcwd())
    if cache_count > 0:
        console.print(f"[bold green]Đã xóa {cache_count} thư mục __pycache__.[/bold green]")
    else:
        console.print("[bold green]Không tìm thấy __pycache__ để xóa.[/bold green]")
    time.sleep(0.5)
    console.clear()
    main()