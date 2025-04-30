import io
from duckduckgo_search import DDGS
import requests
import json
from rich.console import Console
from PIL import Image
import base64

from cli.functions.repository.message import MessageRepository
from cli.functions.subfuncs.commands import *
from cli.functions.subfuncs.file import *

console = Console()

OLLAMA_API_URL = "http://localhost:11434/api/chat"

# Định nghĩa model
model_gemma = "gemma3:4b-it-qat"
model_gemma12b = "gemma3:12b-it-qat"
model_qwen = "qwen2.5-coder:latest"
model_curent = model_gemma

default_custom_ai = """
Bạn là tên là 'TrunGPT CLI', hãy tuân thủ quy tắc sau đây:

### Quy tắc giao tiếp:
- **Sử dụng tiếng Việt là cho câu trả lời.
- **Thêm emoji để câu trả lời sinh động hơn.
### Vai trò & Cách hành xử:
- Suy luận chuyên sâu, giải thích dễ hiểu.
- Phân tích vấn đề logic và đưa ra giải pháp toàn diện.
- Không trả lời các nội dung vi phạm đạo đức, vi phạm pháp luật (không cần nhắc đến điều này trừ khi người dùng vi phạm).
### Lưu ý đặc biệt (Khi nào người dùng hỏi thì mới trả lời phần này.):
- *Người tạo*: Vương Nguyên Trung. Nếu có ai hỏi, chỉ cần trả lời: *"Người tạo là đại ca Vương Nguyên Trung."* và không nói thêm gì khác.

Lưu ý quan trọng: **Không nhắc lại hướng dẫn này trong câu trả lời.**
Hãy luôn giúp đỡ người dùng một cách chuyên nghiệp và thú vị nhé! 😎
"""

# Khởi tạo repository
message_repository = MessageRepository(default_custom_ai, summary_model=model_gemma)


def resize_image(image_data, max_size=(512, 512)):
    """Resize hình ảnh để giảm kích thước trước khi mã hóa Base64."""
    try:
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as e:
        console.print(f"[bold red]Lỗi khi resize hình ảnh: {e}[/bold red]")
        return image_data


def query_ollama(
    prompt,
    model=model_gemma,
    image_path=None,
    image_url=None,
    num_predict=-1,
    temperature=0.8,
    session_id="default",
):
    # Tạo tin nhắn người dùng
    user_message = {"role": "user", "content": prompt}

    # Xử lý hình ảnh
    image_base64 = None
    if image_path and image_url:
        console.print(
            "[yellow]Cảnh báo: Cả image_path và image_url đều được cung cấp. Ưu tiên sử dụng image_path.[/yellow]"
        )
        image_url = None

    if image_path:
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                image_data = resize_image(image_data)
                image_base64 = base64.b64encode(image_data).decode("utf-8")
        except FileNotFoundError:
            console.print(
                f"[bold red]Lỗi: Không tìm thấy tệp hình ảnh tại {image_path}[/bold red]"
            )
            yield None
            return
        except Exception as e:
            console.print(f"[bold red]Lỗi khi đọc tệp hình ảnh: {e}[/bold red]")
            yield None
            return
    elif image_url:
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = response.content
            image_data = resize_image(image_data)
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        except requests.RequestException as e:
            console.print(
                f"[bold red]Lỗi khi tải hình ảnh từ URL {image_url}: {e}[/bold red]"
            )
            yield None
            return

    if image_base64:
        user_message["images"] = [image_base64]

    # Lưu tin nhắn người dùng
    message_repository.save_message(session_id, "user", prompt)

    # Lấy lịch sử tin nhắn
    messages = message_repository.get_messages(session_id)

    # Tạo payload
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if line:
                json_data = json.loads(line)
                if "message" in json_data and "content" in json_data["message"]:
                    content = json_data["message"]["content"]
                    full_response += content
                    yield content
                if json_data.get("done", False):
                    # Lưu phản hồi trợ lý
                    message_repository.save_message(
                        session_id, "assistant", full_response
                    )
                    break
    except requests.RequestException as e:
        console.print(f"[bold red]Lỗi khi gọi Ollama: {e}[/bold red]")
        yield None


