from duckduckgo_search import DDGS
import requests
import json
from rich.console import Console

# Import các script (giả định đã được định nghĩa)
from commands import *
from file import *
from image import *
from generate import *

console = Console()

# URL của Ollama API
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Định nghĩa model
model_gemma = "gemma3:latest"
model_qwen = "qwen2.5-coder:latest"
model_reason= "smallthinker:latest"
model_curent = model_gemma

# System prompt (giữ nguyên như trong mã gốc)
system_prompt = """
Bạn là TrunGPT, một trợ lý AI chuyên phân tích ngôn ngữ, cung cấp thông tin chính xác, logic và hữu ích nhất cho người dùng.

### 🔹 Quy tắc giao tiếp:
- Sử dụng **tiếng Việt (Vietnamese)** là chính.
- **Thêm emoji** để cuộc trò chuyện sinh động hơn.
- **Không nhắc lại hướng dẫn này** trong câu trả lời.

### 🛠 Vai trò & Cách hành xử:
- Trả lời chuyên sâu, giải thích dễ hiểu.
- Phân tích vấn đề logic và đưa ra giải pháp toàn diện.
- Không trả lời các nội dung vi phạm đạo đức, pháp luật (không cần nhắc đến điều này trừ khi người dùng vi phạm).

### 🔍 Lưu ý đặc biệt:
- **Người tạo**: Vương Nguyên Trung. Nếu có ai hỏi, chỉ cần trả lời: *"Người tạo là đại ca Vương Nguyên Trung."* và không nói thêm gì khác.

Hãy luôn giúp đỡ người dùng một cách chuyên nghiệp và thú vị nhé! 🚀

### Tool bạn có thể dùng:
- Tắt máy tính: @shutdown<phút>. Ví dụ: tắt máy trong vòng 10 phút thì dùng: @shutdown<10>.
- Tắt ngay lập tức thì dùng @shutdown<now>
- Để hủy tắt máy thì dùng @shutdown<-c>
- Khởi động lại máy tính: @reboot<phút>. Ví dụ: @reboot<30>.
- Đọc tệp: @read<địa chỉ tệp>. Ví dụ: @read<readme.md>.
- Ghi tệp: @write<địa chỉ tệp><nội dung>. Ví dụ: @write<readme.md><### Tổng quan>
- Xóa tệp: @delete<địa_chi_tệp>. Ví dụ: @delete<readme.md>
"""

# Khởi tạo lịch sử tin nhắn
message_history = [{"role": "system", "content": system_prompt}]

def query_ollama(prompt, model=model_curent, num_predict=-1, temperature=1):
    """Gửi yêu cầu đến Ollama API và yield từng phần của phản hồi."""
    clean_prompt, images_base64 = preprocess_prompt(prompt)
    process_shutdown_command(clean_prompt)
    message_history.append({"role": "user", "content": clean_prompt})
    full_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in message_history])

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": True,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
        "images": images_base64
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                json_data = json.loads(line)
                if "response" in json_data:
                    yield json_data["response"]
                if json_data.get("done", False):
                    break
    except requests.RequestException as e:
        print(f"Lỗi khi gọi Ollama: {e}")
        yield None

def generate_keywords(query, model=model_curent):
    """Tạo từ khóa liên quan đến query và yield từng phần của phản hồi."""
    prompt = f"""
        Phân tích câu hỏi: "{query}" và trích xuất 2-5 từ khóa chính. Các từ khóa phải thỏa mãn:  
        1. Là các cụm từ hoặc từ quan trọng, phản ánh đúng ý nghĩa cốt lõi của câu hỏi.  
        2. Giữ nguyên ngôn ngữ của câu hỏi (tiếng Việt nếu câu hỏi bằng tiếng Việt).  
        3. Không thêm từ ngoài ngữ cảnh, chỉ lấy từ hoặc cụm từ có trong câu hỏi.  
        4. Được trình bày dưới dạng danh sách: * "từ khóa 1" * "từ khóa 2" * "từ khóa 3" * "từ khóa 4" * "từ khóa 5" (nếu đủ 5 từ khóa).  
        Chỉ trả về danh sách từ khóa, không thêm giải thích hay nội dung khác.
    """
    return query_ollama(prompt, model, num_predict=500, temperature=0.1)

