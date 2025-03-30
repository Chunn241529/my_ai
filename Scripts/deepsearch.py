
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

import requests
from rich.markdown import Markdown



# import scripts
from commands import *
from file import *
from image import *
from generate import *

# Khởi tạo console từ Rich
console = Console()
history_analys = []


# Các hàm từ search.py
def search_web(query, max_results=2):
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


def extract_queries(text, history_queries=None):
    if history_queries is None:
        history_queries = set()
    # Nếu text không hỗ trợ split(), nghĩa là nó không phải là chuỗi, ta sẽ tiêu thụ nó
    try:
        lines = text.split('\n')
    except AttributeError:
        # Nếu text là generator, chuyển nó thành chuỗi
        text = ''.join(text)
        lines = text.split('\n')

    queries = set()
    in_query_section = False

    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        if line_clean.startswith('đề xuất truy vấn:') or line_clean.startswith('**đề xuất truy vấn:**'):
            in_query_section = True
        elif in_query_section and (not line.strip() or not line.strip().startswith('*')):
            in_query_section = False

        if in_query_section:
            # Nếu dòng hiện tại không bắt đầu bằng '*' nhưng có chứa 'Đề xuất truy vấn:'
            if i + 1 < len(lines) and not lines[i].strip().startswith('*') and lines[i].strip().startswith('Đề xuất truy vấn:'):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('Truy vấn từ') and not next_line.startswith('Đánh giá:'):
                    clean_query = next_line.strip('"').strip('*').strip()
                    if clean_query and clean_query not in history_queries:
                        queries.add(clean_query)
            # Nếu dòng hiện tại bắt đầu bằng '*' thì trích xuất phần sau dấu *
            elif line.strip().startswith('*'):
                clean_query = line.strip()[1:].strip().strip('"').strip()
                if clean_query and clean_query not in history_queries:
                    queries.add(clean_query)

    return list(queries)[:1]


def deepsearch(initial_query, max_iterations=3):
    current_queries = []
    accumulated_context = ""
    all_answers = {}
    all_data = ""
    history_queries = set([initial_query])
    history_keywords = set()
    keywords = generate_keywords(initial_query, history_keywords=history_keywords)
    history_keywords.update(keywords)
    iteration = 0

    ### phân tích câu hỏi
    analys_question_stream = analys_question(initial_query)
    full_analys_question=""
    for part in analys_question_stream:
        if part is not None:
            full_analys_question += part
    console.print((full_analys_question), soft_wrap=True)
    history_analys.append(full_analys_question)
    ###

    ### phân tích tìm kiếm tạo câu truy vấn
    analys_prompt_stream = analys_prompt(history_analys)
    full_analys_prompt=""
    for part in analys_prompt_stream:
        if part is not None:
            full_analys_prompt += part
    current_queries.append(full_analys_prompt)
    ###

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


        new_query_found = False

        # Duyệt qua từng kết quả tìm kiếm
        for result in search_results:
            content = extract_content(result['url'])
            if "Error" not in content:
                console.print(f" [cyan]Tìm kiếm trong {result['url']}🔍\n[/cyan]")
                analysis = process_link(initial_query, result['url'], content, keywords)
                
                final_analysis = ""
                for part in analysis:
                    if part is not None:
                        final_analysis += part

                console.print(f"[magenta]Phân tích: {final_analysis}\n[/magenta]", soft_wrap=True)
                all_answers[current_query] = final_analysis

                all_data += f"{result['url']}: {final_analysis}\n"
                
                # Trích xuất new_query từ nội dung phân tích
                new_queries = extract_queries(analysis, history_queries)
                if new_queries:
                    for query in new_queries:
                        if query not in history_queries:
                            current_queries.append(query)
                            history_queries.add(query)
                            console.print(f"Thêm truy vấn mới: {query}")
                            new_query_found = True
                    if new_query_found:
                        break

            accumulated_context += f"\nNguồn: {result['url']}\n{content}\n"

        
        ##old
        # for result in search_results:
        #     content = extract_content(result['url'])
        #     accumulated_context += f"\nNguồn: {result['url']}\n{content}\n"


        # Thu thập toàn bộ phản hồi từ reason_with_ollama
        answer_stream = reason_with_ollama(initial_query, accumulated_context)
        full_answer = ""
        for part in answer_stream:
            if part is not None:
                full_answer += part
        all_answers[current_query] = full_answer
        console.print(Markdown(full_answer), soft_wrap=True, end="")

        new_queries_from_reasoning = extract_queries(full_answer)

        # Thu thập toàn bộ phản hồi từ evaluate_answer
        evaluation_stream = evaluate_answer(initial_query, full_answer)
        full_evaluation = ""
        for part in evaluation_stream:
            if part is not None:
                full_evaluation += part
        console.print(f"[magenta]Đánh giá: {full_evaluation}[/magenta]")
        
        if "đã đủ" in full_evaluation.lower():
            console.print("[bold green]Thông tin đã đủ, không cần tìm thêm! 🎉[/bold green]")
            break
        elif "chưa đủ" in full_evaluation.lower():
            new_queries_from_evaluation = extract_queries(full_evaluation)
            # console.print(f"  [blue]Truy vấn từ đánh giá: {new_queries_from_evaluation} 🔄[/blue]")  # Ẩn dòng này
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
            else:
                console.print("[yellow]Không có truy vấn mới phù hợp để tiếp tục. 🤔[/yellow]")
            iteration += 1
        else:
            console.print(f"[red]Đánh giá không rõ ràng: {full_evaluation} ❓[/red]")
            new_queries_from_evaluation = extract_queries(full_evaluation)
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
            else:
                current_queries.append(current_query)
            iteration += 1

    if iteration >= max_iterations:
        console.print(f"\n[bold red]Đã đạt giới hạn {max_iterations} lần tìm kiếm. ⏳[/bold red]")
    else:
        console.print("\n[bold green]Đã hoàn thành tìm kiếm! 🌟[/bold green]")
    
    summary_stream = summarize_answers(initial_query, all_answers)
    final_answer = ""
    for part in summary_stream:
        if part is not None:
            final_answer += part
    return f"\n{final_answer}"


# #Hàm test 
# query = "Model text to image nào phù hợp với card đồ họa 4060 8gb"
# console.print(deepsearch(query))