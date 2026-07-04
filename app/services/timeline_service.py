from typing import List, Dict, Any, Optional
from app.repositories.event_repository import EventRepository

class TimelineService:
    """Business service constructing chronological decision trails for audit logs."""

    def __init__(self, event_repository: Optional[EventRepository] = None):
        self.repository = event_repository or EventRepository()

    def generate_timeline(self, audit_id: str) -> List[Dict[str, Any]]:
        """Fetch all events and build a chronological Decision Timeline map."""
        events = self.repository.get_events_for_audit(audit_id)
        timeline = []

        # Map event types to user-friendly titles and icons
        status_info = {
            "WorkflowStarted": ("Workflow Began", "play", "Started audit pipeline."),
            "AgentStarted": ("Agent Dispatched", "user", "Agent processing execution context."),
            "AgentCompleted": ("Agent Completed", "check-circle", "Agent finalized action."),
            "AgentFailed": ("Agent Failed", "x-circle", "Agent encountered execution limits."),
            "WorkflowCompleted": ("Workflow Finished", "flag", "Pipeline finalized audit outcome.")
        }

        for ev in events:
            etype = ev["event_type"]
            agent = ev["agent"]
            payload = ev["payload"]
            
            title, icon, desc = status_info.get(etype, (etype, "info", "Event triggered."))
            
            if etype == "AgentCompleted" and "explanation" in payload:
                desc = payload["explanation"]
            elif etype == "WorkflowStarted":
                desc = f"Triggered '{payload.get('workflow')}' sequence: {', '.join(payload.get('steps', []))}."
            elif etype == "WorkflowCompleted":
                desc = f"Completed in {payload.get('duration_sec', 0.0):.2f} seconds."

            timeline.append({
                "timestamp": ev["timestamp"],
                "agent": agent,
                "event_type": etype,
                "title": f"[{agent}] {title}",
                "icon": icon,
                "description": desc,
                "payload": payload
            })

        return timeline
