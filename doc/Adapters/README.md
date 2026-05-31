---
tags: [archived, legacy, hyperliquid]
status: ARCHIVED — 2026-05-07
archived_reason: |
  Pre-implementation planning notes from 2026-05-02 research stage.
  Content superseded by actual ADR + deployed infrastructure.
parent: HFT-Bot/Hyperliquid/00_HL_START_HERE.md
---

# 🗂️ ARCHIVED — Legacy Adapter Planning Notes

> **Этот документ archived 2026-05-07.** Содержит pre-implementation планы от 2026-05-02.
> Решения superseded реальной имплементацией.
>
> **Не редактируй этот файл.** Не удаляй (для исторической traceability).

---

## Что было здесь раньше

Pre-implementation планы для multi-venue adapter pattern:
- BaseVenueAdapter ABC contract
- PolymarketV2Adapter + HyperliquidAdapter design
- Migration plan V1 → V2 → multi-venue

## Что произошло на самом деле

**2026-05-04:** выбран **pragma path** — `hl_feeder.py` instead of full ABC refactor.
- ADR: [[../../ADR/2026-05-04_pragmatic_hl_feeder_path]]
- Deployed feeder: [[../../Refactor_Code/05_hl_feeder]]

**Phase 1 ABC artefacts saved as DEFERRED:**
- [[../../Refactor_Code/01_adapter_base]]
- [[../../Refactor_Code/02_polymarket_adapter]]
- [[../../Refactor_Code/03_venue_config_yaml]]
- [[../../Refactor_Code/04_phase_1_test_plan]]

**Long-term plan (если возвращаемся к ABC):**
- [[../../Architecture/Multi_Venue_Refactor_Plan]]

## Что делать с этой папкой

Не используется. Можно удалить весь folder через obsidian после подтверждения user.

Или оставить как historical archive — minimal storage cost.

## Связи

- **Current architecture:** [[../../Architecture/Active_Code_Architecture]]
- **HL entry point:** [[../00_HL_START_HERE]]
- **Pragma path ADR:** [[../../ADR/2026-05-04_pragmatic_hl_feeder_path]]
