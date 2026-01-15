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
from google import genai
from google.genai import types

# Configuration
APP_NAME = "PushAgent"
KEYRING_SERVICE = "PushAgent_GeminiAPI"
KEYRING_USER = "user_key"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        if self.api_key:
            # Fix: Explicitly set API version to v1 to avoid v1beta 404 errors
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version="v1")
            )
        else:
            self.client = None

    def list_models(self):
        if not self.client:
            return []
        try:
            models = []
            # List models using the new SDK
            # Fix: Iterate and store exact names (e.g., "models/gemini-1.5-flash")
            for m in self.client.models.list():
                 # Fix: Remove 'supported_generation_methods' check as it causes errors on some objects
                 # Just filter by name convention
                 if "gemini" in m.name.lower():
                     models.append(m.name)
            
            # Sort to put latest/flash on top
            models.sort(reverse=True) 
            return models
        except Exception as e:
            print(f"Model list error: {e}")
            # Fallback list with correct full names
            return ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-2.0-flash-exp"]

    def generate(self, prompt, model_name="models/gemini-1.5-flash"):
        if not self.client:
            raise ValueError("API Key is missing.")
        
        # Fix: Do NOT strip 'models/' prefix. Use exact string from API.
        
        try:
            # Explicitly using the new SDK method
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            # Re-raise with context
            raise Exception(f"Gemini API Error ({model_name}): {str(e)}")

    def test_connection(self, model_name="models/gemini-1.5-flash"):
        try:
            self.generate("ping", model_name)
            return True, "Connection successful."
        except Exception as e:
            return False, traceback.format_exc()

