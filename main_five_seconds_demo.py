from modules.record_five_seconds import SoundRecorder
from modules.req import FileUploader
from modules.window import WindowCanvasManager
from queue import Queue
from threading import Thread
import asyncio
import sys
import signal

def safe_exit(signum, frame):
    print("Exiting gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    file_path_queue: Queue = Queue()
    voice_angle_queue: Queue = Queue()
    transcribed_text_queue: Queue = Queue()
    url = "http://172.20.10.3:80/api/transcribe"

    # キーボード割り込みを処理するための設定
    signal.signal(signal.SIGINT, safe_exit)

    # SoundRecorderのインスタンスを作成し、録音を開始
    recorder = SoundRecorder(file_path_queue, voice_angle_queue)
    recorder.start_recording()

    # 録音とDOAの検出を行うスレッドを作成し、開始
    create_wav_file_thread = Thread(target=recorder.run)
    create_wav_file_thread.start()

    # FileUploaderのインスタンスを作成
    file_uploader = FileUploader(file_path_queue, transcribed_text_queue, url)

    # 音声ファイルのアップロードを行うスレッドを作成し、開始
    file_upload_thread = Thread(target=asyncio.run, args=(file_uploader.run(),))
    file_upload_thread.start()

    # WindowCanvasManagerのインスタンスを作成
    window = WindowCanvasManager()

    # 音声の方向とアップロード結果を表示するスレッドを作成し、開始
    draw_voice_angle_arc_and_text_forever_thread = Thread(
        target=window.draw_voice_angle_arc_and_text_forever,
        args=(voice_angle_queue, transcribed_text_queue),
    )
    draw_voice_angle_arc_and_text_forever_thread.start()

    # GUIを実行
    try:
        window.run()
    except KeyboardInterrupt:
        safe_exit(None, None)
