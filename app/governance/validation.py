import typing

def validate_model_registry(data: dict):
    if not isinstance(data, dict):
        raise ValueError("Model registry must be a dictionary")
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported model registry schema version: {data.get('schema_version')}")
    if "models" not in data:
        raise ValueError("Missing 'models' key in model registry")
    models = data["models"]
    if not isinstance(models, dict):
        raise ValueError("'models' must be a dictionary")
    for model_name, info in models.items():
        if not isinstance(info, dict):
            raise ValueError(f"Model config for {model_name} must be a dictionary")
        for key in ["display_name", "context_limit", "capabilities"]:
            if key not in info:
                raise ValueError(f"Model {model_name} is missing key: '{key}'")
        caps = info["capabilities"]
        if not isinstance(caps, dict):
            raise ValueError(f"Capabilities for {model_name} must be a dictionary")
        required_caps = [
            "structured_output", "json_mode", "tool_calling", 
            "streaming", "vision", "long_context", 
            "thinking", "reasoning", "function_calling"
        ]
        for cap in required_caps:
            if cap not in caps:
                raise ValueError(f"Model {model_name} capabilities missing key: '{cap}'")
            if not isinstance(caps[cap], bool):
                raise ValueError(f"Capability '{cap}' for {model_name} must be a boolean")

def validate_prompt_registry(data: dict):
    if not isinstance(data, dict):
        raise ValueError("Prompt registry must be a dictionary")
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported prompt registry schema version: {data.get('schema_version')}")
    if "prompts" not in data:
        raise ValueError("Missing 'prompts' key in prompt registry")
    prompts = data["prompts"]
    if not isinstance(prompts, dict):
        raise ValueError("'prompts' must be a dictionary")
    for prompt_name, info in prompts.items():
        if not isinstance(info, dict):
            raise ValueError(f"Prompt config for {prompt_name} must be a dictionary")
        if "active_version" not in info or "versions" not in info:
            raise ValueError(f"Prompt {prompt_name} missing 'active_version' or 'versions'")
        versions = info["versions"]
        if not isinstance(versions, dict):
            raise ValueError(f"'versions' for {prompt_name} must be a dictionary")
        for ver, details in versions.items():
            if not isinstance(details, dict):
                raise ValueError(f"Prompt {prompt_name} version {ver} config must be a dict")
            for key in ["token_budget", "compatible_models", "requires_structured_output", "required_tools"]:
                if key not in details:
                    raise ValueError(f"Prompt {prompt_name} version {ver} missing key: '{key}'")
            if not isinstance(details["token_budget"], int):
                raise ValueError(f"token_budget for {prompt_name} {ver} must be an integer")
            if not isinstance(details["compatible_models"], list):
                raise ValueError(f"compatible_models for {prompt_name} {ver} must be a list")
            if not isinstance(details["requires_structured_output"], bool):
                raise ValueError(f"requires_structured_output for {prompt_name} {ver} must be a boolean")
            if not isinstance(details["required_tools"], list):
                raise ValueError(f"required_tools for {prompt_name} {ver} must be a list")

def validate_workflow_registry(data: dict):
    if not isinstance(data, dict):
        raise ValueError("Workflow registry must be a dictionary")
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported workflow registry schema version: {data.get('schema_version')}")
    if "workflows" not in data:
        raise ValueError("Missing 'workflows' key in workflow registry")
    workflows = data["workflows"]
    if not isinstance(workflows, dict):
        raise ValueError("'workflows' must be a dictionary")
    for wf_name, info in workflows.items():
        if "active_version" not in info or "versions" not in info:
            raise ValueError(f"Workflow {wf_name} missing 'active_version' or 'versions'")
        versions = info["versions"]
        for ver, details in versions.items():
            for key in ["nodes", "execution_order"]:
                if key not in details:
                    raise ValueError(f"Workflow {wf_name} version {ver} missing: '{key}'")
            nodes = details["nodes"]
            if not isinstance(nodes, dict):
                raise ValueError(f"nodes in {wf_name} {ver} must be a dictionary")
            for node_name, node_config in nodes.items():
                if not isinstance(node_config, dict):
                    raise ValueError(f"Node {node_name} config in {wf_name} must be a dict")
                for k in ["timeout", "retries", "parallel"]:
                    if k not in node_config:
                        raise ValueError(f"Node {node_name} in {wf_name} missing: '{k}'")
            order = details["execution_order"]
            if not isinstance(order, list):
                raise ValueError(f"execution_order in {wf_name} {ver} must be a list")

def validate_deployment_registry(data: dict):
    if not isinstance(data, dict):
        raise ValueError("Deployment registry must be a dictionary")
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported deployment registry schema version: {data.get('schema_version')}")
    if "environments" not in data:
        raise ValueError("Missing 'environments' key in deployment registry")
    envs = data["environments"]
    for env_name, config in envs.items():
        for key in ["project_id", "region", "model_version", "prompt_version", "secrets_required", "environment_variables"]:
            if key not in config:
                raise ValueError(f"Deployment environment {env_name} missing: '{key}'")
        if not isinstance(config["secrets_required"], list):
            raise ValueError(f"secrets_required for {env_name} must be a list")
        if not isinstance(config["environment_variables"], dict):
            raise ValueError(f"environment_variables for {env_name} must be a dict")

def validate_evaluation_registry(data: dict):
    if not isinstance(data, dict):
        raise ValueError("Evaluation registry must be a dictionary")
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Unsupported evaluation registry schema version: {data.get('schema_version')}")
    if "benchmarks" not in data:
        raise ValueError("Missing 'benchmarks' key in evaluation registry")
