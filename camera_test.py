# camera_test.py
import cv2
import json
import os

def run_test():
    """
    Runs a diagnostic test to check OpenCV's capabilities and camera stream connections.
    """
    print("="*80)
    print("RUNNING OPENCV & CAMERA CONNECTION DIAGNOSTIC TEST")
    print("="*80)

    # 1. Print OpenCV Build Information
    print("\n[INFO] OpenCV Build Information:\n")
    print(cv2.getBuildInformation())
    print("\n" + "="*80 + "\n")

    # 2. Check for FFMPEG in the build information
    build_info = cv2.getBuildInformation()
    if "FFMPEG" in build_info:
        print("[INFO] FFMPEG backend is mentioned in the build info. Checking status...")
        if "YES" in build_info.split("FFMPEG")[1]:
            print("[SUCCESS] FFMPEG support seems to be enabled.\n")
        else:
            print("[WARNING] FFMPEG is mentioned but does not appear to be enabled (YES not found).\n")
    else:
        print("[ERROR] FFMPEG backend NOT FOUND in the build information. "
              "This is the likely cause of the issue.\n")

    print("="*80)

    # 3. Test Connection to Cameras from cameras.json
    print("\n[INFO] Attempting to connect to camera streams from 'cameras.json'வைக்...")

    cameras_json_path = 'cameras.json'
    if not os.path.exists(cameras_json_path):
        print(f"[ERROR] 'cameras.json' not found in the current directory: {os.getcwd()}")
        print("Please place this script in the 'PackingApp' directory and run it from there.")
        return

    try:
        with open(cameras_json_path, 'r', encoding='utf-8') as f:
            cameras = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read or parse 'cameras.json': {e}")
        return

    if not cameras:
        print("[WARNING] 'cameras.json' is empty. No streams to test.")
        return

    all_tests_passed = True
    for cam in cameras:
        cam_name = cam.get('name', 'N/A')
        rtsp_url = cam.get('rtsp_url')

        print(f"--- Testing Camera: {cam_name} ---")
        if not rtsp_url:
            print("[RESULT] FAILED: 'rtsp_url' is missing for this camera.\n")
            all_tests_passed = False
            continue

        print(f"[URL]    {rtsp_url}")

        # Attempt to open the stream
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

        if cap.isOpened():
            print("[RESULT] SUCCESS: Connection opened successfully.")
            # Try to read one frame
            ret, frame = cap.read()
            if ret:
                print("[FRAME]  SUCCESS: A frame was read successfully.")
                print(f"[DIMS]   Frame dimensions: {frame.shape}")
            else:
                print("[FRAME]  FAILED: Connection opened, but failed to read a frame.")
                all_tests_passed = False
            cap.release()
        else:
            print("[RESULT] FAILED: cv2.VideoCapture() could not open the stream.")
            all_tests_passed = False
        
        print("-" * (len(cam_name) + 20) + "\n")

    print("="*80)
    if all_tests_passed:
        print("\n[FINAL DIAGNOSIS] All tests passed. The Python/OpenCV environment appears to be "
              "set up correctly for these streams. The issue might be related to threading or "
              "GUI integration in the main application.")
    else:
        print("\n[FINAL DIAGNOSIS] One or more tests failed. Please review the errors above. "
              "If FFMPEG is missing or connections fail here, the issue is with the underlying "
              "Python/OpenCV environment, not the application logic.")
    print("="*80)


if __name__ == "__main__":
    run_test()
