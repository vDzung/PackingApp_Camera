# gui_widgets.py

import customtkinter as ctk
import os
import cv2
from PIL import Image
from . import utils, config
from .utils import get_video_metadata
from . import account_widgets
from . import camera_logic
import json # Cần thiết để xử lý dữ liệu settings tạm thời

class CameraWidget:
    """A class to hold the UI elements for a single camera."""
    def __init__(self, parent_frame, camera, app):
        self.frame = ctk.CTkFrame(parent_frame, border_width=2, border_color="gray")
        
        self.name_label = ctk.CTkLabel(self.frame, text=camera.name, font=ctk.CTkFont(size=14, weight="bold"))
        self.name_label.pack(pady=(5, 2), padx=5, fill="x")

        self.video_label = ctk.CTkLabel(self.frame, text="Đang kết nối...",
                                        fg_color="#333", text_color="white",
                                        width=config.CAMERA_PREVIEW_WIDTH,
                                        height=config.CAMERA_PREVIEW_HEIGHT)
        self.video_label.pack(pady=5, padx=5, expand=True, fill="both")

        self.status_label = ctk.CTkLabel(self.frame, text="Trạng thái: Đang chờ", text_color="#555")
        self.status_label.pack(pady=(2, 5), padx=5, fill="x")

        self.stop_button = ctk.CTkButton(self.frame, text="Dừng Ghi Hình",
                                         fg_color=utils.COLOR_RED_EXIT,
                                         command=lambda: camera_logic._stop_manual_recording_for_camera(app, camera))
        self.stop_button.pack(pady=5, padx=5, fill="x")
        self.stop_button.pack_forget() # Hide by default

def update_image_frame(app, frame, camera):
    """Updates the image frame for a specific camera widget with dynamic resizing."""
    try:
        if camera.index in app.camera_widgets:
            widget = app.camera_widgets[camera.index]
            
            # Lấy số lượng camera để quyết định kích thước hiển thị
            num_cams = len(app.cameras)
            h, w, _ = frame.shape
            aspect_ratio = w / h
            
            # Lấy kích thước màn hình để tính toán giới hạn hiển thị tối ưu
            screen_height = app.winfo_screenheight()
            available_height = screen_height - 250 # Trừ khoảng header/footer

            # --- TÍNH TOÁN KÍCH THƯỚC MỤC TIÊU (TARGET SIZE) ---
            # Thay vì dùng config cố định, ta set kích thước dựa trên bố cục
            if num_cams == 1:
                # Chế độ 1 Camera: Tự động tính toán để to nhất có thể (Max 960p)
                target_height = min(960, available_height)
            elif num_cams == 2:
                # Chế độ 2 Camera: Chia đôi màn hình (Max 600p)
                target_height = min(600, available_height)
            else:
                # Chế độ nhiều Camera (Grid): Dùng kích thước chuẩn để tiết kiệm tài nguyên
                target_height = config.CAMERA_PREVIEW_HEIGHT # Thường là 480
            
            new_height = target_height
            new_width = int(new_height * aspect_ratio)

            # Không giới hạn max_width cứng nhắc nữa để hình ảnh có thể phóng to
            # CTkImage sẽ tự scale xuống nếu container nhỏ hơn, nhưng ta cần source to để nó nét.

            resized_frame = utils.resize_frame(frame, new_width, new_height)

            # Convert the frame to a CTkImage
            img = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            ctk_img = ctk.CTkImage(light_image=Image.fromarray(img), size=(new_width, new_height))
            
            # Update the label
            widget.video_label.configure(image=ctk_img, text="")
            widget.video_label.image = ctk_img # Keep a reference
    except Exception as e:
        print(f"Error updating image for CAM {camera.name}: {e}")


def update_camera_status(app, camera, text, color):
    """Updates the status label for a specific camera widget."""
    if camera.index in app.camera_widgets:
        widget = app.camera_widgets[camera.index]
        widget.status_label.configure(text=text, text_color=color)
        if "Đang ghi" in text:
            widget.stop_button.pack(pady=5, padx=5, fill="x")
        else:
            widget.stop_button.pack_forget()

# Monkey-patch the functions in camera_logic to link to our GUI updates
camera_logic.update_image_frame = update_image_frame
camera_logic.update_camera_status = update_camera_status


