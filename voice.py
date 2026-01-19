import threading
import os
import pyaudio
from dotenv import load_dotenv
from deepgram import DeepgramClient
from deepgram.core.events import EventType

load_dotenv()

API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not API_KEY:
    raise RuntimeError("DEEPGRAM_API_KEY not found in environment")

RATE = 16000
CHUNK = 1024

def main():
    
    deepgram = DeepgramClient(api_key=API_KEY)

    with deepgram.listen.v1.connect(
        model="nova-3",
        language="en",
        punctuate=True,
        interim_results=True,
        encoding="linear16",
        sample_rate=RATE,
        channels=1,
    ) as connection:

        def on_message(message):
            if hasattr(message, "channel"):
                transcript = message.channel.alternatives[0].transcript
                if transcript:
                    print("🗣️", transcript)

        connection.on(EventType.OPEN, lambda _: print("Connection opened"))
        connection.on(EventType.MESSAGE, on_message)
        connection.on(EventType.ERROR, lambda e: print("Error:", e))
        connection.on(EventType.CLOSE, lambda _: print("Connection closed"))

        
        threading.Thread(
            target=connection.start_listening,
            daemon=True
        ).start()

        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        print("🎤 Listening... Press Ctrl+C to stop")

        try:
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                connection.send_media(data)
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            connection.finish()

if __name__ == "__main__":
    main()
