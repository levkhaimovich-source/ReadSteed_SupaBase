import customtkinter as ctk

class PromoScreen(ctk.CTkFrame):
    def __init__(self, master, title, desc, action_text, on_action, on_dismiss):
        super().__init__(master)
        self.on_action = on_action
        self.on_dismiss = on_dismiss
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.grid(row=1, column=0, pady=(40, 10))
        
        self.desc_label = ctk.CTkLabel(self, text=desc, font=ctk.CTkFont(size=16))
        self.desc_label.grid(row=2, column=0, pady=(0, 30))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=10)
        
        self.action_btn = ctk.CTkButton(btn_frame, text=action_text, command=self.on_action, width=150, fg_color="#3498db", hover_color="#2980b9")
        self.action_btn.pack(side="left", padx=10)
        
        self.dismiss_btn = ctk.CTkButton(btn_frame, text="Maybe Later", command=self.on_dismiss, width=150, fg_color="gray40", hover_color="gray30")
        self.dismiss_btn.pack(side="left", padx=10)
