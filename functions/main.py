import shutil
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import track
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

# import scripts
from commands import *
from file import *
from image import *
from deepsearch import *
from generate import *

def delete_pycache(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            if dir == '__pycache__':
                shutil.rmtree(os.path.join(root, dir))
                count += 1
    return count  # Trả về số thư mục __pycache__ đã xóa


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
    prompt_continuation=""  # Tùy chọn: Dòng tiếp theo nếu nhập nhiều dòng
)

# URL của Ollama API



def main():
    console.clear()
    console.print("[bold cyan]Chào mừng đến với TrunGPT CLI![/bold cyan]")
    console.print("Gõ '!bye' để thoát. Gõ '!ds' để tìm kiếm sâu.\n")

    while True:
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
            result = deepsearch(query)
            full_response = ""
            with console.status("[bold green][/bold green]", spinner="dots"):
                for part in result:
                    if part is not None:
                        full_response += part
                        # os.system("clear")
                        # console.print(Markdown(full_response), soft_wrap=True)

            # os.system("clear")
            console.print(Markdown(full_response), soft_wrap=True)
            console.print("\n\n")
            message_history.append({"role": "assistant", "content": full_response})

        else:
            user_input = process_file_read(user_input)
            response_stream = query_ollama(user_input)
            full_response = ""
            with console.status("[bold green][/bold green]", spinner="dots"):
                for part in response_stream:
                    if part is not None:
                        full_response += part
                        # os.system("clear")
                        # console.print(Markdown(full_response), soft_wrap=True, end="")

            # os.system("clear")
            console.print(Markdown(full_response), soft_wrap=True, end="")
            console.print("\n\n")
            process_shutdown_command(full_response)
            message_history.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    for i in track(range(delete_pycache(os.getcwd())),description="Xóa cache..."):
        time.sleep(0.01)
    console.clear()
    main()