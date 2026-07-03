import os
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml
from jinja2 import Template


@dataclass
class PromptVersion:
    version: str
    checksum: str
    last_updated: str


@dataclass
class LoadedPrompt:
    template_content: str
    metadata: Dict[str, Any]
    version: Optional[PromptVersion] = None

    def render(self, **kwargs: Any) -> str:
        """Render prompt template using Jinja2 rendering."""
        template = Template(self.template_content)
        return template.render(**kwargs)


class PromptLoader:
    """Lazily loads and parses markdown prompt templates with front-matter.
    
    Example template format:
    ---
    version: 1.0.0
    temperature: 0.1
    system_instruction: You are an OCR extraction assistant.
    ---
    Please extract details from the following receipt:
    {{ receipt_text }}
    """

    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, LoadedPrompt] = {}

    def load_prompt(self, name: str) -> LoadedPrompt:
        """Loads and caches the prompt from the specified file name."""
        if name in self._cache:
            return self._cache[name]

        file_path = os.path.join(self.prompts_dir, f"{name}.md")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML front-matter if present
        metadata: Dict[str, Any] = {}
        template_content = content
        
        front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if front_matter_match:
            front_matter_str = front_matter_match.group(1)
            try:
                metadata = yaml.safe_load(front_matter_str) or {}
            except Exception:
                pass
            template_content = content[front_matter_match.end():]

        # Calculate a simple checksum
        import hashlib
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        
        version_info = None
        if "version" in metadata:
            version_info = PromptVersion(
                version=str(metadata["version"]),
                checksum=checksum,
                last_updated="unknown"
            )

        loaded = LoadedPrompt(
            template_content=template_content,
            metadata=metadata,
            version=version_info
        )
        self._cache[name] = loaded
        return loaded
