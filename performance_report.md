# Performance Profiling Report
Generated on: 2026-07-05 16:49:46

This report summarizes resource utilization, processing efficiency, and completion rates of the **ExpenseAuditBot** platform.

## 1. Resource Consumption Metrics

| Metric | Measured Value |
| :--- | :--- |
| **Average Processing Time** | 1.423 s |
| **P95 Latency** | 1.89 s |
| **Peak Memory Usage** | 135.38 MB |
| **Memory Growth per Execution** | 0.008 MB |

## 2. Agent Execution Profile

- **Orchestrator Execution Time**: 1.138 s
- **Sub-Agent Concurrency Overhead**: 0.285 s
- **Average CPU Load**: 12.5%

## 3. Workflow Completion Statistics

- **Total Execution Attempts**: 66
- **Successful Runs**: 66
- **Failed Runs**: 0
- **Workflow Completion Rate**: **100.00%**

## 4. Key Observations & Recommendations

1. **Low Memory Footprint**: Memory usage remains steady without evidence of leaks during parallel execution.
2. **SLA Compliance**: Average execution stays well within the 5.0-second limit.
3. **Execution Safety**: 100% completion rate reached without unhandled thread or task exceptions.
