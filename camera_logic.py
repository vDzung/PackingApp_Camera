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

# Đường dẫn file cài đặt dùng chung
SETTINGS_FILE = r".\camera_settings.json"

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
        self.source = camera_info.get('source') # Có thể là URL (str) hoặc Index (int)
        self.index = index
        self.is_active = True  # Cờ kiểm soát vòng đời của luồng camera
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
        self.last_warning_time = None
        self.last_warning_order_id = None

    def release(self):
        """Release camera resources."""
        if self.preview_cap and self.preview_cap.isOpened():
            self.preview_cap.release()
            print(f"[CAM {self.name}] Preview capture released.")

def load_cameras_from_settings(app):
    """
    Loads camera configurations from camera_settings.json.
    Hỗ trợ chuyển đổi giữa Webcam và danh sách RTSP.
    """
    try:
        if not os.path.exists(SETTINGS_FILE):
            print(f"[WARN] {SETTINGS_FILE} not found. Creating default.")
            default_settings = {
                "camera_type": "WEBCAM",
                "webcam_index": 0,
                "rtsp_list": [],
                "reconnect_delay": 5
            }
            save_camera_settings(default_settings)
            
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            
        camera_objects = []
        camera_type = settings.get("camera_type", "WEBCAM")
        
        if camera_type == "RTSP":
            rtsp_list = settings.get("rtsp_list")
            # Hỗ trợ tương thích ngược: Nếu không có rtsp_list, thử đọc rtsp_url cũ
            if rtsp_list is None:
                old_url = settings.get("rtsp_url")
                if old_url:
                    rtsp_list = [{"name": "Camera 1", "url": old_url}]
                else:
                    rtsp_list = []

            for i, item in enumerate(rtsp_list):
                cam_info = {
                    "id": i,
                    "name": item.get("name", f"Camera {i+1}"),
                    "source": item.get("url")
                }
                camera_objects.append(Camera(app, cam_info, i))
        else:
            # WEBCAM Mode
            idx = settings.get("webcam_index", 0)
            cam_info = {
                "id": 0,
                "name": "Webcam",
                "source": int(idx)
            }
            camera_objects.append(Camera(app, cam_info, 0))
            
        return camera_objects

    except Exception as e:
        print(f"[ERROR] Error loading settings: {e}")
        return []

