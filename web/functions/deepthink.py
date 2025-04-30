from typing import AsyncGenerator, List

# Giả định các module này đã được định nghĩa
from web.functions.subfuncs.commands import *
from web.functions.subfuncs.file import *
from web.functions.subfuncs.generate import *

class DeepThink:
    # random number

    def __init__(self, initial_query: str):
        self.initial_query = initial_query
        self.history_analys: List[str] = []



    async def thinking(self) -> AsyncGenerator[str, None]:
        """Đưa ra câu trả lời dựa trên suy luận"""
        Prompt_thinking = f"""
        Bạn là một AI có khả năng suy luận và phân tích thông tin. Hãy suy nghĩ kỹ lưỡng về vấn đề sau đây {self.initial_query}.
        Lưu ý quan trọng: Suy nghĩ của bạn phải giống như bạn là một người đang mắc phải vấn đề. Không dùng markdown, không dùng code block, không dùng dấu ngoặc kép, không dùng dấu gạch ngang, không dùng bullet point, không dùng số thứ tự, không dùng emoji và không dùng bất kỳ ký tự nào khác ngoài văn bản thuần túy.
        """
        yield "\n<thinking>\n"
        think = query_ollama(prompt=Prompt_thinking, model="gemma3:12b")
        full_thinking = ""
        for part1 in think:
            if part1 is not None:
                full_thinking += part1
                yield part1
        yield "\n</thinking>\n\n"
        self.history_analys.append(full_thinking)

        summary_stream = summarize_answers(self.initial_query,self.history_analys,model="gemma3:12b")
        final_answer = ""

        for part2 in summary_stream:
            if part2 is not None:
                final_answer += part2
                yield part2

    async def run_thinking(self) -> AsyncGenerator[str, None]:
        """Chạy chat và yield phản hồi."""
        async for part in self.thinking():
            yield part
        self.history_analys.clear()
