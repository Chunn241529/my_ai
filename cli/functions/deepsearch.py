from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from typing import List, Set, Dict
import re
import json
import pickle
import os
from retrying import retry

# Giả định các module đã được định nghĩa
from cli.functions.subfuncs.commands import *
from cli.functions.subfuncs.file import *
from cli.functions.subfuncs.generate import *
from utils.helper.web_utils import search_web, extract_content

console = Console()

class DeepSearch:
    def __init__(
        self,
        initial_query: str,
        max_results: int = 10,
    ):
        """
        Khởi tạo đối tượng DeepSearch với câu hỏi ban đầu và các tham số cấu hình.

        Args:
            initial_query (str): Câu hỏi/truy vấn ban đầu.
            max_results (int): Số kết quả tìm kiếm tối đa mỗi truy vấn (mặc định là 10).
        """
        self.initial_query = initial_query
        self.max_results = max_results
        self.current_queries: List[str] = []
        self.accumulated_context: str = ""
        self.all_answers: Dict[str, str] = {}
        self.all_data: str = ""
        self.history_queries: Set[str] = {initial_query}
        self.history_keywords: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.history_analys: List[str] = []
        self.context_summary: List[str] = []
        self.max_context_size = 100000  # Giới hạn kích thước ngữ cảnh (ký tự)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logs_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "logs"))
        self.state_file = os.path.join(logs_dir, f"deepsearch_state_{hash(initial_query)}.pkl")
        self.load_state()

        ### config live
        self.refresh_second = 10
        self.vertical_overflow = "ellipsis"

    def save_state(self):
        """Lưu trạng thái tìm kiếm."""
        state = {
            "current_queries": self.current_queries,
            "history_queries": self.history_queries,
            "history_keywords": self.history_keywords,
            "processed_urls": self.processed_urls,
            "context_summary": self.context_summary,
            "all_answers": self.all_answers,
            "history_analys": self.history_analys,
        }
        with open(self.state_file, "wb") as f:
            pickle.dump(state, f)

    def load_state(self):
        """Khôi phục trạng thái tìm kiếm."""
        if os.path.exists(self.state_file):
            with open(self.state_file, "rb") as f:
                state = pickle.load(f)
                self.current_queries = state.get("current_queries", [])
                self.history_queries = state.get("history_queries", set())
                self.history_keywords = state.get("history_keywords", set())
                self.processed_urls = state.get("processed_urls", set())
                self.context_summary = state.get("context_summary", [])
                self.all_answers = state.get("all_answers", {})
                self.history_analys = state.get("history_analys", [])

    def extract_queries(self, text):
        """Trích xuất các truy vấn từ văn bản."""
        lines = text.splitlines()
        queries = [line.strip() for line in lines if line.strip() and line != "NOT YET"]
        return queries[:4]

    def generate_keywords_and_analyze_question(self):
        """Tạo từ khóa và phân tích câu hỏi ban đầu."""
        keywords_stream = generate_keywords(self.initial_query)
        full_keywords = ""
        for part in keywords_stream:
            if part is not None:
                full_keywords += part

        keywords = []
        for line in full_keywords.splitlines():
            line = line.strip()
            if line.startswith("*"):
                keyword = line.strip("*").strip().strip('"').strip()
                if keyword:
                    keywords.append(keyword)

        self.history_keywords.update(keywords)

        with Live(
            Markdown("Đang phân tích câu hỏi... 🖐️"),
            refresh_per_second=self.refresh_second,
            console=console,
            vertical_overflow=self.vertical_overflow,
        ) as live:
            analysis_stream = analys_question(self.initial_query, self.history_keywords)
            full_analysis = ""
            for part in analysis_stream:
                if part is not None:
                    full_analysis += part
                    clean_full = (
                        full_analysis.replace("<|begin_of_thought|>", "")
                        .replace("<|end_of_thought|>", "")
                        .replace("<|begin_of_solution|>", "")
                        .replace("<|end_of_solution|>", "")
                    )
                    live.update(Markdown(f"\n{clean_full}"))

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
        """Phân tích gợi ý để tạo danh sách truy vấn ban đầu."""
        analysis_stream = analys_prompt(self.history_analys)
        full_analysis = ""
        for part in analysis_stream:
            if part is not None:
                full_analysis += part

        clean_full_analysis = (
            full_analysis.replace("1. ", "")
            .replace("2. ", "")
            .replace("3. ", "")
            .replace("4. ", "")
        )
        queries = [
            q.strip('"').strip() for q in clean_full_analysis.splitlines() if q.strip()
        ]
        for query in queries:
            if query and query not in self.history_queries:
                self.current_queries.append(query)
                self.history_queries.add(query)

    def summarize_content(self, content: str) -> str:
        """Tóm tắt nội dung để giảm kích thước lưu trữ."""
        prompt = f"""
        Tóm tắt nội dung {content}, giữ lại các ý chính.
        \nLưu ý: Chỉ tóm tắt, không thêm giải thích hay bất kì nội dung nào.
        """

        summary_stream = query_ollama(prompt=prompt, num_predict=1500, temperature=0.2)
        summary = ""
        for part in summary_stream:
            if part is not None:
                summary += part
        return summary

    def process_single_result(self, result: Dict[str, str]) -> bool:
        """Xử lý một kết quả tìm kiếm và trả về liệu nó có đủ thông tin không."""
        url = result["url"]
        if url in self.processed_urls:
            # console.print(f"[yellow]URL {url} đã được xử lý trước đó.[/yellow]")
            return False

        content = extract_content(url, result["snippet"])
        if "Error" in content:
            # console.print(f"[red]Lỗi khi truy cập {url}[/red]")
            return False

        content_summary = self.summarize_content(content)
        self.context_summary.append(f"Nguồn: {url}\n{content_summary}\n")
        while len("".join(self.context_summary)) > self.max_context_size:
            self.context_summary.pop(0)

        console.print("[bold yellow]\nTìm kiếm thông tin: \n[/bold yellow]")
        final_analysis = ""
        with Live(
            Markdown(f"\nTìm kiếm trong [{result['title']}]({url})"),
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
                    clean_final_analysis = (
                        final_analysis.replace("<|begin_of_thought|>", "")
                        .replace("<|end_of_thought|>", "")
                        .replace("<|begin_of_solution|>", "")
                        .replace("<|end_of_solution|>", "")
                        .replace("<|end|> ", "")
                    )
                    live.update(Markdown(f"\nTìm kiếm trong [{result['title']}]({url})\n\n{clean_final_analysis}"))

        self.processed_urls.add(url)

        sufficiency_stream = sufficiency_prompt(
            query=self.initial_query,
            url=url,
            processed_urls=",".join(self.processed_urls),
            final_analysis=clean_final_analysis,
        )
        sufficiency_result = ""
        for part in sufficiency_stream:
            if part is not None:
                sufficiency_result += part

        # Xử lý sufficiency_result
        sufficiency_result = sufficiency_result.strip()
        if sufficiency_result.upper() == "OK":
            is_sufficient = True
            confidence = 1.0
            reason = "Thông tin được xác nhận đủ"
        else:
            try:
                sufficiency_data = json.loads(sufficiency_result)
                is_sufficient = sufficiency_data.get("is_sufficient", False)
                confidence = sufficiency_data.get("confidence", 0.0)
                reason = sufficiency_data.get("reason", "")
            except json.JSONDecodeError:
                # console.print(f"[red]Lỗi: sufficiency_result không phải JSON hợp lệ: {sufficiency_result}[/red]")
                is_sufficient = False
                confidence = 0.0
                reason = "Kết quả không rõ ràng"

        self.history_analys.append(f"URL: {url}, Sufficient: {is_sufficient}, Confidence: {confidence}, Reason: {reason}")

        if is_sufficient and confidence > 0.7:
            # console.print(f"[green]Thông tin từ {url} được đánh giá là đủ (Confidence: {confidence})[/green]")
            self.all_answers[self.initial_query] = clean_final_analysis
            self.all_data += f"{url}: {clean_final_analysis}\n"
            return True

        self.all_answers[self.initial_query] = clean_final_analysis
        self.all_data += f"{url}: {clean_final_analysis}\n"
        self.accumulated_context += f"\nNguồn: {url}\n{content}\nReason: {reason}\n"
        return False

    def rank_sources(self, search_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Xếp hạng các nguồn dựa trên độ tin cậy và mức độ liên quan."""
        def calculate_score(result: Dict[str, str]) -> float:
            score = 0.0
            url = result["url"].lower()
            snippet = result.get("snippet", "").lower()

            trusted_domains = [".edu", ".gov", "wikipedia.org", ".org"]
            for domain in trusted_domains:
                if domain in url:
                    score += 2.0
                    break

            keywords = list(self.history_keywords)
            for keyword in keywords:
                if keyword.lower() in snippet:
                    score += 0.5

            score += len(snippet) / 1000.0
            return score

        ranked_results = sorted(search_results, key=calculate_score, reverse=True)
        return ranked_results

    def generate_improved_queries(self):
        """Tạo truy vấn mới dựa trên lý do thất bại và ngữ cảnh tích lũy."""
        failure_reasons = [entry for entry in self.history_analys if "Reason:" in entry]
        context = "\n".join(self.context_summary)

        query_stream = analys_prompt(
            query=self.initial_query,
            failure_reasons=failure_reasons,
            context=context
        )
        new_queries = []
        for part in query_stream:
            if part is not None:
                new_queries.append(part.strip())

        for query in new_queries:
            if query and query not in self.history_queries:
                self.current_queries.append(query)
                self.history_queries.add(query)

    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def search_web_with_retry(self, query: str) -> List[Dict[str, str]]:
        return search_web(query)

    def search_and_process(self):
        """Thực hiện tìm kiếm và xử lý kết quả cho đến khi không còn truy vấn hoặc tìm thấy câu trả lời đủ tốt."""
        while self.current_queries:
            current_query = self.current_queries.pop(0)
            current_query_cleaned = re.sub(r'[\'"]', "", current_query)
            current_query_cleaned = re.sub(
                r"[^\w\s+-=/*]", "", current_query_cleaned, flags=re.UNICODE
            )
            current_query_cleaned = current_query_cleaned.strip()
            console.print(f"[cyan]\nĐang tìm kiếm: {current_query_cleaned}[/cyan]")

            try:
                search_results = self.search_web_with_retry(current_query_cleaned)
                console.print(f"[yellow]Tìm thấy {len(search_results)} kết quả.[/yellow]")
                if not search_results or any(
                    result.get("title", "").startswith("EOF")
                    for result in search_results
                ):
                    # console.print("[red]Không tìm thấy thông tin hữu ích. Tạo truy vấn mới...[/red]")
                    self.generate_improved_queries()
                    continue

                ranked_results = self.rank_sources(search_results)
                for result in ranked_results:
                    process_result = self.process_single_result(result)
                    if process_result:
                        break

                evaluation_stream = evaluate_answer(
                    self.initial_query,
                    self.history_analys,
                    self.processed_urls,
                )
                full_evaluation = ""
                for part in evaluation_stream:
                    if part is not None:
                        full_evaluation += part

                if "đã đủ" in full_evaluation.lower():
                    full_reason = ""
                    with Live(
                        Markdown("\nĐang suy luận..\n"),
                        refresh_per_second=self.refresh_second,
                        console=console,
                        vertical_overflow=self.vertical_overflow,
                    ) as live:
                        answer_stream = reason_with_ollama(
                            self.initial_query,
                            self.history_analys,
                        )
                        for part in answer_stream:
                            if part is not None:
                                full_reason += part
                                full_reason_answers = (
                                    full_reason.replace("<|begin_of_thought|>", "")
                                    .replace("<|end_of_thought|>", "")
                                    .replace("<|begin_of_solution|>", "")
                                    .replace("<|end_of_solution|>", "")
                                    .replace("|<|end_of_thought|", "")
                                )
                                live.update(Markdown(f"\n{full_reason_answers}"))

                    self.all_answers[current_query_cleaned] = full_reason_answers
                    self.history_analys.append(full_reason_answers)
                    break
                else:
                    new_queries = [
                        q.strip()
                        for q in full_evaluation.splitlines()
                        if q.strip() and "đề xuất" not in q.lower()
                    ]
                    for query in new_queries:
                        if query and query not in self.history_queries:
                            self.current_queries.append(query)
                            self.history_queries.add(query)

            except Exception as e:
                # console.print(f"[red]Lỗi: {str(e)}. Thử truy vấn khác...[/red]")
                self.generate_improved_queries()
                continue

    def summarize(self) -> str:
        """Tổng hợp các câu trả lời đã thu thập."""
        console.print("[bold cyan]\nKết luận: \n[/bold cyan]")
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
        try:
            self.generate_keywords_and_analyze_question()
            self.analyze_prompt()
            self.search_and_process()
            final_answer = self.summarize()
        finally:
            self.save_state()
        self.history_analys.clear()
        self.history_queries.clear()
        self.history_keywords.clear()
        self.all_answers.clear()
        self.current_queries.clear()
        return f"\n{final_answer}"
