import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import sys
import os
import threading
import json
import keyring
import re
import glob
import traceback
import socket
import win32com.client
import win32gui
import win32con
from google import genai
from google.genai import types

# Configuration
APP_NAME = "PushAgent"
KEYRING_SERVICE = "PushAgent_GeminiAPI"
KEYRING_USER = "user_key"
IPC_PORT = 65432  # Local port for single-instance IPC

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        if self.api_key:
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version="v1")
            )
        else:
            self.client = None

    def list_models(self):
        if not self.client: return []
        try:
            models = []
            for m in self.client.models.list():
                 if "gemini" in m.name.lower():
                     models.append(m.name)
            models.sort(reverse=True) 
            return models
        except Exception as e:
            print(f"Model list error: {e}")
            return ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]

    def generate(self, prompt, model_name="models/gemini-1.5-flash"):
        if not self.client: raise ValueError("API Key is missing.")
        try:
            response = self.client.models.generate_content(model=model_name, contents=prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Gemini API Error ({model_name}): {str(e)}")

    def test_connection(self, model_name="models/gemini-1.5-flash"):
        try:
            self.generate("ping", model_name)
            return True, "Connection successful."
        except Exception as e:
            return False, traceback.format_exc()

class PushAgentApp(ctk.CTk):
    def __init__(self, start_path=None):
        # 1. Single Instance Check
        self.ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.ipc_socket.bind(('127.0.0.1', IPC_PORT))
            self.ipc_socket.listen(1)
            # We are the main instance
            super().__init__()
            threading.Thread(target=self.ipc_listener, daemon=True).start()
        except OSError:
            # Port busy -> Check if valid instance or zombie
            if self.send_to_existing_instance(start_path):
                sys.exit(0) # Valid instance found
            else:
                # Zombie port (busy but not listening). Start without IPC.
                print("Warning: IPC Port busy but no response. Single-instance mode disabled.")
                super().__init__()

        self.title("GitHub Push Agent - AI Powered")
        self.geometry("750x900")
        self.minsize(700, 800)
        
        self.api_key = ""
        self.repo_list = []
        self.is_running = False
        self.available_models = ["models/gemini-1.5-flash"] 

        # Load API Key
        try:
            self.api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
        except Exception as e:
            print(f"Keyring error: {e}")

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_tabs = ctk.CTkTabview(self)
        self.main_tabs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_main = self.main_tabs.add("Main")
        self.tab_settings = self.main_tabs.add("Settings")

        # Setup Tabs (UI must exist before we update fields)
        self.setup_settings_tab()
        self.setup_main_tab()
        
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.frame_log.grid_columnconfigure(0, weight=1)
        
        self.lbl_log = ctk.CTkLabel(self.frame_log, text="Activity Log", font=("Segoe UI", 12, "bold"))
        self.lbl_log.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        self.textbox_log = ctk.CTkTextbox(self.frame_log, height=150, font=("Consolas", 10))
        self.textbox_log.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.textbox_log.configure(state="disabled")

        # 2. Path Detection Logic
        detected_path = None
        
        # Priority A: Command line arg
        if start_path and os.path.isdir(start_path):
             detected_path = start_path
             self.log(f"Startup: Using provided path: {detected_path}")
        
        # Priority B: Active Explorer Window
        if not detected_path:
             detected_path = self.get_active_explorer_path()
             if detected_path:
                 self.log(f"Startup: Detected active Explorer folder: {detected_path}")
        
        # Priority C: Fallback to CWD
        if not detected_path:
             detected_path = os.getcwd()
             self.log(f"Startup: No Explorer context found. Fallback to: {detected_path}")

        self.working_dir = detected_path
        
        # Apply State
        if self.working_dir:
            self.path_var.set(self.working_dir)
            self.detect_git_state()
            self.reset_session_state()

        threading.Thread(target=self.fetch_repos, daemon=True).start()
        if self.api_key:
            threading.Thread(target=self.refresh_models, daemon=True).start()

    # --- Session Management ---

    def reset_session_state(self):
        """Resets the Main tab inputs to default for a fresh session."""
        try:
            # 1. Repo Name: Keep what detect_git_state set, or reset if needed
            # We don't wipe it blank because detect_git_state populates a smart default.
            
            # 2. Privacy
            self.privacy_var.set("private")
            
            # 3. Commit
            self.commit_mode_var.set(False)
            self.toggle_commit_input()
            self.entry_commit.delete(0, "end")
            self.entry_commit.insert(0, "Update")
            
            # 4. README
            self.readme_mode_var.set("Do nothing")
            
            self.log("Session UI reset to defaults.")
        except Exception as e:
            self.log(f"Error resetting session: {e}")

    # --- Single Instance & IPC ---

    def send_to_existing_instance(self, path):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', IPC_PORT))
            msg = path if path else "DETECT"
            client.sendall(msg.encode('utf-8'))
            client.close()
            return True
        except Exception as e:
            print(f"IPC Error: {e}")
            return False

    def ipc_listener(self):
        while True:
            try:
                conn, addr = self.ipc_socket.accept()
                data = conn.recv(1024).decode('utf-8').strip()
                conn.close()
                self.after(0, lambda: self.handle_ipc_message(data))
            except Exception as e:
                print(f"IPC Listener Error: {e}")

    def handle_ipc_message(self, data):
        self.log(f"Received signal: {data}")
        self.bring_to_front()
        
        new_path = None
        if data == "DETECT":
            new_path = self.get_active_explorer_path()
            if new_path:
                self.log(f"Auto-detected active folder: {new_path}")
            else:
                self.log("Explorer detection failed during sync.")
        elif data and os.path.exists(data):
            new_path = data
            self.log(f"Received path argument: {new_path}")
            
        if new_path:
            self.working_dir = new_path
            self.path_var.set(new_path)
            self.detect_git_state()
            self.reset_session_state() # Reset UI on switch

    def bring_to_front(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            def callback(hwnd, extra):
                if "GitHub Push Agent" in win32gui.GetWindowText(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
            win32gui.EnumWindows(callback, None)
        except Exception as e:
            self.log(f"Focus error: {e}")
            self.lift()
            self.focus_force()

    def get_active_explorer_path(self):
        try:
            shell = win32com.client.Dispatch("Shell.Application")
            foreground_hwnd = win32gui.GetForegroundWindow()
            
            # 1. Try to match foreground window
            for window in shell.Windows():
                try:
                    if window.HWND == foreground_hwnd:
                        path = window.Document.Folder.Self.Path
                        return path
                except: continue

            # 2. Heuristic: Return the first valid file system window found
            # (Use this cautiously, but user requested 'active' logic.
            # If foreground check fails, maybe don't return random window to avoid confusion?)
            # Reverting to safer behavior: Only return if we are fairly sure.
            # But the user said "detect the currently active File Explorer folder path".
            # If the foreground window is NOT Explorer, we shouldn't guess.
            
            return None 
                    
        except Exception as e:
            self.log(f"Explorer detection error: {e}")
        return None

    # --- UI Setup ---

    def setup_settings_tab(self):
        frame = ctk.CTkFrame(self.tab_settings, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header = ctk.CTkLabel(frame, text="🔑 Gemini API Configuration", font=("Segoe UI", 18, "bold"))
        header.pack(pady=(15, 25), padx=20)
        
        ctk.CTkLabel(frame, text="API Key:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.entry_api = ctk.CTkEntry(frame, width=400, show="*", height=40)
        self.entry_api.pack(pady=10, padx=20)
        if self.api_key: self.entry_api.insert(0, self.api_key)
            
        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="Show Key", variable=self.show_key_var, command=self.toggle_show_key).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkButton(frame, text="💾 Save & Fetch Models", command=self.save_api_key, height=40, font=("Segoe UI", 12)).pack(pady=15, padx=20, fill="x")

        ctk.CTkLabel(frame, text="Select Model:", font=("Segoe UI", 12)).pack(anchor="w", padx=20, pady=(15, 0))
        self.combo_models = ctk.CTkComboBox(frame, values=self.available_models, width=400, height=40)
        self.combo_models.pack(pady=10, padx=20, fill="x")
        self.combo_models.set("models/gemini-1.5-flash")
        
        ctk.CTkButton(frame, text="🔄 Refresh Models", command=lambda: threading.Thread(target=self.refresh_models, daemon=True).start(), height=40, font=("Segoe UI", 11)).pack(pady=10, padx=20, fill="x")
        
        self.btn_test = ctk.CTkButton(frame, text="✓ Test Selected Model", command=self.test_api_key, height=45, font=("Segoe UI", 12), fg_color="#1f6feb", hover_color="#388bfd")
        self.btn_test.pack(pady=20, padx=20, fill="x")

    def setup_main_tab(self):
        self.tab_main.grid_columnconfigure(0, weight=1)
        
        # Path
        frame_path = ctk.CTkFrame(self.tab_main, corner_radius=10)
        frame_path.pack(fill="x", padx=15, pady=12)
        
        ctk.CTkLabel(frame_path, text="📁 Project Folder:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=15, pady=12)
        self.path_var = ctk.StringVar(value="Not Selected")
        self.entry_path = ctk.CTkEntry(frame_path, textvariable=self.path_var, width=300, state="readonly", height=38)
        self.entry_path.pack(side="left", fill="x", expand=True, padx=10, pady=12)
        
        ctk.CTkButton(frame_path, text="Browse", width=70, height=38, command=self.browse_folder).pack(side="left", padx=5)
        ctk.CTkButton(frame_path, text="🔄 Sync", width=70, height=38, fg_color="#555555", hover_color="#666666", command=self.manual_sync_folder).pack(side="left", padx=5)

        # Repos
        self.repo_tabs = ctk.CTkTabview(self.tab_main, height=150, corner_radius=10)
        self.repo_tabs.pack(fill="x", padx=15, pady=12)
        self.tab_exist = self.repo_tabs.add("Existing Remote")
        self.tab_new = self.repo_tabs.add("Create New Remote")
        
        ctk.CTkLabel(self.tab_exist, text="🔗 Select GitHub Repository:", font=("Segoe UI", 11, "bold")).pack(pady=12)
        self.combo_repos = ctk.CTkComboBox(self.tab_exist, values=["Loading..."], width=300, height=38)
        self.combo_repos.pack(pady=10, padx=15)
        
        frame_new = ctk.CTkFrame(self.tab_new, fg_color="transparent")
        frame_new.pack(pady=15, padx=15)
        self.entry_repo_name = ctk.CTkEntry(frame_new, placeholder_text="Repository Name", width=250, height=38)
        self.entry_repo_name.pack(side="left", padx=10)
        
        self.privacy_var = ctk.StringVar(value="private")
        ctk.CTkRadioButton(frame_new, text="🔒 Private", variable=self.privacy_var, value="private").pack(side="left", padx=10)
        ctk.CTkRadioButton(frame_new, text="🌐 Public", variable=self.privacy_var, value="public").pack(side="left", padx=10)

        # Commit
        frame_commit = ctk.CTkFrame(self.tab_main, corner_radius=10)
        frame_commit.pack(fill="x", padx=15, pady=12)
        
        row1 = ctk.CTkFrame(frame_commit, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(row1, text="💬 Commit Message", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        self.commit_mode_var = ctk.BooleanVar(value=False)
        self.check_ai_commit = ctk.CTkCheckBox(row1, text="✨ Generate with Gemini", variable=self.commit_mode_var, command=self.toggle_commit_input)
        self.check_ai_commit.pack(side="right")
        
        self.entry_commit = ctk.CTkEntry(frame_commit, placeholder_text="Enter commit message...", height=38)
        self.entry_commit.pack(fill="x", padx=15, pady=(5, 12))
        self.entry_commit.insert(0, "Update")

        # Readme
        frame_readme = ctk.CTkFrame(self.tab_main, corner_radius=10)
        frame_readme.pack(fill="x", padx=15, pady=12)
        
        row2 = ctk.CTkFrame(frame_readme, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(12, 5))
        ctk.CTkLabel(row2, text="📄 README.md", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        self.readme_mode_var = ctk.StringVar(value="Do nothing")
        self.opt_readme = ctk.CTkOptionMenu(row2, variable=self.readme_mode_var, values=["Do nothing", "Create Minimal", "Generate with Gemini"], height=36)
        self.opt_readme.pack(side="right", padx=15, pady=(5, 12))

        # Push
        self.btn_push = ctk.CTkButton(self.tab_main, text="🚀 Push to GitHub", height=55, font=("Segoe UI", 14, "bold"), fg_color="#2EA44F", hover_color="#2C974B", command=self.on_push)
        self.btn_push.pack(fill="x", padx=15, pady=20)

    # --- Logic ---

    def log(self, message):
        def _update_ui():
            self.textbox_log.configure(state="normal")
            self.textbox_log.insert("end", f"> {message}\n")
            self.textbox_log.see("end")
            self.textbox_log.configure(state="disabled")
        self.after(0, _update_ui)

    def toggle_show_key(self):
        if self.show_key_var.get():
            self.entry_api.configure(show="")
        else:
            self.entry_api.configure(show="*")

    def save_api_key(self):
        key = self.entry_api.get().strip()
        if not key:
            messagebox.showerror("Error", "API Key cannot be empty.")
            return
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)
            self.api_key = key
            messagebox.showinfo("Success", "API Key saved. Fetching models...")
            self.log("API Key updated. Fetching models...")
            threading.Thread(target=self.refresh_models, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save key: {e}")
            self.log(f"Error saving key: {e}")

    def refresh_models(self):
        if not self.api_key: return
        self.log("Fetching available models from Google AI...")
        client = GeminiClient(self.api_key)
        models = client.list_models()
        if models:
            self.available_models = models
            
            def _update():
                self.combo_models.configure(values=models)
                # Smart Default: Prefer 1.5-flash as it has the best quota limits
                curr = self.combo_models.get()
                if curr not in models:
                    preferred = "models/gemini-1.5-flash"
                    if preferred in models:
                        self.combo_models.set(preferred)
                    else:
                        self.combo_models.set(models[0])
                self.log(f"Models loaded: {len(models)} found. Selected: {self.combo_models.get()}")
            self.after(0, _update)
        else:
            self.log("Failed to list models. Using fallback defaults.")

    def test_api_key(self):
        key = self.entry_api.get().strip()
        model = self.combo_models.get()
        if not key:
            messagebox.showerror("Error", "Enter a key first.")
            return
        
        self.btn_test.configure(state="disabled", text="Testing...")
        self.log(f"Testing connection with model: {model}...")
        
        def run_test():
            client = GeminiClient(key)
            success, msg = client.test_connection(model_name=model)
            
            def _update():
                if success:
                    self.log(f"API Test Passed. Model '{model}' is responding.")
                    messagebox.showinfo("Success", f"Connected to {model} successfully!")
                else:
                    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                        self.log(f"API Test Failed: Quota exceeded for {model}. Please wait or try 'gemini-1.5-flash'.")
                        messagebox.showwarning("Quota Exceeded", f"The model {model} has reached its limit.\n\nTry switching to 'gemini-1.5-flash' in Settings.")
                    else:
                        self.log(f"API Test Failed:\n{msg}")
                        messagebox.showerror("Failed", "Connection failed. Check logs for details.")
                self.btn_test.configure(state="normal", text="Test Selected Model")
            
            self.after(0, _update)
            
        threading.Thread(target=run_test, daemon=True).start()

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.working_dir = path
            self.path_var.set(path)
            self.detect_git_state()
            self.reset_session_state()

    def manual_sync_folder(self):
        self.log("Syncing with active Explorer window...")
        path = self.get_active_explorer_path()
        if path:
            self.working_dir = path
            self.path_var.set(path)
            self.detect_git_state()
            self.reset_session_state()
            self.log(f"Synced: {path}")
        else:
            self.log("No active Explorer window found.")
            messagebox.showinfo("Info", "Could not detect an active File Explorer window.")

    def detect_git_state(self):
        if not self.working_dir: return
        folder_name = os.path.basename(os.path.abspath(self.working_dir))
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '-', folder_name).lower()
        self.entry_repo_name.delete(0, "end")
        self.entry_repo_name.insert(0, slug)
        
        is_git = os.path.isdir(os.path.join(self.working_dir, ".git"))
        if is_git:
            self.repo_tabs.set("Existing Remote")
            self.log(f"Opened: {self.working_dir} (Git Repo)")
        else:
            self.repo_tabs.set("Create New Remote")
            self.log(f"Opened: {self.working_dir} (Not a Repo)")

    def toggle_commit_input(self):
        if self.commit_mode_var.get():
            self.entry_commit.configure(state="disabled", placeholder_text="--- Gemini will generate this message ---")
        else:
            self.entry_commit.configure(state="normal", placeholder_text="Enter commit message...")

    def fetch_repos(self):
        try:
            cmd = ["gh", "repo", "list", "--json", "name,url", "--limit", "100"]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                self.repo_list = data
                names = [r['name'] for r in data]
                
                def _update():
                    self.combo_repos.configure(values=names)
                    if names: self.combo_repos.set(names[0])
                self.after(0, _update)
            else:
                self.log("Warning: Could not fetch repos. Ensure 'gh' CLI is installed.")
        except Exception as e:
            self.log(f"Repo fetch error: {e}")

    def run_cmd(self, args, cwd=None, ignore_error=False):
        target_dir = cwd if cwd else self.working_dir
        self.log(f"Exec: {' '.join(args)}")
        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            res = subprocess.run(
                args, 
                cwd=target_dir, 
                capture_output=True, 
                text=True, 
                check=True, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=env,
                timeout=300
            )
            return res.stdout.strip()
        except subprocess.TimeoutExpired:
            self.log("CMD TIMEOUT")
            if not ignore_error: raise Exception("Command timed out")
            return None
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() or e.stdout.strip()
            if not ignore_error:
                self.log(f"CMD ERROR: {err}")
                raise Exception(err)
            return None

    def get_file_tree(self):
        ignore_dirs = {'.git', 'node_modules', '.venv', 'build', 'dist', '__pycache__', '.idea', '.vscode'}
        tree = []
        for root, dirs, files in os.walk(self.working_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = root.replace(self.working_dir, '').count(os.sep)
            indent = '  ' * level
            tree.append(f"{indent}{os.path.basename(root)}/")
            for f in files[:8]: 
                tree.append(f"{indent}  {f}")
        return "\n".join(tree[:80])

    def on_push(self):
        if not self.working_dir:
            messagebox.showerror("Error", "Please select a project folder first.")
            return
        if self.is_running: return
        
        # Gather data on Main Thread
        data = {
            "use_ai_commit": self.commit_mode_var.get(),
            "use_ai_readme": self.readme_mode_var.get() == "Generate with Gemini",
            "model_name": self.combo_models.get(),
            "commit_msg_input": self.entry_commit.get(),
            "readme_opt": self.readme_mode_var.get(),
            "repo_tab": self.repo_tabs.get(),
            "repo_name": self.entry_repo_name.get().strip(),
            "privacy": self.privacy_var.get(),
            "selected_repo": self.combo_repos.get()
        }

        self.is_running = True
        self.btn_push.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_push_workflow, args=(data,), daemon=True).start()

    def run_push_workflow(self, data):
        try:
            use_ai_commit = data["use_ai_commit"]
            use_ai_readme = data["use_ai_readme"]
            model_name = data["model_name"]
            
            if (use_ai_commit or use_ai_readme) and not self.api_key:
                raise Exception("Gemini API Key is missing. Go to Settings tab.")

            client = GeminiClient(self.api_key) if (use_ai_commit or use_ai_readme) else None

            if not os.path.isdir(os.path.join(self.working_dir, ".git")):
                self.run_cmd(["git", "init", "-b", "main"])

            gitignore = os.path.join(self.working_dir, ".gitignore")
            if not os.path.exists(gitignore):
                self.log("Creating default .gitignore")
                with open(gitignore, "w") as f:
                    f.write("__pycache__/\n*.pyc\nnode_modules/\n.env\ndist/\n.DS_Store\n")

            self.run_cmd(["git", "add", "."])
            
            status = self.run_cmd(["git", "status", "--porcelain"])
            
            if status:
                msg = data["commit_msg_input"]
                if use_ai_commit:
                    self.log(f"Gemini ({model_name}): Generating commit message...")
                    diff = self.run_cmd(["git", "diff", "--staged", "--stat"])
                    if not diff: diff = "New files added."
                    
                    prompt = f"Write a concise git commit message (under 60 chars) for this diff:\n{diff}"
                    msg = client.generate(prompt, model_name=model_name)
                    self.log(f"Generated: {msg}")
                
                if not msg: msg = "Update"
                self.run_cmd(["git", "commit", "-m", msg])
            else:
                self.log("Working tree clean (nothing to commit).")

            readme_path = os.path.join(self.working_dir, "README.md")
            readme_opt = data["readme_opt"]
            
            if readme_opt != "Do nothing":
                should_create = False
                if not os.path.exists(readme_path):
                    should_create = True
                else: pass 
                
                if should_create:
                    content = ""
                    if readme_opt == "Create Minimal":
                        name = os.path.basename(self.working_dir)
                        content = f"# {name}"
                    elif readme_opt == "Generate with Gemini":
                        self.log(f"Gemini ({model_name}): Generating README...")
                        tree = self.get_file_tree()
                        prompt = f"Create a professional README.md for a project with this file structure:\n{tree}\n\nKeep it concise."
                        content = client.generate(prompt, model_name=model_name)
                    
                    content = re.sub(r'^```[a-z]*\n', '', content, flags=re.MULTILINE)
                    content = re.sub(r'\n```$', '', content, flags=re.MULTILINE)
                    
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.log("README.md created.")
                    
                    self.run_cmd(["git", "add", "README.md"])
                    self.run_cmd(["git", "commit", "-m", "Add README"])

            repo_url = ""
            current_tab = data["repo_tab"]
            
            if current_tab == "Create New Remote":
                repo_name = data["repo_name"]
                if not repo_name: raise Exception("Repository name is required.")
                visibility = f"--{data['privacy']}"
                
                exists = subprocess.run(["gh", "repo", "view", repo_name], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW).returncode == 0
                
                if not exists:
                    self.log(f"Creating remote repo: {repo_name}...")
                    self.run_cmd(["gh", "repo", "create", repo_name, visibility, "--source=.", "--remote=origin"])
                else:
                    self.log(f"Repo {repo_name} already exists. Linking...")
                    remotes = self.run_cmd(["git", "remote"], ignore_error=True) or ""
                    if "origin" not in remotes:
                        try:
                            login = subprocess.check_output(["gh", "api", "user", "--jq", ".login"], creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
                            url = f"https://github.com/{login}/{repo_name}.git"
                            self.run_cmd(["git", "remote", "add", "origin", url])
                        except:
                            raise Exception("Could not determine repo URL. Is 'gh' logged in?")
            
            else:
                selected = data["selected_repo"]
                match = next((r for r in self.repo_list if r['name'] == selected), None)
                if not match: raise Exception(f"Selected repo '{selected}' not found in list.")
                url = match['url']
                
                remotes = self.run_cmd(["git", "remote"], ignore_error=True) or ""
                if "origin" in remotes:
                    self.run_cmd(["git", "remote", "set-url", "origin", url])
                else:
                    self.run_cmd(["git", "remote", "add", "origin", url])

            self.log("Pushing to origin...")
            self.run_cmd(["git", "push", "-u", "origin", "main"])
            
            repo_url = self.run_cmd(["git", "remote", "get-url", "origin"])
            self.log("Done!")
            self.after(0, lambda: self.show_success(repo_url))

        except Exception as e:
            err_msg = traceback.format_exc()
            self.log(f"CRITICAL ERROR:\n{err_msg}")
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred. Check log.\n{str(e)}"))
        finally:
            self.is_running = False
            self.after(0, lambda: self.btn_push.configure(state="normal", text="Push to GitHub"))

    def show_success(self, url):
        res = messagebox.askyesno("Success", "Code pushed to GitHub successfully!\n\nOpen repository in browser?")
        if res:
            import webbrowser
            webbrowser.open(url)

if __name__ == "__main__":
    path_arg = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        path_arg = sys.argv[1]
    
    app = PushAgentApp(path_arg)
    app.mainloop()
