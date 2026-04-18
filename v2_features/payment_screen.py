import customtkinter as ctk
from database import current_user, upgrade_to_premium

class PaymentScreen(ctk.CTkFrame):
    def __init__(self, master, on_success_callback, on_cancel_callback):
        super().__init__(master)
        self.on_success = on_success_callback
        self.on_cancel = on_cancel_callback
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(self, text="Upgrade to Premium", font=ctk.CTkFont(size=28, weight="bold"))
        title.grid(row=1, column=0, pady=(20, 10))
        
        price = ctk.CTkLabel(self, text="One-time Payment: $14.99", font=ctk.CTkFont(size=20), text_color="#2ecc71")
        price.grid(row=2, column=0, pady=10)
        
        desc = ctk.CTkLabel(self, text="Remove all ads forever and enjoy uninterrupted reading.", font=ctk.CTkFont(size=14))
        desc.grid(row=3, column=0, pady=(0, 30))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=10)
        
        pay_btn = ctk.CTkButton(btn_frame, text="Simulate Payment ($14.99)", command=self.handle_payment, width=200, fg_color="#27ae60", hover_color="#2ecc71")
        pay_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel, width=100, fg_color="gray40", hover_color="gray30")
        cancel_btn.pack(side="left", padx=10)
        
        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.grid(row=6, column=0, pady=10)

    def handle_payment(self):
        if upgrade_to_premium():
            self.on_success()
        else:
            self.error_label.configure(text="Error upgrading. Are you a guest?")
