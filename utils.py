# utils.py

import os
import customtkinter as ctk
import subprocess
import sys
import time
import json
from datetime import datetime, timedelta
import cv2

# Số ngày giữ lại file tối đa
DAYS_TO_KEEP = 30
# --- CẤU HÌNH VÀ THIẾT LẬP ---
OUTPUT_DIR = os.path.join(os.getcwd(), 'Video')
METADATA_DIR = os.path.join(os.getcwd(), 'Metadata')
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_files")

#Format Video mp4
VIDEO_CODEC_FOURCC = 'mp4v' 
VIDEO_FILE_EXTENSION = '.mp4'

#FONT

FONT_FAMILY_SYSTEM = "Arial"
FONT_SIZE_HEADER = 18
FONT_SIZE_SUCCESS = 16
FONT_SIZE_NORMAL = 14

# Màu sắc
COLOR_ORANGE_ACCENT = "#FF9800"
COLOR_BACKGROUND = "#F5F5F5"
COLOR_BLUE_ACTION = "#2196F3"
COLOR_RED_EXIT = "#F44336"
COLOR_GREEN_ACTION = "#4CAF50"
COLOR_BLACK_TEXT = "#000000"
COLOR_GREEN_SUCCESS = "#008000"
COLOR_GRAY_ACCENT = "#A9A9A9"

# Tạo thư mục đầu ra
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)

# ----------------------------------------------------
# A. HÀM TIỆN ÍCH MỞ THƯ MỤC/FILE (MỚI)
# ----------------------------------------------------

