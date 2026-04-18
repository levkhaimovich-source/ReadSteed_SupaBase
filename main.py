import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from PIL import Image
import os
from rsvp_engine import tokenize_text, process_word_for_display, get_delay_multiplier
from database import init_db, current_user, logout, save_reading, get_readings, get_reading_content, delete_reading
from auth_screen import AuthScreen
from promo_screen import PromoScreen

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

def _make_logo_image(size=28):
    """Load logo as a CTkImage, or None if unavailable."""
    try:
        img = Image.open(_LOGO_PATH)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None

FOCUS_MAP = {"Red": "#e74c3c", "Blue": "#3498db", "Green": "#2ecc71", "Yellow": "#f1c40f"}
BG_MAP = {"Black": "#242424", "White": "#EBEBEB", "Pure Black": "black", "Pure White": "white", "Gray": "gray40"}
TX_MAP = {"White": "white", "Black": "black", "Cyan": "cyan", "Yellow": "yellow", "Light Gray": "gray70"}

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, current_settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.geometry("400x450")
        self.minsize(400, 450)
        self.focus_force()
        self.grab_set()
        
        self.on_save = on_save
        self.settings = current_settings.copy()
        
        # UI
        ctk.CTkLabel(self, text="Customization", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Font
        font_frame = ctk.CTkFrame(self, fg_color="transparent")
        font_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(font_frame, text="Font Family:").pack(side="left")
        self.font_menu = ctk.CTkOptionMenu(font_frame, values=["Consolas", "Arial", "Courier New", "Helvetica"])
        self.font_menu.set(self.settings.get("font", "Consolas"))
        self.font_menu.pack(side="right")
        
        # Focus Color
        focus_col_frame = ctk.CTkFrame(self, fg_color="transparent")
        focus_col_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(focus_col_frame, text="Focus Highlight Color:").pack(side="left")
        self.focus_menu = ctk.CTkOptionMenu(focus_col_frame, values=list(FOCUS_MAP.keys()), width=100)
        self.focus_menu.set(self.settings.get("focus_color", "Red"))
        self.focus_menu.pack(side="right")
        
        # Canvas Bg
        bg_col_frame = ctk.CTkFrame(self, fg_color="transparent")
        bg_col_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(bg_col_frame, text="Canvas Background:").pack(side="left")
        self.bg_menu = ctk.CTkOptionMenu(bg_col_frame, values=list(BG_MAP.keys()), width=100)
        self.bg_menu.set(self.settings.get("canvas_bg", "Black"))
        self.bg_menu.pack(side="right")
        
        # Text Color
        tx_col_frame = ctk.CTkFrame(self, fg_color="transparent")
        tx_col_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(tx_col_frame, text="Text Color:").pack(side="left")
        self.tx_menu = ctk.CTkOptionMenu(tx_col_frame, values=list(TX_MAP.keys()), width=100)
        self.tx_menu.set(self.settings.get("text_color", "White" if ctk.get_appearance_mode() == "Dark" else "Black"))
        self.tx_menu.pack(side="right")

        # Save Button
        ctk.CTkButton(self, text="Save Settings", command=self.save_and_close).pack(pady=40)

    def save_and_close(self):
        self.settings["font"] = self.font_menu.get()
        self.settings["focus_color"] = self.focus_menu.get()
        self.settings["canvas_bg"] = self.bg_menu.get()
        self.settings["text_color"] = self.tx_menu.get()
        self.on_save(self.settings)
        self.destroy()

class MainAppFrame(ctk.CTkFrame):
    def __init__(self, master, on_logout):
        super().__init__(master, fg_color="transparent")
        self.master_app = master
        self.on_logout = on_logout
        
        # State variables
        self.words = []
        self.current_idx = 0
        self.is_playing = False
        self.wpm = 300
        self._scheduled_task = None
        self.current_reading_id = None
        
        # Display settings — store human-readable labels internally
        self.display_settings = {
            "font": "Consolas",
            "focus_color": "Red",
            "canvas_bg": "Black",
            "text_color": "White"
        }
        # Resolved actual color values
        self._actual_bg = BG_MAP[self.display_settings["canvas_bg"]]
        
        self.setup_ui()
        self.load_sidebar_readings()
        
    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Content
        
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        
        sidebar_title_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        sidebar_title_frame.pack(fill="x", padx=10, pady=10)
        self.sb_title = ctk.CTkLabel(sidebar_title_frame, text="Your Readings", font=ctk.CTkFont(weight="bold"))
        self.sb_title.pack(side="left")
        self.sb_new_btn = ctk.CTkButton(sidebar_title_frame, text="+ New", width=40, command=self.new_reading)
        self.sb_new_btn.pack(side="right")
        
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.sidebar_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- Main Content ---
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew")
        
        self.main_content.grid_rowconfigure(0, weight=0) # Top bar
        self.main_content.grid_rowconfigure(1, weight=1) # Input area
        self.main_content.grid_rowconfigure(2, weight=0) # Control bar
        self.main_content.grid_rowconfigure(3, weight=0) # Progress bar
        self.main_content.grid_rowconfigure(4, weight=1) # RSVP display area
        self.main_content.grid_columnconfigure(0, weight=1)
        
        # 0. Top Bar
        self.top_bar = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.top_bar.grid_columnconfigure(4, weight=1)
        
        self.sidebar_toggle_btn = ctk.CTkButton(self.top_bar, text="☰", width=40, height=35, command=self.toggle_sidebar)
        self.sidebar_toggle_btn.grid(row=0, column=0, sticky="w", padx=(0, 15))
        
        # Logo + Slogan
        logo_img = _make_logo_image(30)
        if logo_img:
            self.logo_label = ctk.CTkLabel(self.top_bar, image=logo_img, text="")
            self.logo_label.grid(row=0, column=1, sticky="w", padx=(0, 6))
            self.slogan_label = ctk.CTkLabel(self.top_bar, text="ReadSteed | Read with Speed.", font=ctk.CTkFont(size=14, weight="bold", slant="italic"), text_color="#3498db")
            self.slogan_label.grid(row=0, column=2, sticky="w", padx=(0, 20))
        else:
            self.logo_label = None
            self.slogan_label = ctk.CTkLabel(self.top_bar, text="ReadSteed | Read with Speed.", font=ctk.CTkFont(size=14, weight="bold", slant="italic"), text_color="#3498db")
            self.slogan_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        user_info = current_user["username"]
        if current_user["is_premium"]:
            user_info += " ⭐"
            
        self.user_label = ctk.CTkLabel(self.top_bar, text=f"Hi, {user_info}", font=ctk.CTkFont(weight="bold"))
        self.user_label.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        self.appearance_mode_menu = ctk.CTkOptionMenu(self.top_bar, values=["Dark", "Light"], command=self.change_appearance_mode, width=100)
        self.appearance_mode_menu.grid(row=0, column=4, sticky="e", padx=(0, 10))
        self.appearance_mode_menu.set("Dark")
        
        # Top right buttons
        top_btn_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        top_btn_frame.grid(row=0, column=5, sticky="e")
        
        self.settings_btn = ctk.CTkButton(top_btn_frame, text="⚙ Settings", command=self.open_settings, width=100, fg_color="gray30")
        self.settings_btn.pack(side="left", padx=5)
        
        self.logout_btn = ctk.CTkButton(top_btn_frame, text="Logout", command=self.on_logout, width=80, fg_color="gray40", hover_color="gray30")
        self.logout_btn.pack(side="left", padx=5)
        
        self.toggle_input_btn = ctk.CTkButton(top_btn_frame, text="Focus Mode", command=self.toggle_focus_mode, width=100)
        self.toggle_input_btn.pack(side="left", padx=5)
        
        # 1. Input Area
        self.input_text = ctk.CTkTextbox(self.main_content, font=ctk.CTkFont(size=14))
        self.input_text.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="nsew")
        
        default_text = "Welcome to ReadSteed!\n\nPaste your text here to begin reading. \nLog in and open the sidebar to track multiple readings at once!"
        self.input_text.insert("0.0", default_text)
        
        # 2. Control Panels
        self.control_frame = ctk.CTkFrame(self.main_content)
        self.control_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=1)
        self.control_frame.grid_columnconfigure(2, weight=1)
        
        buttons_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        buttons_frame.grid(row=0, column=0, pady=10, padx=10, sticky="w")
        
        self.play_btn = ctk.CTkButton(buttons_frame, text="Play", command=self.master_app.handle_play_request, width=80)
        self.play_btn.pack(side="left", padx=5)
        
        self.reset_btn = ctk.CTkButton(buttons_frame, text="Reset", command=self.reset_reader, width=80, fg_color="gray30", hover_color="gray20")
        self.reset_btn.pack(side="left", padx=5)
        
        wpm_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        wpm_frame.grid(row=0, column=1, pady=10, padx=10)
        self.wpm_label = ctk.CTkLabel(wpm_frame, text=f"Speed: {self.wpm} WPM")
        self.wpm_label.pack(side="top")
        self.wpm_slider = ctk.CTkSlider(wpm_frame, from_=100, to=1000, number_of_steps=180, command=self.update_wpm)
        self.wpm_slider.set(self.wpm)
        self.wpm_slider.pack(side="bottom", fill="x")
        
        self.progress_label = ctk.CTkLabel(self.control_frame, text="0 / 0")
        self.progress_label.grid(row=0, column=2, pady=10, padx=20, sticky="e")
        
        # 3. Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_content)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)
        
        # 4. RSVP Display Area
        self.display_frame = ctk.CTkFrame(self.main_content, fg_color=self._actual_bg, corner_radius=10)
        self.display_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.display_frame.pack_propagate(False)
        
        self.canvas = tk.Canvas(self.display_frame, bg=self._actual_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=20, pady=20)
        self.canvas.bind("<Configure>", lambda e: self.draw_placeholder())
        
        self.credit_label = ctk.CTkLabel(self.main_content, text="By Lev Khaimovich", text_color="gray50", font=ctk.CTkFont(size=10, weight="bold"))
        self.credit_label.place(relx=0.01, rely=0.99, anchor="sw")
        
        self.sidebar_is_open = False
        self.focus_mode_active = False

    def toggle_sidebar(self):
        if self.sidebar_is_open:
            self.sidebar_frame.grid_remove()
            self.sidebar_is_open = False
        else:
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
            self.load_sidebar_readings()
            self.sidebar_is_open = True

    def open_settings(self):
        SettingsWindow(self, self.display_settings, self.apply_settings)
        
    def apply_settings(self, new_settings):
        self.display_settings = new_settings
        self._actual_bg = BG_MAP.get(self.display_settings["canvas_bg"], "#242424")
        self.display_frame.configure(fg_color=self._actual_bg)
        self.canvas.configure(bg=self._actual_bg)
        self._redraw_current_canvas()

    def new_reading(self):
        self.pause_reader()
        # Guarantee saving completes for current text first
        if self.current_reading_id or len(self.words) > 0:
            self.auto_save()
            
        self.current_reading_id = None
        self.input_text.delete("0.0", "end")
        self.current_idx = 0
        self.words = []
        self.update_progress()
        self.draw_placeholder()

    def load_sidebar_readings(self):
        for widget in self.sidebar_scroll.winfo_children():
            widget.destroy()
            
        if current_user["is_guest"]:
            ctk.CTkLabel(self.sidebar_scroll, text="Log in to save readings.", text_color="gray50").pack(pady=20)
            return

        readings = get_readings(current_user["user_id"])
        
        current_date_headers = set()
        
        for reading in readings:
            r_id = reading["id"]
            r_title = reading["title"]
            r_date = reading["date"].split(" ")[0] if reading["date"] else "Unknown Date"
            
            if r_date not in current_date_headers:
                ctk.CTkLabel(self.sidebar_scroll, text=r_date, font=ctk.CTkFont(weight="bold", size=12), text_color="gray60").pack(anchor="w", pady=(10, 2))
                current_date_headers.add(r_date)
                
            frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            btn = ctk.CTkButton(frame, text=r_title, anchor="w", fg_color="transparent", 
                                text_color=("black", "white"), hover_color=("gray80", "gray30"),
                                command=lambda req_id=r_id: self.load_reading_by_id(req_id))
            btn.pack(side="left", fill="x", expand=True)
            
            del_btn = ctk.CTkButton(frame, text="X", width=20, fg_color="transparent", text_color="red", 
                                    hover_color=("gray80", "gray30"),
                                    command=lambda req_id=r_id: self.delete_reading_by_id(req_id))
            del_btn.pack(side="right", padx=(5, 0))

    def load_reading_by_id(self, reading_id):
        self.pause_reader()
        text, idx = get_reading_content(reading_id, current_user["user_id"])
        
        self.current_reading_id = reading_id
        self.input_text.delete("0.0", "end")
        self.input_text.insert("0.0", text)
        self.load_text()
        self.current_idx = min(idx, len(self.words)-1) if self.words else 0
        self.update_progress()
        self.draw_placeholder()

    def delete_reading_by_id(self, reading_id):
        delete_reading(reading_id, current_user["user_id"])
        if self.current_reading_id == reading_id:
            self.current_reading_id = None
            self.input_text.delete("0.0", "end")
            self.words = []
            self.current_idx = 0
            self._redraw_current_canvas()
        self.load_sidebar_readings()

    def auto_save(self):
        if current_user["is_guest"] or not self.words:
            return
            
        text = self.input_text.get("0.0", "end").strip()
        if not text:
            return
            
        title = " ".join(self.words[:4]) + "..." if len(self.words) >= 4 else " ".join(self.words)
        
        self.current_reading_id = save_reading(
            current_user["user_id"], 
            self.current_reading_id, 
            text, 
            self.current_idx, 
            title
        )
        if self.sidebar_is_open:
            self.load_sidebar_readings()

    def change_appearance_mode(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)
        self.apply_settings(self.display_settings)
        
    def _redraw_current_canvas(self):
        if not self.words:
            self.draw_placeholder()
            return
        if self.current_idx == 0:
            self.draw_placeholder()
        elif self.current_idx >= len(self.words):
            self.draw_finished()
        else:
            word_idx_to_draw = self.current_idx - 1 if self.current_idx > 0 else 0
            self.draw_word(self.words[word_idx_to_draw])

    def toggle_focus_mode(self, event=None):
        self.focus_mode_active = not self.focus_mode_active
        
        if self.focus_mode_active:
            self.top_bar.grid_remove()
            self.input_text.grid_remove()
            self.progress_bar.grid_remove()
            self.credit_label.place_forget()
            if self.sidebar_is_open:
                self.sidebar_frame.grid_remove()
                
            self.main_content.grid_rowconfigure(4, weight=3)
            self.master_app.attributes("-fullscreen", True)
            
            # Show toast about escape
            self.canvas.create_text(self.canvas.winfo_width()//2, 30, text="Press ESC to exit Focus Mode", font=("Arial", 12), fill="gray50", tags="toast")
            self.after(3000, lambda: self.canvas.delete("toast"))
            
        else:
            self.top_bar.grid()
            self.input_text.grid()
            self.progress_bar.grid()
            self.credit_label.place(relx=0.01, rely=0.99, anchor="sw")
            if self.sidebar_is_open:
                self.sidebar_frame.grid()
                
            self.main_content.grid_rowconfigure(4, weight=1)
            self.master_app.attributes("-fullscreen", False)

    def update_wpm(self, value):
        self.wpm = int(value)
        self.wpm_label.configure(text=f"Speed: {self.wpm} WPM")
        
    def load_text(self):
        text = self.input_text.get("0.0", "end")
        self.words = tokenize_text(text)
        if self.current_idx >= len(self.words):
            self.current_idx = 0
            
    def actually_start_reader(self):
        # Always reload text from the textbox so pasting new content and pressing Play just works
        self.load_text()
            
        if not self.words:
            return
            
        self.is_playing = True
        self.play_btn.configure(text="Pause")
        self.read_next_word()
        
    def pause_reader(self):
        was_playing = self.is_playing
        self.is_playing = False
        self.play_btn.configure(text="Play")
        if self._scheduled_task:
            self.after_cancel(self._scheduled_task)
            self._scheduled_task = None
        
        if was_playing:
            self.auto_save()
            
    def reset_reader(self):
        self.pause_reader()
        self.current_idx = 0
        self.load_text()
        self.update_progress()
        self.draw_placeholder()
        self.auto_save()
        
    def read_next_word(self):
        if not self.is_playing:
            return
            
        if self.current_idx >= len(self.words):
            self.pause_reader()
            self.draw_finished()
            return
            
        word = self.words[self.current_idx]
        self.draw_word(word)
        
        self.current_idx += 1
        self.update_progress()
        
        if self.current_idx % 20 == 0:
            self.auto_save()
            
        base_delay_ms = (60.0 / self.wpm) * 1000
        multiplier = get_delay_multiplier(word)
        delay = int(base_delay_ms * multiplier)
        
        self._scheduled_task = self.after(delay, self.read_next_word)
        
    def update_progress(self):
        total = len(self.words)
        self.progress_label.configure(text=f"{self.current_idx} / {total}")
        if total > 0:
            self.progress_bar.set(self.current_idx / total)
        else:
            self.progress_bar.set(0)
        
    def draw_placeholder(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1: return 
        self._draw_center_lines(width, height)
        self.canvas.create_text(width//2, height//2, text="Ready", font=(self.display_settings["font"], 32, "bold"), fill="gray50")
        
    def draw_finished(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1: return
        self._draw_center_lines(width, height)
        self.canvas.create_text(width//2, height//2, text="Finished", font=(self.display_settings["font"], 32, "bold"), fill="gray50")
        self.master_app.check_for_promo()

    def _draw_center_lines(self, width, height):
        center_x = width // 2
        center_y = height // 2
        self.canvas.create_line(center_x, center_y - 40, center_x, center_y - 25, fill="gray40", width=2)
        self.canvas.create_line(center_x, center_y + 40, center_x, center_y + 25, fill="gray40", width=2)
        
    def draw_word(self, word):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width <= 1: return
        self._draw_center_lines(width, height)
        
        prefix, focus, suffix = process_word_for_display(word)
        font = (self.display_settings["font"], 40, "bold")
        center_x = width // 2
        center_y = height // 2
        
        actual_focus = FOCUS_MAP.get(self.display_settings["focus_color"], "#e74c3c")
        actual_tx = TX_MAP.get(self.display_settings["text_color"], "white")
        
        focus_id = self.canvas.create_text(center_x, center_y, text=focus, font=font, fill=actual_focus)
        bbox = self.canvas.bbox(focus_id)
        if bbox:
            f_left, f_top, f_right, f_bottom = bbox
            if prefix:
                self.canvas.create_text(f_left, center_y, text=prefix, font=font, fill=actual_tx, anchor="e")
            if suffix:
                self.canvas.create_text(f_right, center_y, text=suffix, font=font, fill=actual_tx, anchor="w")

class RSVPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_db()
        self.title("ReadSteed")
        self.geometry("900x650")
        self.minsize(700, 500)
        self.is_fullscreen = False
        
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_focus_mode_bind)
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.current_frame = None
        self.show_auth_screen()
        
    def exit_focus_mode_bind(self, event=None):
        if self.current_frame and hasattr(self.current_frame, 'focus_mode_active') and self.current_frame.focus_mode_active:
            self.current_frame.toggle_focus_mode()
        else:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        
    def switch_frame(self, frame_class, **kwargs):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self, **kwargs)
        self.current_frame.grid(row=0, column=0, sticky="nsew")
        
    def show_auth_screen(self):
        self.switch_frame(AuthScreen, on_success_callback=self.show_main_app)
        
    def show_main_app(self):
        self.switch_frame(MainAppFrame, on_logout=self.handle_logout)
        
    def handle_play_request(self):
        if self.current_frame.is_playing:
            self.current_frame.pause_reader()
        else:
            self.current_frame.actually_start_reader()

    def check_for_promo(self):
        if current_user["is_guest"]:
            self.show_promo_screen("Create an Account", "Track multiple reading records automatically.", "Sign Up", self.handle_logout)
            
    def show_promo_screen(self, title, desc, btn_text, action_cmd):
        self.current_frame.grid_remove()
        def on_dismiss():
            self.promo_frame.destroy()
            self.current_frame.grid()
        def on_act():
            self.promo_frame.destroy()
            action_cmd()
        self.promo_frame = PromoScreen(self, title, desc, btn_text, on_act, on_dismiss)
        self.promo_frame.grid(row=0, column=0, sticky="nsew")

    def handle_logout(self):
        if hasattr(self.current_frame, 'auto_save'):
            self.current_frame.auto_save()
        logout()
        self.show_auth_screen()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = RSVPApp()
    app.mainloop()
