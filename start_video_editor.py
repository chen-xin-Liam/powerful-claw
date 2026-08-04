import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    from src.services.video_editor import VideoEditor
    
    editor = VideoEditor()
    editor.start()
    
    try:
        while True:
            input("按 Enter 键停止服务器...\n")
            break
    except KeyboardInterrupt:
        pass
    finally:
        editor.stop()

if __name__ == "__main__":
    main()
