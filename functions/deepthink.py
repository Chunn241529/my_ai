from duckduckgo_search import DDGS
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from typing import List

# Giả định các module này đã được định nghĩa
from functions.subfuncs.commands import *
from functions.subfuncs.file import *
from functions.subfuncs.image import *
from functions.generate import *

console = Console()


class DeepThink:
    #random number

    def __init__(self, initial_query: str):
        """
        Khởi tạo đối tượng DeepSearch với câu hỏi ban đầu và các tham số cấu hình.
        
        Args:
            initial_query (str): Câu hỏi/truy vấn ban đầu.
            max_iterations (int): Số lần lặp tối đa (mặc định là 5).
            max_results (int): Số kết quả tìm kiếm tối đa mỗi truy vấn (mặc định là 10).
        """
        self.initial_query = initial_query
        self.history_analys: List[str] = []

        ### config live
        self.refresh_second = 10 
        self.vertical_overflow = "ellipsis" #"visible"


    def thinking(self):
        """Suy luận"""

        with Live(Markdown("Suy luận..."), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
            think = thinking(self.initial_query)
            full_thinking=""
            for part in think:
                if part is not None:
                    full_thinking += part
                    live.update(Markdown(f"\n{full_thinking}"))
            self.history_analys.append(full_thinking)

    def summarize_think(self) -> str:
        """Tổng hợp các câu trả lời đã thu thập."""
        with Live(Markdown("Chờ xíu... "), refresh_per_second=self.refresh_second, console=console, vertical_overflow=self.vertical_overflow) as live:
            summary_stream = summarize_answers(self.initial_query, self.history_analys)
            final_answer = ""

            for part in summary_stream:
                if part is not None:
                    final_answer += part
                    live.update(Markdown(f"\n{final_answer}"))

        return final_answer
    
    def run_think(self) -> str:
        self.thinking()
        console.print("\n\n")
        final_answer = self.summarize_think()
        self.history_analys.clear()
        return f"\n{final_answer}"
