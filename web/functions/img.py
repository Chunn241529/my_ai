import logging
import os
from typing import AsyncGenerator

# Giả định các module này đã được định nghĩa
from web.functions.subfuncs.commands import *
from web.functions.subfuncs.file import *
from web.functions.subfuncs.generate import *
from web.functions.subfuncs.image import genImage  # Import genImage từ image.py

# Suppress all logging from sentence_transformers and datasets
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("datasets").setLevel(logging.ERROR)

class ChatImage:
    def __init__(self, initial_query: str):
        self.initial_query = initial_query
        os.environ["JAX_PLATFORM_NAME"] = "cpu"

    async def generate_image_async(self, prompt: str) -> tuple[str, str]:
        """Tạo ảnh từ prompt và trả về (result_type, result)."""
        try:
            image_paths = genImage(prompt)
            image_path = image_paths if isinstance(image_paths, str) else image_paths[0]
            if not image_path or not os.path.exists(image_path):
                raise ValueError(f"Đường dẫn ảnh không hợp lệ: {image_path}")
            return "success", image_path
        except Exception as e:
            error_msg = f"Lỗi khi tạo ảnh: {str(e)}"
            return "error", error_msg

    async def chat_image(self) -> AsyncGenerator[str, None]:
        """Tạo phản hồi streaming cho yêu cầu tạo ảnh."""
        # Tạo prompt từ câu hỏi
        analys_stream = image_chat_(query=self.initial_query)
        analys = ""
        for part in analys_stream:
            if part:
                analys += part
                yield part

        # Làm sạch phân tích
        _analys_ = (
            analys.replace("`", "").replace("'", "").replace("*", "").replace('"', "")
        )

        # Tạo prompt cho Stable Diffusion
        prompt_sd = generate_image(query=_analys_)
        generate_prompt = ""
        for part in prompt_sd:
            if part is not None:
                generate_prompt += part

        # Tạo ảnh
        result_type, result = await self.generate_image_async(generate_prompt)

        if result_type == "success":
            yield result
        else:
            yield result
