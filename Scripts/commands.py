#import
import re
import sys
import os
from rich.console import Console
console = Console()


def process_shutdown_command(text):
    """
    Kiểm tra xem text có chứa lệnh @shutdown<phút> hay không.
    Nếu có, thực hiện lệnh shutdown -h <phút> trên Linux.
    """
    shutdown_match = re.search(r'@shutdown<(\d+)>', text)
    if shutdown_match:
        shutdown_time = shutdown_match.group(1)
        if sys.platform.startswith("linux"):
            console.print(f"\n[INFO] Thực hiện lệnh tắt máy: shutdown -h {shutdown_time}")
            os.system(f"shutdown -h {shutdown_time}")
        else:
            print("[WARNING] Lệnh shutdown chỉ hỗ trợ trên Linux!")