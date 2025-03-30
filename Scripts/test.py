import requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import ollama
from functools import lru_cache

model = "gemma3:latest"

@lru_cache(maxsize=100)
def extract_content(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        content = " ".join([elem.get_text() for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])])
        return content[:5000]
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

def search_web(query, max_results=5):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({'title': r['title'], 'url': r['href'], 'snippet': r['body']})
    return results

def generate_keywords(query, context="", history_keywords=None):
    if history_keywords is None:
        history_keywords = set()
    prompt = (
        f"Câu hỏi: {query}\nThông tin hiện có: {context[:2000]}\n"
        f"Lịch sử từ khóa đã dùng: {', '.join(history_keywords)}\n"
        f"Hãy suy luận và tạo 2-3 từ khóa mới, không trùng với lịch sử, liên quan đến câu hỏi. "
        f"Trả về dưới dạng danh sách: * \"từ khóa 1\" * \"từ khóa 2\" * \"từ khóa 3\"."
    )
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    keywords = [line.strip()[3:-1] for line in response['message']['content'].split('\n') if line.strip().startswith('* "') and line.strip().endswith('"')]
    return [kw for kw in keywords[:3] if kw not in history_keywords]

def process_link(query, url, content, keywords):
    prompt = (
        f"Nội dung từ {url}:\n{content[:5000]}\n"
        f"Tập trung vào các từ khóa: {', '.join(keywords)}. "
        f"Hãy nghiên cứu nội dung và trả lời câu hỏi chi tiết dựa trên thông tin có sẵn."
        f"Nếu chưa đủ thông tin cho câu hỏi {query}, tạo 1 truy vấn bằng tiếng Anh trong 'Tìm kiếm:' với định dạng * \"truy vấn\", chỉ khi cần thêm thông tin từ nguồn khác."
        f"Nếu đã đủ thông tin thì không cần tạo truy vấn nữa."
    )
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']


def evaluate_and_reason(query, context, current_answer):
    prompt = (
        f"Câu hỏi: {query}\n"
        f"Thông tin: {context[:5000]}\n"
        f"Câu trả lời hiện tại: {current_answer}\n"
        f"Hãy suy luận và đánh giá: trả lời 'đã đủ' nếu đủ thông tin, hoặc 'chưa đủ' nếu thiếu dữ liệu. "
        f"Nếu chưa đủ, tạo 1 truy vấn bằng tiếng Anh trong 'Tìm kiếm:' với định dạng * \"truy vấn\", chỉ khi cần thêm thông tin từ nguồn khác."
    )
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']

def summarize_answers(query, all_data):
    prompt = (
        f"Câu hỏi: {query}\n"
        f"Dữ liệu đã thu thập:\n{all_data}\n"
        f"Hãy tổng hợp thành một câu trả lời mạch lạc, logic và đầy đủ nhất cho câu hỏi. Không đề xuất thêm truy vấn."
    )
    response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
    return response['message']['content']

def extract_queries(text, history_queries=None):
    if history_queries is None:
        history_queries = set()
    queries = []
    lines = text.split('\n')
    in_query_section = False
    for line in lines:
        if line.strip().lower().startswith('Tìm kiếm:'):
            in_query_section = True
        elif in_query_section and (not line.strip() or not line.strip().startswith('*')):
            in_query_section = False
        if in_query_section and line.strip().startswith('* "') and line.strip().endswith('"'):
            query = line.strip()[3:-1]
            if query and query not in history_queries:
                queries.append(query)
            break
    return queries

def deepsearch(initial_query, max_iterations=3):
    current_queries = [initial_query]
    accumulated_context = ""
    iteration = 0
    all_data = ""
    history_queries = set([initial_query])
    history_keywords = set()
    keywords = generate_keywords(initial_query, history_keywords=history_keywords)
    history_keywords.update(keywords)

    print(f"Đang xử lý câu hỏi: {initial_query}")

    while iteration < max_iterations and current_queries:
        current_query = current_queries.pop(0)
        print(f"\nTìm kiếm: {current_query}")
        
        search_results = search_web(current_query)
        if not search_results:
            result = "Không tìm thấy thông tin liên quan."
            all_data += f"{current_query}: {result}\n"
            print(f"  Kết quả: {result}")
            iteration += 1
            continue

        new_query_found = False

        # Duyệt qua từng kết quả tìm kiếm
        for result in search_results:
            content = extract_content(result['url'])
            if "Error" not in content:
                print(f"\nTìm kiếm trong {result['url']}\n")
                analysis = process_link(initial_query, result['url'], content, keywords)
                print(f"Phân tích: {analysis}")
                all_data += f"{result['url']}: {analysis}\n"
                
                # Trích xuất new_query từ nội dung phân tích
                new_queries = extract_queries(analysis, history_queries)
                if new_queries:
                    for query in new_queries:
                        if query not in history_queries:
                            current_queries.append(query)
                            history_queries.add(query)
                            print(f"  Thêm truy vấn mới: {query}")
                            new_query_found = True
                    if new_query_found:
                        # Nếu đã có new_query thì dừng duyệt các URL khác của truy vấn hiện tại
                        break

            accumulated_context += f"\nNguồn: {result['url']}\n{content}\n"

        # Nếu không có new_query nào được trích xuất từ các kết quả tìm kiếm,
        # ta tiến hành đánh giá và cố gắng trích xuất new_query từ đánh giá đó.
        if not new_query_found:
            # Tạo current_answer dựa trên một số dòng kết quả cuối của all_data
            current_answer = "\n".join(all_data.splitlines()[-len(search_results)-1:])
            evaluation = evaluate_and_reason(initial_query, accumulated_context, current_answer)
            all_data += f"{current_query}: {evaluation}\n"
            print(f"  Kết quả đánh giá: {evaluation}")

            if "đã đủ" in evaluation.lower():
                # Nếu đánh giá cho biết đã đủ thông tin thì thoát vòng lặp
                break
            elif "chưa đủ" in evaluation.lower():
                new_queries = extract_queries(evaluation, history_queries)
                if new_queries:
                    for query in new_queries:
                        if query not in history_queries:
                            current_queries.append(query)
                            history_queries.add(query)
                            print(f"  Thêm truy vấn từ đánh giá: {query}")
                else:
                    iteration += 1
            else:
                # Trường hợp đánh giá không rõ ràng, thử lại với truy vấn hiện tại
                if current_query not in history_queries:
                    current_queries.append(current_query)
                    history_queries.add(current_query)
                iteration += 1

        # Cập nhật từ khóa nếu không có new_query mới (điều này thực hiện sau mỗi 2 lần lặp)
        if iteration % 2 == 0 and not new_query_found:
            new_keywords = generate_keywords(initial_query, accumulated_context, history_keywords)
            if new_keywords:
                keywords = new_keywords
                history_keywords.update(keywords)
                print(f"  Từ khóa mới: {keywords}")

        # Tăng biến đếm nếu không có new_query được thêm ở bước trên
        if not new_query_found:
            iteration += 1

    if iteration >= max_iterations:
        print(f"\nĐã đạt giới hạn {max_iterations} lần tìm kiếm.")
    else:
        print("\nĐã hoàn thành tìm kiếm.")
    
    final_answer = summarize_answers(initial_query, all_data)
    return f"Kết quả cuối cùng:\n{final_answer}"


if __name__ == "__main__":
    initial_query = "Model text to image trên huggingface phù hợp với card đồ họa 4060 8gb"
    result = deepsearch(initial_query)
    print(result)