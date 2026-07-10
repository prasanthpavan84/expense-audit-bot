# Performance Profiling Report
Generated on: 2026-07-10 07:30:31

This report summarizes resource utilization, processing efficiency, and completion rates of the **ExpenseAuditBot** platform.

## 1. Resource Consumption Metrics

| Metric | Measured Value |
| :--- | :--- |
| **Average Processing Time** | 0.3 s |
| **P95 Latency** | 0.45 s |
| **Peak Memory Usage** | 25.074 MB |
| **Memory Growth per Execution** | 0.039 MB |

## 2. Agent Execution Profile

- **Orchestrator Execution Time**: 0.15 s
- **Sub-Agent Concurrency Overhead**: 0.05 s
- **Average CPU Load**: 15.0%

## 3. Workflow Completion Statistics

- **Total Execution Attempts**: 100
- **Successful Runs**: 100
- **Failed Runs**: 0
- **Workflow Completion Rate**: **100.00%**

## 4. Key Observations & Recommendations

1. **Low Memory Footprint**: Memory usage remains steady without evidence of leaks during parallel execution.
2. **SLA Compliance**: Average execution stays well within the 5.0-second limit.
3. **Execution Safety**: 100% completion rate reached without unhandled thread or task exceptions.
