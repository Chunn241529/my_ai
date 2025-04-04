
import os
import re

def process_file_read(input_text):
    """Xử lý việc đọc nội dung từ tệp được chỉ định trong input_text."""
    pattern = r"@r<([^>]+)>"
    matches = re.findall(pattern, input_text)
    for file_path in matches:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.r()
                    input_text = input_text.replace(f"@r<{file_path}>", content)
            except Exception as e:
                input_text = input_text.replace(f"@r<{file_path}>", f"[Lỗi đọc tệp: {e}]")
        else:
            input_text = input_text.replace(f"@r<{file_path}>", "[Tệp không tồn tại]")
    return input_text

def process_file_w(full_response, input_text):
    """Xử lý việc ghi phản hồi vào tệp nếu được yêu cầu."""
    pattern = r"@w<([^>]+)>"
    matches = re.findall(pattern, input_text)
    for file_path in matches:
        if "ghi vào" in input_text.lower() or "w to" in input_text.lower():
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.w(full_response)
                return f"Đã ghi phản hồi vào {file_path}"
            except Exception as e:
                return f"Lỗi khi ghi tệp: {e}"
    return full_response