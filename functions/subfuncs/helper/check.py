import os
import platform
import subprocess
import sys

def check_and_install_dependencies():
    system = platform.system().lower()
    print(f"Hệ điều hành: {system}")

    if system == "linux":
        # Kiểm tra và cài đặt trên Linux
        try:
            # Kiểm tra ffmpeg
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("FFmpeg đã được cài đặt.")
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            print("FFmpeg chưa được cài đặt. Đang tiến hành cài đặt...")
            try:
                # Giả sử dùng Ubuntu/Debian, thay đổi nếu dùng distro khác
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"], check=True)
                print("FFmpeg đã được cài đặt thành công.")
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi cài đặt FFmpeg: {e}")
                sys.exit(1)

        try:
            # Kiểm tra libmodplug (thông qua pkg-config hoặc tìm file)
            result = subprocess.run(["pkg-config", "--modversion", "libmodplug"], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Libmodplug đã được cài đặt (phiên bản: {result.stdout.strip()}).")
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            print("Libmodplug chưa được cài đặt. Đang tiến hành cài đặt...")
            try:
                # Giả sử dùng Ubuntu/Debian
                subprocess.run(["sudo", "apt-get", "install", "-y", "libmodplug1"], check=True)
                print("Libmodplug đã được cài đặt thành công.")
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi cài đặt libmodplug: {e}")
                sys.exit(1)

    elif system == "windows":
        # Kiểm tra và cài đặt trên Windows
        try:
            # Kiểm tra ffmpeg
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print("FFmpeg đã được cài đặt.")
            else:
                raise FileNotFoundError
        except FileNotFoundError:
            print("FFmpeg chưa được cài đặt.")
            try:
                # Sử dụng winget để cài đặt FFmpeg (yêu cầu Windows 10/11 với winget)
                print("Đang thử cài đặt FFmpeg qua winget...")
                subprocess.run(["winget", "install", "--id", "Gyan.FFmpeg", "-e"], check=True)
                print("FFmpeg đã được cài đặt thành công qua winget.")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Không thể cài tự động qua winget. Vui lòng cài thủ công:")
                print("1. Tải FFmpeg từ: https://ffmpeg.org/download.html")
                print("2. Thêm đường dẫn FFmpeg vào biến môi trường PATH.")
                sys.exit(1)

        # Trên Windows, libmodplug thường được tích hợp trong pygame, không cần cài riêng
        print("Kiểm tra libmodplug trên Windows...")
        try:
            import pygame
            pygame.mixer.init()
            print("Pygame và libmodplug hoạt động bình thường.")
        except Exception as e:
            print(f"Lỗi với pygame/libmodplug: {e}")
            print("Đề xuất: Cài lại pygame bằng lệnh 'pip install pygame --force-reinstall'")
            sys.exit(1)

    else:
        print(f"Hệ điều hành {system} không được hỗ trợ tự động.")
        sys.exit(1)

def main():
    print("Kiểm tra và cài đặt các thư viện cần thiết...")
    check_and_install_dependencies()
    print("Hoàn tất kiểm tra và cài đặt.")

if __name__ == "__main__":
    main()