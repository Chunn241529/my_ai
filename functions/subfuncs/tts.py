import os
import subprocess
import sys

# Đường dẫn tới thư mục vietTTS (tùy chỉnh theo cấu trúc thực tế)
# Ví dụ: nếu tts.py ở /my_ai/functions/subfuncs/ và vietTTS ở /project/modules/vietTTS/
VIET_TTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "modules", "vietTTS"))

# Kiểm tra xem thư mục có tồn tại không
if not os.path.exists(VIET_TTS_DIR):
    raise FileNotFoundError(f"Thư mục vietTTS không tồn tại tại: {VIET_TTS_DIR}")
sys.path.append(VIET_TTS_DIR)

def run_viettts_synthesis(text="nhập text vào đây", output="assets/infore/clip.wav"):
    """
    Sử dụng vietTTS để tổng hợp giọng nói tiếng Việt dựa trên văn bản đầu vào.
    File tts.py nằm ngoài thư mục vietTTS, lexicon nằm trong modules/vietTTS/assets/infore/.
    
    Args:
        text (str): Văn bản cần tổng hợp.
        output (str): Đường dẫn file đầu ra (mặc định: "assets/infore/clip.wav").
    """
    try:
        # Đảm bảo thư mục đầu ra tồn tại
        output_path = os.path.abspath(output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Đường dẫn tới file lexicon
        lexicon_file = os.path.join(VIET_TTS_DIR, "assets", "infore", "lexicon.txt")
        
        # Kiểm tra xem file lexicon có tồn tại không
        if not os.path.exists(lexicon_file):
            raise FileNotFoundError(f"Không tìm thấy file lexicon: {lexicon_file}")

        # Lệnh tổng hợp âm thanh
        synth_cmd = [
            "python3", "-m", "vietTTS.synthesizer",
            "--text", text,
            "--output", output_path,
            "--lexicon-file", os.path.abspath(lexicon_file),
            "--silence-duration", "0.2"
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
#     # Đọc văn bản từ file transcript.txt

#     text = f"""
#         “Con đúng là sát nhân mà, bảo con chăm sóc cho em gái thật tốt mà con lại làm vậy sao? Niệm Tư của tôi…”

#         Đầu Giang Niệm Tư đau như búa bổ, cô vừa mới tỉnh lại đã nghe thấy tiếng khóc nức nở.

#         “Mẹ, em gái tỉnh rồi.” Chàng trai bị nghe mắng và chọc đầu nhìn Giang Niệm Tư chớp chớp mắt, đôi mắt đỏ hoe lập tức trợn to mắt kinh ngạc, lập tức nhảy lên giường.

#         Đinh Hồng Mai vừa nghe thấy đã nhanh chóng đến đầu giường bế Giang Niệm Tư lên: “Niệm Tư, con của mẹ, con thế nào rồi?”

#         Giang Niệm Tư có chút mơ hồ, cô nghi hoặc nhìn xung quanh.

#         Mái nhà làm bằng gỗ sẫm màu, bức tường lớp bằng bùn đất, bề mặt có nhiều vết loang lổ.

#         Chàng trai ngồi xổm trước giường của cô, vẻ mặt sốt ruột, quần áo trên người còn có vài mảnh chắp vá.

#     """
#     run_viettts_synthesis(text=text, output="assets/infore/clip.wav")