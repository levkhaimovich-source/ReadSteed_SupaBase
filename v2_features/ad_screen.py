import customtkinter as ctk

class AdScreen(ctk.CTkFrame):
    def __init__(self, master, on_complete_callback):
        super().__init__(master)
        self.on_complete = on_complete_callback
        self.seconds_left = 5
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.ad_label = ctk.CTkLabel(self, text="SIMULATED AD", font=ctk.CTkFont(size=40, weight="bold"), text_color="#f1c40f")
        self.ad_label.grid(row=0, column=0, pady=(40, 20))
        
        self.desc_label = ctk.CTkLabel(self, text="Watch this ad to continue reading.\nUpgrade to Premium to remove ads forever!", font=ctk.CTkFont(size=16))
        self.desc_label.grid(row=1, column=0, pady=10)
        
        self.timer_label = ctk.CTkLabel(self, text="Ad ends in: 5s", font=ctk.CTkFont(size=20))
        self.timer_label.grid(row=2, column=0, pady=(20, 40))
        
    def start_ad(self):
        self.seconds_left = 5
        self.timer_label.configure(text=f"Ad ends in: {self.seconds_left}s")
        self._countdown()
        
    def _countdown(self):
        if self.seconds_left > 0:
            self.seconds_left -= 1
            self.timer_label.configure(text=f"Ad ends in: {self.seconds_left}s")
            self.after(1000, self._countdown)
        else:
            self.on_complete()