def create_widgets(app):
    """Khởi tạo toàn bộ các thành phần giao diện chính."""
    
    # 2. Sidebar/Navigation Frame
    app.sidebar_frame = ctk.CTkFrame(app, width=200, fg_color=utils.COLOR_BACKGROUND, corner_radius=0)
    app.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 2), pady=(0, 0))
    app.sidebar_frame.grid_rowconfigure(5, weight=1)

    app.logo_label = ctk.CTkLabel(app.sidebar_frame, text="📦 PACKING SYSTEM", 
                                  font=ctk.CTkFont(size=18, weight="bold"), text_color=utils.COLOR_ORANGE_ACCENT)
    app.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
    
    app.record_button = ctk.CTkButton(app.sidebar_frame, text="QUÉT ĐƠN ĐÓNG GÓI", 
                                      command=lambda: select_frame(app, "record"), fg_color=utils.COLOR_ORANGE_ACCENT)
    app.record_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

    app.search_button = ctk.CTkButton(app.sidebar_frame, text="TRA CỨU VIDEO", 
                                      command=lambda: select_frame(app, "search"), fg_color=utils.COLOR_BLUE_ACTION)
    app.search_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
    
    app.account_button = ctk.CTkButton(app.sidebar_frame, text="👤 TÀI KHOẢN", 
                                       command=lambda: select_frame(app, "account"), fg_color=utils.COLOR_GREEN_SUCCESS)
    app.account_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
    
    app.settings_button = ctk.CTkButton(app.sidebar_frame, text="⚙ CÀI ĐẶT", 
                                       command=lambda: select_frame(app, "settings"), fg_color=utils.COLOR_GRAY_ACCENT)
    app.settings_button.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

    app.exit_button = ctk.CTkButton(app.sidebar_frame, 
                                text="THOÁT ỨNG DỤNG",
                                command=app.on_closing, 
                                fg_color=utils.COLOR_RED_EXIT)
    app.exit_button.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="ew") 

    # 3. Main Content Frame
    app.main_content_frame = ctk.CTkFrame(app, fg_color=utils.COLOR_BACKGROUND)
    app.main_content_frame.grid(row=0, column=1, rowspan=2, sticky="nsew")
    app.main_content_frame.grid_columnconfigure(0, weight=1)
    app.main_content_frame.grid_rowconfigure(0, weight=1)
    
    app.frames = {}
    
    _create_record_frame(app)
    _create_search_frame(app)
    account_widgets._create_account_frame(app)
    _create_settings_frame(app)
    
    select_frame(app, "record")

def select_frame(app, name):
    """Chuyển đổi giữa các frame (tab)"""
    for frame_name, frame in app.frames.items():
        if frame_name == name:
            frame.grid(row=0, column=0, sticky="nsew")
        else:
            frame.grid_forget()

def refresh_camera_views(app):
    """
    Hàm quan trọng: Xóa giao diện camera cũ và vẽ lại dựa trên cấu hình mới.
    Được gọi khi khởi động app hoặc sau khi Lưu cài đặt.
    """
    # 1. Xóa các widget camera cũ trong center_frame
    for widget in app.camera_center_frame.winfo_children():
        widget.destroy()
    
    app.camera_widgets = {} # Reset danh sách quản lý widget

    # --- TÍNH TOÁN BỐ CỤC LƯỚI (GRID LAYOUT) ---
    num_cams = len(app.cameras)
    
    # Xác định số cột dựa trên số lượng camera
    if num_cams == 1:
        columns = 1
    elif num_cams == 2:
        columns = 2 # 2 Camera nằm ngang
    elif num_cams <= 4:
        columns = 2 # 3-4 Camera: Lưới 2x2
    else:
        columns = 3 # 5+ Camera: Lưới 3 cột (ví dụ 2 hàng x 3 cột)

    # Reset cấu hình grid cũ của frame chứa camera
    for i in range(10): # Reset một số lượng hàng/cột dự phòng
        app.camera_center_frame.grid_columnconfigure(i, weight=0)
        app.camera_center_frame.grid_rowconfigure(i, weight=0)

    # Cấu hình weight cho các cột mới để chúng giãn đều nhau
    for c in range(columns):
        app.camera_center_frame.grid_columnconfigure(c, weight=1)

    # 2. Vẽ lại các camera mới từ app.cameras (đã được reload từ logic)
    for i, camera in enumerate(app.cameras):
        widget = CameraWidget(app.camera_center_frame, camera, app)
        
        # Tính toán vị trí row/col
        row = i // columns
        col = i % columns
        
        # Padding: Nếu chỉ có 1 cam thì ít padding để to nhất, nhiều cam thì tăng khoảng cách
        pad_val = 5 if num_cams > 1 else 0
        
        widget.frame.grid(row=row, column=col, padx=pad_val, pady=pad_val, sticky="nsew")
        
        # Cấu hình weight cho hàng hiện tại để giãn chiều dọc
        app.camera_center_frame.grid_rowconfigure(row, weight=1) 
        
        app.camera_widgets[camera.index] = widget