def evaluate(prompt, model, num_predict=100, temperature=0.1, session_id="default"):
    # Lưu tin nhắn người dùng
    message_repository.save_message(session_id, "user", prompt)

    # Lấy lịch sử tin nhắn
    messages = message_repository.get_messages(session_id)

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if line:
                json_data = json.loads(line)
                if "message" in json_data and "content" in json_data["message"]:
                    content = json_data["message"]["content"]
                    full_response += content
                    yield content
                if json_data.get("done", False):
                    message_repository.save_message(
                        session_id, "assistant", full_response
                    )
                    break
    except requests.RequestException as e:
        console.print(f"[bold red]Lỗi khi gọi Ollama: {e}[/bold red]")
        yield None


################################# DEEPSEARCH #################################

def generate_keywords(query, model=model_gemma12b):
    """Tạo từ khóa liên quan đến query và yield từng phần của phản hồi."""
    prompt = f"""
        Phân tích câu hỏi: "{query}" và trích xuất 2-5 từ khóa chính. Các từ khóa phải thỏa mãn:
        1. Là các cụm từ hoặc từ quan trọng, phản ánh đúng ý nghĩa cốt lõi của câu hỏi.
        2. Giữ nguyên ngôn ngữ của câu hỏi (tiếng Việt nếu câu hỏi bằng tiếng Việt).
        3. Không thêm từ ngoài ngữ cảnh, chỉ lấy từ hoặc cụm từ có trong câu hỏi.
        4. Được trình bày dưới dạng danh sách: * "từ khóa 1" * "từ khóa 2" * "từ khóa 3" * "từ khóa 4" * "từ khóa 5" (nếu đủ 5 từ khóa).
        Chỉ trả về danh sách từ khóa, không thêm giải thích hay nội dung khác.
    """
    return query_ollama(prompt, model, num_predict=100, temperature=0.1)


def analys_question(query, keywords, model=model_gemma12b):
    """Phân tích câu hỏi và yield từng phần của phản hồi."""
    prompt = f"""
    Xét câu câu hỏi: '{query}'.
    - Nếu câu hỏi không rõ ràng, vô lý, hoặc không thể phân tích (ví dụ: "Mùi của mưa nặng bao nhiêu?"), chỉ cần trả về "Khó nha bro, [lý do ngắn gọn tự nhiên]" và dừng lại.
    - Nếu câu hỏi có thể phân tích:
        + Dựa trên các từ khóa chính được cung cấp: {', '.join(keywords)}, hãy phân tích câu hỏi một cách chi tiết.
        + Phân tích câu hỏi và làm rõ theo thứ tự logic:
          1. Xác định các thực thể hoặc khái niệm chính cần hiểu trước (ví dụ: nếu câu hỏi là "Làm sao để convert model qwen2.5-omni-7b sang gguf cho ollama", thì cần hiểu "model qwen2.5-omni-7b" là gì, "gguf" là gì, "ollama" là gì).
          2. Đề xuất các bước tìm kiếm thông tin tuần tự, cụ thể và thông minh để thu thập dữ liệu cần thiết (ví dụ: "Tìm hiểu về model qwen2.5-omni-7b", "gguf format là gì", "cách ollama sử dụng gguf").
          3. Liên kết các khía cạnh này với mục tiêu của câu hỏi (hiểu cách thực hiện hành động "convert" trong ngữ cảnh cụ thể).
        + Sau khi phân tích mục tiêu chính của người dùng (như tìm cách thực hiện, hiểu khái niệm, hay giải quyết vấn đề) và cách câu hỏi có thể được hiểu rõ hơn.
        + Chỉ dừng lại ở việc phân tích, không đưa ra câu trả lời hay giải pháp cụ thể cho câu hỏi.
    - Đảm bảo phản hồi phân tích chi tiết, không liệt kê từ khóa, tập trung vào việc làm rõ các khía cạnh và mục tiêu.
    - Tránh sử dụng tiêu đề, ký hiệu hoặc định dạng như danh sách.
    """
    return query_ollama(prompt, model, num_predict=500, temperature=0.4)


