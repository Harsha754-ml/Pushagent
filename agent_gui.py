import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import sys
import os
import threading
import json
import requests
import keyring
import re
import shutil
import glob

# Configuration
APP_NAME = "PushAgent"
KEYRING_SERVICE = "PushAgent_GeminiAPI"
GEMINI_MODEL = "gemini-1.5-flash"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"

    def generate(self, prompt):
        if not self.api_key:
            return "Error: No API Key provided."
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            return f"API Error: {str(e)}"

class PushAgentApp(ctk.CTk):
    def __init__(self, start_path=None):
        super().__init__()
        
        self.title("GitHub Push Agent (AI Powered)")
        self.geometry("600x750")
        self.resizable(False, False)
        
        self.working_dir = start_path
        
        # Load API Key: Try file first (user preference), then keyring
        self.api_key = ""
        key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_key.txt")
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                self.api_key = f.read().strip()
        
        if not self.api_key:
            self.api_key = keyring.get_password(KEYRING_SERVICE, "user_key") or ""
            
        self.repo_list = []
        self.is_running = False

        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Header & Path
        self.frame_header = ctk.CTkFrame(self)
        self.frame_header.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        
        self.path_var = ctk.StringVar(value=self.working_dir if self.working_dir else "Not Selected")
        self.entry_path = ctk.CTkEntry(self.frame_header, textvariable=self.path_var, width=400, state="readonly")
        self.entry_path.pack(side="left", padx=10, pady=10)
        
        self.btn_browse = ctk.CTkButton(self.frame_header, text="Browse", width=80, command=self.browse_folder)
        self.btn_browse.pack(side="left", padx=5)

        # 2. API Key Section
        self.frame_api = ctk.CTkFrame(self)
        self.frame_api.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        self.lbl_api = ctk.CTkLabel(self.frame_api, text="Gemini API Key:")
        self.lbl_api.pack(side="left", padx=10, pady=5)
        
        self.entry_api = ctk.CTkEntry(self.frame_api, show="*", width=250)
        self.entry_api.pack(side="left", padx=5)
        if self.api_key: self.entry_api.insert(0, self.api_key)
        
        self.btn_save_key = ctk.CTkButton(self.frame_api, text="Save Key", width=80, command=self.save_api_key)
        self.btn_save_key.pack(side="left", padx=5)
        
        self.lbl_api_warn = ctk.CTkLabel(self.frame_api, text="Do not share your key.", text_color="gray", font=("Arial", 10))
        self.lbl_api_warn.pack(side="left", padx=5)

        # 3. Repo Mode
        self.frame_mode = ctk.CTkTabview(self, height=150)
        self.frame_mode.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.tab_exist = self.frame_mode.add("Existing Repo")
        self.tab_new = self.frame_mode.add("New Repo")
        
        # Existing Repo Tab
        self.combo_repos = ctk.CTkComboBox(self.tab_exist, values=["Loading..."], width=300)
        self.combo_repos.pack(pady=20)
        
        # New Repo Tab
        self.entry_repo_name = ctk.CTkEntry(self.tab_new, placeholder_text="Repo Name", width=300)
        self.entry_repo_name.pack(pady=10)
        
        self.privacy_var = ctk.StringVar(value="private")
        self.rad_priv = ctk.CTkRadioButton(self.tab_new, text="Private", variable=self.privacy_var, value="private")
        self.rad_priv.pack(side="left", padx=40)
        self.rad_pub = ctk.CTkRadioButton(self.tab_new, text="Public", variable=self.privacy_var, value="public")
        self.rad_pub.pack(side="left")

        # 4. Content Control (Commit & Readme)
        self.frame_content = ctk.CTkFrame(self)
        self.frame_content.grid(row=3, column=0, padx=15, pady=10, sticky="ew")
        self.frame_content.columnconfigure(1, weight=1)
        
        # Commit Section
        self.lbl_commit = ctk.CTkLabel(self.frame_content, text="Commit Message:", font=("Arial", 12, "bold"))
        self.lbl_commit.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.commit_mode_var = ctk.BooleanVar(value=False)
        self.check_ai_commit = ctk.CTkCheckBox(self.frame_content, text="Generate with Gemini", variable=self.commit_mode_var, command=self.toggle_commit_input)
        self.check_ai_commit.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        self.entry_commit = ctk.CTkEntry(self.frame_content, placeholder_text="Type commit message here...")
        self.entry_commit.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.entry_commit.insert(0, "Update")

        # Readme Section
        self.lbl_readme = ctk.CTkLabel(self.frame_content, text="README.md:", font=("Arial", 12, "bold"))
        self.lbl_readme.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.readme_mode_var = ctk.StringVar(value="none")
        self.opt_readme = ctk.CTkOptionMenu(self.frame_content, variable=self.readme_mode_var, values=["Do nothing", "Create Minimal", "Generate with Gemini"])
        self.opt_readme.grid(row=2, column=1, padx=10, pady=5, sticky="e")

        # 5. Log & Execute
        self.check_push = ctk.CTkCheckBox(self, text="Push immediately after commit")
        self.check_push.select()
        self.check_push.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        self.btn_execute = ctk.CTkButton(self, text="🚀 Execute", height=40, font=("Arial", 14, "bold"), command=self.on_execute)
        self.btn_execute.grid(row=5, column=0, padx=15, pady=10, sticky="ew")
        
        self.textbox_log = ctk.CTkTextbox(self, height=120, font=("Consolas", 10))
        self.textbox_log.grid(row=6, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.textbox_log.configure(state="disabled")

        # Startup Logic
        if not self.working_dir or not os.path.exists(self.working_dir):
            self.browse_folder()
        else:
            self.detect_git_state()
            
        threading.Thread(target=self.fetch_repos, daemon=True).start()

    # --- Logic ---

    def log(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", f"> {message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")
        self.update_idletasks()

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.working_dir = path
            self.path_var.set(path)
            self.detect_git_state()

    def detect_git_state(self):
        if not self.working_dir: return
        
        # Suggest repo name
        folder_name = os.path.basename(os.path.abspath(self.working_dir))
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '-', folder_name).lower()
        self.entry_repo_name.delete(0, "end")
        self.entry_repo_name.insert(0, slug)
        
        # Check if git initialized
        is_git = os.path.isdir(os.path.join(self.working_dir, ".git"))
        if is_git:
            self.frame_mode.set("Existing Repo")
            self.log(f"Detected existing Git repo: {self.working_dir}")
        else:
            self.frame_mode.set("New Repo")
            self.log("No Git repo detected. Select 'New Repo' to initialize.")
            
    def save_api_key(self):
        key = self.entry_api.get().strip()
        if key:
            try:
                keyring.set_password(KEYRING_SERVICE, "user_key", key)
                self.api_key = key
                messagebox.showinfo("Success", "API Key saved securely.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save key: {e}")
                
    def toggle_commit_input(self):
        if self.commit_mode_var.get():
            self.entry_commit.configure(state="disabled", placeholder_text="(AI will generate this)")
        else:
            self.entry_commit.configure(state="normal", placeholder_text="Type commit message here...")

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
                self.log("Failed to fetch repos. Is 'gh' authenticated?")
        except Exception as e:
            self.log(f"Error fetching repos: {e}")

    # --- Execution Logic ---

    def on_execute(self):
        if not self.working_dir:
            messagebox.showerror("Error", "No folder selected.")
            return
        if self.is_running: return
        
        self.is_running = True
        self.btn_execute.configure(state="disabled", text="Processing...")
        threading.Thread(target=self.run_workflow, daemon=True).start()

    def run_cmd(self, args, ignore_error=False):
        self.log(f"Run: {' '.join(args)}")
        try:
            res = subprocess.run(args, cwd=self.working_dir, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() or e.stdout.strip()
            if not ignore_error:
                self.log(f"ERROR: {err}")
                raise Exception(err)
            return None

    def get_file_tree(self):
        ignore_dirs = {'.git', 'node_modules', '.venv', 'build', 'dist', '__pycache__', '.idea', '.vscode'}
        tree = []
        for root, dirs, files in os.walk(self.working_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            level = root.replace(self.working_dir, '').count(os.sep)
            indent = ' ' * 4 * (level)
            tree.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files[:10]: # Limit files per folder to avoid huge context
                tree.append(f"{subindent}{f}")
        return "\n".join(tree[:100]) # Limit total lines

    def run_workflow(self):
        try:
            # 1. Initialize Git
            if not os.path.isdir(os.path.join(self.working_dir, ".git")):
                self.run_cmd(["git", "init", "-b", "main"])
            
            # 2. Smart .gitignore
            gitignore_path = os.path.join(self.working_dir, ".gitignore")
            if not os.path.exists(gitignore_path):
                defaults = []
                if glob.glob(os.path.join(self.working_dir, "*.py")):
                    defaults.extend(["__pycache__/", "*.pyc", ".venv/", ".env"])
                if glob.glob(os.path.join(self.working_dir, "package.json")):
                    defaults.extend(["node_modules/", "dist/", ".env"])
                if defaults:
                    with open(gitignore_path, "w") as f:
                        f.write("\n".join(defaults))
                    self.log("Created .gitignore")

            # 3. Add files
            self.run_cmd(["git", "add", "."])
            
            # Check status
            status = self.run_cmd(["git", "status", "--porcelain"])
            if not status:
                self.log("Nothing to commit.")
                # If remote setup is needed, we continue? No, usually commit is needed first.
                # But if remote is missing, we might want to add it anyway.
            else:
                # 4. Generate Commit Message
                msg = "Update"
                if self.commit_mode_var.get():
                    if not self.api_key: raise Exception("API Key required for AI commit.")
                    diff = self.run_cmd(["git", "diff", "--staged", "--stat"])
                    prompt = f"Generate a concise (max 72 chars), professional git commit message for these changes:\n{diff}"
                    self.log("Generating commit message...")
                    msg = GeminiClient(self.api_key).generate(prompt)
                    self.log(f"AI Commit: {msg}")
                else:
                    msg = self.entry_commit.get() or "Update"
                
                self.run_cmd(["git", "commit", "-m", msg])

            # 5. README Generation
            readme_opt = self.readme_mode_var.get()
            readme_path = os.path.join(self.working_dir, "README.md")
            if readme_opt != "Do nothing" and not os.path.exists(readme_path):
                if readme_opt == "Create Minimal":
                    name = os.path.basename(self.working_dir)
                    with open(readme_path, "w") as f:
                        f.write(f"# {name}\n\nProject initialized via PushAgent.")
                    self.log("Created minimal README.")
                elif readme_opt == "Generate with Gemini":
                    if not self.api_key: raise Exception("API Key required for AI README.")
                    tree = self.get_file_tree()
                    prompt = f"Generate a professional README.md (Markdown) for a project with this structure:\n{tree}\nInclude: Title, Description, Setup, Usage."
                    self.log("Generating README...")
                    content = GeminiClient(self.api_key).generate(prompt)
                    # Filter markdown fences
                    content = content.replace("```markdown", "").replace("```", "")
                    with open(readme_path, "w", encoding='utf-8') as f:
                        f.write(content)
                    self.log("Created AI README.")
                
                # Commit README if created
                self.run_cmd(["git", "add", "README.md"])
                self.run_cmd(["git", "commit", "-m", "Add README"])

            # 6. Remote Setup
            repo_url = ""
            mode = self.frame_mode.get()
            remotes = self.run_cmd(["git", "remote"], ignore_error=True) or ""
            
            if mode == "New Repo":
                repo_name = self.entry_repo_name.get()
                flag = "--private" if self.privacy_var.get() == "private" else "--public"
                
                # Check if already exists on remote to avoid error
                # gh repo view returns 0 if exists
                check_remote = subprocess.run(["gh", "repo", "view", repo_name], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if check_remote.returncode != 0:
                    self.run_cmd(["gh", "repo", "create", repo_name, flag, "--source=.", "--remote=origin"])
                else:
                    self.log(f"Repo {repo_name} exists remotely. Linking...")
                    if "origin" not in remotes:
                        self.run_cmd(["gh", "repo", "view", repo_name, "--web"])
                        # Better to just add remote
                        user = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
                        self.run_cmd(["git", "remote", "add", "origin", f"https://github.com/{user}/{repo_name}.git"])

            else: # Existing Repo
                selected = self.combo_repos.get()
                repo = next((r for r in self.repo_list if r['name'] == selected), None)
                if not repo: raise Exception("Invalid repo selected")
                repo_url = repo['url']
                
                if "origin" in remotes:
                    self.run_cmd(["git", "remote", "set-url", "origin", repo_url])
                else:
                    self.run_cmd(["git", "remote", "add", "origin", repo_url])

            # Get final URL
            if not repo_url:
                repo_url = self.run_cmd(["git", "remote", "get-url", "origin"])

            # 7. Push
            if self.check_push.get():
                self.run_cmd(["git", "push", "-u", "origin", "main"])

            self.show_success(repo_url)

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.is_running = False
            self.btn_execute.configure(state="normal", text="🚀 Execute")

    def show_success(self, url):
        res = messagebox.askyesno("Success", "Repo updated successfully!\n\nOpen repository in browser?")
        if res:
            import webbrowser
            webbrowser.open(url)
        # Optional: Close app
        # self.destroy()

if __name__ == "__main__":
    path_arg = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        path_arg = sys.argv[1]
    
    app = PushAgentApp(path_arg)
    app.mainloop()