def _create_record_frame(app):
    """Khung Ghi hình với layout cho nhiều camera."""
    app.record_frame = ctk.CTkFrame(app.main_content_frame, fg_color=utils.COLOR_BACKGROUND)
    app.frames["record"] = app.record_frame
    app.record_frame.grid_columnconfigure(0, weight=1)
    app.record_frame.grid_rowconfigure(1, weight=1) # Row 1 for camera views

    # --- Top Control Frame ---
    top_frame = ctk.CTkFrame(app.record_frame, fg_color="transparent")
    top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    top_frame.grid_columnconfigure(0, weight=1) # Allow the button to push to the right

    # app.log_label đã được loại bỏ theo yêu cầu

    app.stop_button = ctk.CTkButton(top_frame, text="■ DỪNG TẤT CẢ GHI HÌNH", 
                                    command=lambda: camera_logic._stop_all_recordings(app), 
                                    fg_color=utils.COLOR_RED_EXIT, 
                                    font=ctk.CTkFont(size=14, weight="bold"))
    app.stop_button.grid(row=0, column=0, padx=(10, 0), sticky="e") # Di chuyển sang column 0
    app.stop_button.configure(state="disabled")

    # --- Nút Làm Mới Camera (MỚI) ---
    def _manual_refresh_cameras():
        camera_logic.restart_cameras(app)
        refresh_camera_views(app)

    app.refresh_cam_button = ctk.CTkButton(top_frame, text="↻ LÀM MỚI CAMERA", 
                                    command=_manual_refresh_cameras, 
                                    fg_color=utils.COLOR_BLUE_ACTION, 
                                    font=ctk.CTkFont(size=14, weight="bold"))
    app.refresh_cam_button.grid(row=0, column=1, padx=10, sticky="e")

    # --- Cameras Container Frame (để căn giữa) ---
    # Frame này sẽ co lại theo nội dung và được pack vào giữa.
    camera_container = ctk.CTkFrame(app.record_frame, fg_color="transparent")
    camera_container.grid(row=1, column=0, sticky="", padx=10, pady=10)
    
    app.camera_widgets = {} # Dictionary to hold CameraWidget instances

    if not hasattr(app, 'cameras') or not app.cameras:
        ctk.CTkLabel(camera_container, text="Không tìm thấy camera nào trong 'cameras.json'.",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="red").pack(expand=True)
        return

    # --- Center Alignment Frame ---
    # Frame này dùng để chứa các camera và được đặt vào giữa `camera_container`
    # Lưu reference vào app để hàm refresh có thể truy cập
    app.camera_center_frame = ctk.CTkFrame(camera_container, fg_color="transparent")
    app.camera_center_frame.pack(expand=True, fill="both") # fill="both" để mở rộng tối đa

    # Gọi hàm vẽ giao diện lần đầu
    refresh_camera_views(app)

