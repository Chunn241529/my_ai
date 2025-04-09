from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
import yt_dlp
import pygame
from youtube_search import YoutubeSearch
import os
from rich.console import Console
from rich.markdown import Markdown

console = Console()

# Khởi tạo mixer
pygame.mixer.init()

# Biến toàn cục để quản lý trạng thái
music_queue = []
is_looping = False
current_song = None

def download_and_load_song(query: str):
    """Tải bài hát từ YouTube và chuẩn bị phát"""
    global current_song
    try:
        console.print(f"[cyan]Tìm kiếm:[/cyan] [bold yellow]{query}[/bold yellow]")
        results = YoutubeSearch(query, max_results=1).to_dict()

        if not results:
            console.print("[red]Không tìm thấy kết quả![/red]")
            return False

        video_id = results[0]['id']
        url = f"https://www.youtube.com/watch?v={video_id}"
        os.makedirs("assets/music", exist_ok=True)

        # Xóa file cũ nếu tồn tại
        if os.path.exists('assets/music/song.mp3'):
            os.remove('assets/music/song.mp3')

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

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        pygame.mixer.music.load('assets/music/song.mp3')
        current_song = {'title': results[0]['title'], 'url': url, 'query': query}
        return True

    except Exception as e:
        console.print(f"[red]Có lỗi xảy ra: {str(e)}[/red]")
        return False

def play_music(query: str):
    """Phát một bài hát"""
    if download_and_load_song(query):
        pygame.mixer.music.play()
        console.print(Markdown(f"Đang phát: [{current_song['title']}]({current_song['url']})"))

def toggle_loop():
    """Bật/tắt chế độ lặp lại bài hát hiện tại"""
    global is_looping
    is_looping = not is_looping
    state = "bật" if is_looping else "tắt"
    console.print(f"[green]Chế độ lặp lại đã được {state}[/green]")

def add_to_queue(query: str):
    """Thêm bài hát vào hàng chờ"""
    music_queue.append(query)
    console.print(f"[green]Đã thêm '{query}' vào hàng chờ[/green]")
    console.print(f"[cyan]Số bài trong hàng chờ: {len(music_queue)}[/cyan]")

def play_next():
    """Phát bài hát tiếp theo trong hàng chờ hoặc lặp lại nếu bật chế độ loop"""
    global current_song
    if pygame.mixer.music.get_busy():  # Nếu đang phát thì không làm gì
        return

    if is_looping and current_song:
        pygame.mixer.music.play()
        console.print(Markdown(f"Đang lặp lại: [{current_song['title']}]({current_song['url']})"))
    elif music_queue:
        next_song = music_queue.pop(0)
        play_music(next_song)

# Ví dụ sử dụng riêng lẻ các hàm
if __name__ == "__main__":
    # Gọi từng hàm riêng lẻ
    play_music("Tháp rơi tự do")  # Phát bài hát đầu tiên
    add_to_queue("Havana")        # Thêm bài hát vào hàng chờ
    toggle_loop()                 # Bật chế độ lặp lại
