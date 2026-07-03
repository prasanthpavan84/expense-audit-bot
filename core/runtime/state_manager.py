import json
import logging
from enum import Enum, auto
from typing import Dict, Set, Optional

from core.exceptions import BaseAuditException

class RuntimeState(Enum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    FAILED = "FAILED"
    ROLLBACK = "ROLLBACK"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class InvalidStateTransitionError(BaseAuditException):
    code = "INVALID_STATE_TRANSITION"
    message = "Invalid state transition requested."


class StateManager:
    """Manages application/workflow execution state with transition rules.
    
    Valid transitions:
        CREATED -> READY, CANCELLED
        READY -> RUNNING, CANCELLED
        RUNNING -> WAITING, FINISHED, FAILED, ROLLBACK, CANCELLED
        WAITING -> RUNNING, CANCELLED, FAILED
        FAILED -> ROLLBACK, CANCELLED
        ROLLBACK -> FAILED, CANCELLED, READY
        FINISHED -> (none - terminal)
        CANCELLED -> (none - terminal)
    """

    TRANSITION_RULES: Dict[RuntimeState, Set[RuntimeState]] = {
        RuntimeState.CREATED: {RuntimeState.READY, RuntimeState.CANCELLED},
        RuntimeState.READY: {RuntimeState.RUNNING, RuntimeState.CANCELLED},
        RuntimeState.RUNNING: {
            RuntimeState.WAITING,
            RuntimeState.FINISHED,
            RuntimeState.FAILED,
            RuntimeState.ROLLBACK,
            RuntimeState.CANCELLED,
        },
        RuntimeState.WAITING: {RuntimeState.RUNNING, RuntimeState.CANCELLED, RuntimeState.FAILED},
        RuntimeState.FAILED: {RuntimeState.ROLLBACK, RuntimeState.CANCELLED},
        RuntimeState.ROLLBACK: {RuntimeState.FAILED, RuntimeState.CANCELLED, RuntimeState.READY},
        RuntimeState.FINISHED: set(),
        RuntimeState.CANCELLED: set(),
    }

    def __init__(self, log_path: Optional[str] = None):
        self._state = RuntimeState.CREATED
        self._log_path = log_path
        self._logger = logging.getLogger("StateManager")
        self._write_log("INIT", None, self._state.value)

    @property
    def current_state(self) -> RuntimeState:
        return self._state

    def transition_to(self, target_state: RuntimeState, reason: Optional[str] = None) -> None:
        """Transitions the runtime state to the target state if permitted.
        
        Raises:
            InvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = self.TRANSITION_RULES.get(self._state, set())
        if target_state not in allowed:
            err_msg = f"Cannot transition from {self._state.value} to {target_state.value}"
            self._logger.error(err_msg)
            raise InvalidStateTransitionError(
                err_msg,
                current_state=self._state.value,
                target_state=target_state.value
            )

        old_state = self._state
        self._state = target_state
        self._logger.info(f"Transitioned from {old_state.value} to {target_state.value} (Reason: {reason or 'none'})")
        self._write_log("TRANSITION", old_state.value, target_state.value, reason)

    def _write_log(self, action: str, from_state: Optional[str], to_state: str, reason: Optional[str] = None) -> None:
        if not self._log_path:
            return
        
        log_entry = {
            "action": action,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, None, None, None)),
        }
        
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self._logger.error(f"Failed to write state log to {self._log_path}: {e}")
