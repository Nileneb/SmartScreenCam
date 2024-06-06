# -*- coding: utf-8 -*-
import cv2
import cvzone
from cvzone.SelfiSegmentationModule import SelfiSegmentation
import pyautogui
import numpy as np
import time
import pyaudio
import wave
import threading
import subprocess
import os
from datetime import datetime
from pynput import keyboard, mouse

# Einstellungen
webcam_index = 0
output_video_filename = "temp_screen_and_webcam_with_virtual_background.avi"
background_video_path = "processed_background.mp4"
audio_output_filename = "temp_audio_output.wav"
results_folder = "results"
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

# Name der finalen Datei basierend auf Datum und Uhrzeit
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
final_output_filename = os.path.join(results_folder, f"final_output_{current_time}.mp4")

webcam_width = 320
webcam_height = 240
screen_width, screen_height = pyautogui.size()
fps = 20.0
frame_duration = 1.0 / fps
text_color = (0, 165, 255)  # Orange in BGR
text_font = cv2.FONT_HERSHEY_SIMPLEX
text_scale = 1.0
text_thickness = 2

# Audio-Einstellungen
audio_format = pyaudio.paInt16
channels = 1
rate = 44100
chunk = 1024

# Audio-Stream-Initialisierung
audio = pyaudio.PyAudio()

def get_default_microphone_index():
    info = audio.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    for i in range(num_devices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            return i
    return None

default_mic_index = get_default_microphone_index()
if default_mic_index is None:
    print("No microphone found.")
    exit(1)

audio_stream = audio.open(format=audio_format, channels=channels, rate=rate, input=True,
                          input_device_index=default_mic_index, frames_per_buffer=chunk)

audio_frames = []

def record_audio():
    global audio_frames
    while recording:
        data = audio_stream.read(chunk)
        audio_frames.append(data)

recording = True
audio_thread = threading.Thread(target=record_audio)
audio_thread.start()

# Video-Schreiber konfigurieren
fourcc = cv2.VideoWriter_fourcc(*"XVID")
video_writer = cv2.VideoWriter(output_video_filename, fourcc, fps, (screen_width, screen_height))

# Hintergrundvideo öffnen
background_video = cv2.VideoCapture(background_video_path)
if not background_video.isOpened():
    print("Could not open background video.")
    exit(1)

# Start der Video-Aufnahme
cap = cv2.VideoCapture(webcam_index, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("Webcam could not be opened.")
    exit(1)

# SelfiSegmentation initialisieren
segmentor = SelfiSegmentation()
print("Aufnahme gestartet.")

# Variablen für Tastatur- und Mauseingaben
current_text = ""
last_key_time = 0
text_duration = 2  # Sekunden

def on_press(key):
    global current_text, last_key_time
    try:
        if key.char:
            current_text += key.char
    except AttributeError:
        if key == keyboard.Key.space:
            current_text += " "
        elif key == keyboard.Key.enter:
            current_text += " [ENTER]"
        elif key == keyboard.Key.backspace:
            current_text = current_text[:-1]  # Entfernen des letzten Zeichens
        else:
            current_text += f" [{key.name.upper()}]"
    last_key_time = time.time()

def on_release(key):
    global current_text, last_key_time
    if key == keyboard.Key.esc:
        return False

keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
keyboard_listener.start()

def on_click(x, y, button, pressed):
    global current_text, last_key_time
    if pressed:
        current_text = f" {button.name} Mouse"
        last_key_time = time.time()

mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

try:
    while True:
        start_time = time.time()

        # Bildschirmaufnahme machen
        screenshot = pyautogui.screenshot()
        screen_frame = np.array(screenshot)
        screen_frame = cv2.cvtColor(screen_frame, cv2.COLOR_RGB2BGR)

        ret, webcam_frame = cap.read()
        if not ret or webcam_frame is None:
            print("Could not read webcam frame.")
            break

        ret_bg, background_frame = background_video.read()
        if not ret_bg or background_frame is None:
            print("Restarting background video.")
            background_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # Größenanpassung der Frames
        webcam_frame_resized = cv2.resize(webcam_frame, (webcam_width, webcam_height))
        background_frame_resized = cv2.resize(background_frame, (webcam_width, webcam_height))

        # Hintergrund entfernen und durch das Hintergrundvideo ersetzen
        combined_frame = segmentor.removeBG(webcam_frame_resized, background_frame_resized)

        # Platzieren des kombinierten Frames auf dem Bildschirm-Frame
        screen_frame[screen_height - webcam_height - 10: screen_height - 10,
                     screen_width - webcam_width - 10: screen_width - 10] = combined_frame

        # Text für Tastatur- und Mauseingaben anzeigen
        if time.time() - last_key_time < text_duration:
            text_size, _ = cv2.getTextSize(current_text, text_font, text_scale, text_thickness)
            text_x = screen_width - webcam_width - 10
            text_y = screen_height - webcam_height - 20 - text_size[1]
            cv2.putText(screen_frame, current_text, (text_x, text_y), text_font, text_scale, text_color, text_thickness, cv2.LINE_AA)
        else:
            current_text = ""

        # Schreiben des kombinierten Frames ins Video
        video_writer.write(screen_frame)

        # Wartezeit, um die Framerate zu regulieren
        elapsed_time = time.time() - start_time
        if elapsed_time < frame_duration:
            time.sleep(frame_duration - elapsed_time)

except KeyboardInterrupt:
    print("KeyboardInterrupt detected, exiting loop")
finally:
    print("Releasing resources")
    recording = False
    audio_thread.join()
    audio_stream.stop_stream()
    audio_stream.close()
    audio.terminate()
    keyboard_listener.stop()
    mouse_listener.stop()

    with wave.open(audio_output_filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(audio_format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(audio_frames))

    cap.release()
    background_video.release()
    video_writer.release()
    cv2.destroyAllWindows()

# Audio und Video zusammenführen
ffmpeg_command = [
    'ffmpeg', '-y', '-i', output_video_filename, '-i', audio_output_filename, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', final_output_filename
]

print("Running ffmpeg command:", " ".join(ffmpeg_command))
subprocess.run(ffmpeg_command, check=True)

# Temporäre Dateien löschen
os.remove(output_video_filename)
os.remove(audio_output_filename)

print(f"Video saved as: {final_output_filename}")
print(f"Audio saved as: {audio_output_filename}")
