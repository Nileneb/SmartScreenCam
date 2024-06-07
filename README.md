# SmartScreenCam

This project records the screen and webcam simultaneously, replaces the webcam background with a custom video, and records audio input. The final output is a video file with synchronized audio.

## Requirements

- Python 3.10.12
- OpenCV
- cvzone
- pyautogui
- numpy
- pyaudio
- pynput

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Nileneb/SmartScreenCam
    cd SmartScreenCam
    ```

2. Create and activate a conda environment:
    ```sh
    conda env create -f env.yaml
    conda activate smart    ```

3. install dependencies using pip:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Place your background video file in the same directory as the script and name it `processed_background.mp4`.
2. Run the script:
    ```sh
    python app.py
    ```
3. The final output video will be saved in the `results` directory.

## Notes

- Ensure you have a working webcam and microphone.
- Modify the script settings to adjust webcam resolution, frame rate, and other parameters as needed.
