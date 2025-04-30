import re
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from typing import List, Dict, Tuple
from urllib.parse import urljoin
import os

import logging
logging.getLogger().setLevel(logging.WARNING)  # Chỉ hiển thị log từ WARNING trở lên

def search_web(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Tìm kiếm trên web bằng DuckDuckGo và trả về danh sách kết quả."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                # Kiểm tra sự tồn tại của các khóa
                title = r.get("title", "No title")
                href = r.get("href", "")
                body = r.get("body", "No snippet")
                if href:  # Chỉ thêm nếu có URL hợp lệ
                    results.append({"title": title, "url": href, "snippet": body})
    except Exception as e:
        print(f"Error searching web for '{query}': {str(e)}")
    return results

def extract_content(url: str, snippet: str = "", tags: List[str] = None) -> str:
    """Trích xuất nội dung từ URL, bao gồm đoạn trích và văn bản từ các thẻ HTML."""
    if tags is None:
        tags = ["p", "h1", "h2", "h3", "a", "span", "table", "textarea"]
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        content_parts = [
            tag.get_text(strip=True)
            for tag in soup.find_all(tags)
            if tag.get_text(strip=True)
        ]
        content = f"Snippet: {snippet}\n" + "\n".join(content_parts)
        return content
    except requests.RequestException as e:
        return f"Error fetching {url}: {str(e)}"

def extract_hrefs(url: str) -> Tuple[List[str], str]:
    """Trích xuất tất cả liên kết (href) từ một URL, trả về (liên kết, lỗi)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        href_list = [
            urljoin(url, tag["href"])  # Chuyển liên kết tương đối thành tuyệt đối
            for tag in soup.find_all("a", href=True)
        ]
        return href_list, ""
    except requests.RequestException as e:
        return [], f"Error fetching {url}: {str(e)}"

def extract_url_from_input(input_text: str) -> str:
    """Trích xuất URL đầu tiên từ chuỗi đầu vào của người dùng."""
    URL_PATTERN = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*?(?=\s|$)"
    match = re.search(URL_PATTERN, input_text)
    return match.group(0) if match else ""

def extract_image_path(input_text: str) -> str:
    """Trích xuất đường dẫn file ảnh từ chuỗi đầu vào, hỗ trợ Windows, Linux, macOS."""
    IMAGE_PATH_PATTERN = r"(?:(?:[a-zA-Z]:[\\/])|\/)?[\w\-\.\/\\]*(?:[\w\-]+\.(?:jpg|jpeg|png|gif|bmp|webp))"
    match = re.search(IMAGE_PATH_PATTERN, input_text, re.IGNORECASE)
    if match:
        path = match.group(0)
        if os.path.exists(path):
            return path
    return ""

def extract_image_url(input_text: str) -> str:
    """Trích xuất URL ảnh đầu tiên từ chuỗi đầu vào của người dùng."""
    IMAGE_URL_PATTERN = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*?\.(?:jpg|jpeg|png|gif|bmp|webp)(?=\s|$)"
    match = re.search(IMAGE_URL_PATTERN, input_text, re.IGNORECASE)
    return match.group(0) if match else ""


def fallback_search(query: str) -> str:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=2)
            return (
                "\n".join([r["body"] for r in results])
                if results
                else "Không tìm thấy thông tin bổ sung."
            )