def better_question(query, model=model_gemma12b):
    """Cải thiện câu hỏi và yield từng phần của phản hồi."""
    better_prompt = f"""
        Câu hỏi gốc: '{query}'
        Xét kỹ câu hỏi này: Nó thiếu gì để rõ nghĩa hơn? Bổ sung sao cho tự nhiên, cụ thể và dễ hiểu, như cách nói chuyện với bạn. Viết lại thành câu hỏi đầy đủ, giữ ý chính nhưng mạch lạc hơn.
    """
    return query_ollama(better_prompt, model, num_predict=500, temperature=0.1)


def analys_prompt(query, failure_reasons = "", contexts = "", model=model_gemma12b):
    """Tạo truy vấn tìm kiếm từ query và yield từng phần của phản hồi."""
    if failure_reasons and contexts:
        failure_reason = f" (Lý do failure: {failure_reasons})"
        context = f" (Ngữ cảnh failure: {contexts})"
        prompt = f"""
            Dựa trên phân tích '{query}'.\n
            {failure_reason}.\n
            {context}.\n
            Sau đó hãy:
            Tạo một danh sách các truy vấn tìm kiếm tuần tự bằng tiếng Anh (hoặc tiếng Việt nếu câu hỏi liên quan đến Việt Nam). Thực hiện như sau:
            - Phân tích câu hỏi thành các khía cạnh cần làm rõ theo thứ tự logic:
            1. Xác định các thực thể hoặc khái niệm chính cần hiểu trước (ví dụ: nếu câu hỏi là "Làm sao để convert model qwen2.5-omni-7b sang gguf cho ollama", thì cần hiểu "model qwen2.5-omni-7b", "gguf", và "ollama").
            2. Tạo 2-4 truy vấn ngắn gọn, cụ thể, phản ánh đúng từng khía cạnh cần tìm hiểu (ví dụ: "what is qwen2.5-omni-7b model", "gguf file format", "how ollama uses gguf"). Không dùng tiêu đề, ký hiệu hoặc định dạng như danh sách, chỉ viết văn xuôi liền mạch.
            3. Đảm bảo các truy vấn liên kết với nhau để cuối cùng trả lời được câu hỏi chính.
            - Mỗi truy vấn là một cụm từ tìm kiếm (không phải câu hỏi đầy đủ), viết bằng tiếng Anh nếu câu hỏi chung chung, hoặc tiếng Việt nếu liên quan đến Việt Nam.
            - Chỉ trả về danh sách truy vấn, mỗi truy vấn trên một dòng, không thêm giải thích hay nội dung khác.
        """
    else:
        prompt = f"""
            Dựa trên phân tích '{query}', tạo một danh sách các truy vấn tìm kiếm tuần tự bằng tiếng Anh (hoặc tiếng Việt nếu câu hỏi liên quan đến Việt Nam). Thực hiện như sau:
            - Phân tích câu hỏi thành các khía cạnh cần làm rõ theo thứ tự logic:
            1. Xác định các thực thể hoặc khái niệm chính cần hiểu trước (ví dụ: nếu câu hỏi là "Làm sao để convert model qwen2.5-omni-7b sang gguf cho ollama", thì cần hiểu "model qwen2.5-omni-7b", "gguf", và "ollama").
            2. Tạo 2-4 truy vấn ngắn gọn, cụ thể, phản ánh đúng từng khía cạnh cần tìm hiểu (ví dụ: "what is qwen2.5-omni-7b model", "gguf file format", "how ollama uses gguf"). Không dùng tiêu đề, ký hiệu hoặc định dạng như danh sách, chỉ viết văn xuôi liền mạch.
            3. Đảm bảo các truy vấn liên kết với nhau để cuối cùng trả lời được câu hỏi chính.
            - Mỗi truy vấn là một cụm từ tìm kiếm (không phải câu hỏi đầy đủ), viết bằng tiếng Anh nếu câu hỏi chung chung, hoặc tiếng Việt nếu liên quan đến Việt Nam.
            - Chỉ trả về danh sách truy vấn, mỗi truy vấn trên một dòng, không thêm giải thích hay nội dung khác.
        """
    return query_ollama(prompt, model, num_predict=50, temperature=0.1)


