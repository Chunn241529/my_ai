

from typing import AsyncGenerator

# Giả định các module này đã được định nghĩa
from web.functions.subfuncs.commands import *
from web.functions.subfuncs.file import *
from web.functions.subfuncs.generate import *
from utils.helper.web_utils import *

class Chat:
    def __init__(self, initial_query: str):
        self.initial_query = initial_query

        self.only_url = extract_url_from_input(self.initial_query) or ""

    async def chat(self) -> AsyncGenerator[str, None]:
        """Tạo phản hồi streaming từ câu hỏi."""
        image_path = extract_image_path(self.initial_query) or ""
        image_url = extract_image_url(self.initial_query) or ""
        content = extract_content(self.only_url) or ""


        if any(
            keyword in content.lower()
            for keyword in [
                "đăng nhập",
                "sign in",
                "không thể truy cập",
                "Forbidden",
                "404 Not Found",
                "Connection Refused",
            ]
        ):
            fallback = self.fallback_search(self.only_url)
            content += f"\nThông tin bổ sung từ tìm kiếm: {fallback}"

        # Gọi hàm chat từ generate.py và yield từng phần
        summary_stream = chat(
            query=self.initial_query,
            url=self.only_url,
            image_path=image_path,
            url_image=image_url,
            content=content
        )

        final_answer = ""
        for part in summary_stream:
            if part is not None:
                final_answer += part
                yield part


    async def run_chat(self) -> AsyncGenerator[str, None]:
        """Chạy chat và yield phản hồi."""
        async for part in self.chat():
            yield part
