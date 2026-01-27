import requests
import json
import pathlib

class ReadmeGenerator:
    def __init__(self, api_url="http://localhost:11434"):
        self.api_url = api_url

    def get_models(self):
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException:
            return []

    def generate(self, model, project_data, audit_results, root_path):
        prompt = self._build_prompt(project_data, audit_results)
        
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=180
            )
            response.raise_for_status()
            result = response.json()
            readme_content = result.get('response', '')
            
            if not readme_content:
                return False, "Empty response from LLM"

            self._save_readme(root_path, readme_content)
            return True, "README.md generated successfully."
            
        except requests.exceptions.RequestException as e:
            return False, f"Ollama API Error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def _save_readme(self, root_path, content):
        path = pathlib.Path(root_path) / "README.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _build_prompt(self, data, audit_results):
        tree_str = "\n".join(data['tree'])
        
        snippets_str = ""
        items = list(data['snippets'].items())
        for name, code in items[:10]:
            snippets_str += f"\nFile: {name}\n```\n{code}\n```\n"

        return (
            "You are analyzing a real software project.\n\n"
            "Write a PROFESSIONAL GitHub README for a production-quality tool.\n\n"
            "Base everything ONLY on the provided code and structure.\n\n"
            "FIRST PARAGRAPH:\n"
            "In one sentence, define what this software IS and what problem it solves.\n\n"
            "Then include sections:\n\n"
            "## What This Tool Does\n"
            "Explain real functionality in plain English.\n\n"
            "## How It Works (Architecture)\n"
            "Describe roles of main scripts/modules.\n\n"
            "## Installation\n"
            "List exact Python dependencies if visible.\n"
            "Include:\n"
            "pip install customtkinter requests\n\n"
            "## How to Run\n"
            "Assume main entry is app.py unless proven otherwise.\n\n"
            "## Technologies Used\n"
            "Infer from imports.\n\n"
            "## Project Structure\n"
            "Explain purpose of key files.\n\n"
            "## Why This Tool Is Useful\n"
            "Explain practical value.\n\n"
            "Rules:\n"
            "- No generic tutorial phrases\n"
            "- No placeholders\n"
            "- No “Feature 1”\n"
            "- No guessing features not supported by code\n"
            "- If uncertain, say \"Based on available code\"\n\n"
            f"Project Type: {data['type']}\n\n"
            "Audit:\n"
            f".gitignore: {audit_results['gitignore_status']}\n"
            f"requirements.txt: {audit_results['requirements_status']}\n\n"
            "File Tree:\n"
            f"{tree_str}\n\n"
            "Code:\n"
            f"{snippets_str}\n"
        )
