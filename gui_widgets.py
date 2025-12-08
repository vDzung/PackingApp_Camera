# gui_widgets.py

import customtkinter as ctk
import os
import cv2
from PIL import Image
from . import utils, config
from .utils import get_video_metadata
from . import account_widgets
from . import camera_logic

class CameraWidget:
    """A class to hold the UI elements for a single camera."""
    def __init__(self, parent_frame, camera, app):
        self.frame = ctk.CTkFrame(parent_frame, border_width=2, border_color="gray")
        
        self.name_label = ctk.CTkLabel(self.frame, text=camera.name, font=ctk.CTkFont(size=14, weight="bold"))
        self.name_label.pack(pady=(5, 2), padx=5, fill="x")

        self.video_label = ctk.CTkLabel(self.frame, text="Đang kết nối...",
                                        fg_color="#333", text_color="white",
                                        width=config.CAMERA_PREVIEW_WIDTH // 2,
                                        height=config.CAMERA_PREVIEW_HEIGHT // 2)
        self.video_label.pack(pady=5, padx=5, expand=True, fill="both")

        self.status_label = ctk.CTkLabel(self.frame, text="Trạng thái: Đang chờ", text_color="#555")
        self.status_label.pack(pady=(2, 5), padx=5, fill="x")

        self.stop_button = ctk.CTkButton(self.frame, text="Dừng Ghi Hình",
                                         fg_color=utils.COLOR_RED_EXIT,
                                         command=lambda: camera_logic._stop_manual_recording_for_camera(app, camera))
        self.stop_button.pack(pady=5, padx=5, fill="x")
        self.stop_button.pack_forget() # Hide by default

def update_image_frame(app, frame, camera):
    """Updates the image frame for a specific camera widget."""
    try:
        if camera.index in app.camera_widgets:
            widget = app.camera_widgets[camera.index]
            
            # Resize frame for the smaller widget view
            h, w, _ = frame.shape
            aspect_ratio = w / h
            new_height = config.CAMERA_PREVIEW_HEIGHT // 2
            new_width = int(new_height * aspect_ratio)

            # Ensure the new width doesn't exceed the widget's max width
            max_width = config.CAMERA_PREVIEW_WIDTH // 2
            if new_width > max_width:
                new_width = max_width
                new_height = int(new_width / aspect_ratio)

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
    
    select_frame(app, "record")

def select_frame(app, name):
    """Chuyển đổi giữa các frame (tab)"""
    for frame_name, frame in app.frames.items():
        if frame_name == name:
            frame.grid(row=0, column=0, sticky="nsew")
        else:
            frame.grid_forget()

def _create_record_frame(app):
    """Khung Ghi hình với layout cho nhiều camera."""
    app.record_frame = ctk.CTkFrame(app.main_content_frame, fg_color=utils.COLOR_BACKGROUND)
    app.frames["record"] = app.record_frame
    app.record_frame.grid_columnconfigure(0, weight=1)
    app.record_frame.grid_rowconfigure(1, weight=1)

    # --- Top Control Frame ---
    top_frame = ctk.CTkFrame(app.record_frame, fg_color="transparent")
    top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    top_frame.grid_columnconfigure(0, weight=1)
    top_frame.grid_columnconfigure(1, weight=0) # Give the button column a fixed width

    app.log_label = ctk.CTkLabel(top_frame, text="Sẵn sàng. Vui lòng đưa mã QR vào camera để bắt đầu.", 
                                 text_color="#666", wraplength=700, justify="left")
    app.log_label.grid(row=0, column=0, sticky="ew")

    app.stop_button = ctk.CTkButton(top_frame, text="■ DỪNG TẤT CẢ GHI HÌNH", 
                                    command=lambda: camera_logic._stop_all_recordings(app), 
                                    fg_color=utils.COLOR_RED_EXIT, 
                                    font=ctk.CTkFont(size=14, weight="bold"))
    app.stop_button.grid(row=0, column=1, padx=(10, 0), sticky="e")
    app.stop_button.configure(state="disabled")

    # --- Cameras Grid Frame ---
    app.camera_grid_frame = ctk.CTkScrollableFrame(app.record_frame, fg_color="transparent")
    app.camera_grid_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
    
    app.camera_widgets = {} # Dictionary to hold CameraWidget instances

    if not hasattr(app, 'cameras') or not app.cameras:
        ctk.CTkLabel(app.camera_grid_frame, text="Không tìm thấy camera nào trong 'cameras.json'.",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="red").pack(expand=True)
        return

    # Determine grid layout (e.g., 2 columns for up to 4 cams, 3 for more)
    num_cameras = len(app.cameras)
    num_cols = 2 if num_cameras <= 4 else 3
    
    for i, camera in enumerate(app.cameras):
        row, col = divmod(i, num_cols)
        app.camera_grid_frame.grid_columnconfigure(col, weight=1)
        
        widget = CameraWidget(app.camera_grid_frame, camera, app)
        widget.frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        app.camera_widgets[camera.index] = widget

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
    app.search_entry = ctk.CTkEntry(search_widget_frame, width=300, placeholder_text="Ví dụ: SPXVN...")
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

