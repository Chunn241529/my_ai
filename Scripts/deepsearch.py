
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


import random                                                                  
                                                                            
def random_number():                                                           
    """                                                                          
    Hàm này tạo ra một số ngẫu nhiên từ 10 đến 25.                               
    """                                                                          
    return random.randint(10, 25)     

max_results = random_number() # number of ressults 

# Các hàm từ search.py
def search_web(query, max_results=max_results):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                'title': r['title'],
                'url': r['href'],
                'snippet': r['body']
            })
    return results

def extract_content(url, snippet=""):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Kiểm tra lỗi HTTP
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Danh sách các thẻ muốn trích xuất nội dung
        tags_to_extract = ['p', 'h1', 'h2', 'li', 'a']
        content_parts = []
        
        # Duyệt qua từng loại thẻ
        for tag in soup.find_all(tags_to_extract):
            if tag.name == 'a' and tag.get('href'):  # Đặc biệt xử lý thẻ <a>
                text = tag.get_text(strip=True)
                href = tag['href']
                content_parts.append(f"{text} (link: {href})")
            else:  # Các thẻ khác chỉ lấy text
                text = tag.get_text(strip=True)
                if text:  # Chỉ thêm nếu có nội dung
                    content_parts.append(text)
        
        # Ghép tất cả nội dung thành một chuỗi, thêm snippet nếu có
        content = f"Snippet: {snippet}\n" + " ".join(content_parts)
        return content[:5000]  # Giới hạn 5000 ký tự
    
    except requests.RequestException as e:
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

    ###

    iteration = 0
    processed_urls = set()  # Danh sách để lưu các URL đã phân tích

    ### phân tích câu hỏi
    analys_question_stream = analys_question(initial_query)
    full_analys_question=""
    with console.status("[bold green]Phân tích vấn đề... [/bold green]", spinner="dots"):
        for part in analys_question_stream:
            if part is not None:
                full_analys_question += part
    console.print(Markdown(full_analys_question), soft_wrap=True, end="")
    history_analys.append(full_analys_question)
    ###

    ### phân tích tìm kiếm tạo câu truy vấn
    analys_prompt_stream = analys_prompt(history_analys)
    full_analys_prompt=""
    with console.status("[bold green]Tìm kiếm... [/bold green]", spinner="dots"):
        for part in analys_prompt_stream:
            if part is not None:
                full_analys_prompt += part
    final_analys_prompt = full_analys_prompt.strip('"')  # Loại bỏ dấu ngoặc kép nếu có
    current_queries.append(final_analys_prompt)
    ###

    while iteration < max_iterations and current_queries:
        current_query = current_queries.pop(0)
        
        console.print("\n")
        console.print(f"[cyan]🔍 {current_query} [/cyan]")
        console.print("\n")

        search_results = search_web(current_query)
        console.print(f"[yellow]Tìm thấy {len(search_results)} kết quả.[/yellow]")

        if not search_results:
            all_answers.clear()
            console.print("\n")
            console.print(f"[red]Khó nha bro! Không tìm thấy thông tin, để tôi phân tích lại câu hỏi...[/red]")
            console.print("\n")
            return deepsearch(initial_query)
        
        if any(result.get('title', '').startswith('EOF') for result in search_results):
            all_answers.clear()
            console.print("\n")
            console.print(f"[red]Khó nha bro! Không tìm thấy thông tin, để tôi phân tích lại câu hỏi...[/red]")
            console.print("\n")
            return deepsearch(initial_query)


        new_query_found = False

        # Duyệt qua từng kết quả tìm kiếm
        result_processed = False
        new_query_found = False
    
        for i, result in enumerate(search_results):
            url = result['url']
            
            # Kiểm tra xem URL đã được phân tích chưa
            if url in processed_urls:
                continue
            
            content = extract_content(url)
            if "Error" in content:
                continue
                   
            # Phân tích chính bằng process_link
            analysis = process_link(initial_query, url, content)
            console.print("\n")
            final_analysis = ""
            with console.status(Markdown(f"Tìm kiếm trong [{result['title']}]({url})"), spinner="dots"):
                for part in analysis:
                    if part is not None:
                        final_analysis += part
            
            console.print(Markdown(final_analysis), soft_wrap=True, end="")
            
            # Đánh giá thông tin bằng process_link
            sufficiency_prompt = (
                f"Url: {url}\n"
                f"Nội dung phân tích: {final_analysis}\n"
                f"Câu hỏi ban đầu: {initial_query}\n"
                f"Danh sách URL đã phân tích: {', '.join(processed_urls)}\n"
                f"Nếu URL này trùng với bất kỳ URL nào trong danh sách đã phân tích, trả lời 'NOT YET' và không đánh giá thêm.\n"
                f"Nếu không trùng, hãy đánh giá xem thông tin này đã đủ để trả lời câu hỏi chưa. "
                f"Trả lời 'OK' nếu đủ, 'NOT YET' nếu chưa đủ, kèm theo lý do ngắn gọn."
            )
            
            sufficiency_analysis = process_link(initial_query, url, sufficiency_prompt)
            console.print("\n")
            sufficiency_result = ""
            for part in sufficiency_analysis:
                if part is not None:
                    sufficiency_result += part
            
            # Kiểm tra kết quả đánh giá
            if "OK" in sufficiency_result.upper():
                result_processed = True
                all_answers[initial_query] = final_analysis
                history_analys.append(final_analysis)
                all_data += f"{url}: {final_analysis}\n"
                processed_urls.add(url)  # Thêm URL vào danh sách đã phân tích
            elif "NOT YET" not in sufficiency_result.upper():
                result_processed = False
                processed_urls.add(url)
            else:
                result_processed = False
                processed_urls.add(url)            
            # Trích xuất new_query
            new_queries = extract_queries(analysis, history_queries)
            if new_queries:
                for query in new_queries:
                    if query not in history_queries:
                        current_queries.append(query)
                        history_queries.add(query)
                        console.print(f"Thêm truy vấn mới: {query}")
                        new_query_found = True
            
            accumulated_context += f"\nNguồn: {url}\n{content}\n"
            if result_processed or new_query_found:
                break
        

        # Thu thập toàn bộ phản hồi từ reason_with_ollama
        answer_stream = reason_with_ollama(initial_query, accumulated_context)
        full_answer = ""
        with console.status("[bold green]Suy luận... [/bold green]", spinner="dots"):
            for part in answer_stream:
                if part is not None:
                    full_answer += part
        all_answers[current_query] = full_answer
        history_analys.append(full_answer)
        console.print(Markdown(full_answer), soft_wrap=True, end="")

        new_queries_from_reasoning = extract_queries(full_answer)

        # Thu thập toàn bộ phản hồi từ evaluate_answer
        evaluation_stream = evaluate_answer(initial_query, full_answer, evaluate_answer)
        full_evaluation = ""
        with console.status("[bold green]Đánh giá nội dung... [/bold green]", spinner="dots"):
            for part in evaluation_stream:
                if part is not None:
                    full_evaluation += part
        
        if "đã đủ" in full_evaluation.lower():
            break
        elif "chưa đủ" in full_evaluation.lower():
            new_queries_from_evaluation = extract_queries(full_evaluation)
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
            iteration += 1
        else:
            new_queries_from_evaluation = extract_queries(full_evaluation)
            relevant_query = new_queries_from_evaluation[0] if new_queries_from_evaluation else (new_queries_from_reasoning[0] if new_queries_from_reasoning else None)
            if relevant_query and relevant_query not in current_queries and relevant_query not in all_answers:
                current_queries.append(relevant_query)
            else:
                current_queries.append(current_query)
            iteration += 1
 
    if iteration >= max_iterations:
        console.print("\n[bold green]Kết thúc DeepSearch! 🌟\n[/bold green]")
    else:
        console.print("\n[bold green]Kết thúc DeepSearch! 🌟\n[/bold green]")


    summary_stream = summarize_answers(initial_query, history_analys)
    final_answer = ""
    with console.status("[bold green]Tổng hợp... [/bold green]", spinner="dots"):
        for part in summary_stream:
            if part is not None:
                final_answer += part
    history_analys.clear()
    history_queries.clear()
    history_keywords.clear()
    all_answers.clear()
    console.clear()
    return f"\n{final_answer}"

                                                           
                                                                                                  
                                                                                                                       
                                                            
                     

# #Hàm test
# if __name__ == "__main__":
#     query = "Cập nhật giúp tôi những từ ngữ hot trend của giới trẻ genz Việt Nam đầu năm 2025"
#     console.print(deepsearch(query))