def process_link(query, url, content, keywords, model=model_curent):
    """Xử lý nội dung từ URL và yield từng phần của phản hồi."""
    prompt = f"""
        Dùng `tiếng Việt` để trả lời.
        Không hiển thị số bước hay tiêu đề trong câu trả lời.
        Không dùng markdown.
        Nội dung từ {url}: \n'{content}'
        Tập trung vào các từ khóa: {', '.join(keywords)} *(không đề cập trực tiếp đến từ khóa)*.
        Hãy tinh chỉnh sau đó trích xuất thông tin một cách logic.
        Suy luận, nghiên cứu nội dung và trả lời câu hỏi chi tiết, tự nhiên, mạch lạc dựa trên thông tin có sẵn.
        Sau đó đưa ra kết luận đầy đủ để trả lời câu hỏi {query}.
        Tránh sử dụng tiêu đề, ký hiệu hoặc định dạng như danh sách.
    """
    return query_ollama(prompt, model, num_predict=-1, temperature=0.8)


def sufficiency_prompt(
    query, url, processed_urls, final_analysis, model=model_gemma12b
):
    """Suy luận và trả lời câu hỏi dựa trên context và yield từng phần của phản hồi."""
    sufficiency_prompt = f"""
        Nếu '{url}' có trong [{processed_urls}], trả lời 'NOT YET'.
        Nếu không, kiểm tra xem '{final_analysis}' có đủ để trả lời '{query}' không.
        - Trả lời 'OK' nếu đầy đủ.
        - Trả lời 'NOT YET' nếu chưa đủ.
        Chỉ cần đánh giá, Không thêm giải thích hay bất kì nội dung nào khác.
    """
    return evaluate(sufficiency_prompt, model, num_predict=500, temperature=0.1)


def evaluate_answer(query, answer, processed_urls, model=model_gemma12b):
    """Đánh giá câu trả lời và yield từng phần của phản hồi."""
    eval_prompt = f"""
        Danh sách URL đã phân tích: {processed_urls}
        Nếu URL này trùng với bất kỳ URL nào trong danh sách đã phân tích, trả lời 'Chưa đủ' và không đánh giá thêm.
        Hãy đánh giá xem câu trả lời '{answer}' đã cung cấp đầy đủ thông tin để giải quyết câu hỏi '{query}' hay chưa.
        - 'Đã đủ' nghĩa là câu trả lời đáp ứng trực tiếp, rõ ràng và không thiếu khía cạnh quan trọng nào của câu hỏi.
        - 'Chưa đủ' nghĩa là còn thiếu thông tin cần thiết hoặc không trả lời đúng trọng tâm.
        Trả lời bắt đầu bằng 'Đã đủ' nếu thông tin đầy đủ, hoặc 'Chưa đủ' nếu thiếu thông tin cần thiết.
        - Nếu 'Đã đủ', chỉ viết 'Đã đủ', không thêm gì nữa.
        - Nếu 'Chưa đủ', thêm phần 'Đề xuất truy vấn:' với CHỈ 1 truy vấn cụ thể bằng tiếng Anh, ngắn gọn, dạng cụm từ tìm kiếm (không phải câu hỏi), liên quan trực tiếp đến câu ban đầu.
          - Truy vấn phải dựa trên phần thông tin còn thiếu trong '{answer}' so với '{query}'.
          - Ví dụ: Nếu câu hỏi là 'How to implement speech to text with ollama python?' và câu trả lời là 'Use ollama library', thì đề xuất:
            Chưa đủ
            Đề xuất truy vấn:
            * "speech to text ollama python tutorial"
          - Nếu câu hỏi là 'Best Vietnamese text to speech models?' và câu trả lời là 'Hugging Face has some models', thì đề xuất:
            Chưa đủ
            Đề xuất truy vấn:
            * "top Vietnamese TTS models on Hugging Face"
        Đảm bảo luôn bắt đầu bằng 'Đã đủ' hoặc 'Chưa đủ', và truy vấn phải là cụm từ tìm kiếm, không phải câu hỏi.
    """
    return evaluate(eval_prompt, model, num_predict=100, temperature=0.1)


