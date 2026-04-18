import customtkinter as ctk
from database import create_user, login, login_guest
from PIL import Image
import os

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

def _make_logo_image(size=80):
    """Load and return a CTkImage of the logo, or None if unavailable."""
    try:
        img = Image.open(_LOGO_PATH)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None

class AuthScreen(ctk.CTkFrame):
    def __init__(self, master, on_success_callback):
        super().__init__(master)
        self.on_success = on_success_callback
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.login_frame = self.create_login_frame()
        self.signup_frame = self.create_signup_frame()
        
        self.show_login()
        
    def show_login(self):
        self.signup_frame.grid_remove()
        self.login_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        
    def show_signup(self):
        self.login_frame.grid_remove()
        self.signup_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        
    def create_login_frame(self):
        frame = ctk.CTkFrame(self)
        frame.grid_columnconfigure(0, weight=1)
        
        # Logo
        logo_img = _make_logo_image(72)
        if logo_img:
            logo_lbl = ctk.CTkLabel(frame, image=logo_img, text="")
            logo_lbl.grid(row=0, column=0, pady=(30, 4))
            title_row, slogan_row = 1, 2
        else:
            title_row, slogan_row = 0, 1

        title = ctk.CTkLabel(frame, text="Login to ReadSteed", font=ctk.CTkFont(size=26, weight="bold"))
        title.grid(row=title_row, column=0, pady=(0, 2))
        
        slogan = ctk.CTkLabel(frame, text="Read with Speed.", font=ctk.CTkFont(size=14, slant="italic"), text_color="gray60")
        slogan.grid(row=slogan_row, column=0, pady=(0, 20))
        
        self.login_email = ctk.CTkEntry(frame, placeholder_text="Email", width=250, height=35)
        self.login_email.grid(row=3, column=0, pady=(10, 5))
        
        self.login_password = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=250, height=35)
        self.login_password.grid(row=4, column=0, pady=5)
        
        self.login_error = ctk.CTkLabel(frame, text="", text_color="red")
        self.login_error.grid(row=5, column=0)
        
        login_btn = ctk.CTkButton(frame, text="Login", command=self.handle_login, width=250, height=35, font=ctk.CTkFont(weight="bold"))
        login_btn.grid(row=6, column=0, pady=(15, 5))
        
        switch_signup_btn = ctk.CTkButton(frame, text="Create Account", fg_color="transparent", 
                                          command=self.show_signup)
        switch_signup_btn.grid(row=7, column=0, pady=5)
        
        guest_btn = ctk.CTkButton(frame, text="Continue as Guest", fg_color="gray30", hover_color="gray20",
                                  command=self.handle_guest, width=250)
        guest_btn.grid(row=8, column=0, pady=(20, 20))
        
        credit = ctk.CTkLabel(frame, text="By Lev Khaimovich", font=ctk.CTkFont(size=10), text_color="gray50")
        credit.place(relx=0.02, rely=0.98, anchor="sw")
        
        return frame
        
    def create_signup_frame(self):
        frame = ctk.CTkFrame(self)
        frame.grid_columnconfigure(0, weight=1)
        
        # Logo
        logo_img = _make_logo_image(72)
        if logo_img:
            logo_lbl = ctk.CTkLabel(frame, image=logo_img, text="")
            logo_lbl.grid(row=0, column=0, pady=(30, 4))
            title_row2, slogan_row2 = 1, 2
        else:
            title_row2, slogan_row2 = 0, 1

        title = ctk.CTkLabel(frame, text="Create Account", font=ctk.CTkFont(size=26, weight="bold"))
        title.grid(row=title_row2, column=0, pady=(0, 2))
        
        slogan = ctk.CTkLabel(frame, text="Read with Speed.", font=ctk.CTkFont(size=14, slant="italic"), text_color="gray60")
        slogan.grid(row=slogan_row2, column=0, pady=(0, 20))
        
        self.signup_email = ctk.CTkEntry(frame, placeholder_text="Email", width=250, height=35)
        self.signup_email.grid(row=3, column=0, pady=(10, 5))
        
        self.signup_username = ctk.CTkEntry(frame, placeholder_text="Username", width=250, height=35)
        self.signup_username.grid(row=4, column=0, pady=5)
        
        self.signup_password = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=250, height=35)
        self.signup_password.grid(row=5, column=0, pady=5)
        
        self.signup_error = ctk.CTkLabel(frame, text="", text_color="red")
        self.signup_error.grid(row=6, column=0)
        
        signup_btn = ctk.CTkButton(frame, text="Sign Up", command=self.handle_signup, width=250, height=35, font=ctk.CTkFont(weight="bold"))
        signup_btn.grid(row=7, column=0, pady=(15, 5))
        
        switch_login_btn = ctk.CTkButton(frame, text="Back to Login", fg_color="transparent", 
                                         command=self.show_login)
        switch_login_btn.grid(row=8, column=0, pady=(5, 20))
        
        credit = ctk.CTkLabel(frame, text="By Lev Khaimovich", font=ctk.CTkFont(size=10), text_color="gray50")
        credit.place(relx=0.02, rely=0.98, anchor="sw")
        
        return frame
        
    def handle_login(self):
        email = self.login_email.get()
        pwd = self.login_password.get()
        
        if not email or not pwd:
            self.login_error.configure(text="Fill all fields", text_color="red")
            return
            
        success, msg = login(email, pwd)
        if success:
            self.on_success()
        else:
            self.login_error.configure(text=msg, text_color="red")

    def handle_signup(self):
        email = self.signup_email.get()
        uname = self.signup_username.get()
        pwd = self.signup_password.get()
        
        if not email or not uname or not pwd:
            self.signup_error.configure(text="Fill all fields", text_color="red")
            return
            
        if create_user(email, uname, pwd):
            self.show_login()
            self.cleanup_signup()
            self.login_email.delete(0, 'end')
            self.login_email.insert(0, email)
            self.login_error.configure(text="Account created! Please log in.", text_color="green")
        else:
            self.signup_error.configure(text="Email already exists", text_color="red")
            
    def handle_guest(self):
        login_guest()
        self.on_success()
        
    def cleanup_signup(self):
        self.signup_email.delete(0, 'end')
        self.signup_username.delete(0, 'end')
        self.signup_password.delete(0, 'end')
        self.signup_error.configure(text="")
