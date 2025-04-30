import os
import subprocess
import sys
import re

VIET_TTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "modules", "vietTTS"))

if not os.path.exists(VIET_TTS_DIR):
    raise FileNotFoundError(f"Thư mục vietTTS không tồn tại tại: {VIET_TTS_DIR}")
sys.path.append(VIET_TTS_DIR)

def clean_text(text):
    text = re.sub(r'\bAI\b', 'Ây ai', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'([.,!?])([^\s])', r'\1 \2', text)
    return text

def run_viettts_synthesis(text="nhập text vào đây", output="assets/infore/clip.wav"):
    cleaned_text = clean_text(text)

    try:
        output_path = os.path.abspath(output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        lexicon_file = os.path.join(VIET_TTS_DIR, "assets", "infore", "lexicon.txt")
        if not os.path.exists(lexicon_file):
            raise FileNotFoundError(f"Không tìm thấy file lexicon: {lexicon_file}")
        synth_cmd = [
            "python3", "-m", "vietTTS.synthesizer",
            "--text", cleaned_text,
            "--output", output_path,
            "--lexicon-file", os.path.abspath(lexicon_file),
            "--silence-duration", "0.5"
        ]
        result = subprocess.run(synth_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=VIET_TTS_DIR)
        if result.returncode == 0:
            return True
        else:
            print(f"Có lỗi xảy ra: {result.stderr.decode()}")
            return False
    except FileNotFoundError as e:
        print(f"Lỗi: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi chạy vietTTS: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return False

# if __name__ == "__main__":
#     text = f"""
#     """
#     run_viettts_synthesis(text=text, output="assets/infore/clip.wav")
