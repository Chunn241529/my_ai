#import
import re
import sys
import os
import time
from rich.console import Console
console = Console()


def process_shutdown_command(text):
    """
    Kiểm tra xem text có chứa lệnh @shutdown<phút> hay không.
    Nếu có, thực hiện lệnh shutdown -h <phút> trên Linux và đếm ngược cooldown bằng vòng lặp for.
    """
    shutdown_match = re.search(r'@shutdown<(\d+)>', text)
    if shutdown_match:
        shutdown_time = int(shutdown_match.group(1))  # Chuyển sang int
        if sys.platform.startswith("linux"):
            console.print(f"\n[INFO] Thực hiện lệnh tắt máy: shutdown -h {shutdown_time}")
            os.system(f"shutdown -h {shutdown_time}")
            
            # Đếm ngược cooldown bằng vòng lặp for (tính bằng giây)
            cooldown_seconds = shutdown_time * 60  # Chuyển phút thành giây
            console.print(f"[INFO] Bắt đầu cooldown trong {shutdown_time} phút ({cooldown_seconds} giây)...")
            
            for i in range(cooldown_seconds, 0, -1):  # Đếm ngược từ cooldown_seconds về 1
                console.print(f"[COOLDOWN] Còn {i} giây...", end="\r")  # end="\r" để ghi đè dòng
                time.sleep(1)  # Chờ 1 giây mỗi lần lặp
            
        else:
            console.print("[WARNING] Lệnh shutdown chỉ hỗ trợ trên Linux!")
    