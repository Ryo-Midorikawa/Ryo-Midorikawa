import time
import pyaudio
import wave
import usb.core
import usb.util
import struct
from threading import Thread
from queue import Queue

class SoundRecorder:
    RESPEAKER_RATE = 16000
    RESPEAKER_CHANNELS = 1
    RESPEAKER_WIDTH = 2
    RESPEAKER_INDEX = 2
    CHUNK = 1024
    RECORD_SECONDS = 5
    DEVICE = usb.core.find(idVendor=0x2886, idProduct=0x0018)
    TIMEOUT = 100000
    PARAMETERS = {
        "DOAANGLE": (
            21,
            0,
            "int",
            359,
            0,
            "ro",
            "DOA angle. Current value. \
            Orientation depends on build configuration.",
        ),
    }

    def __init__(self, file_path_queue: Queue, voice_angle_queue: Queue):
        self.p = pyaudio.PyAudio()
        self.file_number = 0
        self.file_path_queue = file_path_queue
        self.voice_angle_queue = voice_angle_queue

    def read_parameter(self, param_name):
        try:
            data = self.PARAMETERS[param_name]
        except KeyError:
            return

        id = data[0]

        cmd = 0x80 | data[1]
        if data[2] == "int":
            cmd |= 0x40

        length = 8

        response = self.DEVICE.ctrl_transfer(
            usb.util.CTRL_IN
            | usb.util.CTRL_TYPE_VENDOR
            | usb.util.CTRL_RECIPIENT_DEVICE,
            0,
            cmd,
            id,
            length,
            self.TIMEOUT,
        )

        response = struct.unpack(b"ii", response.tobytes())

        if data[2] == "int":
            result = response[0]
        else:
            result = response[0] * (2.0 ** response[1])

        return result

    def start_recording(self):
        self.stream = self.p.open(
            rate=self.RESPEAKER_RATE,
            format=self.p.get_format_from_width(self.RESPEAKER_WIDTH),
            channels=self.RESPEAKER_CHANNELS,
            input=True,
            input_device_index=self.RESPEAKER_INDEX,
        )
        print("\\n\\n-- Start Stream --\\n")

    def save_recorded_data(self, frames):
        file_name = str(self.file_number) + ".wav"
        wf = wave.open(file_name, "wb")
        wf.setnchannels(self.RESPEAKER_CHANNELS)
        wf.setsampwidth(
            self.p.get_sample_size(
                self.p.get_format_from_width(self.RESPEAKER_WIDTH)
            )
        )
        wf.setframerate(self.RESPEAKER_RATE)
        wf.writeframes(b"".join(frames))
        wf.close()
        print(" * Done Save!")
        self.file_path_queue.put(file_name)
        self.file_number += 1

    def run(self):
        try:
            while True:
                frames = []
                for i in range(0, int(self.RESPEAKER_RATE / self.CHUNK * self.RECORD_SECONDS)):
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    frames.append(data)
                    voice_angle = self.read_parameter("DOAANGLE")
                    self.voice_angle_queue.put(voice_angle)
                self.save_recorded_data(frames)

        except Exception as e:
            print("\\nExcept : " + str(e))

        finally:
            print("\\nFinally!")
            print("\\n-- Stop Stream  --")
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

if __name__ == "__main__":

    def get_voice_angle(voice_angle_queue: Queue):
        while True:
            print(f"Voice_Angle : { voice_angle_queue.get() }")

    def get_file_name(file_name_queue: Queue):
        while True:
            print(f"File_Name : { file_name_queue.get() }")

    file_path_queue: Queue = Queue()
    voice_angle_queue: Queue = Queue()

    Thread(target=get_file_name, args=(file_path_queue,)).start()
    Thread(target=get_voice_angle, args=(voice_angle_queue,)).start()

    recorder = SoundRecorder(file_path_queue, voice_angle_queue)
    recorder.start_recording()
    recorder.run()
