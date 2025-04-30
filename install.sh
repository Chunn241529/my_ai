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

# python3 -m pip3 install --upgrade pip3
pip3 install rich requests
pip3 install python-dotenv
pip3 install prompt_toolkit
pip3 install pillow
pip3 install numpy
pip3 install duckduckgo_search
pip3 install beautifulsoup4
pip3 install yt-dlp pygame
pip3 install youtube-search
pip3 install setuptools-rust
pip3 install speechrecognition pyaudio
pip3 install fastapi uvicorn pydantic aiohttp
pip3 install --upgrade torch transformers invisible_watermark accelerate peft
pip3 install --upgrade datasets sentence-transformers
pip3 install faiss-cpu
pip3 install pycryptodome
pip3 install -U xformers --index-url https://download.pytorch.org/whl/cu128
pip3 install sentencepiece
pip3 install huggingface_hub[hf_xet]
pip3 install retrying
pip3 install --upgrade realesrgan basicsr
pip3 install onnxruntime-gpu
pip3 install basicsr
pip3 install facexlib
pip3 install gfpgan
pip3 install opencv-python
pip3 install torchvision
pip3 install tqdm
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip3 uninstall diffusers
pip3 install diffusers


# pip3 install TTS

echo "Đã xong!"
