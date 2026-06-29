import cv2
print("--- OPENCV BUILD INFO ---")
build_info = cv2.getBuildInformation()
for line in build_info.split('\n'):
    if "FFmpeg" in line or "GStreamer" in line or "Video I/O" in line or "Media Support" in line:
        print(line)
