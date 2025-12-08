# main_app.py

# -*- coding: utf-8 -*-
import customtkinter as ctk
import threading
import sys
import queue
# Import các module đã chia nhỏ
from . import utils
from . import gui_widgets
from . import camera_logic
from . import login_window
from . import activate_window
from . import auth

class PackingApp(ctk.CTk):
    def __init__(self, user_data=None):
        super().__init__()
        self.title("Packing System - Exon Technology")
        # self.geometry("1000x750")
        self.resizable(True, True)
        self.configure(fg_color=utils.COLOR_BACKGROUND)
        
        # Lưu thông tin user
        self.user_data = user_data
        self.auth_manager = auth.AuthManager()
        
        # Biến trạng thái
        self.is_running = True
        self.cameras = camera_logic.load_cameras_from_json(self) # Load camera data BEFORE creating UI
        self.camera_threads = []
        
        # Lock đồng bộ hóa
        self.lock = threading.Lock()
        
        # Queue for cleanup thread communication
        self.cleanup_queue = queue.Queue()

        # Thiết lập layout grid chính
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Khởi tạo các thành phần giao diện từ gui_widgets
        gui_widgets.create_widgets(self)
        
        # Schedule background tasks to start after the mainloop is running
        self.after(100, self.start_background_tasks)
        
        # Start the cleanup queue poller
        self.process_cleanup_queue()
        
        # Hiển thị thông tin user nếu có
        if self.user_data:
            self.show_user_info()
        
        # ✅ Tạo periodic check để tự động logout khi key hết hạn
        # Check mỗi 30 giây
        self.check_key_periodically()

    def start_background_tasks(self):
        """Start background threads after the GUI is fully initialized and running."""
        # Khởi động luồng camera từ camera_logic
        camera_logic.start_camera_threads(self)
        
        # Khoi dong luong don dep dinh ky
        camera_logic.start_cleanup_thread(self)

    def process_cleanup_queue(self):
        """Process messages from the cleanup queue to update the GUI safely."""
        try:
            while not self.cleanup_queue.empty():
                count, size_mb = self.cleanup_queue.get_nowait()
                camera_logic._update_cleanup_log(self, count, size_mb)
        except queue.Empty:
            pass
        finally:
            if self.is_running:
                self.after(1000, self.process_cleanup_queue) # Poll every second


    def show_user_info(self):
        """Hiển thị thông tin user đã đăng nhập"""
        if self.user_data:
            session = self.auth_manager.get_session_info()
            if session:
                key_status, status_msg = self.auth_manager.check_key_status()
                # Có thể thêm label hiển thị thông tin user ở header nếu cần
                print(f"Đã đăng nhập: {session.get('email_or_phone')}")
                print(f"Key status: {status_msg}")
    
    def check_key_periodically(self):
        """✅ Check key expiration định kỳ và tự động logout nếu hết hạn"""
        if not self.is_running:
            return
        
        try:
            # Gọi API /license-info để check key status
            license_success, license_data, license_error = self.auth_manager.get_license_info()
            
            if license_error == "KEY_EXPIRED":
                # Key hết hạn → tự động đăng xuất
                print(f"❌ KEY_EXPIRED detected - auto logout")
                self.auth_manager.clear_session()
                import tkinter.messagebox as messagebox
                try:
                    messagebox.showerror(
                        "Key đã hết hạn",
                        "Key đã hết hạn hoặc bị xóa. Vui lòng liên hệ admin để gia hạn.\n\nỨng dụng sẽ đóng."
                    )
                except:
                    pass
                self.on_closing()
                sys.exit(0)
                return
            elif license_success and license_data:
                status = license_data.get('status', 'expired')
                if status == 'expired' or status == 'suspended':
                    # Key hết hạn hoặc bị đình chỉ
                    print(f"❌ Key status: {status} - auto logout")
                    self.auth_manager.clear_session()
                    import tkinter.messagebox as messagebox
                    try:
                        messagebox.showerror(
                            "Key không hợp lệ",
                            f"Key đã {status == 'expired' and 'hết hạn' or 'bị đình chỉ'}. Vui lòng liên hệ admin để gia hạn.\n\nỨng dụng sẽ đóng."
                        )
                    except:
                        pass
                    self.on_closing()
                    sys.exit(0)
                    return
        except Exception as e:
            print(f"⚠️ Error in periodic key check: {e}")
        
        # Schedule next check (30 seconds)
        if self.is_running:
            self.after(30000, self.check_key_periodically)  # 30 seconds = 30000 ms
    
    # Sự kiện đóng cửa sổ
    def on_closing(self):
        """Xử lý sự kiện đóng cửa sổ."""
        self.is_running = False
        
        # Dừng tất cả các bản ghi đang hoạt động
        camera_logic._stop_all_recordings(self)
        
        # Chờ các luồng camera kết thúc
        for thread in self.camera_threads:
            if thread.is_alive():
                thread.join(timeout=1.0) # Cho mỗi luồng 1 giây để kết thúc
        
        # Dọn dẹp tài nguyên camera
        for camera in self.cameras:
            camera.release()

        self.destroy()

