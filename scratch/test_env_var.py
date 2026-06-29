import os
import sys
import subprocess

code = """
import os
import cv2
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "dummy_invalid_parameter_test;1"
cap = cv2.VideoCapture("rtsp://192.168.1.14:554/onvif1")
cap.release()
"""

p = subprocess.Popen([sys.executable, "-"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = p.communicate(input=code)

print("STDOUT:", stdout.strip())
print("STDERR:", stderr.strip())
