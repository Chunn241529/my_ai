import requests
import json
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

import os
# import scripts
from commands import *
from file import *
from image import *
from deepsearch import *
from generate import *

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
    prompt_continuation="... "  # Tùy chọn: Dòng tiếp theo nếu nhập nhiều dòng
)

# URL của Ollama API



def main():
    console.print("[bold cyan]Chào mừng đến với Ollama CLI![/bold cyan]")
    console.print("Gõ '!bye' để thoát. Gõ '!deepsearch' để tìm kiếm sâu.\n")

    while True:
        user_input = prompt_session.prompt()
        if user_input.lower() == "!bye":
            break

        # Kiểm tra lệnh !deepsearch
        if user_input.lower().startswith("!deepsearch"):
            query = user_input[len("!deepsearch"):].strip()
            if not query:
                console.print("[bold red]Vui lòng nhập câu hỏi sau '!deepsearch'. Ví dụ: !deepsearch Câu hỏi của bạn[/bold red]")
                continue
            result = deepsearch(query)
            full_response = ""
            with console.status("[bold green][/bold green]", spinner="dots"):
                for part in result:
                    if part is not None:
                        full_response += part
                        os.system("clear")
                        console.print(Markdown(full_response), soft_wrap=True, end="")

            os.system("clear")
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
                        os.system("clear")
                        console.print(Markdown(full_response), soft_wrap=True, end="")

            os.system("clear")
            console.print(Markdown(full_response), soft_wrap=True)
            console.print("\n\n")
            message_history.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()