

import re
import requests
###image
import base64
from io import BytesIO
from PIL import Image


def convert_image_to_base64(image_url):
    """Tải ảnh từ URL và chuyển đổi thành base64."""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Đọc dữ liệu ảnh
        image = Image.open(BytesIO(response.content))
        buffered = BytesIO()
        image.save(buffered, format="PNG")  # Lưu dưới dạng PNG để dễ xử lý
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Lỗi khi xử lý ảnh: {e}")
        return None
    
def extract_image_urls(prompt):
    """Tìm các URL hình ảnh trong prompt theo cú pháp @img<URL>"""
    return re.findall(r'@img<(.*?)>', prompt)

def preprocess_prompt(prompt):
    """Thay thế các hình ảnh @img<URL> bằng nội dung base64."""
    image_urls = extract_image_urls(prompt)
    images_base64 = [convert_image_to_base64(url) for url in image_urls if convert_image_to_base64(url)]
    
    # Loại bỏ các tag @img<URL> trong prompt
    clean_prompt = re.sub(r'@img<.*?>', '', prompt).strip()
    
    return clean_prompt, images_base64