---
tags: [archived, legacy, hyperliquid]
status: ARCHIVED — 2026-05-07
archived_reason: |
  Pre-implementation planning notes from 2026-05-02 research stage.
  Active ADRs now live in HFT-Bot/ADR/ folder, not here.
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
---

# 🗂️ ARCHIVED — Legacy Architecture Planning Notes

> **Этот документ archived 2026-05-07.**
> Все active ADRs live в `HFT-Bot/ADR/` папке (project-level), не здесь.
>
> **Не редактируй этот файл.**

---

## Что было здесь раньше

Pre-implementation planned ADRs:
- `2026-05-02_hyperliquid_initial_research.md` — never created
- `2026-05-02_24h_outcomes_not_viable.md` — never created (decision made implicitly)
- `2026-05-XX_multi_venue_adapter_contract.md` — never created (pragma path chosen)
- `2026-05-XX_polymarket_v2_migration_plan.md` — never created (V2 deferred)

## Active ADRs (где actually live)

```
HFT-Bot/ADR/
├── 2026-05-04_pragmatic_hl_feeder_path.md         # pragma decision
└── 2026-05-05_hl_collector_subscription_lifecycle_fix.md   # storm fix
```

Также:
- `HFT-Bot/Architecture/Active_Code_Architecture.md` — single source of truth для current state
- `HFT-Bot/Architecture/Multi_Venue_Refactor_Plan.md` — long-term plan (DEFERRED)

## Active design docs в этой папке

- `2026-05-04_data_collector_schema.md` — design for collector. **IMPLEMENTED** — kept as reference.

## Что делать с этой папкой

`README.md` (этот файл) не используется. `2026-05-04_data_collector_schema.md` — historical reference, IMPLEMENTED.

При следующей чистке можно удалить README.md (этот файл) если не нужно historical traceability.

## Связи

- **Active ADRs:** [[../../ADR/2026-05-04_pragmatic_hl_feeder_path]], [[../../ADR/2026-05-05_hl_collector_subscription_lifecycle_fix]]
- **Architecture map:** [[../../Architecture/Active_Code_Architecture]]
- **HL entry point:** [[../00_HL_START_HERE]]
