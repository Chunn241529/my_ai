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
from functions.subfuncs.generate import *

console = Console()


class DeepSearch:
    # random number

    def random_number(self, min_val: int, max_val: int) -> int:
        """Tạo số ngẫu nhiên trong khoảng min_val đến max_val."""
        return random.randint(min_val, max_val)

    def __init__(
        self,
        initial_query: str,
        max_iterations: int = 5,
        max_results: int = random_number(5, 10, 25),
    ):
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
        self.vertical_overflow = "ellipsis"  # "visible"
    

    def search_web(self, query: str) -> List[Dict[str, str]]:
        """Tìm kiếm trên web bằng DuckDuckGo và trả về danh sách kết quả."""
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=self.max_results):
                results.append(
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                )
        return results

    def extract_content(self, url: str, snippet: str = "") -> str:
        """Trích xuất nội dung từ URL, bao gồm đoạn trích và văn bản từ các thẻ HTML."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            tags_to_extract = ["p", "h1", "h2", "h3", "a", "span", "table"]
            content_parts = [
                tag.get_text(strip=True)
                for tag in soup.find_all(tags_to_extract)
                if tag.get_text(strip=True)
            ]
            content = f"Snippet: {snippet}\n" + "\n".join(content_parts)
            return content
        except requests.RequestException as e:
            return f"Error fetching {url}: {str(e)}"

    def extract_hrefs(self, url: str) -> List[str]:
        """Trích xuất tất cả liên kết (href) từ một URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            href_list = [tag["href"] for tag in soup.find_all("a", href=True)]
            return href_list
        except requests.RequestException as e:
            return [f"Error fetching {url}: {str(e)}"]

    def extract_queries(self, text):
        """Trích xuất các truy vấn từ văn bản, đảm bảo đa dạng."""
        import re
        
        # Tìm dòng "Đề xuất truy vấn:" và lấy truy vấn
        match = re.search(r"Đề xuất truy vấn:\s*\*\s*\"([^\"]+)\"", text)
        if match:
            base_query = match.group(1)
        else:
            return []

        # Tạo các biến thể của truy vấn dựa trên base_query
        words = base_query.split()
        if len(words) < 2:
            return [base_query]
        
        # Ví dụ: Nếu base_query là "best vietnamese text to speech models hugging face"
        variations = [
            base_query,  # Giữ nguyên truy vấn gốc
            " ".join(words[:3]),  # "best vietnamese text"
            " ".join(words[-3:]),  # "models hugging face"
            f"{words[0]} {words[-2]} {words[-1]}",  # "best hugging face"
        ]
        
        # Loại bỏ trùng lặp và trả về
        return list(dict.fromkeys(variations))[:3]  # Giới hạn tối đa 3 truy vấn

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
            if line.startswith("*"):  # Chỉ lấy dòng bắt đầu bằng *
                keyword = (
                    line.strip("*").strip().strip('"').strip()
                )  # Loại bỏ *, ", và khoảng trắng thừa
                if keyword:  # Chỉ thêm nếu từ khóa không rỗng
                    keywords.append(keyword)

        self.history_keywords.update(keywords)  # Cập nhật set với từ khóa đã làm sạch
        # console.print(f"[red][DEBUG]{self.history_keywords}[/red]")

        with Live(
            Markdown("Chờ xíu...🖐️"),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
            analysis_stream = analys_question(self.initial_query, self.history_keywords)
            full_analysis = ""

            for part in analysis_stream:
                if part is not None:
                    full_analysis += part
                    clean_full = full_analysis.replace("<|begin_of_thought|>", "").replace("<|end_of_thought|>", "").replace("<|begin_of_solution|>", "").replace("<|end_of_solution|>", "")
                    live.update(Markdown(f"\n{clean_full}"))

        # console.print(Markdown(full_analysis), soft_wrap=True, end="")

        if "Khó nha bro" in clean_full:
            self.all_answers.clear()
            better_question_stream = better_question(self.initial_query)
            new_question = ""
            with Live(
                Markdown("Chờ xíu...🖐️"),
                refresh_per_second=self.refresh_second,
                console=console,
                vertical_overflow=self.vertical_overflow,
            ) as live:
                for part in better_question_stream:
                    if part is not None:
                        new_question += part
                        live.update(Markdown(f"\n{new_question}"))
            clean_full = new_question

        self.history_analys.append(clean_full)

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
        """Xử lý một kết quả tìm kiếm và trả về liệu nó có đủ thông tin không. Trả về False tối đa 3 lần."""
        # Khởi tạo biến đếm False nếu chưa có (giả sử là thuộc tính của class)
        if not hasattr(self, 'false_count'):
            self.false_count = 0

        url = result["url"]
        if url in self.processed_urls:
            if self.false_count < 3:
                self.false_count += 1
                return False
            return True  # Nếu đã đủ 3 lần False trước đó, trả về True để dừng

        content = self.extract_content(url, result["snippet"])

        if "Error" in content:
            if self.false_count < 3:
                self.false_count += 1
                return False
            return True  # Nếu đã đủ 3 lần False trước đó, trả về True để dừng

        # Sử dụng Live để hiển thị cả trạng thái và nội dung
        final_analysis = ""
        console.print("\n")
        status_text = f"Tìm kiếm trong [{result['title']}]({url}): "
        with Live(
            Markdown(status_text),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
            analysis_stream = process_link(
                self.initial_query, url, content, list(self.history_keywords)
            )
            for part in analysis_stream:
                if part is not None:
                    final_analysis += part
                    clean_final_analysis = final_analysis.replace("<|begin_of_thought|>", "").replace("<|end_of_thought|>", "").replace("<|begin_of_solution|>", "").replace("<|end_of_solution|>", "").replace("<|end|> ", "")
                    live.update(Markdown(f"{status_text}\n\n{clean_final_analysis}"))

        # Phần còn lại giữ nguyên
        self.processed_urls.add(url)
        sufficiency_stream = sufficiency_prompt(
            query=self.initial_query,
            url=url,
            processed_urls=self.processed_urls,
            final_analysis=clean_final_analysis,
        )
        sufficiency_result = ""
        for part in sufficiency_stream:
            if part is not None:
                sufficiency_result += part

        if "OK" in sufficiency_result.upper():
            self.all_answers[self.initial_query] = clean_final_analysis
            self.history_analys.append(f"Thông tin chuẩn: [{clean_final_analysis}]")
            self.all_data += f"{url}: {clean_final_analysis}\n"
            return True

        new_queries = self.extract_queries(clean_final_analysis)
        for query in new_queries:
            if query not in self.history_queries:
                self.current_queries.append(query)
                self.history_queries.add(query)

        self.all_answers[self.initial_query] = clean_final_analysis
        self.history_analys.append(clean_final_analysis)
        self.all_data += f"{url}: {clean_final_analysis}\n"

        self.accumulated_context += f"\nNguồn: {url}\n{content}\n"
        
        # Kiểm tra và cập nhật false_count
        if self.false_count < 3:
            self.false_count += 1
            return False
        return True  # Nếu đã đủ 3 lần False, trả về True để dừng


    def search_and_process(self):
        """Thực hiện tìm kiếm và xử lý kết quả trong tối đa max_iterations lần."""
        iteration = 0
        while iteration < self.max_iterations and self.current_queries:
            current_query = self.current_queries.pop(0)
            current_query_cleaned = re.sub(
                r'[\'"]', "", current_query
            )  # Loại bỏ dấu nháy
            current_query_cleaned = re.sub(
                r"[^\w\s+-=/*]", "", current_query_cleaned, flags=re.UNICODE
            )  # Giữ chữ, số, khoảng trắng và dấu gạch ngang, hỗ trợ Unicode
            current_query_cleaned = current_query_cleaned.strip()
            console.print(f"[cyan]\nĐang tìm kiếm: {current_query_cleaned}\n[/cyan]")

            try:
                search_results = self.search_web(current_query_cleaned)
                console.print(f"[yellow]Tìm thấy {len(search_results)} kết quả.[/yellow]")
                console.print("\n")
                if not search_results or any(
                    result.get("title", "").startswith("EOF") for result in search_results
                ):
                    self.all_answers.clear()
                    console.print(
                        "[red]Không tìm thấy thông tin hữu ích. Đang khởi động lại với truy vấn mới...[/red]"
                    )
                    self.generate_keywords_and_analyze_question()
                    self.analyze_prompt()
                    continue

                for result in search_results:
                    if self.process_single_result(result):
                        break
                console.print("\n")

                evaluation_stream = evaluate_answer(
                    self.initial_query, self.history_analys, self.processed_urls
                )
                full_evaluation = ""
                for part in evaluation_stream:
                    if part is not None:
                        full_evaluation += part

                if "đã đủ" in full_evaluation.lower():
                    full_answer = ""
                    with Live(
                        Markdown("\nĐang suy luận..\n"),
                        refresh_per_second=self.refresh_second,
                        console=console,
                        vertical_overflow=self.vertical_overflow,
                    ) as live:
                        answer_stream = reason_with_ollama(
                            self.initial_query, self.history_analys
                        )
                        for part in answer_stream:
                            if part is not None:
                                full_answer += part
                                full_answers = (
                                    full_answer.replace("<|begin_of_thought|>", "")
                                    .replace("<|end_of_thought|>", "")
                                    .replace("<|begin_of_solution|>", "")
                                    .replace("<|end_of_solution|>", "")
                                    .replace("|<|end_of_thought|", "")
                                )
                                live.update(Markdown(f"\n{full_answers}"))

                    self.all_answers[current_query_cleaned] = full_answers
                    self.history_analys.append(full_answers)
                    break
                else:
                    # Lấy các truy vấn mới từ full_evaluation
                    new_queries = self.extract_queries(full_evaluation)
                    console.print(f"[magenta]New queries generated: {new_queries}[/magenta]")

                    # Thêm các truy vấn mới, tránh trùng lặp
                    added_any = False
                    for query in new_queries:
                        if (
                            query not in self.current_queries
                            and query not in self.history_queries
                            and query not in self.all_answers
                        ):
                            self.current_queries.append(query)
                            self.history_queries.add(query)
                            console.print(f"[green]Added query: {query}[/green]")
                            added_any = True

                    # Nếu không có truy vấn mới, thoát vòng lặp
                    if not added_any:
                        console.print("[red]No more unique queries available. Exiting...[/red]")
                        break

            except Exception as e:
                console.print(f"[red]Đã xảy ra lỗi: {str(e)}[/red]")
                break

            iteration += 1

    def summarize(self) -> str:
        """Tổng hợp các câu trả lời đã thu thập."""
        with Live(
            Markdown("Chờ xíu...🖐️"),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
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
