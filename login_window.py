# login_window.py
# Giao diện đăng nhập với CustomTkinter

import customtkinter as ctk
from . import auth
from . import utils
import threading
import sys
import os
from PIL import Image, ImageTk

class LoginWindow(ctk.CTk):
    """Cửa sổ đăng nhập"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Đăng Nhập - Packing System")
        
        # Lấy kích thước màn hình
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Đặt kích thước cửa sổ (có thể fullscreen)
        window_width = min(600, screen_width)
        window_height = min(700, screen_height)
        
        # Tính toán vị trí để căn giữa
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.configure(fg_color=utils.COLOR_BACKGROUND)
        
        # Cho phép resize và maximize
        self.resizable(True, True)
        
        # Bind event để xử lý resize
        self.bind('<Configure>', self.on_window_resize)
        
        # Auth manager
        self.auth_manager = auth.AuthManager()
        
        # Biến trạng thái
        self.login_success = False
        self.user_data = None
        self.needs_activation = False  # Flag để biết có cần nhập key không
        self.pending_email = None  # Lưu email/password khi cần activation
        self.pending_password = None
        
        # Tạo giao diện
        self.create_widgets()
        
        # Kiểm tra session cũ
        self.check_existing_session()
    
    def create_widgets(self):
        """Tạo các widget cho giao diện đăng nhập"""
        
        # Main container với padding responsive - Sử dụng grid
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header - Sử dụng pack với logo
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(pady=(20, 30), fill="x")
        
        # Logo container
        logo_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_container.pack(pady=(0, 15))
        
        # Load logo nếu có
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "images", "logo.png")
        if os.path.exists(logo_path):
            try:
                logo_image = Image.open(logo_path)
                # Resize logo để vừa mắt (max width 200px, giữ tỷ lệ)
                logo_image.thumbnail((200, 200), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image)
                
                logo_label = ctk.CTkLabel(
                    logo_container,
                    image=logo_photo,
                    text=""
                )
                logo_label.image = logo_photo  # Giữ reference để không bị garbage collected
                logo_label.pack()
            except Exception as e:
                print(f"Lỗi load logo: {e}")
                # Fallback về text logo
                title_label = ctk.CTkLabel(
                    logo_container,
                    text="📦 PACKING SYSTEM",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color=utils.COLOR_ORANGE_ACCENT
                )
                title_label.pack()
        else:
            # Fallback về text logo nếu không có file
            title_label = ctk.CTkLabel(
                logo_container,
                text="📦 PACKING SYSTEM",
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color=utils.COLOR_ORANGE_ACCENT
            )
            title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Đăng nhập để sử dụng ứng dụng",
            font=ctk.CTkFont(size=16),
            text_color=utils.COLOR_GRAY_ACCENT
        )
        subtitle_label.pack(pady=(10, 0))
        
        # Form Frame - Responsive - Sử dụng pack
        form_frame = ctk.CTkFrame(self.main_container, fg_color="white", corner_radius=15)
        form_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Form content container - Sử dụng pack
        form_content = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_content.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Email/Phone input - Sử dụng pack (nhỏ hơn)
        email_label = ctk.CTkLabel(
            form_content,
            text="Email hoặc Số điện thoại:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        email_label.pack(pady=(0, 6), padx=10, fill="x")
        
        self.email_entry = ctk.CTkEntry(
            form_content,
            placeholder_text="Nhập email hoặc số điện thoại",
            height=38,
            font=ctk.CTkFont(size=14),
            corner_radius=8
        )
        self.email_entry.pack(pady=(0, 15), padx=10, fill="x")
        
        # Password input
        password_label = ctk.CTkLabel(
            form_content,
            text="Mật khẩu:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        password_label.pack(pady=(0, 6), padx=10, fill="x")
        
        self.password_entry = ctk.CTkEntry(
            form_content,
            placeholder_text="Nhập mật khẩu",
            height=38,
            show="*",
            font=ctk.CTkFont(size=14),
            corner_radius=8
        )
        self.password_entry.pack(pady=(0, 15), padx=10, fill="x")
        
        # Key input (ẩn mặc định, chỉ hiện khi cần activation)
        self.key_label = ctk.CTkLabel(
            form_content,
            text="Key kích hoạt:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        # Không pack ngay, sẽ pack khi cần
        
        self.key_entry = ctk.CTkEntry(
            form_content,
            placeholder_text="Nhập key để kích hoạt tài khoản",
            height=38,
            font=ctk.CTkFont(size=14),
            corner_radius=8
        )
        # Không pack ngay, sẽ pack khi cần
        
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
        
        # Login/Activate button
        self.login_button = ctk.CTkButton(
            form_content,
            text="ĐĂNG NHẬP",
            command=self.handle_login,
            height=50,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=utils.COLOR_BLUE_ACTION,
            hover_color=utils.COLOR_ORANGE_ACCENT,
            corner_radius=10
        )
        self.login_button.pack(padx=10, pady=(0, 20), fill="x")
        
        # Footer - Sử dụng pack
        footer_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        footer_frame.pack(pady=(0, 20), fill="x")
        
        help_label = ctk.CTkLabel(
            footer_frame,
            text="💬 Liên hệ admin nếu quên mật khẩu hoặc key | Nhấn F11 để fullscreen",
            font=ctk.CTkFont(size=11),
            text_color=utils.COLOR_GRAY_ACCENT
        )
        help_label.pack(pady=(5, 0))
        
        # Bind Enter key
        self.email_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.handle_login() if not self.needs_activation else self.handle_activate())
        self.key_entry.bind("<Return>", lambda e: self.handle_activate())
        
        # Bind F11 để toggle fullscreen
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        
        # Focus vào email entry khi mở
        self.after(100, lambda: self.email_entry.focus())
    
    def on_window_resize(self, event=None):
        """Xử lý khi cửa sổ được resize"""
        # Có thể thêm logic responsive ở đây nếu cần
        pass
    
    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        current_state = self.attributes("-fullscreen")
        self.attributes("-fullscreen", not current_state)
    
    def check_existing_session(self):
        """Kiểm tra session cũ và tự động điền thông tin"""
        session = self.auth_manager.get_session_info()
        if session and session.get('email_or_phone'):
            self.email_entry.insert(0, session.get('email_or_phone', ''))
            self.status_label.configure(
                text="Đã tìm thấy session cũ. Vui lòng nhập mật khẩu và đăng nhập lại.",
                text_color=utils.COLOR_BLUE_ACTION
            )
    
    def update_status(self, message, color=None):
        """Cập nhật thông báo trạng thái"""
        if color is None:
            color = utils.COLOR_GRAY_ACCENT
        self.status_label.configure(text=message, text_color=color)
    
    def set_loading(self, loading=True):
        """Thiết lập trạng thái loading"""
        if loading:
            self.login_button.configure(state="disabled", text="Đang xử lý...")
        else:
            self.login_button.configure(state="normal", text="ĐĂNG NHẬP")
    
    def handle_login(self):
        """Xử lý đăng nhập"""
        email_or_phone = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        
        # Validation
        if not email_or_phone:
            self.update_status("Vui lòng nhập email hoặc số điện thoại", utils.COLOR_RED_EXIT)
            return
        
        if not password:
            self.update_status("Vui lòng nhập mật khẩu", utils.COLOR_RED_EXIT)
            return
        
        # Disable button
        self.set_loading(True)
        self.update_status("Đang đăng nhập...", utils.COLOR_BLUE_ACTION)
        
        # Chạy đăng nhập trong thread riêng để không block UI
        thread = threading.Thread(target=self.login_thread, args=(email_or_phone, password), daemon=True)
        thread.start()
    
    def login_thread(self, email_or_phone, password):
        """Thread xử lý đăng nhập - REAL-TIME CHECK từ database"""
        try:
            # Clear session cũ trước khi login để đảm bảo check real-time
            print(f"🔍 Đang đăng nhập với real-time check từ database...")
            self.auth_manager.clear_session()
            
            # Đăng nhập với email/phone và password - API sẽ check is_suspended và is_activated real-time
            success, message, data = self.auth_manager.login(email_or_phone, password)
            
            if not success:
                # Kiểm tra nếu lỗi do chưa có key hoặc key chưa được kích hoạt
                if ("chưa có key" in message.lower() or 
                    "key chưa được kích hoạt" in message.lower() or 
                    "chưa được kích hoạt" in message.lower() or
                    "nhập key" in message.lower()):
                    # Cần nhập key để kích hoạt key lần đầu
                    self.needs_activation = True
                    self.pending_email = email_or_phone
                    self.pending_password = password
                    self.after(0, lambda: self.show_activation_form(message))
                elif "đình chỉ" in message.lower() or "suspended" in message.lower():
                    self.after(0, lambda: self.update_status(message, utils.COLOR_RED_EXIT))
                else:
                    self.after(0, lambda: self.update_status(message, utils.COLOR_RED_EXIT))
                self.after(0, lambda: self.set_loading(False))
                return
            
            # Đăng nhập thành công - API đã check real-time và user không bị suspended, đã được kích hoạt
            is_admin = data.get('is_admin', False) if data else False
            
            self.login_success = True
            self.user_data = {
                'email_or_phone': email_or_phone,
                'is_admin': is_admin,
                'user_id': data.get('user_id'),
                'session_data': data
            }
            
            print(f"✅ Đăng nhập thành công (real-time check passed)")
            self.after(0, lambda: self.update_status("Đăng nhập thành công! Đang kiểm tra license...", utils.COLOR_GREEN_SUCCESS))
            self.after(0, lambda: self.after(500, self.destroy))
            
        except Exception as e:
            print(f"❌ Lỗi đăng nhập: {e}")
            self.after(0, lambda: self.update_status(f"Lỗi: {str(e)}", utils.COLOR_RED_EXIT))
            self.after(0, lambda: self.set_loading(False))
    
    def show_activation_form(self, message):
        """Hiển thị form nhập key để kích hoạt key (lần đầu sử dụng app)"""
        # Hiển thị thông báo
        self.update_status(message + " Vui lòng nhập key để kích hoạt key lần đầu.", utils.COLOR_ORANGE_ACCENT)
        
        # Hiển thị key input
        self.key_label.pack(pady=(0, 6), padx=10, fill="x", before=self.status_label)
        self.key_entry.pack(pady=(0, 15), padx=10, fill="x", before=self.status_label)
        
        # Đổi text button thành "KÍCH HOẠT"
        self.login_button.configure(text="KÍCH HOẠT", command=self.handle_activate)
        
        # Disable email và password fields
        self.email_entry.configure(state="disabled")
        self.password_entry.configure(state="disabled")
        
        # Focus vào key entry
        self.after(100, lambda: self.key_entry.focus())
    
    def handle_activate(self):
        """Xử lý kích hoạt key để sử dụng app (lần đầu)"""
        if not self.needs_activation or not self.pending_email or not self.pending_password:
            self.update_status("Lỗi: Không có thông tin để kích hoạt key", utils.COLOR_RED_EXIT)
            return
        
        key = self.key_entry.get().strip()
        
        if not key:
            self.update_status("Vui lòng nhập key để kích hoạt", utils.COLOR_RED_EXIT)
            return
        
        # Disable button
        self.set_loading(True)
        self.update_status("Đang kích hoạt key...", utils.COLOR_BLUE_ACTION)
        
        # Chạy activation trong thread riêng
        thread = threading.Thread(
            target=self.activate_thread, 
            args=(self.pending_email, self.pending_password, key), 
            daemon=True
        )
        thread.start()
    
    def activate_thread(self, email_or_phone, password, key):
        """Thread xử lý kích hoạt key (lần đầu sử dụng app)"""
        try:
            print(f"🔑 Đang kích hoạt key để sử dụng app...")
            
            # Gọi API activate
            success, message, data = self.auth_manager.activate_account(email_or_phone, password, key)
            
            if not success:
                self.after(0, lambda: self.update_status(message, utils.COLOR_RED_EXIT))
                self.after(0, lambda: self.set_loading(False))
                return
            
            # Kích hoạt thành công
            is_admin = data.get('is_admin', False) if data else False
            
            self.login_success = True
            self.user_data = {
                'email_or_phone': email_or_phone,
                'is_admin': is_admin,
                'user_id': data.get('user_id'),
                'session_data': data,
                'activated': True
            }
            
            print(f"✅ Kích hoạt tài khoản thành công!")
            self.after(0, lambda: self.update_status("Kích hoạt thành công! Đang kiểm tra license...", utils.COLOR_GREEN_SUCCESS))
            self.after(0, lambda: self.after(500, self.destroy))
            
        except Exception as e:
            print(f"❌ Lỗi kích hoạt: {e}")
            self.after(0, lambda: self.update_status(f"Lỗi: {str(e)}", utils.COLOR_RED_EXIT))
            self.after(0, lambda: self.set_loading(False))
    
    def run(self):
        """Chạy cửa sổ đăng nhập và trả về kết quả"""
        self.mainloop()
        return self.login_success, self.user_data

