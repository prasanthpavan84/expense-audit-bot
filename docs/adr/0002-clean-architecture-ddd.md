# ADR 0002: Clean Architecture & Domain-Driven Design (DDD)

## Status
Approved

## Context
The legacy application coupled orchestration rules, database queries, and business limits inside single agent scripts. This made the system hard to extend, difficult to test, and tightly bound to SQLite database logic.

## Decision
We separate concerns using Clean Architecture and Domain-Driven Design (DDD):
1. **Domain Models (`app/models/domain.py`)**: Rich domain models representing business concepts (e.g. `Expense`, `Receipt`, `Employee`, `Policy`, `AuditResult`).
2. **Repositories (`app/repositories/`)**: Independent database loaders (e.g. `AuditRepository`, `PolicyRepository`) to isolate SQLite queries.
3. **Services (`app/services/`)**: Pure business logic (e.g. `ReceiptService`, `PolicyService`) performing limits calculations, RAG lookups, and validations.
4. **Agents (`app/agents/`)**: Clean decision-making wrappers implementing `BaseAgent`. Agents decide *what* to do, services do the actual *work*.

## Consequences
- Highly modular and testable codebase.
- Database systems (e.g. SQLite to PostgreSQL) can be swapped in repositories without affecting agents or services.