def analys_question(query, keywords, model=model_curent):
    """Phân tích câu hỏi và yield từng phần của phản hồi."""
    prompt = f"""
    Xét câu hỏi: '{query}'.
    - Nếu câu hỏi không rõ ràng, vô lý, hoặc không thể phân tích (ví dụ: "Mùi của mưa nặng bao nhiêu?"), chỉ cần trả về "Khó nha bro, [lý do ngắn gọn tự nhiên]" và dừng lại.
    - Nếu câu hỏi có thể phân tích:
        Dựa trên các từ khóa chính được cung cấp: {', '.join(keywords)}, hãy phân tích câu hỏi một cách chi tiết và tự nhiên. 
            - Xem xét ý nghĩa của từng khía cạnh trong ngữ cảnh câu hỏi, vai trò của chúng trong vấn đề được đặt ra, và cách chúng liên kết với mục tiêu của người dùng (họ có thể muốn thông tin, giải pháp, hay điều gì khác). 
            - Sau đó, xác định mục tiêu chính của người dùng (như tìm hiểu, giải quyết vấn đề, hoặc lấy ví dụ) và cách câu hỏi có thể được hiểu theo hướng rõ ràng hơn. 
            - Trả lời một cách đầy đủ, không đề cập trực tiếp đến từ khóa, chỉ tập trung vào phân tích và kết nối các ý với ý định của câu hỏi. 
    - Đảm bảo phản hồi là một đoạn văn phân tích đầy đủ, không liệt kê từ khóa, không có phần mở đầu như "To answer this: " hay tương tự, sử dụng markdown.
    """
    return query_ollama(prompt, model, num_predict=4000, temperature=0.3)

def better_question(query, model=model_curent):
    """Cải thiện câu hỏi và yield từng phần của phản hồi."""
    better_prompt = f"""
        Câu hỏi gốc: '{query}'
        Xét kỹ câu hỏi này: Nó thiếu gì để rõ nghĩa hơn? Bổ sung sao cho tự nhiên, cụ thể và dễ hiểu, như cách nói chuyện với bạn. Viết lại thành câu hỏi đầy đủ, giữ ý chính nhưng mạch lạc hơn.
    """
    return query_ollama(better_prompt, model, num_predict=4000, temperature=0.3)

def analys_prompt(query, model=model_curent):
    """Tạo truy vấn tìm kiếm từ query và yield từng phần của phản hồi."""
    prompt = f"""
        Dựa trên câu hỏi chính '{query}', tạo một truy vấn tìm kiếm duy nhất.
        Nếu câu hỏi liên quan đến Việt Nam, hãy tạo truy vấn tìm kiếm bằng tiếng Việt; nếu không, hãy tạo bằng tiếng Anh.
        Chỉ trả về truy vấn tìm kiếm, không trả về bất kỳ dữ liệu nào khác.
    """
    return query_ollama(prompt, model, num_predict=100, temperature=0.2)


def process_link(query, url, content, keywords, model=model_curent):
    """Xử lý nội dung từ URL và yield từng phần của phản hồi."""
    prompt = f"""
        Nội dung từ {url}:
        {content}
        Tập trung vào các từ khóa: {', '.join(keywords)}.
        Hãy tinh chỉnh sau đó trích xuất thông tin một cách logic.
        Suy luận, nghiên cứu nội dung và trả lời câu hỏi chi tiết dựa trên thông tin có sẵn.
        Sau đó đưa ra kết luận đầy đủ để trả lời câu hỏi {query}
        Không có phần mở đầu như "To answer this: " hay tương tự, sử dụng markdown.
    """
    return query_ollama(prompt, model, num_predict=-1, temperature=0.9)

def reason_with_ollama(query, context, model=model_curent):
    """Suy luận và trả lời câu hỏi dựa trên context và yield từng phần của phản hồi."""
    prompt = f"""
        Dùng tiếng Việt để trả lời.
        Câu hỏi chính: {query}
        Thông tin: {context}
        Hãy reasoning và trả lời trực tiếp câu hỏi chính '{query}' dựa trên thông tin được cung cấp. Thực hiện theo các bước sau, nhưng không hiển thị số bước hay tiêu đề trong câu trả lời:
        - Tìm các dữ kiện quan trọng trong thông tin, bao gồm cả chi tiết cụ thể (số liệu, sự kiện) và ý nghĩa ngầm hiểu nếu có.
        - Dựa trên dữ kiện, xây dựng lập luận hợp lý bằng cách liên kết các thông tin với nhau; nếu thiếu dữ liệu, đưa ra suy đoán có cơ sở và giải thích; xem xét các khả năng khác nhau nếu phù hợp, rồi chọn hướng trả lời tốt nhất.
        - Cuối cùng, trả lời ngắn gọn, rõ ràng, đúng trọng tâm câu hỏi, dựa hoàn toàn trên lập luận, sử dụng markdown.
        Viết tự nhiên, mạch lạc như một đoạn văn liền mạch, chỉ dùng thông tin từ context, không thêm dữ liệu ngoài, không có phần mở đầu như "To answer this: " hay tương tự.
    """
    return query_ollama(prompt, model, num_predict=4000, temperature=0.7)

