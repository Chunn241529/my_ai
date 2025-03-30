
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



def reason_with_ollama(query, context):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = f"Câu hỏi chính: {query}\nThông tin: {context}\nHãy suy luận và trả lời trực tiếp câu hỏi chính {query}. Tập trung hoàn toàn vào trọng tâm câu hỏi, bỏ qua thông tin không liên quan."
    payload = {
        "model": model_gemma,
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

def evaluate_answer(query, answer):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    eval_prompt = f"Câu hỏi chính: {query}\nCâu trả lời: {answer}\nCâu trả lời này đã đủ để đưa ra câu trả lời cho Câu hỏi chính: {query} chưa? Đầu tiên, trả lời 'Đã đủ' nếu câu trả lời cung cấp đầy đủ câu trả lời cho Câu hỏi chính: {query}, hoặc 'Chưa đủ' nếu thiếu thông tin cần thiết. Nếu 'Đã đủ', không đề xuất gì thêm. Nếu 'Chưa đủ', đề xuất CHỈ 1 truy vấn cụ thể, liên quan trực tiếp đến Câu hỏi chính: {query}, trong phần 'Đề xuất truy vấn:' với định dạng:\nĐề xuất truy vấn:\n* \"truy vấn\"\nVí dụ:\nChưa đủ\nĐề xuất truy vấn:\n* \"{query}\"\nĐảm bảo luôn bắt đầu bằng 'Đã đủ' hoặc 'Chưa đủ'."
    payload = {
        "model": model_gemma,
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
    # summary_prompt = f"Câu hỏi chính: {query}\nDưới đây là các thông tin đã thu thập:\n" + "\n".join([f"{q}: {a}" for q, a in all_answers.items()]) + f"\nTổng hợp thành một câu trả lời mạch lạc, logic và đầy đủ nhất cho Câu hỏi chính: {query}, tập trung vào trọng tâm."
    summary_prompt = f"Câu hỏi chính: {query}\nDưới đây là các thông tin đã thu thập:\n" + "\n".join([f"{a}" for a in all_answers]) + f"\nTổng hợp thành một câu trả lời mạch lạc, logic và đầy đủ nhất cho Câu hỏi chính: {query}, tập trung vào trọng tâm."
    # console.print(f"\n[red][DEBUG]{summary_prompt}[/red]\n")
    payload = {
        "model": model_gemma,
        "prompt": summary_prompt,
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

def analys_question(query):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = f"Phân tích câu hỏi {query}. Không cần trả lời câu hỏi. *Ví dụ: Ah, người dùng đang muốn '{query}'. Đầu tiên chúng ta sẽ phân tích kỹ câu hỏi của người dùng...*"
    payload = {
        "model": model_gemma,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 4060,
            "top_k": 20,
            "top_p": 0.9,
            "min_p": 0.0,
            "temperature": 1,
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
        "model": model_gemma,
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
        f"Nội dung từ {url}:\n{content[:5000]}\n"
        f"Tập trung vào các từ khóa: {', '.join(keywords)}.\n"
        f"Hãy nghiên cứu nội dung và trả lời câu hỏi chi tiết dựa trên thông tin có sẵn.\n"
        f"Sau đó đưa ra kết luận đầy đủ để trả lời câu hỏi {query} \n"
    )    
    
    payload = {
        "model": model_gemma,
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
        "model": model_gemma,
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
    