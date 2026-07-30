from clicue.stt.vosk_engine import VoskSTTListener

# Backward compatibility alias
STTListener = VoskSTTListener

if __name__ == "__main__":
    listener = STTListener()
    try:
        for text in listener.listen():
            print(f"Recognized: {text}")
    except KeyboardInterrupt:
        print("\nStopped listening.")
