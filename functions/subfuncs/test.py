import whisper

model = whisper.load_model("turbo")
result = model.transcribe("functions/subfuncs/audio.mp3")
print(result["text"])
