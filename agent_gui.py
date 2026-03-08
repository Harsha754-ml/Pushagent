import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import os
import sys
import threading
import socket
import keyring
import json
import re
import traceback
import queue
import time
import shutil
from google import genai
from google.genai import types

# --- CONFIGURATION ---
APP_NAME = "PushAgent"
KEYRING_SERVICE = "PushAgent_GeminiAPI"
KEYRING_USER = "user_key"
IPC_PORT = 65432
MAX_FILE_TREE_ENTRIES = 30
MAX_FILES_PER_DIR = 10
GEMINI_MODEL = "models/gemini-2.0-flash"

# --- BACKEND SERVICES ---

class GitError(Exception):
    """Raised when a git command fails."""
    pass

class GitService:
    @staticmethod
    def run(args, cwd):
        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            result = subprocess.run(
                args, cwd=cwd, env=env,
                capture_output=True, text=True, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitError(e.stderr.strip() or e.stdout.strip())

    @staticmethod
    def get_status(cwd):
        return GitService.run(["git", "status", "--porcelain"], cwd)

    @staticmethod
    def get_diff(cwd):
        return GitService.run(["git", "diff", "--staged", "--stat"], cwd) or "No changes staged."

    @staticmethod
    def get_remote(cwd):
        try:
            return GitService.run(["git", "remote", "get-url", "origin"], cwd)
        except GitError:
            return None

    @staticmethod
    def get_branch(cwd):
        try:
            return GitService.run(["git", "branch", "--show-current"], cwd)
        except GitError:
            return "main"

class GeminiService:
    def __init__(self):
        self.api_key = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(api_version="v1"))
            except Exception as e:
                print(f"[PushAgent] Gemini init failed: {e}")

    def generate_commit_message(self, diff_text):
        if not self.client:
            return "Update (AI Key Missing)"
        try:
            prompt = (
                "Write a concise git commit message (under 60 chars) for this diff. "
                "Return ONLY the message, no quotes or backticks:\n"
                f"{diff_text}"
            )
            res = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            return res.text.strip().replace('"', '').replace("`", "")
        except Exception as e:
            return f"Update (AI Error: {str(e)[:40]})"

    def generate_readme(self, file_tree, project_name):
        if not self.client:
            return f"# {project_name}"
        try:
            prompt = (
                f"Create a minimalist, professional README.md for a project named '{project_name}' "
                f"with this structure:\n{file_tree}\n\nKeep it concise."
            )
            res = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            text = res.text.strip()
            # Strip wrapping markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("\n", 1)[0]
            return text
        except Exception as e:
            print(f"[PushAgent] README generation failed: {e}")
            return f"# {project_name}"

# --- STATE MANAGEMENT ---

class ProjectContext:
    """Holds the state for a single project session."""
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.is_git = False
        self.remote_url = None
        self.branch = None
        self.has_changes = False
        self.ai_commit_msg = ""
        self.files = []

    def load(self):
        """Analyzes the folder synchronously."""
        if not os.path.exists(os.path.join(self.path, ".git")):
            self.is_git = False
            return

        self.is_git = True
        self.remote_url = GitService.get_remote(self.path)
        self.branch = GitService.get_branch(self.path)

        status = GitService.get_status(self.path)
        self.has_changes = bool(status.strip())

        # Build file list for AI context
        ignore = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', '.eggs', 'build'}
        self.files = []
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if d not in ignore]
            for f in files[:MAX_FILES_PER_DIR]:
                self.files.append(os.path.join(root, f).replace(self.path, "").lstrip(os.sep))
            if len(self.files) >= MAX_FILE_TREE_ENTRIES:
                break

# --- GUI APPLICATION ---

def sanitize_repo_name(name):
    """Sanitize repo name to prevent command injection and invalid GitHub names."""
    name = re.sub(r'[^a-zA-Z0-9._-]', '-', name)
    name = re.sub(r'-+', '-', name).strip('-.')
    return name or "my-repo"

