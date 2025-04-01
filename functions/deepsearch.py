
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
                                                                            
def random_number(min, max):                                                           
    """                                                                          
    Hàm này tạo ra một số ngẫu nhiên từ 10 đến 25.                               
    """                                                                          
    return random.randint(min, max)     

max_results = random_number(10, 25) 

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
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        tags_to_extract = ['p', 'h1', 'h2', 'h3', 'li']
        content_parts = []
        for tag in soup.find_all(tags_to_extract):
            text = tag.get_text(strip=True)
            if text:
                content_parts.append(text)
        content = f"Snippet: {snippet}\n" + " ".join(content_parts)
        return content
    except requests.RequestException as e:
        return f"Error fetching {url}: {str(e)}"

def extract_hrefs(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        href_list = [tag['href'] for tag in soup.find_all('a', href=True)]
        return href_list
    except requests.RequestException as e:
        return f"Error fetching {url}: {str(e)}"


def extract_queries(text, history_queries=None):
    if history_queries is None:
        history_queries = set()
    try:
        lines = text.split('\n')
    except AttributeError:
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
            if i + 1 < len(lines) and not lines[i].strip().startswith('*') and lines[i].strip().startswith('Đề xuất truy vấn:'):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('Truy vấn từ') and not next_line.startswith('Đánh giá:'):
                    clean_query = next_line.strip('"').strip('*').strip()
                    if clean_query and clean_query not in history_queries:
                        queries.add(clean_query)
            elif line.strip().startswith('*'):
                clean_query = line.strip()[1:].strip().strip('"').strip()
                if clean_query and clean_query not in history_queries:
                    queries.add(clean_query)

    return list(queries)[:1]


def deepsearch(initial_query, max_iterations=random_number(2, 5)):
    current_queries = []
    accumulated_context = ""
    all_answers = {}
    all_data = ""
    history_queries = set([initial_query])
    history_keywords = set()
    keywords = generate_keywords(initial_query, history_keywords=history_keywords)
    history_keywords.update(keywords)

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

    if "Khó nha bro" in full_analys_question:
        all_answers.clear()
        history_analys.clear()
        console.print(f"\n[red]Không tìm thấy thông tin, để tôi phân tích lại câu hỏi...[/red]\n")
        better_question_prompt = better_question(initial_query)
        
        new_question = ""
        with console.status("[bold green]Phân tích câu hỏi... [/bold green]", spinner="dots"):
            for part in better_question_prompt:
                if part is not None:
                    new_question += part

        console.print(Markdown(new_question), soft_wrap=True, end="")
        full_analys_question = new_question
    
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
        console.print(f"[cyan]Tìm kiếm: {current_query}[/cyan]")
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

        result_processed = False
        new_query_found = False
    
        for i, result in enumerate(search_results):
            url = result['url']
            
            if url in processed_urls:
                continue
            ### content trong url
            content = extract_content(url)
            ### 

            if "Error" in content:
                continue
            
            analysis = process_link(initial_query, url, content, keywords)
            console.print("\n")
            final_analysis = ""
            with console.status(Markdown(f"Tìm kiếm trong [{result['title']}]({url})"), spinner="dots"):
                for part in analysis:
                    if part is not None:
                        final_analysis += part
            
            console.print(Markdown(f"Tìm kiếm trong [{result['title']}]({url})\n"), soft_wrap=True, end="")
            processed_urls.add(url)
            console.print(Markdown(final_analysis), soft_wrap=True, end="")
            
            # Đánh giá thông tin bằng process_link
            sufficiency_prompt = (
                f"Url: {url}\n"
                f"Nội dung phân tích: {final_analysis}\n"
                f"Câu hỏi ban đầu: {initial_query}\n"
                f"Nếu '{url}' này trùng với bất kỳ URL nào trong danh sách '{', '.join(processed_urls)}', trả lời 'NOT YET' và không đánh giá thêm.\n"
                f"Nếu không trùng, hãy đánh giá xem thông tin này đã đủ để trả lời câu hỏi chưa.\n"
                f"Trả lời 'OK' nếu đủ, 'NOT YET' nếu chưa đủ."
            )
            
            sufficiency_analysis = process_link(initial_query, url, sufficiency_prompt, keywords)
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
                all_data += f"{result['url']}: {final_analysis}\n"           
            else:
                result_processed = False


            # Trích xuất new_query
            new_queries = extract_queries(final_analysis, history_queries)

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
        evaluation_stream = evaluate_answer(initial_query, full_answer, processed_urls)
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