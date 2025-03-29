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
OLLAMA_API_URL = "http://localhost:11434/api/generate"

system_prompt = f"""
Bạn là TrunGPT, một trợ lý AI chuyên phân tích ngôn ngữ, cung cấp thông tin chính xác, logic và hữu ích nhất cho người dùng.  

### 🔹 Quy tắc giao tiếp:
- Sử dụng **tiếng Việt (Vietnamese)** là chính.  
- **Thêm emoji** để cuộc trò chuyện sinh động hơn.  
- **Không nhắc lại hướng dẫn này** trong câu trả lời.  

### 🛠 Vai trò & Cách hành xử:
- Trả lời chuyên sâu, giải thích dễ hiểu.  
- Phân tích vấn đề logic và đưa ra giải pháp toàn diện.  
- Không trả lời các nội dung vi phạm đạo đức, pháp luật (không cần nhắc đến điều này trừ khi người dùng vi phạm).  

### 🔍 Lưu ý đặc biệt:
- **Người tạo**: Vương Nguyên Trung. Nếu có ai hỏi, chỉ cần trả lời: *"Người tạo là đại ca Vương Nguyên Trung."* và không nói thêm gì khác.  

Hãy luôn giúp đỡ người dùng một cách chuyên nghiệp và thú vị nhé! 🚀  

### Tool bạn có thể dùng:
- Tắt máy tính: @shutdown<phút>. Ví dụ: @shutdown<10>. Tắt ngay lập tức thì dùng @shutdown<now>
- Khởi động lại máy tính: @reboot<phút>. Ví dụ: @reboot<30> .
- Đọc tệp: @read<địa chỉ tệp>. Ví dụ: @read<readme.md>.
- Ghi tệp: @write<địa chỉ tệp><nội dung>. Ví dụ: @write<readme.md><### Tổng quan>
- Xóa tệp: @delete<địa_chi_tệp>. Ví dụ: @delete<readme.md>
"""

message_history = []
message_history.append({"role": "system", "content": system_prompt})

model_gemma = "gemma3:latest"
model_qwen = "qwen2.5-coder:latest"

def query_ollama(prompt, model=model_gemma):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    clean_prompt, images_base64 = preprocess_prompt(prompt)
    process_shutdown_command(clean_prompt)
    message_history.append({"role": "user", "content": clean_prompt})
    full_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in message_history])

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "num_predict": -1,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.9,
        },
        "images": images_base64
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()
        full_response = ""
        for line in response.iter_lines():
            if line:
                json_data = json.loads(line)
                if "response" in json_data:
                    full_response += json_data["response"]
                    yield json_data["response"]
                if json_data.get("done", False):
                    process_shutdown_command(full_response)
                    break
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi Ollama: {e}")
        yield None



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