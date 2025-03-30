
from duckduckgo_search import DDGS

import requests
import json


# import scripts
from commands import *
from file import *
from image import *
from generate import *

# Khởi tạo console từ Rich
console = Console()


# URL của Ollama API
OLLAMA_API_URL = "http://localhost:11434/api/generate"

model_gemma = "gemma3:latest"
model_qwen = "qwen2.5-coder:latest"

model_curent = model_gemma

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


def query_ollama(prompt, model=model_curent):
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


def analys_question(query):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = f"""
    Phân tích câu hỏi: '{query}'.  
    - Không trả lời trực tiếp câu hỏi.  
    - Chỉ tập trung vào:  
      * Ý định của người dùng (họ muốn gì?).  
      * Các cách hiểu khác nhau của câu hỏi.  
    - Đi thẳng vào phân tích, không thêm lời nhận xét hoặc mở đầu thừa thãi.  
    - Giữ giọng điệu tự nhiên, ngắn gọn. Ví dụ: 'Câu "{query}" cho thấy người dùng muốn [ý định]. Nó cũng có thể được hiểu là [cách hiểu khác].'\n
    - Nếu câu hỏi Không khả thi, hãy trả lời "Khó nha bro..."
    """
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 1000,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.7,  # Giảm để giảm ngẫu nhiên
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None


def reason_with_ollama(query, context):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = (
        f"Câu hỏi chính: {query}\n"
        f"Thông tin: {context}\n"
        f"Hãy reasoning và trả lời trực tiếp câu hỏi chính '{query}' dựa trên thông tin được cung cấp. Thực hiện theo các bước sau:\n"
        f"1. Phân tích thông tin: Xác định các dữ kiện quan trọng liên quan trực tiếp đến câu hỏi.\n"
        f"2. Suy luận logic: Dựa trên các dữ kiện đã phân tích, đưa ra lập luận hợp lý để trả lời câu hỏi.\n"
    )
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": -1,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.7,  # Giảm temperature để tăng tính logic và chính xác
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None

def evaluate_answer(query, answer):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    eval_prompt = (
        f"Câu trả lời: {answer}\n"
        f"Câu ban đầu: {query}\n"
        f"Câu trả lời này đã đủ để trả lời đầy đủ Câu ban đầu chưa? \n"
        f"Trả lời bắt đầu bằng 'Đã đủ' nếu thông tin đầy đủ, hoặc 'Chưa đủ' nếu thiếu thông tin cần thiết. \n"
        f"Nếu 'Đã đủ', không thêm gì nữa. \n"
        f"Nếu 'Chưa đủ', thêm phần 'Đề xuất truy vấn:' với CHỈ 1 truy vấn cụ thể bằng tiếng Anh, ngắn gọn, dạng câu lệnh tìm kiếm (không phải câu hỏi), liên quan trực tiếp đến Câu ban đầu, theo định dạng:\n"
        f"Đề xuất truy vấn:\n* \"từ khóa hoặc cụm từ tìm kiếm cụ thể\"\n"
        f"Ví dụ:\nChưa đủ\nĐề xuất truy vấn:\n* \"details about {query}\"\n"
        f"Đảm bảo luôn bắt đầu bằng 'Đã đủ' hoặc 'Chưa đủ', và truy vấn phải là cụm từ tìm kiếm, không phải câu hỏi."
    )

    payload = {
        "model": model_curent,
        "prompt": eval_prompt,
        "stream": True,
        "options": {
            "num_predict": -1,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.9,
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None

def summarize_answers(query, all_answers):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    summary_prompt = f"""
    Câu hỏi chính: '{query}'  
    Các thông tin đã thu thập: {'\n'.join([f'- {a}' for a in all_answers])}  
    Tổng hợp tất cả thông tin trên thành một câu trả lời đầy đủ nhất cho câu hỏi '{query}'.  
    - Tập trung vào trọng tâm của câu hỏi.   
    - Sử dụng giọng điệu tự nhiên, dễ hiểu.  
    Ví dụ: Nếu câu hỏi là 'Làm sao để học tiếng Anh nhanh?' và thông tin gồm: 'Học từ vựng mỗi ngày', 'Xem phim tiếng Anh', thì tổng hợp thành: 'Để học tiếng Anh nhanh, bạn nên học từ vựng mỗi ngày và xem phim tiếng Anh thường xuyên.'  
    """
    payload = {
        "model": model_curent,
        "prompt": summary_prompt,
        "stream": True,
        "options": {
            "num_predict": -1,  # Giới hạn độ dài để ngắn gọn
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.5,  # Giảm để tăng tính logic
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None


def analys_prompt(query):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = f"From the given query, translate it to English if necessary, then provide exactly one concise English search query (no explanations, no extra options) that a user would use to find relevant information on the web. Query: {query}"

    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": -1,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.9,
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None


def process_link(query, url, content, keywords):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = (
        f"Nội dung từ {url}:\n{content[:12000]}\n"
        f"Tập trung vào các từ khóa: {', '.join(keywords)}.\n"
        f"Hãy suy luận và trả lời câu hỏi '{query}' dựa trên nội dung được cung cấp, thực hiện theo các bước sau:\n"
        f"1. Phân tích nội dung: Xác định các thông tin quan trọng liên quan đến từ khóa và câu hỏi. Lưu ý các dữ kiện cụ thể, số liệu, hoặc ý chính.\n"
        f"2. Liên kết với từ khóa: Đánh giá cách các từ khóa xuất hiện trong nội dung và ý nghĩa của chúng đối với câu hỏi.\n"
        f"3. Suy luận logic: Dựa trên thông tin đã phân tích, đưa ra lập luận hợp lý để giải quyết câu hỏi. Nếu cần, hãy so sánh, đối chiếu hoặc suy ra từ các dữ kiện.\n"
    )    
    
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 4000,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.5,  # Giảm temperature để tăng tính logic
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None

def generate_keywords(query, context="", history_keywords=None):
    if history_keywords is None:
        history_keywords = set()
    prompt = (
        f"Câu hỏi: {query}\nThông tin hiện có: {context[:2000]}\n"
        f"Lịch sử từ khóa đã dùng: {', '.join(history_keywords)}\n"
        f"Hãy suy luận và tạo 2-3 từ khóa mới, không trùng với lịch sử, liên quan đến câu hỏi. "
        f"Trả về dưới dạng danh sách: * \"từ khóa 1\" * \"từ khóa 2\" * \"từ khóa 3\"."
    )
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 500,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 0.9,
        }
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
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi API Ollama: {e}")
        yield None
    