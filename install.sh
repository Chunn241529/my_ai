# Kiểm tra xem môi trường ảo đã tồn tại chưa
if [ -d ".venv" ]; then
    echo "Môi trường ảo virtual environment đã tồn tại."
else
    # Tạo mới môi trường ảo
    echo "Đang tạo mới virtual environment..."
    python3 -m venv .venv

    # Kiểm tra việc tạo môi trường ảo có thành công không
    if [ ! -d ".venv" ]; then
        echo "Lỗi khi tạo môi trường ảo virtual environment."
        exit 1
    fi
fi

# Kích hoạt môi trường ảo
echo "Kích hoạt môi trường ảo virtual environment..."
source .venv/bin/activate

echo "Đang cài thư viện..."

# python3 -m pip3 install --upgrade pip
pip3 install rich requests
pip3 install python-dotenv
pip3 install prompt_toolkit
pip3 install pillow
pip3 install numpy
pip3 install duckduckgo_search
pip3 install beautifulsoup4
pip3 install yt-dlp pygame
pip3 install youtube-search
pip3 install gtts pydub

echo "Đã xong!"
