from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
import asyncio
from typing import AsyncGenerator
from web.functions.chat import Chat
from web.functions.deepsearch import DeepSearch
from web.functions.deepthink import DeepThink
from web.functions.img import ChatImage
import re
import os
from pathlib import Path

app = FastAPI(title="TrunGPT Web API", description="API cho ứng dụng chat TrunGPT trên web")

# Thư mục lưu ảnh (cấu hình theo thư mục mà genImage sử dụng)
IMAGE_DIR = Path("/home/nguyentrung/Documents/project/my_ai/models/img")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

class ChatRequest(BaseModel):
    query: str
    is_deepthink: bool = False
    is_deepsearch: bool = False
    is_image: bool = False

class DownloadImageRequest(BaseModel):
    image_path: str


async def stream_chat_response(chat_instance: Chat) -> AsyncGenerator[str, None]:
    """Tạo phản hồi streaming từ hàm chat."""
    async for part in chat_instance.run_chat():
        if part is not None:
            yield part
        await asyncio.sleep(0.1)

async def stream_deepthink_response(chat_instance: DeepThink) -> AsyncGenerator[str, None]:
    """Tạo phản hồi streaming từ hàm chat."""
    async for part in chat_instance.run_thinking():
        if part is not None:
            yield part
        await asyncio.sleep(0.1)

async def stream_deepsearch_response(chat_instance: DeepSearch) -> AsyncGenerator[str, None]:
    """Tạo phản hồi streaming từ hàm chat."""
    async for part in chat_instance.run_deepsearch():
        if part is not None:
            yield part
        await asyncio.sleep(0.1)

async def stream_image_response(image_instance: ChatImage) -> AsyncGenerator[str, None]:
    """Tạo phản hồi streaming từ hàm chat_image."""
    async for part in image_instance.chat_image():
        if part is not None:
            yield part
        await asyncio.sleep(0.1)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint để xử lý yêu cầu chat."""

    _deepthink_ = request.is_deepthink
    _deepsearch_ = request.is_deepsearch
    _image_ = request.is_image

    if _deepthink_:
        try:
            chat_instance = DeepThink(initial_query=request.query)
            return StreamingResponse(
                stream_deepthink_response(chat_instance),
                media_type="text/plain"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý yêu cầu: {str(e)}")
    elif _deepsearch_:
        try:
            chat_instance = DeepSearch(initial_query=request.query)
            return StreamingResponse(
                stream_deepsearch_response(chat_instance),
                media_type="text/plain"
            )
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý yêu cầu: {str(e)}")
    elif _image_:
        try:
            chat_instance = ChatImage(initial_query=request.query)
            return StreamingResponse(
                stream_image_response(chat_instance),
                media_type="text/plain"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý yêu cầu: {str(e)}")
    else:
        try:
            chat_instance = Chat(initial_query=request.query)
            return StreamingResponse(
                stream_chat_response(chat_instance),
                media_type="text/plain"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý yêu cầu: {str(e)}")


@app.get("/download-image")
async def download_image_endpoint(image_path: str):
    """Endpoint để tải ảnh dựa trên image_path qua query parameter, tự động kích hoạt tải về."""
    try:
        # Chuyển image_path thành đối tượng Path và nối với IMAGE_DIR
        image_file = Path(image_path).name  # Chỉ lấy tên file, bỏ đường dẫn
        image_path = IMAGE_DIR / image_file  # Nối với IMAGE_DIR

        # Kiểm tra file có nằm trong thư mục IMAGE_DIR không
        if not image_path.is_relative_to(IMAGE_DIR):
            raise HTTPException(status_code=403, detail="Truy cập đường dẫn không được phép")

        # Kiểm tra định dạng file
        if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Định dạng file không được hỗ trợ")

        # Kiểm tra file tồn tại
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="File ảnh không tồn tại")

        # Trả về file ảnh với Content-Disposition để tải về
        return FileResponse(
            path=image_path,
            media_type="image/" + image_path.suffix.lstrip("."),
            filename=image_path.name,
            headers={"Content-Disposition": f"attachment; filename={image_path.name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải ảnh: {str(e)}")

@app.get("/health")
async def health_check():
    """Kiểm tra trạng thái API."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import torch
    torch.cuda.empty_cache()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
