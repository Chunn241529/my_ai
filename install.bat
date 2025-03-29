@echo off

REM Kiểm tra xem môi trường ảo đã tồn tại chưa
if exist ".venv" (
    echo Moi truong ao virtual environment da ton tai.
) else (
    REM Tạo mới môi trường ảo
    echo Dang tao moi virtual environment...
    python -m venv .venv

    REM Kiểm tra việc tạo môi trường ảo có thành công không
    if not exist ".venv" (
        echo Loi khi tao moi truong ao virtual environment.
        exit /b 1
    )
)

REM Kích hoạt môi trường ảo
echo Kich hoat moi truong ao virtual environment...
call .venv\Scripts\activate

echo Dang cai thu vien...

REM Nâng cấp pip (tùy chọn, bỏ comment nếu cần)
REM python -m pip install --upgrade pip

REM Cài đặt các thư viện
pip install rich requests
pip install python-dotenv
pip install prompt_toolkit
pip install pillow
pip install numpy
pip install ollama
pip install duckduckgo_search
pip install beautifulsoup4

echo Da xong!

pause