
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
            "temperature": 1,
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
        Xét câu hỏi: '{query}'.  
        - Nếu câu hỏi không đủ rõ, vô lý, hoặc không thể suy luận (ví dụ: "Mùi của mưa nặng bao nhiêu?"), trả về: "Khó nha bro, [lý do ngắn gọn tự nhiên]."  
        - Nếu câu hỏi có thể suy luận được:  
            1. Tạo keyword: Lấy 2-4 từ khóa chính từ câu hỏi (ngắn gọn, sát nghĩa). * Không cần show ra cho người dùng thấy.  
            2. Phân tích từng keyword: Mỗi từ khóa gợi lên ý gì? Liên quan thế nào đến ý định người dùng?  
            3. Tổng hợp:  
                * Ý định: Người dùng muốn gì? (thông tin, giải pháp, hay gì khác)  
                * Cách hiểu: Câu hỏi có thể diễn giải thế nào?  
            Reasoning và viết ngắn gọn, tự nhiên, không trả lời trực tiếp, ví dụ:  
            'Keyword: [từ khóa 1] - [phân tích], [từ khóa 2] - [phân tích]. Người dùng muốn [ý định], câu này cũng có thể hiểu là [cách hiểu].'  
    """
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 500,
            "temperature": 0.4,  # Giảm để giảm ngẫu nhiên
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
            "num_predict": 200,
            "temperature": 0.4,
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


def process_link(query, url, content):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    prompt = (
        f"Nội dung từ {url}:\n{content}\n"
        f"Hãy suy luận và trả lời câu hỏi '{query}' dựa trên nội dung được cung cấp, thực hiện theo các bước sau:\n"
        f"* Phân tích nội dung và trích xuất các thông tin quan trọng liên quan đến từ khóa và câu hỏi. Lưu ý các dữ kiện cụ thể (số liệu, sự kiện), bối cảnh, và ý chính. Xem xét cả những chi tiết ngầm hiểu hoặc không được nói trực tiếp.\n"
        f"* Dựa trên thông tin đã phân tích, xây dựng lập luận chi tiết để trả lời câu hỏi. Hãy:\n"
        f"   - So sánh và đối chiếu các dữ kiện nếu có mâu thuẫn hoặc nhiều góc nhìn.\n"
        f"   - Suy ra từ những gì không được nói rõ, nếu nội dung gợi ý điều đó.\n"
        f"   - Đưa ra giả định hợp lý (nếu thiếu dữ liệu) và giải thích tại sao giả định đó có cơ sở.\n"
        f"   - Nếu có thể, dự đoán hoặc mở rộng suy luận để làm rõ thêm ý nghĩa của câu trả lời.\n"
        f"* Viết câu trả lời đầy đủ, tự nhiên, dựa hoàn toàn trên nội dung và suy luận, không thêm thông tin ngoài.\n"
    )
    
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 4000,
            "temperature": 0.5,
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
        f"Hãy reasoning và trả lời trực tiếp câu hỏi chính '{query}' dựa trên thông tin được cung cấp. Thực hiện theo các bước sau, nhưng không hiển thị số bước hay tiêu đề trong câu trả lời:\n"
        f"- Tìm các dữ kiện quan trọng trong thông tin, bao gồm cả chi tiết cụ thể (số liệu, sự kiện) và ý nghĩa ngầm hiểu nếu có.\n"
        f"- Dựa trên dữ kiện, xây dựng lập luận hợp lý bằng cách liên kết các thông tin với nhau; nếu thiếu dữ liệu, đưa ra suy đoán có cơ sở và giải thích; xem xét các khả năng khác nhau nếu phù hợp, rồi chọn hướng trả lời tốt nhất.\n"
        f"- Cuối cùng, trả lời ngắn gọn, rõ ràng, đúng trọng tâm câu hỏi, dựa hoàn toàn trên lập luận.\n"
        f"Viết tự nhiên, mạch lạc như một đoạn văn liền mạch, chỉ dùng thông tin từ context, không thêm dữ liệu ngoài.\n"
    )
    payload = {
        "model": model_curent,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": 4000,
            "temperature": 0.7,
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

def evaluate_answer(query, answer, processed_urls):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    eval_prompt = (
        f"Câu trả lời: {answer}\n"
        f"Câu ban đầu: {query}\n"
        f"Danh sách URL đã phân tích: {processed_urls}\n"
        f"Nếu URL này trùng với bất kỳ URL nào trong danh sách đã phân tích, trả lời 'Chưa đủ' và không đánh giá thêm.\n"
        f"Hãy đánh giá xem câu trả lời này đã cung cấp đầy đủ thông tin để giải quyết câu ban đầu chưa. "
        f"- 'Đầy đủ' nghĩa là câu trả lời đáp ứng trực tiếp, rõ ràng và không thiếu khía cạnh quan trọng nào của câu hỏi.\n"
        f"- 'Chưa đủ' nghĩa là còn thiếu thông tin cần thiết hoặc không trả lời đúng trọng tâm.\n"
        f"Trả lời bắt đầu bằng 'Đã đủ' nếu thông tin đầy đủ, hoặc 'Chưa đủ' nếu thiếu thông tin cần thiết.\n"
        f"- Nếu 'Đã đủ', chỉ viết 'Đã đủ', không thêm gì nữa.\n"
        f"- Nếu 'Chưa đủ', thêm phần 'Đề xuất truy vấn:' với CHỈ 1 truy vấn cụ thể bằng tiếng Anh, ngắn gọn, dạng cụm từ tìm kiếm (không phải câu hỏi), liên quan trực tiếp đến câu ban đầu, theo định dạng:\n"
        f"Đề xuất truy vấn:\n* \"từ khóa hoặc cụm từ tìm kiếm cụ thể\"\n"
        f"Ví dụ: Nếu câu ban đầu là 'Làm sao để học tiếng Anh nhanh?' và câu trả lời là 'Học từ vựng mỗi ngày', thì:\n"
        f"Chưa đủ\nĐề xuất truy vấn:\n* \"methods to learn English faster\"\n"
        f"Đảm bảo luôn bắt đầu bằng 'Đã đủ' hoặc 'Chưa đủ', và truy vấn phải là cụm từ tìm kiếm, không phải câu hỏi."
    )

    payload = {
        "model": model_curent,
        "prompt": eval_prompt,
        "stream": True,
        "options": {
            "num_predict": 50,
            "temperature": 0.5,
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
        Câu hỏi: '{query}'  
        Thông tin thu thập: {'\n'.join([f'- {a}' for a in all_answers])}  
        Trả lời '{query}' bằng cách:  
        - Suy luận từng thông tin: Ý này nói gì? Liên quan thế nào đến câu hỏi? Loại ý không hợp lệ và giải thích ngắn gọn lý do.  
        - Gộp các ý liên quan thành câu trả lời đầy đủ, đúng trọng tâm.  
        - Sắp xếp logic (theo thời gian, mức độ quan trọng, hoặc chủ đề).  
        - Viết đầy đủ, tự nhiên, như nói với bạn, không dùng tiêu đề hay phân đoạn.  
        - Thêm thông tin bổ sung nếu có (URL, file...).  
    """
    payload = {
        "model": model_curent,
        "prompt": summary_prompt,
        "stream": True,
        "options": {
            "num_predict": -1,  # Giữ 700 để đủ cho reasoning + tổng hợp
            "temperature": 0.8,  # Giữ logic và tự nhiên
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

def better_question(query):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    summary_prompt = f"""
        Câu hỏi gốc: '{query}'  
        Xét kỹ câu hỏi này: Nó thiếu gì để rõ nghĩa hơn? Bổ sung sao cho tự nhiên, cụ thể và dễ hiểu, như cách nói chuyện với bạn. Viết lại thành câu hỏi đầy đủ, giữ ý chính nhưng mạch lạc hơn.  
    """
    payload = {
        "model": model_curent,
        "prompt": summary_prompt,
        "stream": True,
        "options": {
            "num_predict": 200,  # Tăng lên 200 để đủ cho câu hỏi cải thiện
            "temperature": 0.7,  # Giảm nhẹ để logic và tự nhiên hơn
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