class PushAgentApp(ctk.CTk):
    def __init__(self, start_path=None):
        super().__init__()
        
        self.title("GitHub Push Agent (AI Powered)")
        self.geometry("650x850")
        
        self.working_dir = start_path
        self.api_key = ""
        self.repo_list = []
        self.is_running = False
        # Fix: Default model must include 'models/' prefix
        self.available_models = ["models/gemini-1.5-flash"] 

        # Load API Key
        try:
            self.api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
        except Exception as e:
            print(f"Keyring error: {e}")

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabs
        self.main_tabs = ctk.CTkTabview(self)
        self.main_tabs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_main = self.main_tabs.add("Main")
        self.tab_settings = self.main_tabs.add("Settings")

        # Setup
        self.setup_settings_tab()
        self.setup_main_tab()
        
        # Log
        self.frame_log = ctk.CTkFrame(self)
        self.frame_log.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.frame_log.grid_columnconfigure(0, weight=1)
        
        self.lbl_log = ctk.CTkLabel(self.frame_log, text="Activity Log", font=("Segoe UI", 12, "bold"))
        self.lbl_log.grid(row=0, column=0, sticky="w", padx=5, pady=2)
        
        self.textbox_log = ctk.CTkTextbox(self.frame_log, height=150, font=("Consolas", 10))
        self.textbox_log.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.textbox_log.configure(state="disabled")

        # Init Logic
        if self.working_dir and os.path.exists(self.working_dir):
            self.path_var.set(self.working_dir)
            self.detect_git_state()
        elif not self.working_dir:
            cwd = os.getcwd()
            self.working_dir = cwd
            self.path_var.set(cwd)
            self.detect_git_state()

        threading.Thread(target=self.fetch_repos, daemon=True).start()
        if self.api_key:
            threading.Thread(target=self.refresh_models, daemon=True).start()

    # --- UI Setup ---

    def setup_settings_tab(self):
        frame = ctk.CTkFrame(self.tab_settings)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Gemini API Configuration", font=("Segoe UI", 16, "bold")).pack(pady=(10, 20))
        
        ctk.CTkLabel(frame, text="API Key:").pack(anchor="w", padx=20)
        self.entry_api = ctk.CTkEntry(frame, width=400, show="*")
        self.entry_api.pack(pady=5, padx=20)
        if self.api_key: self.entry_api.insert(0, self.api_key)
            
        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text="Show Key", variable=self.show_key_var, command=self.toggle_show_key).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkButton(frame, text="Save & Fetch Models", command=self.save_api_key).pack(pady=10)

        ctk.CTkLabel(frame, text="Select Model:").pack(anchor="w", padx=20, pady=(10, 0))
        self.combo_models = ctk.CTkComboBox(frame, values=self.available_models, width=400)
        self.combo_models.pack(pady=5, padx=20)
        self.combo_models.set("models/gemini-1.5-flash")
        
        ctk.CTkButton(frame, text="Refresh Models", width=100, command=lambda: threading.Thread(target=self.refresh_models, daemon=True).start()).pack(pady=5)
        
        self.btn_test = ctk.CTkButton(frame, text="Test Selected Model", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.test_api_key)
        self.btn_test.pack(pady=20)

    def setup_main_tab(self):
        self.tab_main.grid_columnconfigure(0, weight=1)
        
        # Path
        frame_path = ctk.CTkFrame(self.tab_main)
        frame_path.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame_path, text="Project Folder:").pack(side="left", padx=10)
        self.path_var = ctk.StringVar(value="Not Selected")
        self.entry_path = ctk.CTkEntry(frame_path, textvariable=self.path_var, width=300, state="readonly")
        self.entry_path.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        ctk.CTkButton(frame_path, text="Browse", width=80, command=self.browse_folder).pack(side="left", padx=10)

        # Repos
        self.repo_tabs = ctk.CTkTabview(self.tab_main, height=150)
        self.repo_tabs.pack(fill="x", padx=10, pady=5)
        self.tab_exist = self.repo_tabs.add("Existing Remote")
        self.tab_new = self.repo_tabs.add("Create New Remote")
        
        ctk.CTkLabel(self.tab_exist, text="Select GitHub Repository:").pack(pady=5)
        self.combo_repos = ctk.CTkComboBox(self.tab_exist, values=["Loading..."], width=300)
        self.combo_repos.pack(pady=10)
        
        frame_new = ctk.CTkFrame(self.tab_new, fg_color="transparent")
        frame_new.pack(pady=10)
        self.entry_repo_name = ctk.CTkEntry(frame_new, placeholder_text="Repository Name", width=250)
        self.entry_repo_name.pack(side="left", padx=10)
        
        self.privacy_var = ctk.StringVar(value="private")
        ctk.CTkRadioButton(frame_new, text="Private", variable=self.privacy_var, value="private").pack(side="left", padx=10)
        ctk.CTkRadioButton(frame_new, text="Public", variable=self.privacy_var, value="public").pack(side="left", padx=10)

        # Commit
        frame_commit = ctk.CTkFrame(self.tab_main)
        frame_commit.pack(fill="x", padx=10, pady=10)
        
        row1 = ctk.CTkFrame(frame_commit, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row1, text="Commit Message", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        self.commit_mode_var = ctk.BooleanVar(value=False)
        self.check_ai_commit = ctk.CTkCheckBox(row1, text="Generate with Gemini", variable=self.commit_mode_var, command=self.toggle_commit_input)
        self.check_ai_commit.pack(side="right")
        
        self.entry_commit = ctk.CTkEntry(frame_commit, placeholder_text="Enter commit message...")
        self.entry_commit.pack(fill="x", padx=10, pady=(0, 10))
        self.entry_commit.insert(0, "Update")

        # Readme
        frame_readme = ctk.CTkFrame(self.tab_main)
        frame_readme.pack(fill="x", padx=10, pady=5)
        
        row2 = ctk.CTkFrame(frame_readme, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="README.md", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        self.readme_mode_var = ctk.StringVar(value="Do nothing")
        self.opt_readme = ctk.CTkOptionMenu(row2, variable=self.readme_mode_var, values=["Do nothing", "Create Minimal", "Generate with Gemini"])
        self.opt_readme.pack(side="right")

        # Push
        self.btn_push = ctk.CTkButton(self.tab_main, text="Push to GitHub", height=50, font=("Segoe UI", 16, "bold"), fg_color="#2EA44F", hover_color="#2C974B", command=self.on_push)
        self.btn_push.pack(fill="x", padx=10, pady=20)

    # --- Logic ---

    def log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", f"> {message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")
        self.update_idletasks()

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
            
        threading.Thread(target=run_test, daemon=True).start()

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.working_dir = path
            self.path_var.set(path)
            self.detect_git_state()

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
                self.combo_repos.configure(values=names)
                if names: self.combo_repos.set(names[0])
            else:
                self.log("Warning: Could not fetch repos. Ensure 'gh' CLI is installed.")
        except Exception as e:
            self.log(f"Repo fetch error: {e}")

    def run_cmd(self, args, ignore_error=False):
        self.log(f"Exec: {' '.join(args)}")
        try:
            res = subprocess.run(args, cwd=self.working_dir, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return res.stdout.strip()
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
        self.is_running = True
        self.btn_push.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_push_workflow, daemon=True).start()

    def run_push_workflow(self):
        try:
            use_ai_commit = self.commit_mode_var.get()
            use_ai_readme = self.readme_mode_var.get() == "Generate with Gemini"
            model_name = self.combo_models.get()

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
                msg = self.entry_commit.get()
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
            readme_opt = self.readme_mode_var.get()
            
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
            current_tab = self.repo_tabs.get()
            
            if current_tab == "Create New Remote":
                repo_name = self.entry_repo_name.get().strip()
                if not repo_name: raise Exception("Repository name is required.")
                visibility = f"--{self.privacy_var.get()}"
                
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
                selected = self.combo_repos.get()
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
            self.show_success(repo_url)

        except Exception as e:
            err_msg = traceback.format_exc()
            self.log(f"CRITICAL ERROR:\n{err_msg}")
            messagebox.showerror("Error", f"An error occurred. Check log.\n{str(e)}")
        finally:
            self.is_running = False
            self.btn_push.configure(state="normal", text="Push to GitHub")

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