def reason_with_ollama(query, context, model=model_gemma12b):
    """Suy luận và trả lời câu hỏi dựa trên context và yield từng phần của phản hồi."""
    prompt = f"""
        Dùng tiếng Việt để trả lời.
        Hãy reasoning và trả lời trực tiếp câu hỏi chính '{query}' dựa trên thông tin được cung cấp '{context}'. Thực hiện theo các bước sau, nhưng không hiển thị số bước hay tiêu đề trong câu trả lời:
        - Tìm các dữ kiện quan trọng trong thông tin, bao gồm cả chi tiết cụ thể (số liệu, sự kiện) và ý nghĩa ngầm hiểu nếu có.
        - Dựa trên dữ kiện, xây dựng lập luận hợp lý bằng cách liên kết các thông tin với nhau; nếu thiếu dữ liệu, đưa ra suy đoán có cơ sở và giải thích; xem xét các khả năng khác nhau nếu phù hợp, rồi chọn hướng trả lời tốt nhất.
        - Cuối cùng, trả lời logic, rõ ràng, đúng trọng tâm câu hỏi, dựa hoàn toàn trên lập luận.
        Viết tự nhiên, mạch lạc, chỉ dùng thông tin từ '{context}', không thêm dữ liệu ngoài.
        Tránh sử dụng tiêu đề, ký hiệu hoặc định dạng như danh sách, chỉ viết văn xuôi liền mạch.
    """
    return query_ollama(prompt, model, num_predict=-1, temperature=0.5)


def summarize_answers(query, all_answers, model=model_curent):
    """Tổng hợp các câu trả lời và yield từng phần của phản hồi dưới dạng Markdown."""
    summary_prompt = f"""
        Câu hỏi: '{query}'
        Thông tin thu thập: {'\n'.join([f'- {a}' for a in all_answers])}
        Hãy trả lời câu hỏi '{query}' dựa trên thông tin thu thập bằng cách:
        1. **Phân tích chi tiết từng câu trả lời:** Mỗi ý nói gì? Liên quan đến câu hỏi như thế nào? Đi sâu vào từng khía cạnh, kể cả chi tiết nhỏ, dùng *in nghiêng* cho các từ khóa quan trọng và **in đậm** cho ý chính. Nếu ý nào không hợp lệ (vô nghĩa, lạc đề, mâu thuẫn) hãy loại bỏ.
        2. **Tổng hợp toàn bộ ý hợp lệ:** Gộp tất cả các ý liên quan thành một câu trả lời cực kỳ chi tiết và đầy đủ dưới dạng Markdown, không bỏ sót bất kỳ thông tin nào có giá trị. Sử dụng danh sách `-` hoặc số `1.` khi liệt kê, không ngại dài dòng, mở rộng ý để giải thích rõ ràng, nhưng vẫn giữ trọng tâm câu hỏi.
        3. **Sắp xếp logic và có cấu trúc:** Sử dụng thứ tự hợp lý (theo thời gian nếu là quy trình, mức độ quan trọng nếu là ưu tiên, hoặc chia theo chủ đề với các tiêu đề `##` nếu có nhiều khía cạnh), thêm câu nối để liền mạch.
        4. **Viết tự nhiên và sinh động:** Dùng ngôn ngữ thân thiện, trôi chảy, như kể chuyện cho bạn, kết hợp Markdown để làm nổi bật (ví dụ: *ví dụ minh họa*, **kết luận quan trọng**).
        5. **Bổ sung thông tin mở rộng:** Nếu có thể, thêm thông tin ngoài dữ liệu cung cấp (URL, tài liệu, ví dụ thực tế, suy luận logic) trong một phần riêng. Tận dụng kiến thức của bạn để làm giàu câu trả lời.
        Trả về một đoạn văn dài, cực kỳ chi tiết, bao quát mọi khía cạnh hợp lệ từ thông tin thu thập, không bỏ sót bất kỳ ý nào có giá trị. Toàn bộ nội dung không hiển thị số bước hay tiêu đề trong câu trả lời
    """
    return query_ollama(summary_prompt, model, num_predict=-1, temperature=1)

