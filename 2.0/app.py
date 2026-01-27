import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import threading

from analyzer import ProjectAnalyzer
from auditor import ProjectAuditor
from generator import ReadmeGenerator

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Project Auditor & README Generator")
        self.geometry("700x650")

        self.analyzer = ProjectAnalyzer()
        self.auditor = ProjectAuditor()
        self.generator = ReadmeGenerator()
        
        self.selected_folder = None
        self.project_data = None
        self.audit_results = {}

        self._setup_ui()
        self._load_models()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # 1. Model Selection
        self.model_frame = ctk.CTkFrame(self)
        self.model_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_model = ctk.CTkLabel(self.model_frame, text="Select Ollama Model:")
        self.lbl_model.pack(side="left", padx=10)
        
        self.model_var = ctk.StringVar(value="Loading...")
        self.model_dropdown = ctk.CTkOptionMenu(self.model_frame, variable=self.model_var)
        self.model_dropdown.pack(side="left", padx=10, fill="x", expand=True)

        # 2. Folder Selection
        self.folder_frame = ctk.CTkFrame(self)
        self.folder_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_browse = ctk.CTkButton(self.folder_frame, text="Select Project Folder", command=self.select_folder)
        self.btn_browse.pack(side="left", padx=10, pady=10)
        
        self.lbl_path = ctk.CTkLabel(self.folder_frame, text="No folder selected", text_color="gray")
        self.lbl_path.pack(side="left", padx=10, pady=10)

        # 3. Action Area
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.lbl_type = ctk.CTkLabel(self.action_frame, text="Project Type: -", font=("Arial", 14, "bold"))
        self.lbl_type.pack(side="left", padx=20, pady=10)
        
        self.btn_generate = ctk.CTkButton(self.action_frame, text="Audit & Generate README", command=self.start_generation, state="disabled", fg_color="green")
        self.btn_generate.pack(side="right", padx=20, pady=10)

        # 4. Status Details
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.lbl_gitignore = ctk.CTkLabel(self.status_frame, text=".gitignore: Pending")
        self.lbl_gitignore.pack(side="left", padx=10, pady=5)
        
        self.lbl_reqs = ctk.CTkLabel(self.status_frame, text="requirements.txt: Pending")
        self.lbl_reqs.pack(side="left", padx=10, pady=5)

        # 5. Log
        self.lbl_log = ctk.CTkLabel(self, text="Activity Log:")
        self.lbl_log.grid(row=4, column=0, padx=20, pady=(10,0), sticky="w")
        
        self.log_box = ctk.CTkTextbox(self)
        self.log_box.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")
        self.log("Welcome! Please ensure Ollama is running and select a model.")

    def _load_models(self):
        def fetch():
            models = self.generator.get_models()
            if models:
                self.model_dropdown.configure(values=models)
                self.model_var.set(models[0])
                self.log(f"Loaded {len(models)} models from Ollama.")
            else:
                self.model_var.set("No models found / Ollama Offline")
                self.model_dropdown.configure(state="disabled")
                self.log("Error: Could not fetch models. Is Ollama running?")
        
        threading.Thread(target=fetch, daemon=True).start()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder = folder
            self.lbl_path.configure(text=folder, text_color=("black", "white"))
            self.log(f"Selected folder: {folder}")
            
            # Scan immediately
            self.project_data = self.analyzer.scan_project(folder)
            self.lbl_type.configure(text=f"Project Type: {self.project_data['type']}")
            self.log(f"Detected Type: {self.project_data['type']}")
            self.log(f"Found {len(self.project_data['tree'])} files.")
            
            # Reset status labels
            self.lbl_gitignore.configure(text=".gitignore: Pending")
            self.lbl_reqs.configure(text="requirements.txt: Pending")
            
            self.btn_generate.configure(state="normal")

    def start_generation(self):
        if not self.selected_folder:
            return
        
        model = self.model_var.get()
        if "Offline" in model or "Loading" in model:
            self.log("Error: Invalid model selection.")
            return

        self.btn_generate.configure(state="disabled")
        self.log("\n--- Starting Deep Analysis & Generation ---")
        
        threading.Thread(target=self._process, args=(model,), daemon=True).start()

    def _process(self, model):
        try:
            # Audit
            self.log("Running Auditor...")
            self.audit_results = self.auditor.audit(self.selected_folder, self.project_data['type'])
            
            # Update Status UI
            self.lbl_gitignore.configure(text=f".gitignore: {self.audit_results['gitignore_status']}")
            self.lbl_reqs.configure(text=f"requirements.txt: {self.audit_results['requirements_status']}")
            
            self.log(f"Audit Complete: .gitignore ({self.audit_results['gitignore_status']}), requirements ({self.audit_results['requirements_status']})")

            # Generate
            self.log(f"Analyzing code and generating README with '{model}'...")
            success, msg = self.generator.generate(
                model, 
                self.project_data, 
                self.audit_results, 
                self.selected_folder
            )
            
            if success:
                self.log("SUCCESS: README.md created based on analysis!")
            else:
                self.log(f"FAILED: {msg}")
                
        except Exception as e:
            self.log(f"Critical Error: {e}")
        finally:
            self.btn_generate.configure(state="normal")

    def log(self, message):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")

if __name__ == "__main__":
    app = App()
    app.mainloop()