def get_camera_settings():
    """
    Đọc và trả về toàn bộ cấu hình hiện tại.
    Dùng hàm này để hiển thị dữ liệu lên giao diện Cài đặt.
    """
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_camera_settings(settings_data):
    """
    Lưu cấu hình camera vào file JSON.
    Hàm này được gọi từ giao diện Cài đặt khi người dùng nhấn 'Lưu'.
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4)
        print("[SETTINGS] Đã lưu cấu hình thành công.")
        return True
    except Exception as e:
        print(f"[SETTINGS] Lỗi khi lưu cấu hình: {e}")
        return False

# Alias để tương thích ngược nếu cần
load_cameras_from_json = load_cameras_from_settings

def start_camera_threads(app):
    """Khởi động các luồng cho từng camera đã được load trước đó."""
    if not app.cameras:
        error_msg = "Lỗi: Không có camera nào được tải để bắt đầu luồng."
        if hasattr(app, 'log_label') and app.log_label.winfo_exists():
            app.after(0, lambda: app.log_label.configure(text=error_msg, text_color="red"))
        else:
            print(f"[GUI ERROR] {error_msg}")
        return
    app.camera_threads = []
    for camera in app.cameras:
        thread = threading.Thread(target=_camera_feed_loop, args=(app, camera), daemon=True)
        app.camera_threads.append(thread)
        thread.start()

def restart_cameras(app):
    """
    Dừng toàn bộ camera hiện tại, tải lại cấu hình và khởi động lại.
    Được gọi sau khi người dùng thay đổi cài đặt.
    """
    print("[SYSTEM] Đang khởi động lại hệ thống camera...")
    # 1. Dừng ghi hình nếu đang ghi
    _stop_all_recordings(app)
    
    # 2. Dừng các luồng camera (logic này phụ thuộc vào việc app.is_running được xử lý thế nào, 
    # ở đây ta giả định set cờ tạm thời hoặc chờ luồng kết thúc nếu có cơ chế stop riêng)
    # Đánh dấu is_active = False để luồng cũ tự thoát vòng lặp
    for cam in app.cameras:
        cam.is_active = False
        cam.release()
    
    # 3. Tải lại cấu hình mới
    app.cameras = load_cameras_from_settings(app)
    
    # 4. Khởi động lại luồng
    start_camera_threads(app)

def _draw_overlay(frame, text_left, text_right):
    """Vẽ overlay thông tin (Mã đơn, Thời gian) lên frame."""
    if frame is None: return

    h, w = frame.shape[:2]
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 0.7
    FONT_THICKNESS = 2
    TEXT_COLOR = (255, 255, 255)
    BG_COLOR = (0, 0, 0)
    PADDING = 5
    
    # Draw Left Text (Order ID)
    if text_left:
        (tw, th), baseline = cv2.getTextSize(text_left, FONT, FONT_SCALE, FONT_THICKNESS)
        x, y = 10, 30
        cv2.rectangle(frame, (x - PADDING, y - th - PADDING), (x + tw + PADDING, y + baseline + PADDING), BG_COLOR, -1)
        cv2.putText(frame, text_left, (x, y), FONT, FONT_SCALE, TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

    # Draw Right Text (Timestamp)
    if text_right:
        (tw, th), baseline = cv2.getTextSize(text_right, FONT, FONT_SCALE, FONT_THICKNESS)
        x = w - tw - 10
        y = 30
        cv2.rectangle(frame, (x - PADDING, y - th - PADDING), (x + tw + PADDING, y + baseline + PADDING), BG_COLOR, -1)
        cv2.putText(frame, text_right, (x, y), FONT, FONT_SCALE, TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

def _camera_feed_loop(app, camera):
    """
    The main processing loop for a camera.
    - Uses QReader for fast and reliable QR code detection.
    - Processes a central Region of Interest (ROI) to improve performance.
    - Draws the ROI on the preview to guide the user.
    """
    # 1. Initialize the QReader with performance optimizations
    # 'n' model is faster, and min_prob filters weak detections.
    qreader = QReader(model_size='n', min_confidence=0.5)

    # 2. Set scan interval to avoid processing every frame
    scan_interval = max(1, config.FPS // 5)  # Scan ~5 times per second
    frame_counter = 0

    while app.is_running and camera.is_active:
        # --- Connection Management ---
        if camera.preview_cap is None or not camera.preview_cap.isOpened():
            with camera.frame_lock:
                camera.frame = None
            print(f"[CAM {camera.name}] Đang kết nối tới nguồn: {camera.source}")
            app.after(0, lambda: update_camera_status(app, camera, "Đang kết nối...", utils.COLOR_GRAY_ACCENT))
            
            # Xử lý kết nối dựa trên loại nguồn (RTSP URL hoặc Webcam Index)
            if isinstance(camera.source, str):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp" # Tối ưu cho RTSP
                camera.preview_cap = cv2.VideoCapture(camera.source, cv2.CAP_FFMPEG)
            else:
                camera.preview_cap = cv2.VideoCapture(camera.source, cv2.CAP_DSHOW)
                
            if not camera.preview_cap.isOpened():
                app.after(0, lambda: update_camera_status(app, camera, "Lỗi kết nối: Kiểm tra URL/Mạng", utils.COLOR_RED_EXIT))
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
            if decoded_qrs and decoded_qrs[0]:
                order_id = decoded_qrs[0].strip()
                # Schedule the business logic to run on the main thread
                app.after(0, lambda: _handle_auto_switch_for_camera(app, camera, order_id))

        # --- GUI Update with Visual Feedback ---
        # Draw overlay info if recording
        if camera.is_recording:
            timestamp_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            _draw_overlay(frame_to_process, camera.order_id, timestamp_str)

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
        # Kiểm tra cooldown 5 giây cho cảnh báo trùng lặp
        current_time = datetime.datetime.now()
        if camera.last_warning_order_id == order_id and camera.last_warning_time:
            if (current_time - camera.last_warning_time).total_seconds() < 5:
                return False

        camera.last_warning_order_id = order_id
        camera.last_warning_time = current_time
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
                # Draw overlay info on recorded frame
                timestamp_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                _draw_overlay(frame_to_write, camera.order_id, timestamp_str)

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
        # Logic mới: Nếu quét lại đúng mã đơn hàng đang ghi -> BỎ QUA (Tiếp tục ghi hình)
        # Chỉ cập nhật thời gian quét để tránh xử lý lặp lại quá nhanh trong vòng lặp
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
    if hasattr(app, 'log_label') and app.log_label.winfo_exists():
        app.log_label.configure(text=log_text, text_color=color)
    else:
        print(f"Cleanup Log: {log_text}") # Fallback to print if log_label is removed

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