def _create_search_frame(app):
    """Khung Tra cứu."""
    app.search_frame = ctk.CTkFrame(app.main_content_frame, fg_color=utils.COLOR_BACKGROUND)
    app.frames["search"] = app.search_frame
    app.search_frame.grid_columnconfigure(0, weight=1)
    
    ctk.CTkLabel(app.search_frame, text="TRA CỨU VIDEO ĐÓNG GÓI", 
                 font=ctk.CTkFont(size=24, weight="bold"), text_color="#333").grid(row=0, column=0, pady=(20, 10))

    # Khung tìm kiếm (row 1)
    search_widget_frame = ctk.CTkFrame(app.search_frame, fg_color="white", corner_radius=10)
    search_widget_frame.grid(row=1, column=0, padx=50, pady=20, sticky="ew")
    search_widget_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(search_widget_frame, text="Nhập Mã Đơn Hàng:", font=ctk.CTkFont(size=16)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
    app.search_entry = ctk.CTkEntry(search_widget_frame, width=300, placeholder_text="Ví dụ: SPX...")
    app.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    action_buttons_frame = ctk.CTkFrame(search_widget_frame, fg_color="transparent")
    action_buttons_frame.grid(row=0, column=2, padx=10, pady=10)
    
    app.search_button_action = ctk.CTkButton(action_buttons_frame, text="🔍 TÌM KIẾM", 
                                             command=lambda: utils.search_video(app, create_list_buttons), 
                                             fg_color=utils.COLOR_BLUE_ACTION)
    app.search_button_action.grid(row=0, column=0, padx=(0, 5), sticky="e")
    
    app.refresh_button = ctk.CTkButton(action_buttons_frame, text="🔄 LÀM MỚI", 
                                       command=lambda: utils.display_file_list(app, create_list_buttons), 
                                       fg_color=utils.COLOR_GREEN_ACTION,
                                       hover_color="#006400")
    app.refresh_button.grid(row=0, column=1, sticky="e")
    
    app.result_label = ctk.CTkLabel(app.search_frame, text="Kết quả sẽ hiển thị ở đây.", 
                                    text_color="#666", wraplength=500)
    app.result_label.grid(row=2, column=0, pady=(10, 20))
    
    ctk.CTkLabel(app.search_frame, text="📦 DANH SÁCH VIDEO ĐÓNG GÓI:", 
                 font=ctk.CTkFont(size=16, weight="bold"), text_color=utils.COLOR_BLUE_ACTION).grid(row=3, column=0, padx=50, pady=(10, 5), sticky="w")

    app.list_container_frame = ctk.CTkScrollableFrame(app.search_frame, fg_color="white", corner_radius=10, height=350)
    app.list_container_frame.grid(row=4, column=0, padx=50, pady=(0, 10), sticky="ew")
    app.list_container_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(app.search_frame, text=f"Thư mục lưu trữ: {utils.OUTPUT_DIR}", 
                 text_color="#999").grid(row=5, column=0, pady=(0, 20))
    
    utils.display_file_list(app, create_list_buttons)

def create_list_buttons(app, file_names):
    """Xóa các widget cũ và tạo bảng chi tiết video, căn chỉnh thẩm mỹ hơn."""

    for widget in app.list_container_frame.winfo_children():
        widget.destroy()

    if not file_names:
        ctk.CTkLabel(app.list_container_frame, text="Thư mục Video hiện đang trống.", 
                      text_color="#666",
                      font=ctk.CTkFont(family=utils.FONT_FAMILY_SYSTEM, size=utils.FONT_SIZE_NORMAL)).pack(padx=10, pady=10, fill="x")
        return

    headers = [("STT", 1), ("Mã Đơn Hàng", 4), ("🕐 Bắt Đầu", 3), ("🛑 Kết Thúc", 3), ("⏳ Thời Lượng", 2), ("Hành Động", 4)]
    
    header_frame = ctk.CTkFrame(app.list_container_frame, fg_color="#3B8ED0")
    header_frame.pack(fill="x", padx=5, pady=(0, 2)) 
    
    for col_idx, (text, weight) in enumerate(headers):
        label = ctk.CTkLabel(header_frame, text=text, 
                             font=ctk.CTkFont(size=14, weight="bold"), 
                             text_color="white")
        label.grid(row=0, column=col_idx, sticky="nsew", padx=5, pady=5)
        header_frame.grid_columnconfigure(col_idx, weight=weight)
        
    for i, file_name in enumerate(file_names):
        file_path = os.path.join(utils.OUTPUT_DIR, file_name)
        metadata = get_video_metadata(file_name) 
        
        row_frame = ctk.CTkFrame(app.list_container_frame)
        row_frame.pack(fill="x", padx=5, pady=0)
        
        bg_color = ("#ffffff" if i % 2 == 0 else "#f0f0f0") 
        row_frame.configure(fg_color=bg_color)
        
        for col_idx, (_, weight) in enumerate(headers):
            row_frame.grid_columnconfigure(col_idx, weight=weight)
            
        ctk.CTkLabel(row_frame, text=f"{i+1}.", fg_color="transparent", 
                     anchor="center").grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        entry_file_name = ctk.CTkEntry(row_frame, fg_color="transparent", border_width=0, 
                                       text_color="#333", justify="left")
        entry_file_name.insert(0, file_name)
        entry_file_name.configure(state="readonly") 
        entry_file_name.grid(row=0, column=1, padx=(5, 10), sticky="ew")

        ctk.CTkLabel(row_frame, text=metadata["start_time"], fg_color="transparent", 
                     anchor="center").grid(row=0, column=2, padx=5, pady=5, sticky="nsew") 
        
        ctk.CTkLabel(row_frame, text=metadata["end_time"], fg_color="transparent", 
                     anchor="center").grid(row=0, column=3, padx=5, pady=5, sticky="nsew") 
        
        ctk.CTkLabel(row_frame, 
                     text=metadata["duration"], 
                     font=ctk.CTkFont(size=14, weight="bold"), 
                     text_color=utils.COLOR_ORANGE_ACCENT, 
                     fg_color="transparent", 
                     anchor="center").grid(row=0, column=4, padx=5, pady=5, sticky="nsew") 
        
        action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        action_frame.grid(row=0, column=5, padx=5, pady=5, sticky="e") 
        
        ctk.CTkButton(action_frame, text="▶ Xem Video", 
                      command=lambda path=file_path: utils.open_file_or_dir(path), 
                      width=90, height=25, fg_color=utils.COLOR_ORANGE_ACCENT).pack(side="left", padx=(0, 5))
                      
        ctk.CTkButton(action_frame, text="✕ Xóa Video", 
                      command=lambda name=file_name: utils.delete_video(app, name, create_list_buttons), 
                      width=90, height=25, fg_color=utils.COLOR_RED_EXIT).pack(side="left")

def _create_settings_frame(app):
    """Khung Cài đặt Camera (Mới)."""
    app.settings_frame = ctk.CTkFrame(app.main_content_frame, fg_color=utils.COLOR_BACKGROUND)
    app.frames["settings"] = app.settings_frame
    app.settings_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(app.settings_frame, text="CẤU HÌNH CAMERA", 
                 font=ctk.CTkFont(size=24, weight="bold"), text_color="#333").pack(pady=(20, 10))

    # Container chính
    content_frame = ctk.CTkScrollableFrame(app.settings_frame, fg_color="white", corner_radius=10, width=600, height=500)
    content_frame.pack(pady=10, padx=20, fill="both", expand=True)

    # --- Load Settings hiện tại ---
    current_settings = camera_logic.get_camera_settings()
    
    # 1. Chọn loại Camera
    ctk.CTkLabel(content_frame, text="Loại Nguồn Camera:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
    
    camera_type_var = ctk.StringVar(value=current_settings.get("camera_type", "WEBCAM"))
    
    def on_type_change():
        if camera_type_var.get() == "WEBCAM":
            webcam_frame.pack(fill="x", padx=10, pady=5)
            rtsp_frame.pack_forget()
        else:
            webcam_frame.pack_forget()
            rtsp_frame.pack(fill="x", padx=10, pady=5)

    type_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    type_frame.pack(fill="x", padx=10)
    ctk.CTkRadioButton(type_frame, text="Webcam (USB)", variable=camera_type_var, value="WEBCAM", command=on_type_change).pack(side="left", padx=10)
    ctk.CTkRadioButton(type_frame, text="Camera IP (RTSP)", variable=camera_type_var, value="RTSP", command=on_type_change).pack(side="left", padx=10)

    # 2. Cấu hình Webcam
    webcam_frame = ctk.CTkFrame(content_frame, border_width=1, border_color="#ddd")
    ctk.CTkLabel(webcam_frame, text="Chỉ số Webcam (Mặc định là 0):").pack(side="left", padx=10, pady=10)
    webcam_index_entry = ctk.CTkEntry(webcam_frame, width=50)
    webcam_index_entry.insert(0, str(current_settings.get("webcam_index", 0)))
    webcam_index_entry.pack(side="left", padx=10)

    # 3. Cấu hình RTSP (Danh sách động)
    rtsp_frame = ctk.CTkFrame(content_frame, border_width=1, border_color="#ddd")
    ctk.CTkLabel(rtsp_frame, text="Danh sách Camera RTSP:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
    
    rtsp_list_container = ctk.CTkFrame(rtsp_frame, fg_color="transparent")
    rtsp_list_container.pack(fill="x", padx=5, pady=5)
    
    rtsp_entries = [] # List chứa các widget entry để lấy dữ liệu sau này

    def add_rtsp_row(name="", url=""):
        row_frame = ctk.CTkFrame(rtsp_list_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        
        ctk.CTkLabel(row_frame, text="Tên:").pack(side="left", padx=2)
        name_entry = ctk.CTkEntry(row_frame, width=100)
        name_entry.insert(0, name)
        name_entry.pack(side="left", padx=2)
        
        ctk.CTkLabel(row_frame, text="URL:").pack(side="left", padx=2)
        url_entry = ctk.CTkEntry(row_frame, width=300)
        url_entry.insert(0, url)
        url_entry.pack(side="left", padx=2, fill="x", expand=True)
        
        del_btn = ctk.CTkButton(row_frame, text="X", width=30, fg_color=utils.COLOR_RED_EXIT,
                                command=lambda: delete_rtsp_row(row_frame, name_entry, url_entry))
        del_btn.pack(side="left", padx=5)
        
        rtsp_entries.append({"frame": row_frame, "name": name_entry, "url": url_entry})

    def delete_rtsp_row(frame, name_entry, url_entry):
        frame.destroy()
        # Xóa khỏi danh sách quản lý
        for item in rtsp_entries:
            if item["name"] == name_entry and item["url"] == url_entry:
                rtsp_entries.remove(item)
                break

    # Load dữ liệu cũ vào list
    saved_rtsp_list = current_settings.get("rtsp_list", [])
    # Tương thích ngược
    if not saved_rtsp_list and current_settings.get("rtsp_url"):
        saved_rtsp_list = [{"name": "Camera 1", "url": current_settings.get("rtsp_url")}]
        
    for item in saved_rtsp_list:
        add_rtsp_row(item.get("name", ""), item.get("url", ""))
        
    # Nút thêm dòng
    ctk.CTkButton(rtsp_frame, text="+ Thêm Camera", command=lambda: add_rtsp_row(f"Camera {len(rtsp_entries)+1}", ""),
                  fg_color=utils.COLOR_BLUE_ACTION, height=30).pack(pady=10)

    # Trigger hiển thị ban đầu
    on_type_change()

    # --- Label Thông Báo Trạng Thái (Khởi tạo 1 lần duy nhất) ---
    status_label = ctk.CTkLabel(app.settings_frame, text="", font=ctk.CTkFont(size=14, weight="bold"))

    # --- Nút Lưu ---
    def save_settings():
        new_settings = {
            "camera_type": camera_type_var.get(),
            "webcam_index": int(webcam_index_entry.get()) if webcam_index_entry.get().isdigit() else 0,
            "reconnect_delay": 5
        }
        
        # Thu thập RTSP list
        new_rtsp_list = []
        for item in rtsp_entries:
            name = item["name"].get().strip()
            url = item["url"].get().strip()
            if url: # Chỉ lưu nếu có URL
                new_rtsp_list.append({"name": name, "url": url})
        
        new_settings["rtsp_list"] = new_rtsp_list
        
        # Lưu và khởi động lại
        if camera_logic.save_camera_settings(new_settings):
            # Gọi hàm restart bên camera_logic
            # Lưu ý: restart_cameras cần được gọi cẩn thận để tránh treo UI
            # Ở đây ta set cờ hoặc gọi trực tiếp nếu logic cho phép
            camera_logic.restart_cameras(app)
            
            # QUAN TRỌNG: Vẽ lại giao diện camera ngay lập tức
            refresh_camera_views(app)
            
            # Cập nhật nội dung cho label có sẵn (Thay vì tạo mới)
            status_label.configure(text="✅ Đã lưu và khởi động lại Camera!", text_color=utils.COLOR_GREEN_SUCCESS)
            
            # Tự động xóa thông báo sau 3 giây để giao diện sạch sẽ
            app.after(3000, lambda: status_label.configure(text=""))
            
            # Chuyển về màn hình record
            app.after(1500, lambda: select_frame(app, "record"))

    ctk.CTkButton(app.settings_frame, text="LƯU CẤU HÌNH & KHỞI ĐỘNG LẠI", 
                  command=save_settings, fg_color=utils.COLOR_GREEN_SUCCESS, height=50, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10), padx=20, fill="x")

    # Đặt label thông báo ở dưới cùng nút Lưu
    status_label.pack(pady=5)
