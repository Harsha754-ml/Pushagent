import customtkinter as ctk
import subprocess
import sys
import os
import threading
import shutil
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import webbrowser
import re

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PushAgentApp(ctk.CTk):
    def __init__(self, start_path=None):
        super().__init__()
        
        self.title("GitHub Push Agent")
        self.geometry("500x550")
        self.resizable(False, False)
        
        self.working_dir = start_path
        if not self.working_dir or not os.path.exists(self.working_dir):
            self.working_dir = filedialog.askdirectory(title="Select Project Folder")
            if not self.working_dir:
                sys.exit(0)
                
        self.repo_list = []
        self.is_git_initialized = os.path.isdir(os.path.join(self.working_dir, ".git"))
        
        # --- UI Layout ---
        self.grid_columnconfigure(0, weight=1)
        
        # Path Label
        self.lbl_path = ctk.CTkLabel(self, text=f"📂 {self.truncate_path(self.working_dir)}", font=("Arial", 12, "bold"))
        self.lbl_path.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Repo Type Selection
        self.repo_type_var = ctk.StringVar(value="Existing" if self.is_git_initialized else "New")
        self.frame_type = ctk.CTkFrame(self)
        self.frame_type.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.rad_new = ctk.CTkRadioButton(self.frame_type, text="New Repo", variable=self.repo_type_var, value="New", command=self.update_ui_state)
        self.rad_new.grid(row=0, column=0, padx=20, pady=10)
        self.rad_exist = ctk.CTkRadioButton(self.frame_type, text="Existing Repo", variable=self.repo_type_var, value="Existing", command=self.update_ui_state)
        self.rad_exist.grid(row=0, column=1, padx=20, pady=10)

        # Dynamic Content Frame
        self.frame_dynamic = ctk.CTkFrame(self)
        self.frame_dynamic.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_dynamic.grid_columnconfigure(1, weight=1)
        
        # New Repo Fields
        self.lbl_name = ctk.CTkLabel(self.frame_dynamic, text="Repo Name:")
        self.entry_name = ctk.CTkEntry(self.frame_dynamic, placeholder_text="my-awesome-project")
        
        self.lbl_privacy = ctk.CTkLabel(self.frame_dynamic, text="Visibility:")
        self.switch_privacy = ctk.CTkSwitch(self.frame_dynamic, text="Private")
        self.switch_privacy.select() # Default to Private
        
        # Existing Repo Fields
        self.lbl_select = ctk.CTkLabel(self.frame_dynamic, text="Select Repo:")
        self.combo_repos = ctk.CTkComboBox(self.frame_dynamic, values=["Loading..."])
        
        # Common Options
        self.check_readme = ctk.CTkCheckBox(self, text="Create README.md")
        self.check_readme.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        
        self.entry_commit = ctk.CTkEntry(self, placeholder_text="Commit message")
        self.entry_commit.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        self.entry_commit.insert(0, "Initial commit" if not self.is_git_initialized else "Update")
        
        self.check_push = ctk.CTkCheckBox(self, text="Push immediately?")
        self.check_push.select()
        self.check_push.grid(row=5, column=0, padx=20, pady=10, sticky="w")
        
        # Execute Button
        self.btn_execute = ctk.CTkButton(self, text="🚀 Execute", command=self.on_execute, height=40, font=("Arial", 14, "bold"))
        self.btn_execute.grid(row=6, column=0, padx=20, pady=20, sticky="ew")
        
        self.update_ui_state()
        
        # Start fetching repos in background if needed
        threading.Thread(target=self.fetch_repos, daemon=True).start()

    def truncate_path(self, path):
        if len(path) > 40:
            return "..." + path[-37:]
        return path

    def update_ui_state(self):
        # Clear dynamic frame
        for widget in self.frame_dynamic.winfo_children():
            widget.grid_forget()
            
        mode = self.repo_type_var.get()
        
        if mode == "New":
            self.lbl_name.grid(row=0, column=0, padx=10, pady=10, sticky="w")
            self.entry_name.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
            self.lbl_privacy.grid(row=1, column=0, padx=10, pady=10, sticky="w")
            self.switch_privacy.grid(row=1, column=1, padx=10, pady=10, sticky="w")
            
            # Suggest name
            folder_name = os.path.basename(os.path.abspath(self.working_dir))
            clean_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', folder_name).lower()
            if not self.entry_name.get():
                self.entry_name.delete(0, "end")
                self.entry_name.insert(0, clean_name)
                
        else:
            self.lbl_select.grid(row=0, column=0, padx=10, pady=10, sticky="w")
            self.combo_repos.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Check readme availability
        readme_exists = os.path.exists(os.path.join(self.working_dir, "README.md"))
        if readme_exists:
            self.check_readme.deselect()
            self.check_readme.configure(state="disabled")
        else:
            self.check_readme.configure(state="normal")

    def fetch_repos(self):
        try:
            # Check if gh is installed
            subprocess.run(["gh", "--version"], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            result = subprocess.run(
                ["gh", "repo", "list", "--json", "name,sshUrl,url", "--limit", "100"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                self.repo_list = data
                repo_names = [r['name'] for r in data]
                self.combo_repos.configure(values=repo_names)
                if repo_names:
                    self.combo_repos.set(repo_names[0])
            else:
                print("Error fetching repos:", result.stderr)
        except FileNotFoundError:
            self.combo_repos.configure(values=["Error: 'gh' CLI not found"])
        except Exception as e:
            print(e)

    def run_cmd(self, args, cwd=None):
        if cwd is None:
            cwd = self.working_dir
        try:
            subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Command failed:\n{' '.join(args)}\n\n{e.stderr}")
            return False

    def on_execute(self):
        self.btn_execute.configure(state="disabled", text="Working...")
        self.update_idletasks()
        
        try:
            # 1. Init Git if needed
            if not os.path.isdir(os.path.join(self.working_dir, ".git")):
                if not self.run_cmd(["git", "init", "-b", "main"]): return

            # 2. Create README
            if self.check_readme.get():
                readme_path = os.path.join(self.working_dir, "README.md")
                project_name = os.path.basename(self.working_dir)
                with open(readme_path, "w") as f:
                    f.write(f"# {project_name}\n")

            # 3. Add and Commit
            if not self.run_cmd(["git", "add", "."]): return
            
            msg = self.entry_commit.get() or "Update"
            # Check if there are changes to commit
            status = subprocess.run(["git", "status", "--porcelain"], cwd=self.working_dir, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if status.stdout.strip():
                if not self.run_cmd(["git", "commit", "-m", msg]): return

            repo_url = ""
            
            # 4. Handle Remote
            mode = self.repo_type_var.get()
            if mode == "New":
                repo_name = self.entry_name.get()
                is_private = self.switch_privacy.get() == 1
                flag = "--private" if is_private else "--public"
                
                # Create repo on GH
                if not self.run_cmd(["gh", "repo", "create", repo_name, flag, "--source=.", "--remote=origin"]): return
                
                # Get URL
                res = subprocess.run(["gh", "repo", "view", repo_name, "--json", "url"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if res.returncode == 0:
                    import json
                    repo_url = json.loads(res.stdout)['url']
                    
            else: # Existing
                selected_name = self.combo_repos.get()
                selected_repo = next((r for r in self.repo_list if r['name'] == selected_name), None)
                if not selected_repo:
                    messagebox.showerror("Error", "Invalid repo selected")
                    return
                
                repo_url = selected_repo['url']
                ssh_url = selected_repo['sshUrl'] # Prefer SSH if available/setup, but 'gh' usually handles auth well.
                # Actually, let's use the URL provided by gh list
                
                # Set origin
                # Check if origin exists
                remotes = subprocess.run(["git", "remote"], cwd=self.working_dir, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
                if "origin" in remotes:
                    self.run_cmd(["git", "remote", "set-url", "origin", repo_url])
                else:
                    self.run_cmd(["git", "remote", "add", "origin", repo_url])

            # 5. Push
            if self.check_push.get():
                if not self.run_cmd(["git", "push", "-u", "origin", "main"]): return

            # Success
            self.show_success(repo_url)
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_execute.configure(state="normal", text="🚀 Execute")

    def show_success(self, url):
        top = ctk.CTkToplevel(self)
        top.title("Success")
        top.geometry("400x200")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        
        lbl = ctk.CTkLabel(top, text="Operation Completed Successfully!", font=("Arial", 14, "bold"), text_color="green")
        lbl.pack(pady=20)
        
        btn_open_repo = ctk.CTkButton(top, text="Open Repo (Web)", command=lambda: webbrowser.open(url))
        btn_open_repo.pack(pady=10)
        
        btn_open_folder = ctk.CTkButton(top, text="Open Local Folder", command=lambda: os.startfile(self.working_dir))
        btn_open_folder.pack(pady=10)
        
        # Close main app when success dialog closes? Or just close main app now.
        top.protocol("WM_DELETE_WINDOW", self.destroy)
        # top.focus()

if __name__ == "__main__":
    path_arg = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        path_arg = sys.argv[1]
        
    app = PushAgentApp(path_arg)
    app.mainloop()