def open_file_or_dir(path):
    """Mở file hoặc thư mục bằng trình quản lý file mặc định của hệ thống."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Lỗi khi mở đường dẫn {path}: {e}")

def resize_frame(frame, width, height):
    """Resizes a frame to a specific width and height."""
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

# ----------------------------------------------------
# B. HÀM TRA CỨU VIDEO (CẬP NHẬT)
# ----------------------------------------------------

def search_video(app_instance, create_buttons_func):
    """Tìm kiếm file video theo Mã Đơn Hàng và kiểm tra trạng thái ghi hình."""
    order_id = app_instance.search_entry.get().strip()
    
    if not order_id:
        app_instance.result_label.configure(
            text="[LỖI] Vui lòng nhập Mã Đơn Hàng.", 
            text_color=COLOR_RED_EXIT,
            font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_NORMAL, weight="normal")
        )
        display_file_list(app_instance, create_buttons_func)
        return

    found_file = None
    
    # 1. Quét thư mục để tìm file khớp
    for f in os.listdir(OUTPUT_DIR):
        file_path = os.path.join(OUTPUT_DIR, f)
        if os.path.isfile(file_path) and f.startswith(order_id) and f.lower().endswith((".avi", ".mp4", ".mov", ".mkv")):
             found_file = f
             break

    if found_file:
        file_path = os.path.join(OUTPUT_DIR, found_file)
        
        # BƯỚC MỚI: KIỂM TRA BẮT BUỘC NẾU FILE ĐANG GHI
        current_recording = getattr(app_instance, 'current_recording_filename', None)
        
        if current_recording and current_recording == found_file:
            # Trường hợp đang ghi hình
            app_instance.result_label.configure(
                text=f"[CẢNH BÁO] Mã vận đơn '{order_id}' đang ghi hình.\nHãy kết thúc và lưu Video để xem.", 
                text_color=COLOR_RED_EXIT, 
                font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_SUCCESS, weight="bold")
            )
            
        else:
            # Trường hợp file đã hoàn thành và có thể mở
            app_instance.result_label.configure(
                # Áp dụng màu Xanh Lá Cây ĐẬM
                text=f"Đã tìm thấy Video: {found_file}.\nĐường dẫn lưu Video: {file_path}", 
                text_color=COLOR_GREEN_SUCCESS, 
                font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_SUCCESS, weight="bold")
            )
            open_file_or_dir(file_path)
        
    else:
        # Trường hợp không tìm thấy file
        app_instance.result_label.configure(
            text=f"[LỖI] Không tìm thấy video nào bắt đầu bằng mã đơn hàng '{order_id}'.\nKiểm tra lại Mã Đơn Hàng.", 
            text_color=COLOR_RED_EXIT,
            font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_NORMAL, weight="normal")
        )
        
    # Luôn hiển thị danh sách file sau khi tra cứu
    display_file_list(app_instance, create_buttons_func)

# ----------------------------------------------------
# C. HÀM HIỂN THỊ DANH SÁCH FILE (MỚI)
# ----------------------------------------------------

def display_file_list(app_instance, create_buttons_func):
    """
    Lấy danh sách file đang tồn tại, sắp xếp theo thời gian sửa đổi, 
    và truyền cho hàm tạo nút trong GUI.
    """
    try:
        # Lấy danh sách tất cả các file .avi đang tồn tại
        files = []
        for f in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, f)
            
            # Lọc: chỉ giữ file VÀ phải tồn tại và là video
            if os.path.isfile(file_path) and f.lower().endswith((".avi", ".mp4", ".mov", ".mkv")):
                files.append((f, os.path.getmtime(file_path)))
        
        # Sắp xếp giảm dần theo thời gian (mới nhất lên đầu)
        files.sort(key=lambda x: x[1], reverse=True)
        
        file_list = [f[0] for f in files]
        
        # KHÔNG GIỚI HẠN SỐ LƯỢNG FILE NỮA (Sử dụng Scrollbar của Frame)
        display_files = file_list 

        # GỌI HÀM TẠO NÚT TỪ GUI
        create_buttons_func(app_instance, display_files)

    except Exception as e:
        # Xử lý lỗi nếu không thể đọc thư mục
        if hasattr(app_instance, 'list_container_frame'):
            error_message = f"[LỖI HỆ THỐNG] Không thể đọc thư mục: {e}"
            # Xóa các widget cũ
            for widget in app_instance.list_container_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(app_instance.list_container_frame, text=error_message, 
                         text_color=COLOR_RED_EXIT).pack(padx=10, pady=10)
        else:
            print(f"Lỗi khi hiển thị danh sách file: {e}")

def delete_video(app_instance, file_name, create_buttons_func):
    """Xóa file video khỏi thư mục và cập nhật danh sách."""
    
    file_path = os.path.join(OUTPUT_DIR, file_name)
    
    # BƯỚC 1: Xóa file
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            
            # Cập nhật thông báo
            app_instance.result_label.configure(
                text=f"[THÀNH CÔNG] Đã xóa video: {file_name}.", 
                text_color=COLOR_RED_EXIT, # Dùng màu đỏ cho hành động xóa
                font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_SUCCESS, weight="bold")
            )
            print(f"Đã xóa file: {file_path}")
        else:
            # File không tồn tại nhưng vẫn nằm trong danh sách tạm thời (nếu có lỗi trước đó)
            app_instance.result_label.configure(
                text=f"[CẢNH BÁO] Không tìm thấy file: {file_name} để xóa.", 
                text_color=COLOR_ORANGE_ACCENT,
                font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_NORMAL)
            )
    except Exception as e:
        app_instance.result_label.configure(
            text=f"[LỖI HỆ THỐNG] Không thể xóa file {file_name}: {e}", 
            text_color=COLOR_RED_EXIT,
            font=ctk.CTkFont(family=FONT_FAMILY_SYSTEM, size=FONT_SIZE_SUCCESS, weight="bold")
        )
        print(f"Lỗi khi xóa file: {e}")

    display_file_list(app_instance, create_buttons_func)


def get_video_metadata(file_name):
    """
    Đọc file metadata (.json) tương ứng để lấy thông tin chi tiết về video
    và chuyển đổi định dạng thời gian sang chuỗi hiển thị.
    """
    
    # 1. Xác định đường dẫn file metadata
    # Lấy tên file không có đuôi (Ví dụ: SPXVN05353157345C)
    base_name = os.path.splitext(file_name)[0]
    metadata_file_path = os.path.join(METADATA_DIR, f"{base_name}.json")
    
    # Dữ liệu mặc định nếu không tìm thấy file
    default_data = {
        "start_time": "N/A",
        "end_time": "N/A",
        "duration": "00:00:00"
    }

    if not os.path.exists(metadata_file_path):
        return default_data

    try:
        # 2. Đọc file JSON
        with open(metadata_file_path, 'r') as f:
            metadata = json.load(f)

        # 3. Chuyển đổi thời gian từ chuỗi ISO sang đối tượng datetime
        start_time_iso = metadata.get("start_time")
        end_time_iso = metadata.get("end_time")
        duration_sec = metadata.get("duration_seconds", 0)
        
        # Kiểm tra dữ liệu thời gian có hợp lệ không
        # if not start_time_iso or not end_time_iso:
        #      return default_data
        if not start_time_iso or not end_time_iso:
             return default_data

        # Thay thế bằng datetime.fromisoformat an toàn hơn
        # Cần xử lý lỗi nếu chuỗi không đúng format ISO 8601
        try:
             start_dt = datetime.fromisoformat(start_time_iso)
             end_dt = datetime.fromisoformat(end_time_iso)
        except ValueError:
             print(f"[LỖI FORMAT] Chuỗi thời gian không phải ISO 8601: {start_time_iso} hoặc {end_time_iso}")
             return default_data

        start_dt = datetime.fromisoformat(start_time_iso)
        end_dt = datetime.fromisoformat(end_time_iso)
        
        # 4. Định dạng lại chuỗi thời gian cho giao diện (HH:MM:SS dd/mm/YYYY)
        start_formatted = start_dt.strftime("%H:%M:%S %d/%m/%Y")
        end_formatted = end_dt.strftime("%H:%M:%S %d/%m/%Y")
        
        # 5. Định dạng Thời lượng (chuyển giây sang HH:MM:SS)
        # Sử dụng timedelta để chuyển tổng số giây sang định dạng giờ:phút:giây
        duration_delta = timedelta(seconds=round(duration_sec))
        
        # Loại bỏ phần thập phân/miligiây nếu có
        duration_formatted = str(duration_delta).split('.')[0] 
        
        # Đảm bảo định dạng HH:MM:SS (nếu < 1 giờ, timedelta có thể trả về '0:00:50')
        parts = duration_formatted.split(':')
        if len(parts) == 1: # Chỉ có giây
            duration_formatted = f"00:00:{parts[0]}"
        elif len(parts) == 2: # Phút:Giây
            duration_formatted = f"00:{parts[0]}:{parts[1]}"

        return {
            "start_time": start_formatted,
            "end_time": end_formatted,
            "duration": duration_formatted
        }

    except Exception as e:
        print(f"[LỖI] Không thể đọc/xử lý metadata từ file JSON: {metadata_file_path}. Lỗi: {e}")
        return default_data
