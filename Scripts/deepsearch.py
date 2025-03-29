
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

import requests
import json
from rich.markdown import Markdown


# import scripts
from commands import *
from file import *
from image import *

# Khởi tạo console từ Rich
console = Console()


# URL của Ollama API
OLLAMA_API_URL = "http://localhost:11434/api/generate"


model_gemma = "gemma3:latest"
model_qwen = "qwen2.5-coder:latest"

# Các hàm từ search.py
def search_web(query, max_results=5):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                'title': r['title'],
                'url': r['href'],
                'snippet': r['body']
            })
    return results

def extract_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs])
        return content[:12000]
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"




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
    summary_prompt = f"Câu hỏi chính: {query}\nDưới đây là các thông tin đã thu thập:\n" + "\n".join([f"{q}: {a}" for q, a in all_answers.items()]) + f"\nTổng hợp thành một câu trả lời mạch lạc, logic và đầy đủ nhất cho Câu hỏi chính: {query}, tập trung vào trọng tâm."
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

def extract_queries(text):
    queries = set()
    lines = text.split('\n')
    in_query_section = False
    
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        if line_clean.startswith('đề xuất truy vấn:') or line_clean.startswith('**đề xuất truy vấn:**'):
            in_query_section = True
        elif in_query_section and (not line.strip() or not line.strip().startswith('*')):
            in_query_section = False
        
        if in_query_section:
            if i + 1 < len(lines) and not lines[i].strip().startswith('*') and lines[i].strip().startswith('Đề xuất truy vấn:'):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('Truy vấn từ') and not next_line.startswith('Đánh giá:'):
                    clean_query = next_line.strip('"').strip('*').strip()
                    if clean_query:
                        analys_prompt_stream = analys_prompt(clean_query)

                        full_query=""
                        for part in analys_prompt_stream:
                            if part is not None:
                                full_query += part


                        queries.add(full_query)
            elif line.strip().startswith('*'):
                clean_query = line.strip()[1:].strip().strip('"').strip()
                if clean_query:
                    queries.add(clean_query)
    
    return list(queries)[:1]


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

def deepsearch(initial_query, max_iterations=3):
    current_queries = []
    accumulated_context = ""
    iteration = 0
    all_answers = {}

    analys_prompt_stream = analys_prompt(initial_query)

    full_query=""
    for part in analys_prompt_stream:
        if part is not None:
            full_query += part

    current_queries.append(full_query)

    while iteration < max_iterations and current_queries:
        current_query = current_queries.pop(0)
        
        console.print("\n")
        console.print(f"[cyan]Tìm kiếm: {current_query} 🔍[/cyan]")
        console.print("\n")

        search_results = search_web(current_query)
        if not search_results:
            all_answers[current_query] = "Không tìm thấy thông tin liên quan."
            console.print(f"  [red]Kết quả: Không tìm thấy thông tin liên quan. 😕[/red]")
            continue

        for result in search_results:
            content = extract_content(result['url'])
            accumulated_context += f"\nNguồn: {result['url']}\n{content}\n"

        # Thu thập toàn bộ phản hồi từ reason_with_ollama
        answer_stream = reason_with_ollama(initial_query, accumulated_context)
        full_answer = ""
        for part in answer_stream:
            if part is not None:
                full_answer += part
        all_answers[current_query] = full_answer
        console.print(Markdown(full_answer), soft_wrap=True, end="")

        # Trích xuất truy vấn từ suy luận nhưng không hiển thị
        new_queries_from_reasoning = extract_queries(full_answer)
        # console.print(f"  [blue]Truy vấn từ suy luận: {new_queries_from_reasoning} 🤓[/blue]")  # Ẩn dòng này

        # Thu thập toàn bộ phản hồi từ evaluate_answer
        evaluation_stream = evaluate_answer(initial_query, full_answer)
        full_evaluation = ""
        for part in evaluation_stream:
            if part is not None:
                full_evaluation += part
        console.print(f"[magenta]Đánh giá: {full_evaluation}[/magenta]")
        
        if "đã đủ" in full_evaluation.lower():
            console.print("[bold green]Thông tin đã đủ, không cần tìm thêm! 🎉[/bold green]")
            # if new_queries_from_reasoning:
            #     console.print(f"  [yellow]Lưu ý: Có truy vấn từ suy luận ({new_queries_from_reasoning}) nhưng bị bỏ qua vì đánh giá 'Đã đủ'.[/yellow]")  # Ẩn dòng này
            break
        elif "chưa đủ" in full_evaluation.lower():
            new_queries_from_evaluation = extract_queries(full_evaluation)
            # console.print(f"  [blue]Truy vấn từ đánh giá: {new_queries_from_evaluation} 🔄[/blue]")  # Ẩn dòng này
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
                # console.print(f"  [cyan]Truy vấn được thêm: [{relevant_query}] 🚀[/cyan]")  # Ẩn dòng này
            else:
                console.print("[yellow]Không có truy vấn mới phù hợp để tiếp tục. 🤔[/yellow]")
            iteration += 1
        else:
            console.print(f"[red]Đánh giá không rõ ràng: {full_evaluation} ❓[/red]")
            new_queries_from_evaluation = extract_queries(full_evaluation)
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
                # console.print(f"  [cyan]Truy vấn từ đánh giá không rõ ràng: [{relevant_query}] 🔄[/cyan]")  # Ẩn dòng này
            else:
                current_queries.append(current_query)
            iteration += 1

    if iteration >= max_iterations:
        console.print(f"\n[bold red]Đã đạt giới hạn {max_iterations} lần tìm kiếm. ⏳[/bold red]")
    else:
        console.print("\n[bold green]Đã hoàn thành tìm kiếm! 🌟[/bold green]")
    
    # Thu thập toàn bộ phản hồi từ summarize_answers
    summary_stream = summarize_answers(initial_query, all_answers)
    final_answer = ""
    for part in summary_stream:
        if part is not None:
            final_answer += part
    return f"\n{final_answer}"

#Hàm test 

# query = "So sánh hiệu suất các mô hình AI lớn hiện tại"
# console.print(deepsearch(query))