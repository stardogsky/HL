"""
Outcome discovery — parses outcomeMeta and builds list of coins to subscribe to.

Filters:
- "all_real": only outcomes with `class:priceBinary` in description (skip joke testnet outcomes)
- "explicit": only outcome IDs from explicit list

For each real outcome, generates two coin names:
- YES coin: "#<10*outcome_id + 0>"
- NO coin:  "#<10*outcome_id + 1>"

Returns OutcomeInfo with parsed metadata for downstream consumers.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OutcomeInfo:
    outcome_id: int
    name: str
    description: str
    parsed: dict = field(default_factory=dict)
    yes_coin: str = ""
    no_coin: str = ""
    side_specs: list = field(default_factory=list)

    @property
    def is_price_binary(self) -> bool:
        return self.parsed.get("class") == "priceBinary"

    @property
    def underlying(self) -> Optional[str]:
        return self.parsed.get("underlying")

    @property
    def period(self) -> Optional[str]:
        return self.parsed.get("period")

    @property
    def target_price(self) -> Optional[float]:
        tp = self.parsed.get("targetPrice")
        try:
            return float(tp) if tp else None
        except (ValueError, TypeError):
            return None

    @property
    def expiry_str(self) -> Optional[str]:
        return self.parsed.get("expiry")

    @property
    def expiry_dt(self) -> Optional[datetime]:
        """Parse expiry like '20260505-0600' to UTC datetime."""
        s = self.expiry_str
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @property
    def seconds_until_expiry(self) -> Optional[float]:
        dt = self.expiry_dt
        if not dt:
            return None
        return (dt - datetime.now(timezone.utc)).total_seconds()


def parse_description(desc: str) -> dict:
    """Parse 'class:priceBinary|underlying:BTC|expiry:...|targetPrice:...|period:1d'."""
    if not isinstance(desc, str):
        return {}
    parts = {}
    for chunk in desc.split("|"):
        if ":" in chunk:
            k, v = chunk.split(":", 1)
            parts[k.strip()] = v.strip()
    return parts


def build_outcome_info(raw: dict) -> OutcomeInfo:
    """Build OutcomeInfo from one item of outcomeMeta.outcomes[]."""
    outcome_id = raw.get("outcome")
    desc = raw.get("description", "")
    parsed = parse_description(desc)
    side_specs = raw.get("sideSpecs", [])

    encoding_yes = 10 * outcome_id + 0
    encoding_no = 10 * outcome_id + 1

    return OutcomeInfo(
        outcome_id=outcome_id,
        name=raw.get("name", ""),
        description=desc,
        parsed=parsed,
        yes_coin=f"#{encoding_yes}",
        no_coin=f"#{encoding_no}",
        side_specs=side_specs,
    )


def filter_outcomes(outcomes_raw: list, mode: str = "all_real",
                    explicit_ids: Optional[list] = None) -> list[OutcomeInfo]:
    """
    Build OutcomeInfo list filtered by mode and active status.

    mode='all_real': only outcomes with 'class:priceBinary' AND not yet expired
    mode='explicit': only outcomes with outcome_id in explicit_ids AND not yet expired

    Filtering by expiry is critical: subscribing to a settled/expired coin
    causes HL server to silently close the WS connection (no close frame, no error).
    See Incidents/2026-05-05_hl_collector_reconnect_storm.md.
    """
    all_outcomes = [build_outcome_info(o) for o in outcomes_raw]

    def is_active(o: OutcomeInfo) -> bool:
        """True only if outcome has not yet expired."""
        ts = o.seconds_until_expiry
        return ts is not None and ts > 0

    if mode == "explicit":
        explicit_set = set(explicit_ids or [])
        return [o for o in all_outcomes
                if o.outcome_id in explicit_set and is_active(o)]

    # mode == "all_real" or default
    return [o for o in all_outcomes if o.is_price_binary and is_active(o)]
