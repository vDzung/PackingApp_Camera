# activate_window.py
# Màn hình kích hoạt License

import customtkinter as ctk
from . import auth
from . import utils
import threading

class ActivateWindow(ctk.CTk):
    """Cửa sổ kích hoạt License"""
    
    def __init__(self, parent=None):
        super().__init__()
        
        self.title("Kích Hoạt License - Packing System")
        
        # Lấy kích thước màn hình
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Đặt kích thước cửa sổ
        window_width = min(500, screen_width)
        window_height = min(500, screen_height)
        
        # Tính toán vị trí để căn giữa
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.configure(fg_color=utils.COLOR_BACKGROUND)
        
        # Cho phép resize
        self.resizable(True, True)
        
        # Auth manager
        self.auth_manager = auth.AuthManager()
        
        # Biến trạng thái
        self.activation_success = False
        self.key_data = None
        self.is_closing = False  # Flag để kiểm tra window đang đóng
        self.pending_callbacks = []  # Lưu các callback IDs để cancel
        self.want_to_go_back = False  # Flag để biết user muốn quay lại đăng nhập
        
        # Parent window (nếu có)
        self.parent = parent
        
        # Tạo giao diện
        self.create_widgets()
        
        # Focus vào key entry
        callback_id = self.after(100, lambda: self.safe_focus_entry())
        self.pending_callbacks.append(callback_id)
    
    def create_widgets(self):
        """Tạo các widget cho giao diện kích hoạt"""
        
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(pady=(20, 30), fill="x")
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🔐 KÍCH HOẠT LICENSE",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=utils.COLOR_ORANGE_ACCENT
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Nhập key để kích hoạt license và sử dụng ứng dụng",
            font=ctk.CTkFont(size=14),
            text_color=utils.COLOR_GRAY_ACCENT
        )
        subtitle_label.pack(pady=(10, 0))
        
        # Form Frame
        form_frame = ctk.CTkFrame(self.main_container, fg_color="white", corner_radius=15)
        form_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Form content
        form_content = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Key input
        key_label = ctk.CTkLabel(
            form_content,
            text="Key License:",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        key_label.pack(pady=(0, 8), padx=10, fill="x")
        
        self.key_entry = ctk.CTkEntry(
            form_content,
            placeholder_text="Nhập key license (KEY_...)",
            height=50,
            font=ctk.CTkFont(size=16, family="Courier"),
            corner_radius=8
        )
        self.key_entry.pack(pady=(0, 25), padx=10, fill="x")
        
        # Status label
        self.status_label = ctk.CTkLabel(
            form_content,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=utils.COLOR_GRAY_ACCENT,
            wraplength=400,
            justify="left"
        )
        self.status_label.pack(pady=(0, 15), padx=10, fill="x")
        
        # Button container
        button_container = ctk.CTkFrame(form_content, fg_color="transparent")
        button_container.pack(padx=10, pady=(0, 20), fill="x")
        
        # Activate button
        self.activate_button = ctk.CTkButton(
            button_container,
            text="KÍCH HOẠT",
            command=self.handle_activate,
            height=50,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=utils.COLOR_GREEN_SUCCESS,
            hover_color="#45a049",
            corner_radius=10
        )
        self.activate_button.pack(pady=(0, 10), fill="x")
        
        # Back to login button
        self.back_button = ctk.CTkButton(
            button_container,
            text="← Quay lại đăng nhập",
            command=self.back_to_login,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=utils.COLOR_BLUE_ACTION,
            hover_color="#E3F2FD",
            corner_radius=8
        )
        self.back_button.pack(fill="x")
        
        # Info box
        info_box = ctk.CTkFrame(self.main_container, fg_color="#E3F2FD", corner_radius=8)
        info_box.pack(padx=20, pady=10, fill="x")
        
        info_label = ctk.CTkLabel(
            info_box,
            text="💡 Key license được cấp từ Web App. Liên hệ admin nếu cần hỗ trợ.",
            font=ctk.CTkFont(size=12),
            text_color="#1976D2",
            wraplength=400
        )
        info_label.pack(pady=10, padx=15)
        
        # Bind Enter key
        self.key_entry.bind("<Return>", lambda e: self.handle_activate())
        
        # Bind Escape để đóng (nếu cần)
        self.bind("<Escape>", lambda e: self.cancel_activation())
        
        # Bind window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def safe_focus_entry(self):
        """Focus vào entry một cách an toàn"""
        if not self.is_closing and hasattr(self, 'key_entry'):
            try:
                self.key_entry.focus()
            except:
                pass
    
    def update_status(self, message, color=None):
        """Cập nhật thông báo trạng thái"""
        if self.is_closing:
            return
        if color is None:
            color = utils.COLOR_GRAY_ACCENT
        try:
            self.status_label.configure(text=message, text_color=color)
        except:
            pass
    
    def set_loading(self, loading=True):
        """Thiết lập trạng thái loading"""
        if self.is_closing:
            return
        try:
            if loading:
                self.activate_button.configure(state="disabled", text="Đang xử lý...")
            else:
                self.activate_button.configure(state="normal", text="KÍCH HOẠT")
        except:
            pass
    
    def handle_activate(self):
        """Xử lý kích hoạt license"""
        key = self.key_entry.get().strip()
        
        # Validation
        if not key:
            self.update_status("Vui lòng nhập key license", utils.COLOR_RED_EXIT)
            return
        
        # Disable button
        self.set_loading(True)
        self.update_status("Đang xác thực key...", utils.COLOR_BLUE_ACTION)
        
        # Chạy activate trong thread riêng
        thread = threading.Thread(target=self.activate_thread, args=(key,), daemon=True)
        thread.start()
    
    def activate_thread(self, key):
        """Thread xử lý kích hoạt"""
        try:
            # Xác thực key
            key_success, key_message, key_data = self.auth_manager.verify_key(key)
            
            if not key_success:
                if not self.is_closing:
                    callback1 = self.after(0, lambda: self.update_status(key_message, utils.COLOR_RED_EXIT))
                    callback2 = self.after(0, lambda: self.set_loading(False))
                    self.pending_callbacks.extend([callback1, callback2])
                return
            
            # Kích hoạt thành công
            self.activation_success = True
            self.key_data = key_data
            
            if not self.is_closing:
                callback1 = self.after(0, lambda: self.update_status("Kích hoạt thành công! Đang mở ứng dụng...", utils.COLOR_GREEN_SUCCESS))
                callback2 = self.after(0, lambda: self.safe_destroy(1000))
                self.pending_callbacks.extend([callback1, callback2])
            
        except Exception as e:
            if not self.is_closing:
                callback1 = self.after(0, lambda: self.update_status(f"Lỗi: {str(e)}", utils.COLOR_RED_EXIT))
                callback2 = self.after(0, lambda: self.set_loading(False))
                self.pending_callbacks.extend([callback1, callback2])
    
    def cancel_all_callbacks(self):
        """Hủy tất cả pending callbacks"""
        for callback_id in self.pending_callbacks:
            try:
                self.after_cancel(callback_id)
            except:
                pass
        self.pending_callbacks.clear()
    
    def safe_destroy(self, delay=0):
        """Đóng cửa sổ một cách an toàn"""
        if self.is_closing:
            return
        
        def do_destroy():
            if not self.is_closing:
                self.is_closing = True
                self.cancel_all_callbacks()
                try:
                    self.destroy()
                except:
                    pass
        
        if delay > 0:
            callback_id = self.after(delay, do_destroy)
            self.pending_callbacks.append(callback_id)
        else:
            do_destroy()
    
    def cancel_activation(self):
        """Hủy kích hoạt và đóng cửa sổ"""
        self.activation_success = False
        self.safe_destroy()
    
    def on_closing(self):
        """Xử lý khi đóng cửa sổ"""
        self.activation_success = False
        self.safe_destroy()
    
    def back_to_login(self):
        """Quay lại màn hình đăng nhập"""
        # Đánh dấu là user muốn quay lại đăng nhập (không phải lỗi)
        self.want_to_go_back = True
        
        # Xóa session hiện tại để đăng nhập lại
        try:
            from . import auth
            auth_manager = auth.AuthManager()
            auth_manager.clear_session()
        except Exception as e:
            print(f"Lỗi khi xóa session: {e}")
        
        # Đóng cửa sổ kích hoạt
        self.activation_success = False
        self.safe_destroy()
    
    def run(self):
        """Chạy cửa sổ kích hoạt và trả về kết quả"""
        try:
            self.mainloop()
        except Exception as e:
            print(f"Error in activate window mainloop: {e}")
        finally:
            # Đảm bảo cleanup
            self.cancel_all_callbacks()
        return self.activation_success, self.key_data, getattr(self, 'want_to_go_back', False)

