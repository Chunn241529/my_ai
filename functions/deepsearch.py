from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
import random
from typing import List, Set, Dict

# Giả định các module này đã được định nghĩa
from functions.subfuncs.commands import *
from functions.subfuncs.file import *
from functions.subfuncs.image import *
from functions.generate import *

console = Console()


class DeepSearch:
    #random number

    def random_number(self, min_val: int, max_val: int) -> int:
        """Tạo số ngẫu nhiên trong khoảng min_val đến max_val."""
        return random.randint(min_val, max_val)

    def __init__(self, initial_query: str, max_iterations: int = 5, max_results: int = random_number(5, 10, 25)):
        """
        Khởi tạo đối tượng DeepSearch với câu hỏi ban đầu và các tham số cấu hình.
        
        Args:
            initial_query (str): Câu hỏi/truy vấn ban đầu.
            max_iterations (int): Số lần lặp tối đa (mặc định là 5).
            max_results (int): Số kết quả tìm kiếm tối đa mỗi truy vấn (mặc định là 10).
        """
        self.initial_query = initial_query
        self.max_iterations = max_iterations
        self.max_results = max_results
        self.current_queries: List[str] = []
        self.accumulated_context: str = ""
        self.all_answers: Dict[str, str] = {}
        self.all_data: str = ""
        self.history_queries: Set[str] = {initial_query}
        self.history_keywords: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.history_analys: List[str] = []

        ### config live
        self.refresh_second = 10 
        self.vertical_overflow = "ellipsis" #"visible"


    def search_web(self, query: str) -> List[Dict[str, str]]:
        """Tìm kiếm trên web bằng DuckDuckGo và trả về danh sách kết quả."""
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=self.max_results):
                results.append({
                    'title': r['title'],
                    'url': r['href'],
                    'snippet': r['body']
                })
        return results

    def extract_content(self, url: str, snippet: str = "") -> str:
        """Trích xuất nội dung từ URL, bao gồm đoạn trích và văn bản từ các thẻ HTML."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            tags_to_extract = ['p', 'h1', 'h2', 'h3', 'a']
            content_parts = [tag.get_text(strip=True) for tag in soup.find_all(tags_to_extract) if tag.get_text(strip=True)]
            content = f"Snippet: {snippet}\n" + "\n".join(content_parts)
            return content
        except requests.RequestException as e:
            return f"Error fetching {url}: {str(e)}"

    def extract_hrefs(self, url: str) -> List[str]:
        """Trích xuất tất cả liên kết (href) từ một URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            href_list = [tag['href'] for tag in soup.find_all('a', href=True)]
            return href_list
        except requests.RequestException as e:
            return [f"Error fetching {url}: {str(e)}"]

    def extract_queries(self, text: str) -> List[str]:
        """Trích xuất các truy vấn được đề xuất từ văn bản phân tích."""
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
                        if clean_query and clean_query not in self.history_queries:
                            queries.add(clean_query)
                elif line.strip().startswith('*'):
                    clean_query = line.strip()[1:].strip().strip('"').strip()
                    if clean_query and clean_query not in self.history_queries:
                        queries.add(clean_query)
        return list(queries)[:1]

    def generate_keywords_and_analyze_question(self):
        """Tạo từ khóa và phân tích câu hỏi ban đầu."""
        keywords_stream = generate_keywords(self.initial_query)
        full_keywords = ""
        for part in keywords_stream:
            if part is not None:
                full_keywords += part
        
        # Làm sạch và trích xuất từ khóa từ định dạng danh sách
        keywords = []
        for line in full_keywords.splitlines():
            line = line.strip()
            if line.startswith('*'):  # Chỉ lấy dòng bắt đầu bằng *
                keyword = line.strip('*').strip().strip('"').strip()  # Loại bỏ *, ", và khoảng trắng thừa
                if keyword:  # Chỉ thêm nếu từ khóa không rỗng
                    keywords.append(keyword)
        
        self.history_keywords.update(keywords)  # Cập nhật set với từ khóa đã làm sạch
        # console.print(f"[red][DEBUG]{self.history_keywords}[/red]")

        with Live(Markdown("Chờ xíu..."), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
            analysis_stream = analys_question(self.initial_query, self.history_keywords)
            full_analysis = ""
            
            for part in analysis_stream:
                if part is not None:
                    full_analysis += part
                    live.update(Markdown(f"\n{full_analysis}"))

        # console.print(Markdown(full_analysis), soft_wrap=True, end="")

        if "Khó nha bro" in full_analysis:
            self.all_answers.clear()
            better_question_stream = better_question(self.initial_query)
            new_question = ""
            with Live(Markdown("Chờ xíu..."), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
                for part in better_question_stream:
                    if part is not None:
                        new_question += part
                        live.update(Markdown(f"\n{new_question}"))
            full_analysis = new_question

        self.history_analys.append(full_analysis)

    def analyze_prompt(self):
        """Phân tích gợi ý để tạo truy vấn đầu tiên."""
        analysis_stream = analys_prompt(self.history_analys)
        full_analysis = ""
        for part in analysis_stream:
            if part is not None:
                full_analysis += part
        final_query = full_analysis.strip('"')
        self.current_queries.append(final_query)


    def process_single_result(self, result: Dict[str, str]) -> bool:
        """Xử lý một kết quả tìm kiếm và trả về liệu nó có đủ thông tin không."""
        url = result['url']
        if url in self.processed_urls:
            return False

        content = self.extract_content(url, result['snippet'])

        if "Error" in content:
            return False

        # Sử dụng Live để hiển thị cả trạng thái và nội dung
        final_analysis = ""
        console.print("\n")
        status_text = f"Tìm kiếm trong [{result['title']}]({url}): "
        with Live(Markdown(status_text), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
            analysis_stream = process_link(self.initial_query, url, content, list(self.history_keywords))
            for part in analysis_stream:
                if part is not None:
                    final_analysis += part
                    live.update(Markdown(f"{status_text}\n\n{final_analysis}"))

        # Phần còn lại giữ nguyên
        self.processed_urls.add(url)
        sufficiency_stream = sufficiency_prompt(query=self.initial_query, url=url, processed_urls=self.processed_urls, final_analysis=final_analysis)
        sufficiency_result = ""
        for part in sufficiency_stream:
            if part is not None:
                sufficiency_result += part

        if "OK" in sufficiency_result.upper():
            self.all_answers[self.initial_query] = final_analysis
            self.history_analys.append(final_analysis)
            self.all_data += f"{url}: {final_analysis}\n"
            return True

        new_queries = self.extract_queries(final_analysis)
        for query in new_queries:
            if query not in self.history_queries:
                self.current_queries.append(query)
                self.history_queries.add(query)

        self.accumulated_context += f"\nNguồn: {url}\n{content}\n"
        return False

    def search_and_process(self):
        """Thực hiện tìm kiếm và xử lý kết quả trong tối đa max_iterations lần."""
        iteration = 0
        while iteration < self.max_iterations and self.current_queries:
            current_query = self.current_queries.pop(0)
            current_query_cleaned = re.sub(r'[\'"]', '', current_query)  # Loại bỏ dấu nháy
            current_query_cleaned = re.sub(r'[^\w\s-]', '', current_query_cleaned, flags=re.UNICODE)  # Giữ chữ, số, khoảng trắng và dấu gạch ngang, hỗ trợ Unicode
            current_query_cleaned = current_query_cleaned.strip()
            console.print(f"[cyan]\nĐang tìm kiếm: {current_query_cleaned}\n[/cyan]")

            search_results = self.search_web(current_query_cleaned)
            console.print(f"[yellow]Tìm thấy {len(search_results)} kết quả.[/yellow]")
            console.print("\n") 
            if not search_results or any(result.get('title', '').startswith('EOF') for result in search_results):
                self.all_answers.clear()
                console.print("[red]Không tìm thấy thông tin hữu ích. Đang khởi động lại với truy vấn mới...[/red]")
                self.generate_keywords_and_analyze_question()
                self.analyze_prompt()
                continue

            for result in search_results:
                if self.process_single_result(result):
                    break
            console.print("\n") 

            
            evaluation_stream = evaluate_answer(self.initial_query, self.all_data , self.processed_urls)
            full_evaluation = ""
            for part in evaluation_stream:
                if part is not None:
                    full_evaluation += part

            if "đã đủ" in full_evaluation.lower():
                full_answer = ""
                with Live(Markdown("\nĐang suy luận..\n"), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
                    answer_stream = reason_with_ollama(self.initial_query, self.history_analys)
                    for part in answer_stream:
                        if part is not None:
                            full_answer += part
                            live.update(Markdown(f"\n{full_answer}"))

                self.all_answers[current_query_cleaned] = full_answer
                self.history_analys.append(full_answer)
                break
            else:
                new_queries = self.extract_queries(full_evaluation) or self.extract_queries(full_answer)
                if new_queries:
                    relevant_query = new_queries[0]
                    if relevant_query not in self.current_queries and relevant_query not in self.all_answers:
                        self.current_queries.append(relevant_query)
            iteration += 1

    def summarize(self) -> str:
        """Tổng hợp các câu trả lời đã thu thập."""
        status_text = "\nĐang tổng hợp...\n"
        with Live(Markdown(status_text), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
            summary_stream = summarize_answers(self.initial_query, self.history_analys)
            final_answer = ""

            for part in summary_stream:
                if part is not None:
                    final_answer += part
                    live.update(Markdown(f"\n{final_answer}"))

        return final_answer

    def run(self) -> str:
        """Chạy toàn bộ quá trình tìm kiếm sâu và trả về câu trả lời cuối cùng."""
        self.generate_keywords_and_analyze_question()
        self.analyze_prompt()
        self.search_and_process()
        console.clear()
        final_answer = self.summarize()
        # Xóa lịch sử để giải phóng bộ nhớ
        self.history_analys.clear()
        self.history_queries.clear()
        self.history_keywords.clear()
        self.all_answers.clear()
        return f"\n{final_answer}"

# # Ví dụ sử dụng
# if __name__ == "__main__":
#     query = "Cập nhật từ vựng hot trend mới của genz Việt Nam đầu năm 2025"
#     deep_search = DeepSearch(query)
#     console.print(deep_search.run())