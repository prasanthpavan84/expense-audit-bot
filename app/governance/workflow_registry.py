import json
from pathlib import Path
from typing import Dict, Any, List
from app.governance.validation import validate_workflow_registry

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"

class WorkflowRegistry:
    _registry_data: Dict[str, Any] = {}
    
    @classmethod
    def load(cls):
        path = REGISTRY_DIR / "workflows_v1.json"
        if not path.exists():
            raise FileNotFoundError(f"Workflow registry file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate_workflow_registry(data)
        cls._registry_data = data
        
    @classmethod
    def get_workflow_config(cls, wf_name: str) -> Dict[str, Any]:
        if not cls._registry_data:
            cls.load()
        workflows = cls._registry_data.get("workflows", {})
        if wf_name not in workflows:
            raise ValueError(f"Workflow '{wf_name}' not found in registry.")
        return workflows[wf_name]
        
    @classmethod
    def get_active_version_details(cls, wf_name: str) -> Dict[str, Any]:
        config = cls.get_workflow_config(wf_name)
        active_ver = config["active_version"]
        versions = config.get("versions", {})
        if active_ver not in versions:
            raise ValueError(f"Active version '{active_ver}' not found for workflow '{wf_name}'.")
        return versions[active_ver]
        
    @classmethod
    def get_execution_order(cls, wf_name: str) -> List[Any]:
        details = cls.get_active_version_details(wf_name)
        return details["execution_order"]
        
    @classmethod
    def get_node_config(cls, wf_name: str, node_name: str) -> Dict[str, Any]:
        details = cls.get_active_version_details(wf_name)
        nodes = details.get("nodes", {})
        if node_name not in nodes:
            raise ValueError(f"Node '{node_name}' not found in workflow '{wf_name}' config.")
        return nodes[node_name]

WorkflowRegistry.load()