class PushAgentWizard(ctk.CTk):
    def __init__(self, start_path=None):
        # SINGLE INSTANCE CHECK
        self.ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.ipc_socket.bind(('127.0.0.1', IPC_PORT))
            self.ipc_socket.listen(1)
        except OSError:
            self._send_ipc(start_path)
            sys.exit(0)

        super().__init__()

        # UI Setup
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("PushAgent")
        self.geometry("600x700")
        self.resizable(False, False)

        self.project = None
        self.gemini = GeminiService()
        self.queue = queue.Queue()

        # Container for Wizard Steps
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Start IPC Listener
        threading.Thread(target=self._ipc_listener, daemon=True).start()
        self.after(100, self._process_queue)

        # Initial Load
        if start_path:
            self.load_project(start_path)
        else:
            self.show_welcome()

    # --- CORE LOGIC ---

    def load_project(self, path):
        """The brain. Resets everything and loads new context."""
        if not path or not os.path.isdir(path):
            return

        self.project = ProjectContext(path)
        self.show_loading()

        def _analyze():
            try:
                self.project.load()
                if not self.project.is_git or not self.project.remote_url:
                    self.queue.put(("SHOW_SETUP", None))
                else:
                    self.queue.put(("PREPARE_COMMIT", None))
            except Exception as e:
                self.queue.put(("ERROR", str(e)))

        threading.Thread(target=_analyze, daemon=True).start()

    def prepare_commit_data(self):
        """Background task to stage files and fetch AI commit message."""
        def _fetch():
            try:
                cwd = self.project.path
                GitService.run(["git", "add", "."], cwd)
                diff = GitService.get_diff(cwd)
                self.project.ai_commit_msg = self.gemini.generate_commit_message(diff)
                self.queue.put(("SHOW_COMMIT", None))
            except Exception as e:
                self.queue.put(("ERROR", str(e)))
        threading.Thread(target=_fetch, daemon=True).start()

    # --- GUI STEPS (WIZARD) ---

    def clear_ui(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_loading(self):
        self.clear_ui()
        lbl = ctk.CTkLabel(self.container, text=f"Analyzing\n{self.project.name}...", font=("Arial", 20))
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        progress = ctk.CTkProgressBar(self.container, width=200)
        progress.place(relx=0.5, rely=0.6, anchor="center")
        progress.start()

    def show_welcome(self):
        self.clear_ui()
        ctk.CTkLabel(self.container, text="PushAgent Ready", font=("Arial", 24, "bold")).pack(pady=40)
        ctk.CTkLabel(
            self.container,
            text="Press Ctrl+Shift+G in Explorer\nor select a folder below.",
            font=("Arial", 14)
        ).pack(pady=20)
        ctk.CTkButton(self.container, text="Browse Folder", command=self._browse).pack(pady=10)

        if not self.gemini.api_key:
            self._show_api_input()

    def _show_api_input(self):
        f = ctk.CTkFrame(self.container)
        f.pack(pady=20, fill="x")
        ctk.CTkLabel(f, text="Enter Gemini API Key (First Run):").pack(pady=5)
        self.ent_key = ctk.CTkEntry(f, show="*")
        self.ent_key.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(f, text="Save Key", command=self._save_key).pack(pady=10)

    def show_setup(self):
        """Screen 1: Setup New Repo"""
        self.clear_ui()

        ctk.CTkLabel(self.container, text="New Repository", font=("Arial", 22, "bold")).pack(pady=(10, 5))
        ctk.CTkLabel(
            self.container, text=self.project.path,
            font=("Arial", 10), text_color="gray"
        ).pack(pady=5)

        ctk.CTkLabel(self.container, text="This folder is not connected to GitHub.").pack(pady=20)

        self.var_repo_name = ctk.StringVar(value=sanitize_repo_name(self.project.name))
        ctk.CTkEntry(
            self.container, textvariable=self.var_repo_name,
            placeholder_text="Repo Name"
        ).pack(pady=10, fill="x")

        self.var_private = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.container, text="Private Repository", variable=self.var_private).pack(pady=10)

        ctk.CTkButton(
            self.container, text="Create & Link Repo",
            command=self._run_create_repo, fg_color="green"
        ).pack(pady=20, fill="x")

    def show_commit(self):
        """Screen 2: Review & Push"""
        self.clear_ui()

        # Header
        top = ctk.CTkFrame(self.container, fg_color="transparent")
        top.pack(fill="x", pady=5)
        ctk.CTkLabel(top, text=self.project.name, font=("Arial", 20, "bold")).pack(side="left")
        ctk.CTkLabel(
            top, text=f"({self.project.branch})",
            font=("Arial", 12), text_color="gray"
        ).pack(side="left", padx=10, pady=5)

        # Branch warning
        if self.project.branch not in ('main', 'master'):
            ctk.CTkLabel(
                self.container,
                text=f"Warning: Pushing to '{self.project.branch}'",
                text_color="yellow", font=("Arial", 12, "bold")
            ).pack(pady=5)

        # Commit Message
        ctk.CTkLabel(self.container, text="Commit Message (AI Generated)", anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_commit = ctk.CTkTextbox(self.container, height=80)
        self.entry_commit.pack(fill="x", pady=5)
        self.entry_commit.insert("0.0", self.project.ai_commit_msg)

        # Options
        readme_exists = os.path.exists(os.path.join(self.project.path, "README.md"))
        self.var_readme = ctk.BooleanVar(value=not readme_exists)
        readme_label = "Generate README.md" if not readme_exists else "Regenerate README.md (backup saved)"
        ctk.CTkCheckBox(self.container, text=readme_label, variable=self.var_readme).pack(pady=10, anchor="w")

        # Push Button
        self.btn_push = ctk.CTkButton(
            self.container, text="Push Changes", height=50,
            font=("Arial", 16, "bold"), fg_color="green",
            command=self._run_push
        )
        self.btn_push.pack(fill="x", pady=20, side="bottom")

    def show_success(self, url):
        self.clear_ui()
        ctk.CTkLabel(
            self.container, text="Success!",
            font=("Arial", 28, "bold"), text_color="#4ade80"
        ).pack(pady=40)
        ctk.CTkLabel(self.container, text="Code pushed to GitHub.").pack(pady=10)

        if url:
            ctk.CTkButton(
                self.container, text="Open Repository",
                command=lambda: os.startfile(url)
            ).pack(pady=10, fill="x")
        ctk.CTkButton(self.container, text="Close", command=self.destroy, fg_color="gray").pack(pady=10, fill="x")

    # --- ACTIONS ---

    def _save_key(self):
        k = self.ent_key.get().strip()
        if not k:
            messagebox.showwarning("Missing Key", "Please enter your Gemini API key.")
            return
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, k)
        self.gemini = GeminiService()
        if self.gemini.client:
            messagebox.showinfo("Saved", "API key saved successfully.")
        else:
            messagebox.showwarning("Warning", "Key saved but could not initialize Gemini client. Check the key.")
        self.show_welcome()

    def _browse(self):
        p = filedialog.askdirectory()
        if p:
            self.load_project(p)

    def _run_create_repo(self):
        raw_name = self.var_repo_name.get()
        name = sanitize_repo_name(raw_name)
        if name != raw_name:
            self.var_repo_name.set(name)

        is_priv = self.var_private.get()

        def _work():
            try:
                cwd = self.project.path
                if not os.path.exists(os.path.join(cwd, ".git")):
                    GitService.run(["git", "init", "-b", "main"], cwd)

                # Check gh auth
                try:
                    GitService.run(["gh", "auth", "status"], cwd)
                except GitError:
                    raise GitError("GitHub CLI (gh) not logged in. Run 'gh auth login' in terminal.")

                vis = "--private" if is_priv else "--public"
                GitService.run(["gh", "repo", "create", name, vis, "--source=.", "--remote=origin"], cwd)

                self.project.load()
                self.queue.put(("PREPARE_COMMIT", None))
            except Exception as e:
                self.queue.put(("ERROR", f"Repo Creation Failed: {e}"))

        self.show_loading()
        threading.Thread(target=_work, daemon=True).start()

    def _run_push(self):
        msg = self.entry_commit.get("0.0", "end").strip()
        if not msg:
            messagebox.showwarning("Empty Message", "Please enter a commit message.")
            return

        gen_readme = self.var_readme.get()
        branch = self.project.branch or "main"

        def _work():
            try:
                cwd = self.project.path

                # README generation with backup
                if gen_readme:
                    readme_path = os.path.join(cwd, "README.md")
                    if os.path.exists(readme_path):
                        backup_path = os.path.join(cwd, "README.md.bak")
                        shutil.copy2(readme_path, backup_path)
                    content = self.gemini.generate_readme("\n".join(self.project.files), self.project.name)
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    GitService.run(["git", "add", "README.md"], cwd)

                # Stage and commit
                GitService.run(["git", "add", "."], cwd)
                if GitService.get_status(cwd):
                    GitService.run(["git", "commit", "-m", msg], cwd)

                # Push using actual branch name
                try:
                    GitService.run(["git", "push", "-u", "origin", branch], cwd)
                except GitError:
                    GitService.run(["git", "pull", "--rebase", "origin", branch], cwd)
                    GitService.run(["git", "push", "-u", "origin", branch], cwd)

                url = GitService.get_remote(cwd)
                self.queue.put(("SUCCESS", url))

            except Exception as e:
                self.queue.put(("ERROR", f"Push Failed: {e}"))

        self.btn_push.configure(state="disabled", text="Pushing...")
        threading.Thread(target=_work, daemon=True).start()

    # --- INFRASTRUCTURE ---

    def _process_queue(self):
        try:
            while True:
                action, payload = self.queue.get_nowait()
                if action == "SHOW_SETUP":
                    self.show_setup()
                elif action == "PREPARE_COMMIT":
                    self.prepare_commit_data()
                elif action == "SHOW_COMMIT":
                    self.show_commit()
                elif action == "SUCCESS":
                    self.show_success(payload)
                elif action == "LOAD_PROJECT":
                    self.load_project(payload)
                elif action == "ERROR":
                    messagebox.showerror("Error", payload)
                    self.show_welcome()
        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    def _ipc_listener(self):
        while True:
            try:
                conn, _ = self.ipc_socket.accept()
                data = conn.recv(1024).decode().strip()
                conn.close()
                if data == "DETECT":
                    data = self._get_active_explorer()
                if data:
                    # Route through queue for thread safety
                    self.queue.put(("LOAD_PROJECT", data))
            except OSError:
                break

    def _send_ipc(self, msg):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', IPC_PORT))
            s.sendall((msg if msg else "DETECT").encode())
            s.close()
        except OSError:
            pass

    def _get_active_explorer(self):
        try:
            import win32gui, win32com.client
            hwnd = win32gui.GetForegroundWindow()
            shell = win32com.client.Dispatch("Shell.Application")
            for w in shell.Windows():
                if w.HWND == hwnd:
                    return w.Document.Folder.Self.Path
        except Exception:
            return None
        return None

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else None
    app = PushAgentWizard(start)
    app.mainloop()