def check_license_status(auth_manager):
    """
    Kiểm tra trạng thái license (key expiration) từ database real-time
    KHÔNG cần nhập key lại - chỉ check expiration
    """
    session = auth_manager.get_session_info()
    if not session:
        return False, "Chưa đăng nhập"
    
    is_admin = session.get('is_admin', False)
    
    # Admin không cần license
    if is_admin:
        return True, "Admin - Không cần license"
    
    # Kiểm tra account đã được activate chưa (từ database real-time)
    # Nếu chưa activate, user sẽ không thể login vào app (đã được check ở login)
    # Nếu đã login thành công, nghĩa là đã activate rồi
    
    # Kiểm tra key expiration từ database (real-time check)
    # Sử dụng validate_user API để check key status và expiration
    try:
        is_valid, validation_message = auth_manager.validate_session_with_server()
        if not is_valid:
            # User bị suspended hoặc key hết hạn
            if "hết hạn" in validation_message.lower() or "expired" in validation_message.lower():
                return False, "Key đã hết hạn"
            elif "đình chỉ" in validation_message.lower() or "suspended" in validation_message.lower():
                return False, "Tài khoản hoặc key đã bị đình chỉ"
            else:
                return False, validation_message
        
        # Nếu validate thành công, check key expiration từ session hoặc database
        # Lấy key expiration từ session (đã được lưu sau khi activate)
        key_expires_at = session.get('key_expires_at')
        if key_expires_at:
            try:
                from datetime import datetime
                expires_date = datetime.fromisoformat(key_expires_at)
                now = datetime.now()
                
                if now > expires_date:
                    return False, "Key đã hết hạn"
            except Exception as e:
                print(f"⚠️ Lỗi parse key_expires_at: {e}")
        
        # Nếu không có trong session, check từ database qua validate_user
        # validate_user đã check rồi, nếu pass thì OK
        return True, "License hợp lệ"
        
    except Exception as e:
        print(f"❌ Lỗi kiểm tra license: {e}")
        # Nếu không thể check từ server, dùng session làm fallback
        key_expires_at = session.get('key_expires_at')
        if key_expires_at:
            try:
                from datetime import datetime
                expires_date = datetime.fromisoformat(key_expires_at)
                now = datetime.now()
                
                if now > expires_date:
                    return False, "Key đã hết hạn"
                return True, "License hợp lệ (offline check)"
            except:
                pass
        
        return False, f"Lỗi kiểm tra license: {str(e)}"

