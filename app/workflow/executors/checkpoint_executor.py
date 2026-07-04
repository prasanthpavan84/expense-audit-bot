from typing import Optional, Dict, Any, Tuple
from app.repositories.checkpoint_repository import CheckpointRepository

class CheckpointExecutor:
    """Manages saving and restoring workflow state checkpoints in SQLite for resiliency."""

    def __init__(self, checkpoint_repository: Optional[CheckpointRepository] = None):
        self.repository = checkpoint_repository or CheckpointRepository()

    def save_checkpoint(
        self,
        audit_id: str,
        correlation_id: str,
        last_completed_step: str,
        context_data: Dict[str, Any]
    ) -> None:
        """Checkpoint current context to the database."""
        self.repository.save_checkpoint(
            audit_id=audit_id,
            correlation_id=correlation_id,
            last_completed_step=last_completed_step,
            state_data=context_data
        )

    def restore_checkpoint(self, audit_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Fetch the checkpoint and return (last_completed_step, state_data)."""
        checkpoint = self.repository.get_checkpoint(audit_id)
        if not checkpoint:
            return None
        return checkpoint["last_completed_step"], checkpoint["state_data"]

    def clear_checkpoint(self, audit_id: str) -> bool:
        """Delete checkpoint upon final execution of the workflow."""
        return self.repository.delete_checkpoint(audit_id)
