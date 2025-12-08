import cv2
import threading
import time
from PIL import Image
import customtkinter as ctk
import os
import datetime
import pyttsx3
import json
import winsound
from qreader import QReader # Import the new, powerful QR detector
from . import utils, config

# =====================================================================
# Frame Grabber Thread (Unchanged)
# =====================================================================
def _frame_grabber_loop(app, camera):
    """
    A tight loop that continuously reads frames from the camera stream.
    Its only job is to empty the buffer and keep camera.frame fresh.
    """
    print(f"[CAM {camera.name}] Frame grabber thread started.")
    while app.is_running and camera.preview_cap and camera.preview_cap.isOpened():
        ret, frame = camera.preview_cap.read()
        if not ret:
            print(f"[CAM {camera.name}] Grabber: Failed to read frame. Signaling for reconnect.")
            break
        with camera.frame_lock:
            camera.frame = frame
    print(f"[CAM {camera.name}] Frame grabber thread stopped.")

# =====================================================================
# Main Camera Logic (Modified to use QReader)
# =====================================================================

class Camera:
    def __init__(self, app, camera_info, index):
        self.app = app
        self.id = camera_info.get('id', index)
        self.name = camera_info.get('name', f"Camera {index + 1}")
        self.rtsp_url = camera_info.get('rtsp_url')
        self.index = index
        self.is_recording = False
        self.order_id = None
        self.video_writer = None
        self.start_time = None
        self.last_file = None
        self.preview_cap = None
        self.last_scan_time = None
        self.frame = None
        self.frame_lock = threading.Lock()
        self.record_thread = None
        self.grabber_thread = None

    def release(self):
        """Release camera resources."""
        if self.preview_cap and self.preview_cap.isOpened():
            self.preview_cap.release()
            print(f"[CAM {self.name}] Preview capture released.")

