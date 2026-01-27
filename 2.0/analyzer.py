import os
import pathlib

class ProjectAnalyzer:
    def __init__(self):
        self.supported_extensions = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md'}
        self.max_snippet_length = 2000

    def scan_project(self, root_path):
        """
        Scans the project folder to build a file tree and extract code snippets.
        Determines the project type based on file presence.
        """
        file_tree = []
        code_snippets = {}
        has_py = False
        has_package_json = False
        has_html = False
        
        root_path = pathlib.Path(root_path)

        for root, dirs, files in os.walk(root_path):
            # Skip common ignore dirs
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode'}]
            
            rel_root = pathlib.Path(root).relative_to(root_path)
            
            for file in files:
                file_path = pathlib.Path(root) / file
                rel_path = rel_root / file
                file_tree.append(str(rel_path))
                
                # Type detection markers
                if file.endswith('.py'):
                    has_py = True
                if file == 'package.json':
                    has_package_json = True
                if file.endswith('.html') or file.endswith('.css'):
                    has_html = True

                # content extraction
                if file_path.suffix in self.supported_extensions:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(self.max_snippet_length)
                            code_snippets[str(rel_path)] = content
                    except Exception:
                        pass

        # Determine Project Type
        project_type = "Unknown"
        if has_py:
            project_type = "Python"
        elif has_package_json:
            project_type = "Node.js"
        elif has_html and not has_py and not has_package_json:
            project_type = "Web (Static)"

        return {
            "tree": file_tree,
            "snippets": code_snippets,
            "type": project_type
        }