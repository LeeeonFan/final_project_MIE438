import cv2

for i in range(10):
    cap = cv2.VideoCapture(i)
    ok, frame = cap.read()
    if ok:
        print(f"Camera index {i} works, frame shape = {frame.shape}")
    cap.release()