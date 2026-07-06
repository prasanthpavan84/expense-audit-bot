# ExpenseAuditBot Architecture Diagram

This document illustrates the structural layout and data flow within the **ExpenseAuditBot** platform using Mermaid diagrams.

## 1. System Architecture Flowchart

```mermaid
flowchart TD
    User([User / Employee])
    API["API Gateway (run.py / entrypoint)"]
    Security{"Security Checkpoint (SSN/PII & Prompt Injection)"}
    Orchestrator["Active Orchestrator Node (audit_orchestrator_node)"]
    SharedState[("Shared Context State (Context.state)")]
    
    subgraph "Sub-Agents"
        Extractor["Receipt Extractor Agent"]
        Fraud["Fraud Detector Agent"]
        Policy["Policy Verifier Agent"]
    end
    
    subgraph "Rule Engines & Databases"
        PolicyEngine["Business Policy Rule Engine"]
        FraudEngine["Fraud Anomaly Intelligence Engine"]
    end
    
    HumanReview{"Human Review Gate (HITL Trigger)"}
    ReportGen["Report Generator Node"]
    
    %% Relationships
    User -->|Sends Expense Prompt| API
    API -->|Validates Input| Security
    Security -->|Blocked| API
    Security -->|Clear| Orchestrator
    
    Orchestrator -->|Writes / Reads| SharedState
    Orchestrator -->|Triggers| Extractor
    Orchestrator -->|Triggers Concurrently| Fraud
    Orchestrator -->|Triggers Concurrently| Policy
    
    Fraud -->|Calls| FraudEngine
    Policy -->|Calls| PolicyEngine
    
    Orchestrator -->|Evaluates Decisions| HumanReview
    HumanReview -->|Needs Review| User
    HumanReview -->|Approved/Denied| ReportGen
    
    ReportGen -->|Generates Report| User
```

## 2. Dynamic Execution Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as API/Entrypoint
    participant Sec as Security Checkpoint
    participant Orch as Orchestrator Node
    participant State as Shared Context State
    participant Ext as Receipt Extractor
    participant PE as Policy Engine
    participant FE as Fraud Engine
    participant HR as Human Review Gate
    participant Rep as Report Generator

    User->>API: Submit Expense Request
    API->>Sec: Validate Input (SSN/PII/Injection check)
    alt Injection/PII Detected
        Sec-->>API: Return Blocked Error
        API-->>User: Show Security Warning
    else Clean Input
        Sec->>Orch: Initialize Graph Session
        Orch->>State: Write Initial Payload
        Orch->>Ext: Invoke Receipt Extractor
        Ext-->>Orch: Return Extracted Fields (JSON)
        Orch->>State: Store Extracted Expense
        
        par Parallel Analysis
            Orch->>PE: Run Policy Enforcement
            PE-->>Orch: Return Policy Violations
            Orch->>FE: Run Fraud/Anomaly Checks
            FE-->>Orch: Return Fraud Risk Score
        end
        
        Orch->>State: Save Audit & Score Outputs
        Orch->>HR: Assess Escalation Conditions
        alt Threshold Exceeded (e.g. >= $200)
            HR-->>User: Escalate for Manual Review
        else Compliant
            HR->>Rep: Generate Markdown Report
            Rep-->>User: Deliver Settlement Decision
        end
    end
```

## 3. Non-Production Telemetry Isolation

To keep test suites and continuous integration pipelines (such as GitHub Actions) fully decoupled from cloud-side Google Cloud authentication requirements:
- **Telemetry Toggle**: The application uses the `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY` environment variable (default: `true`).
- **Isolation Boundary**: In the GitHub Actions CI workflow (.yml) and local integration tests (`test_server_e2e.py`), this environment variable is explicitly overridden to `false`.
- **Decoupled Verification**: This bypasses `google.auth.default()` and Vertex AI instrumentation builder calls. Testing is fully hermetic and runs offline without GCP credentials, preventing `DefaultCredentialsError` failures while preserving observability in live deployments.

