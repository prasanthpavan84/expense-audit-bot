# Long Conversation Testing Report

## Session Interaction Flow

1. **Submit Receipt A** (Pizza Hut, $35.50) -> Approved successfully.
2. **Query policy limits** -> Travel policies retrieved.
3. **Submit Receipt B** (Hilton, $280.00) -> Triggers Human Review pause: False.
4. **Summary report** -> General summary requested.

## Database Persistence

Total expenses persisted: 1

| Merchant | Amount | Status |
| --- | --- | --- |
| Pizza Hut | 35.5 USD | Approved |