if __name__ == "__main__":
    import os
    # Force OpenCV to use TCP for RTSP, which is more reliable than UDP over many networks.
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    # Increase analyze duration and probe size to give FFMPEG more time to detect stream parameters.
    os.environ["OPENCV_FFMPEG_DECODE_OPTIONS"] = "analyzeduration;2000000|probesize;2000000"

    # Thiết lập giao diện màu sắc tổng thể
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    
    auth_manager = auth.AuthManager()
    
    # Kiểm tra xem đã đăng nhập chưa
    session = auth_manager.get_session_info()
    is_logged_in = session and session.get('email_or_phone')
    
    # Nếu có session, validate với server để đảm bảo user vẫn tồn tại và không bị suspended (REAL-TIME CHECK)
    if is_logged_in:
        # Không phải offline mode thì phải validate với server (check real-time từ database)
        if not auth_manager.session_data.get('offline_mode'):
            print("🔍 Đang kiểm tra session với server (real-time check)...")
            is_valid, validation_message = auth_manager.validate_session_with_server()
            if not is_valid:
                # Session không hợp lệ hoặc user bị suspended - xóa session và yêu cầu đăng nhập lại
                print(f"⚠️ Session không hợp lệ hoặc user bị đình chỉ: {validation_message}")
                auth_manager.clear_session()
                is_logged_in = False
            else:
                print(f"✅ Session hợp lệ: {validation_message}")
    
    if not is_logged_in:
        # Hiển thị cửa sổ đăng nhập
        login_win = login_window.LoginWindow()
        login_success, user_data = login_win.run()
        
        if not login_success or not user_data:
            # Đăng nhập thất bại, thoát ứng dụng
            sys.exit(0)
        
        # Reload session sau khi đăng nhập
        auth_manager.load_session()
    
    # Kiểm tra license status (key expiration) - REAL-TIME từ API /license-info
    # Key chỉ dùng 1 lần để activate account, sau đó chỉ check expiration
    license_valid, license_message = check_license_status(auth_manager)
    
    # Gọi API /license-info để lấy thông tin real-time và cập nhật session
    # ✅ [3] Session sẽ được update tự động trong get_license_info()
    try:
        license_success, license_data, license_error = auth_manager.get_license_info()
        if license_success and license_data:
            # Session đã được update trong get_license_info(), chỉ log để debug
            print(f"✅ License info received: expire_at={license_data.get('expire_at')}, days_left={license_data.get('days_left')}, status={license_data.get('status')}")
            
            if license_data.get('status') == 'expired':
                # Key hết hạn - force logout
                print(f"❌ Key đã hết hạn - forcing logout")
                auth_manager.clear_session()
                import tkinter.messagebox as messagebox
                messagebox.showerror(
                    "Key đã hết hạn",
                    "Key đã hết hạn – vui lòng liên hệ Admin để gia hạn.\n\nỨng dụng sẽ đóng."
                )
                sys.exit(0)
        elif license_error:
            print(f"⚠️ License info error: {license_error}")
    except Exception as e:
        print(f"⚠️ Error getting license info: {e}")
    
    if not license_valid:
        # Key hết hạn hoặc chưa activate - báo lỗi và thoát
        # KHÔNG hiển thị activate_window vì key đã được dùng để activate account rồi
        print(f"❌ License không hợp lệ: {license_message}")
        
        # Hiển thị thông báo lỗi cho user
        try:
            import tkinter.messagebox as messagebox
            error_msg = f"Không thể sử dụng ứng dụng:\n{license_message}\n\n"
            if "hết hạn" in license_message.lower():
                error_msg += "Vui lòng gia hạn key trên Web App để tiếp tục sử dụng."
            elif "chưa kích hoạt" in license_message.lower():
                error_msg += "Vui lòng sử dụng key để kích hoạt tài khoản lần đầu."
            else:
                error_msg += "Vui lòng liên hệ admin để được hỗ trợ."
            
            messagebox.showerror("Lỗi License", error_msg)
        except Exception as e:
            print(f"Error showing message box: {e}")
        
        # Thoát ứng dụng
        sys.exit(0)
        
        # Reload session sau khi kích hoạt thành công
        auth_manager.load_session()
    
    # Đăng nhập và license đều OK, mở app chính
    session = auth_manager.get_session_info()
    user_data = {
        'email_or_phone': session.get('email_or_phone'),
        'is_admin': session.get('is_admin', False),
        'user_id': session.get('user_id'),
        'key': session.get('key'),
        'key_data': {
            'phone': session.get('key_phone'),
            'expires_at': session.get('key_expires_at')
        } if session.get('key') else None
    }
    
    app = PackingApp(user_data=user_data)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()