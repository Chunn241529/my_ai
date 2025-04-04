import yt_dlp
import pygame
from youtube_search import YoutubeSearch
import os
from rich.console import Console
from rich.markdown import Markdown

console = Console()

# Khởi tạo pygame mixer để phát nhạc
pygame.mixer.init()


def search_music(query: str) -> list:
    """Tìm kiếm 5 kết quả trên YouTube và trả về danh sách các bài hát."""
    try:
        console.print(f"[cyan]Tìm kiếm:[/cyan] [bold yellow]{query}[/bold yellow]")
        results = YoutubeSearch(query, max_results=5).to_dict()
        
        if not results:
            console.print("[red]Không tìm thấy kết quả![/red]")
            return []
        
        # console.print(f"\n")
        # # Hiển thị danh sách kết quả
        # for i, result in enumerate(results):
        #     console.print(f"[bold green]{i + 1}.[/bold green] {result['title']} - {result['channel']}")
        
        return results
    except Exception as e:
        console.print(f"[red]Có lỗi xảy ra khi tìm kiếm: {str(e)}[/red]")
        return []


def select_music(results: list, choice: int) -> str:
    """Chọn bài hát từ danh sách kết quả dựa trên số thứ tự (1-5). Trả về URL."""
    if not results:
        console.print("[red]Danh sách kết quả rỗng! Không thể chọn bài hát.[/red]")
        return ""
    
    if not isinstance(choice, int):
        console.print("[red]Lựa chọn phải là một số nguyên![/red]")
        return ""
    
    if choice < 1 or choice > len(results):
        console.print(f"[red]Lựa chọn không hợp lệ! Vui lòng chọn từ 1 đến {len(results)}.[/red]")
        return ""
    
    try:
        console.print(f"\n")
        video_id = results[choice - 1]['id']  # Lấy ID của bài hát được chọn
        url = f"https://www.youtube.com/watch?v={video_id}"
        console.print(f"[cyan]Đã chọn:[/cyan] [bold yellow]{results[choice - 1]['title']}[/bold yellow]")
        return url
    except IndexError:
        console.print("[red]Lỗi: Chỉ số vượt quá danh sách kết quả![/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Có lỗi khi chọn bài hát: {str(e)}[/red]")
        return ""


def play_music_from_url(url: str):
    """Tải và phát nhạc từ URL YouTube."""
    if not url:
        console.print("[red]Không có URL để phát nhạc![/red]")
        return
    
    try:
        # Tạo thư mục assets/music nếu chưa tồn tại
        os.makedirs("assets/music", exist_ok=True)
        
        # Cấu hình yt_dlp để tải audio
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'outtmpl': 'assets/music/song.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }
        
        # Tải audio từ URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Phát nhạc từ file vừa tải
        pygame.mixer.music.load('assets/music/song.mp3')
        pygame.mixer.music.play()
        console.print(Markdown("`Đang phát nhạc...`"))
        console.print(Markdown("\nNhập *câu hỏi* và nhấn `ENTER` để tiếp tục\n"))
        

        
        # Chờ nhạc phát xong và xóa file
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
            if os.path.exists('assets/music/song.mp3'):
                os.remove('assets/music/song.mp3')
            
    except Exception as e:
        console.print(f"[red]Có lỗi khi phát nhạc: {str(e)}[/red]")


# # Ví dụ sử dụng
# if __name__ == "__main__":
#     # Bước 1: Tìm kiếm nhạc
#     search_query = "Như mộng - châu thâm"
#     results = search_music(search_query)
    
#     # Bước 2: Chọn bài hát (giả sử chọn số 1)
#     if results:
#         selected_url = select_music(results, 1)  # Chọn bài đầu tiên
        
#         # Bước 3: Phát nhạc
#         if selected_url:
#             play_music_from_url(selected_url)