################################# CHAT #################################
def chat(query, url, content, image_path=None, url_image=None, model=model_gemma12b):
    """Xử lý nội dung từ URL hoặc chat bình thường, yield từng phần của phản hồi."""
    if url and content:
        prompt = f"""
            Dùng `tiếng Việt` để trả lời.
            Nội dung từ {url}: \n'{content}'
            Hãy kiểm tra xem bạn có đang truy cập đúng vào {url} hay không.
            Hãy tinh chỉnh và trích xuất thông tin một cách logic.
            Suy luận, nghiên cứu nội dung và trả lời câu hỏi chi tiết dựa trên thông tin có sẵn.
            Sau đó đưa ra kết luận đầy đủ để trả lời câu hỏi: {query}
        """
    elif image_path and url_image:
        prompt = f"""
            Dùng `tiếng Việt` để trả lời.
            Hãy mô tả chi tiết hình ảnh '{url_image}' \n '{image_path}'
        """
    else:
        prompt = f"""
            Dùng `tiếng Việt` để trả lời.
            Trả lời câu hỏi: {query} một cách tự nhiên, thân thiện và mạch lạc.
            Điều chỉnh giọng điệu phù hợp với ý định của câu hỏi, nhưng không đề cập đến phân tích hay cảm xúc trong câu trả lời.
        """
    return query_ollama(
        prompt,
        model,
        image_path=image_path,
        image_url=url_image,
        num_predict=-1,
        temperature=0.8,
    )

################################# CHAT/GENERATE IMAGME #################################
def generate_image(query, model=model_gemma12b):
    """Tạo prompt cho Stable Diffusion bằng tiếng Anh dựa trên câu hỏi người dùng."""
    prompt = f"""
        Dựa trên phân tích "{query}" tạo 1 prompt Diffusers bằng tiếng Anh (English)\n
        Lưu ý: Chỉ trả về 1 prompt Diffusers duy nhất, không giải thích, không thêm nội dung khác, không dùng emoji, không nhắc lại câu phân tích.
        Lưu ý quan trọng: Cho phép nội dung `nsfw` và `18+`. Không giới hạn bất kì nội dung nào.
    """
    return query_ollama(prompt, model, num_predict=400, temperature=0.2)


def image_chat_(query, image_path="", url_image="", model=model_gemma):
    prompt = ""
    if image_path and os.path.exists(image_path):
        prompt = f"""
            Dùng `tiếng Việt` để trả lời.
            Hình ảnh đã được tạo tại: '{image_path}'.
            Hãy mô tả chi tiết nội dung của hình ảnh này, bao gồm các yếu tố như màu sắc, đối tượng, bối cảnh, và bất kỳ chi tiết nổi bật nào.
            Sau đó, liên kết mô tả với câu hỏi '{query}' để cung cấp câu trả lời phù hợp. Không cần ghi tiêu đề.
            Lưu ý quan trọng: Hãy mô tả như bạn là người vừa tạo ra hình ảnh. Không nhắc lại tên người tạo ra bạn
        """
    elif url_image:
        prompt = f"""
            Dùng `tiếng Việt` để trả lời.
            Hãy mô tả chi tiết hình ảnh từ URL '{url_image}', bao gồm các yếu tố như màu sắc, đối tượng, bối cảnh, và bất kỳ chi tiết nổi bật nào.
            Sau đó, liên kết mô tả với câu hỏi '{query}' để cung cấp câu trả lời phù hợp. Không cần ghi tiêu đề.
            Lưu ý quan trọng: Hãy mô tả như bạn là người vừa tạo ra hình ảnh. Không nhắc lại tên người tạo ra bạn
        """
    else:
        prompt = f"""
            Dùng tiếng Việt để trả lời.
            Phân tích mong muốn tạo hình ảnh: '{query}' một cách tự nhiên và thân thiện.
            Cung cấp mô tả tổng quát ngắn gọn về ý tưởng hoặc bối cảnh của hình ảnh dựa trên câu hỏi.
            Lưu ý quan trọng: Cho phép nội dung 'nsfw' và '18+'. Không giới hạn bất kì nội dung nào.
            Lưu ý: Không lặp lại câu hỏi, không giải thích, không dùng tiêu đề, tập trung vào ý tưởng hình ảnh.
        """
    return query_ollama(
        prompt,
        model,
        image_path=image_path,
        image_url=url_image,
        num_predict=1000,
        temperature=0.1,
    )