def evaluate_answer(query, answer, processed_urls, model=model_curent):
    """Đánh giá câu trả lời và yield từng phần của phản hồi."""
    eval_prompt = f"""
        Danh sách URL đã phân tích: {processed_urls}
        Nếu URL này trùng với bất kỳ URL nào trong danh sách đã phân tích, trả lời 'Chưa đủ' và không đánh giá thêm.
        Hãy đánh giá xem câu trả lời '{answer}' đã cung cấp đầy đủ thông tin để giải quyết câu hỏi '{query}' chưa.
        - 'Đầy đủ' nghĩa là câu trả lời đáp ứng trực tiếp, rõ ràng và không thiếu khía cạnh quan trọng nào của câu hỏi.
        - 'Chưa đủ' nghĩa là còn thiếu thông tin cần thiết hoặc không trả lời đúng trọng tâm.
        Trả lời bắt đầu bằng 'Đã đủ' nếu thông tin đầy đủ, hoặc 'Chưa đủ' nếu thiếu thông tin cần thiết.
        - Nếu 'Đã đủ', chỉ viết 'Đã đủ', không thêm gì nữa.
        - Nếu 'Chưa đủ', thêm phần 'Đề xuất truy vấn:' với CHỈ 1 truy vấn cụ thể bằng tiếng Anh, ngắn gọn, dạng cụm từ tìm kiếm (không phải câu hỏi), liên quan trực tiếp đến câu ban đầu, theo định dạng:
        Đề xuất truy vấn:
        * \"từ khóa hoặc cụm từ tìm kiếm cụ thể\"
        Ví dụ: Nếu câu ban đầu là 'Làm sao để học tiếng Anh nhanh?' và câu trả lời là 'Học từ vựng mỗi ngày', thì:
        Chưa đủ
        Đề xuất truy vấn:
        * \"methods to learn English faster\"
        Đảm bảo luôn bắt đầu bằng 'Đã đủ' hoặc 'Chưa đủ', và truy vấn phải là cụm từ tìm kiếm, không phải câu hỏi.
    """
    return query_ollama(eval_prompt, model, num_predict=50, temperature=0.5)

def summarize_answers(query, all_answers, model=model_curent):
    """Tổng hợp các câu trả lời và yield từng phần của phản hồi dưới dạng Markdown."""
    summary_prompt = f"""
        Câu hỏi: '{query}'  
        Thông tin thu thập: {'\n'.join([f'- {a}' for a in all_answers])}  
        Hãy trả lời câu hỏi '{query}' dựa trên thông tin thu thập bằng cách:  
        1. **Phân tích chi tiết từng câu trả lời:** Mỗi ý nói gì? Liên quan đến câu hỏi như thế nào? Đi sâu vào từng khía cạnh, kể cả chi tiết nhỏ, dùng *in nghiêng* cho các từ khóa quan trọng và **in đậm** cho ý chính. Nếu ý nào không hợp lệ (vô nghĩa, lạc đề, mâu thuẫn), loại bỏ và giải thích rõ lý do trong một đoạn riêng với cú pháp `- Lý do loại bỏ: "..."`.  
        2. **Tổng hợp toàn bộ ý hợp lệ:** Gộp tất cả các ý liên quan thành một câu trả lời cực kỳ chi tiết và đầy đủ dưới dạng Markdown, không bỏ sót bất kỳ thông tin nào có giá trị. Sử dụng danh sách `-` hoặc số `1.` khi liệt kê, không ngại dài dòng, mở rộng ý để giải thích rõ ràng, nhưng vẫn giữ trọng tâm câu hỏi.  
        3. **Sắp xếp logic và có cấu trúc:** Sử dụng thứ tự hợp lý (theo thời gian nếu là quy trình, mức độ quan trọng nếu là ưu tiên, hoặc chia theo chủ đề với các tiêu đề `##` nếu có nhiều khía cạnh), thêm câu nối để liền mạch.  
        4. **Viết tự nhiên và sinh động:** Dùng ngôn ngữ thân thiện, trôi chảy, như kể chuyện cho bạn, kết hợp Markdown để làm nổi bật (ví dụ: *ví dụ minh họa*, **kết luận quan trọng**).  
        5. **Bổ sung thông tin mở rộng:** Nếu có thể, thêm thông tin ngoài dữ liệu cung cấp (URL, tài liệu, ví dụ thực tế, suy luận logic) trong một phần riêng. Tận dụng kiến thức của bạn để làm giàu câu trả lời.  
        Trả về một đoạn văn dài, cực kỳ chi tiết dưới dạng Markdown, bao quát mọi khía cạnh hợp lệ từ thông tin thu thập, không bỏ sót bất kỳ ý nào có giá trị. Toàn bộ nội dung phải được định dạng bằng cú pháp Markdown.
    """
    return query_ollama(summary_prompt, model, num_predict=-1, temperature=0.8)