def load_cameras_from_json(app):
    """Loads camera configurations from cameras.json."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cameras_json_path = os.path.join(base_dir, 'cameras.json')
        with open(cameras_json_path, 'r', encoding='utf-8') as f:
            cameras_data = json.load(f)
        if not isinstance(cameras_data, list):
            print("[ERROR] cameras.json should contain a list of camera objects.")
            return []
        camera_objects = []
        seen_ids = set()
        for i, cam_info in enumerate(cameras_data):
            cam_id = cam_info.get('id')
            if cam_id in seen_ids:
                print(f"[WARNING] Duplicate camera ID '{cam_id}' found. Assigning a unique index {i} instead.")
                cam_info['id'] = i
            if cam_id is not None:
                seen_ids.add(cam_id)
            camera_objects.append(Camera(app, cam_info, i))
        return camera_objects
    except FileNotFoundError:
        print("[ERROR] cameras.json not found. Please create it.")
        return []
    except json.JSONDecodeError:
        print("[ERROR] Could not decode cameras.json. Please check its format.")
        return []
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while loading cameras: {e}")
        return []

def start_camera_threads(app):
    """Khởi động các luồng cho từng camera đã được load trước đó."""
    if not app.cameras:
        app.after(0, lambda: app.log_label.configure(text="Lỗi: Không có camera nào được tải để bắt đầu luồng.", text_color="red"))
        return
    app.camera_threads = []
    for camera in app.cameras:
        thread = threading.Thread(target=_camera_feed_loop, args=(app, camera), daemon=True)
        app.camera_threads.append(thread)
        thread.start()

def _camera_feed_loop(app, camera):
    """
    The main processing loop for a camera.
    - Uses QReader for fast and reliable QR code detection.
    - Processes a central Region of Interest (ROI) to improve performance.
    - Draws the ROI on the preview to guide the user.
    """
    # 1. Initialize the QReader with performance optimizations
    # 'n' model is faster, and min_prob filters weak detections.
    qreader = QReader(model_size='n', min_prob=0.5)

    # 2. Set scan interval to avoid processing every frame
    scan_interval = max(1, config.FPS // 5)  # Scan ~5 times per second
    frame_counter = 0

    while app.is_running:
        # --- Connection Management ---
        if camera.preview_cap is None or not camera.preview_cap.isOpened():
            with camera.frame_lock:
                camera.frame = None
            print(f"[CAM {camera.name}] Đang kết nối tới: {camera.rtsp_url}")
            app.after(0, lambda: update_camera_status(app, camera, "Đang kết nối...", utils.COLOR_GRAY_ACCENT))
            camera.preview_cap = cv2.VideoCapture(camera.rtsp_url, cv2.CAP_FFMPEG)
            if not camera.preview_cap.isOpened():
                app.after(0, lambda: update_camera_status(app, camera, "Lỗi kết nối", utils.COLOR_RED_EXIT))
                print(f"[CAM {camera.name}] Lỗi: không thể kết nối tới luồng.")
                time.sleep(5) # Wait before retrying
                continue
            else:
                print(f"[CAM {camera.name}] Kết nối thành công. Bắt đầu luồng lấy hình ảnh.")
                app.after(0, lambda: update_camera_status(app, camera, "Trạng thái: Đang chờ", "#555"))
                camera.grabber_thread = threading.Thread(target=_frame_grabber_loop, args=(app, camera), daemon=True)
                camera.grabber_thread.start()

        # --- Frame Acquisition ---
        frame_to_process = None
        with camera.frame_lock:
            if camera.frame is not None:
                frame_to_process = camera.frame.copy()
        
        if frame_to_process is None:
            time.sleep(0.1) # Wait for the first frame
            continue
            
        frame_counter += 1
        
        # --- Timed QR Code Detection within ROI ---
        if frame_counter >= scan_interval:
            frame_counter = 0

            # Define a central Region of Interest (ROI) for faster scanning.
            # This focuses the detection on the most likely area for a QR code.
            h, w, _ = frame_to_process.shape
            roi_w, roi_h = int(w * 0.7), int(h * 0.7) # 70% of the frame
            roi_x, roi_y = int((w - roi_w) / 2), int((h - roi_h) / 2)
            frame_roi = frame_to_process[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]

            # Use QReader's combined detect_and_decode method on the ROI.
            # This is the correct and most efficient way to use the library.
            decoded_qrs = qreader.detect_and_decode(image=frame_roi)

            # detect_and_decode returns a tuple of strings (or None if nothing found)
            if decoded_qrs:
                order_id = decoded_qrs[0].strip()
                # Schedule the business logic to run on the main thread
                app.after(0, lambda: _handle_auto_switch_for_camera(app, camera, order_id))

        # --- GUI Update with Visual Feedback ---
        # Resize frame for display
        preview_frame = cv2.resize(frame_to_process, (config.CAMERA_PREVIEW_WIDTH, config.CAMERA_PREVIEW_HEIGHT))

        # Calculate ROI coordinates for the resized preview frame to draw a guide box.
        preview_h, preview_w, _ = preview_frame.shape
        # The ROI percentages are the same, so we can calculate directly on preview dimensions
        preview_roi_w, preview_roi_h = int(preview_w * 0.7), int(preview_h * 0.7)
        preview_roi_x, preview_roi_y = int((preview_w - preview_roi_w) / 2), int((preview_h - preview_roi_h) / 2)
        
        # Draw the green guide box for the user
        top_left = (preview_roi_x, preview_roi_y)
        bottom_right = (preview_roi_x + preview_roi_w, preview_roi_y + preview_roi_h)
        cv2.rectangle(preview_frame, top_left, bottom_right, (0, 255, 0), 2)

        # Update the GUI on the main thread
        app.after(0, lambda f=preview_frame, cam=camera: update_image_frame(app, f, cam))
        
        # Control the processing/display rate to match desired FPS
        time.sleep(1 / config.FPS)

    # --- Cleanup on exit ---
    if camera.grabber_thread and camera.grabber_thread.is_alive():
        camera.grabber_thread.join()
    camera.release()

# =====================================================================
# Recording Logic and other helpers (all unchanged)
# =====================================================================

def _start_recording_for_camera(app, camera, order_id):
    os.makedirs(utils.OUTPUT_DIR, exist_ok=True)
    file_name = f"{order_id}.avi"
    file_path = os.path.join(utils.OUTPUT_DIR, file_name)
    if os.path.exists(file_path):
        update_camera_status(app, camera, f"Lỗi: Đơn hàng {order_id} đã tồn tại", utils.COLOR_RED_EXIT)
        app.after(0, lambda: _play_audio('DonHangTonTai.wav'))
        return False
    with app.lock:
        if camera.is_recording:
            return False
        with camera.frame_lock:
            if camera.frame is None:
                update_camera_status(app, camera, "Lỗi: Không có hình ảnh từ camera", utils.COLOR_RED_EXIT)
                print(f"[CAM {camera.name}] Không thể ghi hình, không có frame.")
                return False
            frame_height, frame_width, _ = camera.frame.shape
            frame_size = (frame_width, frame_height)
        fourcc = cv2.VideoWriter_fourcc(*utils.VIDEO_CODEC_FOURCC)
        video_writer = cv2.VideoWriter(file_path, fourcc, config.FPS, frame_size)
        if not video_writer.isOpened():
            update_camera_status(app, camera, f"Lỗi: Không tạo được file video", utils.COLOR_RED_EXIT)
            return False
        camera.is_recording = True
        camera.order_id = order_id
        camera.start_time = datetime.datetime.now()
        camera.last_file = file_name
        camera.last_scan_time = datetime.datetime.now()
        camera.video_writer = video_writer
        camera.record_thread = threading.Thread(target=_record_loop, args=(app, camera), daemon=True)
        camera.record_thread.start()
    app.after(0, lambda: _play_audio('BatDauGhiHinh.wav'))
    update_camera_status(app, camera, f"Đang ghi: {order_id}", utils.COLOR_ORANGE_ACCENT)
    app.stop_button.configure(state="normal")
    return True

def _record_loop(app, camera):
    print(f"[CAM {camera.name}] Luồng ghi hình bắt đầu cho đơn hàng {camera.order_id}.")
    while camera.is_recording and app.is_running:
        frame_to_write = None
        with camera.frame_lock:
            if camera.frame is not None:
                frame_to_write = camera.frame.copy()
        if frame_to_write is not None:
            try:
                if camera.video_writer and camera.video_writer.isOpened():
                    camera.video_writer.write(frame_to_write)
                else:
                    print(f"[CAM {camera.name}] Lỗi: VideoWriter không mở. Dừng ghi hình.")
                    camera.is_recording = False
            except Exception as e:
                print(f"[CAM {camera.name}] Lỗi khi đang ghi frame: {e}")
                camera.is_recording = False
        time.sleep(1 / config.FPS)
    print(f"[CAM {camera.name}] Luồng ghi hình đã dừng cho đơn hàng {camera.order_id}.")

def _stop_recording_for_camera(app, camera):
    with app.lock:
        if not camera.is_recording:
            return
        recording_end_time = datetime.datetime.now()
        saved_id = camera.order_id
        saved_file_name = camera.last_file
        recording_start_time = camera.start_time
        camera.is_recording = False
        if camera.record_thread and camera.record_thread.is_alive():
            print(f"[CAM {camera.name}] Chờ luồng ghi hình hoàn tất...")
            camera.record_thread.join(timeout=2)
        if camera.video_writer:
            camera.video_writer.release()
            camera.video_writer = None
            print(f"[CAM {camera.name}] Đã giải phóng VideoWriter cho đơn {saved_id}.")
        camera.order_id = None
        camera.start_time = None
        camera.last_file = None
        camera.record_thread = None
    if saved_id and saved_file_name and recording_start_time:
        try:
            duration_sec = (recording_end_time - recording_start_time).total_seconds()
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể tính duration cho {saved_file_name}: {e}")
            duration_sec = 0
        metadata = {
            "file_name": saved_file_name,
            "camera_name": camera.name,
            "camera_id": camera.id,
            "start_time": recording_start_time.isoformat(), 
            "end_time": recording_end_time.isoformat(),
            "duration_seconds": round(duration_sec, 2)
        }
        os.makedirs(utils.METADATA_DIR, exist_ok=True)
        metadata_file_name = f"{saved_id}.json"
        metadata_file_path = os.path.join(utils.METADATA_DIR, metadata_file_name)
        try:
            with open(metadata_file_path, 'w') as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            print(f"[LỖI] Không thể lưu metadata cho {saved_id} tại {metadata_file_path}: {e}")
    update_camera_status(app, camera, "Trạng thái: Đã lưu", utils.COLOR_GREEN_SUCCESS)
    app.after(1500, lambda: update_camera_status(app, camera, "Trạng thái: Đang chờ", "#555"))
    any_recording = any(cam.is_recording for cam in app.cameras)
    if not any_recording:
        app.stop_button.configure(state="disabled")

def _play_audio(file_name):
    file_path = os.path.join(utils.AUDIO_DIR, file_name)
    if not os.path.exists(file_path):
        print(f"[AUDIO ERROR] File không tồn tại: {file_path}")
        return
    try:
        winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as e:
        print(f"[AUDIO ERROR] Lỗi phát file {file_name}: {e}")

def _play_beep():
    try:
        winsound.Beep(1000, 150)
        winsound.Beep(1500, 150)
    except Exception as e:
        print("[BEEP ERROR]", e)

def speak(text):
    def _run():
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)
            vietnamese_voice_found = False
            voices = engine.getProperty("voices")
            for v in voices:
                if ("VI" in v.id.upper() or "VN" in v.name.upper()) and "ANNA" not in v.name.upper():
                    engine.setProperty("voice", v.id)
                    vietnamese_voice_found = True
                    break
            if not vietnamese_voice_found:
                 print("[WARN] Không tìm thấy giọng nói tiếng Việt. Sử dụng giọng mặc định.")
            engine.say(text)
            engine.runAndWait()
            engine.stop() 
        except Exception as e:
            print("[TTS ERROR]", e)
    threading.Thread(target=_run, daemon=True).start()
        
def _stop_manual_recording_for_camera(app, camera):
    _stop_recording_for_camera(app, camera)
    app.after(0, lambda: _play_audio('DungGhiHinh.wav'))

def _handle_auto_switch_for_camera(app, camera, new_order_id):
    if camera.last_scan_time and (datetime.datetime.now() - camera.last_scan_time).total_seconds() < 3:
        if camera.order_id == new_order_id:
             print(f"[CAM {camera.name}] Bỏ qua quét lặp lại cho mã {new_order_id} (cooldown).")
             return
    if camera.is_recording and camera.order_id == new_order_id:
        print(f"[CAM {camera.name}] Quét lại mã '{new_order_id}'. Dừng ghi hình.")
        app.after(0, lambda: _play_audio('KetThucGhiHinh.wav'))
        _stop_recording_for_camera(app, camera)
        camera.last_scan_time = datetime.datetime.now()
        return
    with app.lock:
        for other_cam in app.cameras:
            if other_cam.is_recording and other_cam.order_id == new_order_id and other_cam.id != camera.id:
                msg = f"Lỗi: Đơn {new_order_id} đang được ghi bởi {other_cam.name}"
                update_camera_status(app, camera, msg, utils.COLOR_RED_EXIT)
                app.after(2000, lambda: update_camera_status(app, camera, "Trạng thái: Đang chờ", "#555"))
                return
    if camera.is_recording:
        _stop_recording_for_camera(app, camera)
        time.sleep(0.5)
    _start_recording_for_camera(app, camera, new_order_id)
    camera.last_scan_time = datetime.datetime.now()

def _stop_all_recordings(app):
    print("Dừng tất cả các camera đang ghi hình...")
    for camera in app.cameras:
        if camera.is_recording:
            _stop_recording_for_camera(app, camera)

def _cleanup_old_files(app):
    print(f"[DỌN DẸP] Bắt đầu kiểm tra và xóa các file đã cũ hơn {utils.DAYS_TO_KEEP} ngày...")
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=utils.DAYS_TO_KEEP)
    directories_to_clean = [utils.OUTPUT_DIR, utils.METADATA_DIR]
    deleted_count = 0
    deleted_space = 0
    for folder_path in directories_to_clean:
        if not os.path.isdir(folder_path):
            print(f"[CẢNH BÁO] Thư mục dọn dẹp không tồn tại: {folder_path}")
            continue
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    file_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_modified_time < cutoff_time:
                        file_size_bytes = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        deleted_space += file_size_bytes
                        print(f"[XÓA] Đã xóa: {file_name}")
        except Exception as e:
            print(f"[LỖI DỌN DẸP] Lỗi khi xử lý thư mục {folder_path}: {e}")
    deleted_space_mb = deleted_space / (1024 * 1024)
    print(f"[HOÀN TẤT] Đã xóa tổng cộng {deleted_count} file, giải phóng {deleted_space_mb:.2f} MB.")
    app.cleanup_queue.put((deleted_count, deleted_space_mb))
    
def _update_cleanup_log(app, count, size_mb):
    if count > 0:
        log_text = f"[DỌN DẸP] Tự động xóa {count} file cũ. Giải phóng {size_mb:.2f} MB."
        color = utils.COLOR_ORANGE_ACCENT 
    else:
        log_text = "[DỌN DẸP] Không tìm thấy file nào cần xóa."
        color = utils.COLOR_GRAY_ACCENT
    app.log_label.configure(text=log_text, text_color=color)

CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60

def start_cleanup_thread(app):
    def cleanup_loop():
        _cleanup_old_files(app) 
        while app.is_running:
            time.sleep(CLEANUP_INTERVAL_SECONDS)
            if app.is_running:
                _cleanup_old_files(app)
    threading.Thread(target=cleanup_loop, daemon=True).start()

def update_camera_status(app, camera, text, color):
    print(f"[STATUS CAM {camera.name}]: {text}")

def update_image_frame(app, frame, camera):
    pass
