# run.py
"""Demo script to bootstrap the minimal expense‑audit runtime.

It wires together the concrete ``ThreadScheduler``, ``SimplePlanner``,
``SimpleArtifactManager``, ``SimpleWorkflowExecutor`` and ``SimpleAgentExecutor``
with the ``RuntimeEngine``. The script prints the result of a dummy workflow
named ``demo``.
"""

from __future__ import annotations

import uuid

# Core services
from core.container import ServiceContainer
from core.scheduler import ThreadScheduler
from core.planner import SimplePlanner
from core.artifact_manager import SimpleArtifactManager
from core.workflow_executor import SimpleWorkflowExecutor
from core.agent_executor import SimpleAgentExecutor

# Runtime infrastructure
from framework.runtime.runtime_context import RuntimeContext
from framework.runtime.state_manager import StateManager
from framework.runtime.runtime_engine import RuntimeEngine


def main() -> None:
    # ---------------------------------------------------------------------
    # Prepare execution metadata
    # ---------------------------------------------------------------------
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    context = RuntimeContext(
        run_id=run_id,
        session_id="session_001",
        user_id="user_123",
        workflow="demo",
        execution_token="token_xyz",
        memory=None,
        services=None,
    )

    # ---------------------------------------------------------------------
    # Initialise core components
    # ---------------------------------------------------------------------
    scheduler = ThreadScheduler()
    planner = SimplePlanner()
    planner.initialize()
    artifact_manager = SimpleArtifactManager()
    workflow_executor = SimpleWorkflowExecutor()
    agent_executor = SimpleAgentExecutor()

    # Create a ServiceContainer – useful for downstream extensions
    container = ServiceContainer(
        scheduler=scheduler,
        planner=planner,
        artifact_manager=artifact_manager,
        workflow_executor=workflow_executor,
        agent_executor=agent_executor,
    )

    # State manager keeps the runtime FSM in sync with the context
    state_manager = StateManager(context)

    # ---------------------------------------------------------------------
    # Build the engine and run a workflow
    # ---------------------------------------------------------------------
    engine = RuntimeEngine(
        container=container,
        context=context,
        state_manager=state_manager,
        scheduler=scheduler,
        planner=planner,
        artifact_manager=artifact_manager,
        workflow_executor=workflow_executor,
        agent_executor=agent_executor,
    )

    # Optional: create an execution bundle and store a starter artifact
    bundle_path = artifact_manager.create_execution_bundle(run_id)
    artifact_manager.write_artifact(
        path=bundle_path,
        filename="run_info.json",
        data={"run_id": run_id, "status": "started"},
    )

    # Engine lifecycle
    engine.start()
    result = engine.run_workflow("demo", foo="bar")
    print("Workflow result:", result)
    engine.shutdown()


if __name__ == "__main__":
    main()
