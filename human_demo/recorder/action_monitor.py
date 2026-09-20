"""Record one atomic interaction, including its visual boundaries and OBS video."""
from datetime import datetime
from pathlib import Path
import shutil
import threading
import time

EXIT_HOTKEY = '<ctrl>+<shift>+<f11>'


def start_listening(save_folder):
    # Lazy imports keep plan/process/test commands usable without a display server.
    from pynput import mouse, keyboard
    import pyautogui
    from human_demo.recorder.obs_util import connect_to_obs, start_recording, stop_recording, disconnect

    folder = Path(save_folder) / datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    logfile = folder / 'events.log'
    done, lock = threading.Event(), threading.Lock()
    ctrl_keys = set()
    last_move = 0.0
    client = connect_to_obs()
    listeners = []
    recording = False
    try:
        # Wait until the start hotkey has been released before capture begins.
        time.sleep(0.5)
        pyautogui.screenshot().save(folder / 'before.png')
        start_recording(client)
        recording = True
        with logfile.open('w', encoding='utf-8') as stream:
            def emit(event):
                if not done.is_set():
                    with lock:
                        stream.write(f'{datetime.now():%Y-%m-%d %H-%M-%S-%f} - {event}\n')
                        stream.flush()

            def click(x, y, button, pressed):
                if button not in (mouse.Button.left, mouse.Button.right):
                    return
                name = ('right click' if button == mouse.Button.right else 'click') if pressed else 'release'
                emit(f'Mouse {name} at ({int(x)}, {int(y)})')

            def move(x, y):
                nonlocal last_move
                now = time.monotonic()
                if now - last_move >= .03:
                    emit(f'Mouse move to ({int(x)}, {int(y)})')
                    last_move = now

            def scroll(x, y, dx, dy):
                prefix = 'Hotkey (ctrl+scroll)' if ctrl_keys else 'Mouse scroll'
                emit(f'{prefix} at ({int(x)}, {int(y)}) with delta ({int(dx)}, {int(dy)})')

            def press(key):
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    ctrl_keys.add(key)
                emit(f'Key pressed: {key}')

            def release(key):
                ctrl_keys.discard(key)
                emit(f'Key released: {key}')

            listeners = [mouse.Listener(on_click=click, on_move=move, on_scroll=scroll),
                         keyboard.Listener(on_press=press, on_release=release),
                         keyboard.GlobalHotKeys({EXIT_HOTKEY: done.set})]
            for listener in listeners:
                listener.start()
            print('Recording. Ctrl+Shift+F11 stops this atomic interaction.')
            while not done.wait(.1):
                if not all(listener.is_alive() for listener in listeners):
                    raise RuntimeError('An input listener stopped unexpectedly')
            for listener in listeners:
                listener.stop()
            for listener in listeners:
                listener.join(timeout=2)
        pyautogui.screenshot().save(folder / 'after.png')
        source = stop_recording(client)
        recording = False
        # Copy only the path returned for this recording; never sweep the OBS directory.
        shutil.copy2(source, folder / ('video' + source.suffix.lower()))
    finally:
        done.set()
        for listener in listeners:
            listener.stop()
        if recording:
            stop_recording(client)
        disconnect(client)
    return str(logfile)
