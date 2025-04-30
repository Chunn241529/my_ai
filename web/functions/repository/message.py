import sqlite3
import json
import requests
import os
import sys

from datetime import datetime
from rich.console import Console


console = Console()

# Cấu hình
HISTORY_LIMIT = 50  # Giới hạn số tin nhắn trong RAM
# HISTORY_DB = os.path.join("logs", "chat_history.sqlite3")
HISTORY_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs", "chat_history.sqlite3")
# os.makedirs(log_dir, exist_ok=True)
OLLAMA_API_URL = "http://localhost:11434/api/chat"

class MessageRepository:
    def __init__(self, default_system_message, summary_model="gemma3"):
        self.sessions = {}  # {session_id: [messages]}
        self.default_system_message = default_system_message
        self.summary_model = summary_model
        self.init_db()

    def init_db(self):
        """Khởi tạo cơ sở dữ liệu SQLite trong thư mục logs."""
        # Tạo thư mục logs nếu chưa tồn tại
        os.makedirs(os.path.dirname(HISTORY_DB), exist_ok=True)

        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_message(self, session_id, role, content):
        """Lưu tin nhắn vào SQLite và bộ nhớ RAM."""
        if session_id not in self.sessions:
            self.sessions[session_id] = self.load_messages(session_id)

        # Thêm tin nhắn vào bộ nhớ
        self.sessions[session_id].append({"role": role, "content": content})

        # Lưu vào SQLite
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, timestamp)
        )
        conn.commit()
        conn.close()

        # Giới hạn số tin nhắn trong RAM
        if len(self.sessions[session_id]) > HISTORY_LIMIT:
            old_messages = self.sessions[session_id][:-HISTORY_LIMIT]
            summary = self.summarize_history(old_messages)
            self.sessions[session_id] = [
                {"role": "system", "content": f"Tóm tắt lịch sử: {summary}"}
            ] + self.sessions[session_id][-HISTORY_LIMIT:]

    def load_messages(self, session_id, limit=HISTORY_LIMIT):
        """Tải tin nhắn từ SQLite cho một phiên."""
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        messages = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
        conn.close()
        return messages[::-1]  # Đảo ngược để theo thứ tự thời gian

    def summarize_history(self, messages):
        """Tóm tắt lịch sử tin nhắn bằng mô hình ngôn ngữ."""
        prompt = """
        Tóm tắt các tin nhắn sau thành một đoạn ngắn gọn bằng tiếng Việt, giữ lại ý chính và ngữ cảnh quan trọng:
        {}
        Chỉ trả về đoạn tóm tắt, không thêm giải thích.
        """.format("\n".join([f"{msg['role']}: {msg['content']}" for msg in messages]))

        full_summary = ""
        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": self.summary_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "options": {"num_predict": 500, "temperature": 0.1},
                },
                stream=True
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    json_data = json.loads(line)
                    if "message" in json_data and "content" in json_data["message"]:
                        full_summary += json_data["message"]["content"]
        except requests.RequestException as e:
            console.print(f"[bold red]Lỗi khi tóm tắt lịch sử: {e}[/bold red]")
            full_summary = "Tóm tắt không khả dụng do lỗi."
        return full_summary

    def get_messages(self, session_id):
        """Lấy lịch sử tin nhắn, đảm bảo có tin nhắn hệ thống."""
        if session_id not in self.sessions:
            self.sessions[session_id] = self.load_messages(session_id)
        if not any(msg["role"] == "system" for msg in self.sessions[session_id]):
            self.sessions[session_id].insert(0, {"role": "system", "content": self.default_system_message})
        return self.sessions[session_id]

    def clear_session(self, session_id):
        """Xóa lịch sử của một phiên."""
        self.sessions[session_id] = [{"role": "system", "content": self.default_system_message}]
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
