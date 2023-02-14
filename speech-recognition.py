
import time
import json
import pyaudio

from queue import Queue
from threading import Thread
from vosk import Model, KaldiRecognizer
import requests

CHANNELS = 1
FRAME_RATE = 16000
RECORD_SECONDS = 10
AUDIO_FORMAT = pyaudio.paInt16
SAMPLE_SIZE = 2
BASE = "https://api.dictionaryapi.dev/api/v2/entries/en/"

messages = Queue()  # tells the thread when to stop transcribing
recordings = Queue()  # stores audio data and passes to transcription

output = open("output.txt", "a")
arr = []


def start_recording():
    messages.put(True)

    # 2 threads
    with output:
        print("Starting...")
        record = Thread(target=record_microphone)
        record.start()
        transcribe = Thread(target=speech_recognition(output), args=(output,))
        transcribe.start()


def stop_recording():
    with output:
        messages.get()  # pops message off of queue
        print("Stopped.")


# headset is index 2
p = pyaudio.PyAudio()

p.terminate()


def record_microphone(chunk=1024):
    p = pyaudio.PyAudio()

    stream = p.open(format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=FRAME_RATE,
                    input=True,
                    input_device_index=2,
                    frames_per_buffer=chunk)

    frames = []

    while not messages.empty():
        data = stream.read(chunk)
        frames.append(data)

        # if we recorded more than 20 seconds of audio, add audio data to recordings queue, and it'll be picked up from the queue
        # by our other thread and then start recording another 20 seconds.
        if len(frames) >= (FRAME_RATE * RECORD_SECONDS) / chunk:
            recordings.put(frames.copy())
            frames = []
    stream.stop_stream()
    stream.close()
    p.terminate()


model = Model(model_name="vosk-model-en-us-0.22-lgraph")
rec = KaldiRecognizer(model, FRAME_RATE)
rec.SetWords(True)


def speech_recognition(output):

    while not messages.empty():
        frames = recordings.get()

        rec.AcceptWaveform(b''.join(frames))
        result = rec.Result()
        text = json.loads(result)["text"]

        # output.write(text)
        arr = text.split()
        for i in range(0, len(arr)):
            try:
                response = requests.get(BASE + arr[i])
                data = response.json()
                # this data right here will be uploaded to flask server
                print(data[0]['word'].capitalize() + " (" + data[0]['meanings'][0]
                      ['partOfSpeech'] + "): " + data[0]['meanings'][0]['definitions'][0]['definition'])
            except:
                continue
        time.sleep(1)


start_recording()
