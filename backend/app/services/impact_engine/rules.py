"""EVENT -> INFRASTRUCTURE -> SUPPLY CHAIN -> COMMODITY -> MARKET rule table.

This is intentionally a plain, editable config rather than a learned model:
the master spec requires every AI/complex signal to be tested against
transparent baselines, and a hand-authored causal chain is the most
auditable baseline of all. Each rule maps one event_type to one or more
(asset, exposure, direction) outcomes with the intermediate chain nodes to
render in the UI. `direction` is the expected sign of the price reaction on
`asset_symbol` if the hypothesis holds — bullish for supply-constrained
commodities, bearish for operationally-impaired equities.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImpactRule:
    chain: tuple[str, ...]
    asset_symbol: str
    base_exposure: float  # 0-1, before event confidence/severity adjustment
    direction: str  # "bullish" | "bearish"
    rationale: str


IMPACT_RULES: dict[str, list[ImpactRule]] = {
    "flood": [
        ImpactRule(("EVENT", "PORT", "CRUDE_IMPORTS", "REFINERY", "REGIONAL_SUPPLY", "CRUDE"), "CL=F", 0.55, "bullish", "Flooding disrupts port throughput and refinery feedstock delivery."),
        ImpactRule(("EVENT", "REGIONAL_LOGISTICS", "AGRICULTURE_EXPORT", "GRAIN"), "ZC=F", 0.35, "bullish", "Flooding damages crop transport and storage infrastructure."),
    ],
    "hurricane": [
        ImpactRule(("EVENT", "OFFSHORE_PLATFORM", "CRUDE_PRODUCTION", "CRUDE"), "CL=F", 0.7, "bullish", "Offshore production shut-ins during hurricanes reduce crude supply."),
        ImpactRule(("EVENT", "OFFSHORE_PLATFORM", "NATGAS_PRODUCTION", "NATURAL_GAS"), "NG=F", 0.6, "bullish", "Gulf hurricanes routinely curtail natural gas production."),
    ],
    "port_disruption": [
        ImpactRule(("EVENT", "PORT", "CONTAINER_THROUGHPUT", "FREIGHT_RATES", "LOGISTICS_EQUITIES"), "FDX", 0.4, "bearish", "Port congestion raises freight costs, pressuring logistics operators."),
        ImpactRule(("EVENT", "PORT", "CRUDE_IMPORTS", "REGIONAL_SUPPLY", "CRUDE"), "CL=F", 0.3, "bullish", "Delayed crude imports tighten regional refinery supply."),
    ],
    "earthquake": [
        ImpactRule(("EVENT", "MINE", "ORE_PRODUCTION", "COPPER"), "HG=F", 0.5, "bullish", "Seismic activity in mining regions risks output disruption."),
        ImpactRule(("EVENT", "REGIONAL_INFRASTRUCTURE", "INSURANCE_EXPOSURE", "REINSURERS"), "SPX", 0.2, "bearish", "Large earthquakes increase insured-loss expectations."),
    ],
    "wildfire": [
        ImpactRule(("EVENT", "FOREST_OPERATIONS", "LUMBER_SUPPLY", "LUMBER"), "LBS=F", 0.5, "bullish", "Wildfires reduce harvestable timber and disrupt mills."),
        ImpactRule(("EVENT", "REGIONAL_GRID", "POWER_UTILITIES"), "XLU", 0.25, "bearish", "Wildfire risk drives preventive utility shutdowns."),
    ],
    "drought": [
        ImpactRule(("EVENT", "FARMLAND", "CROP_YIELD", "GRAIN"), "ZC=F", 0.6, "bullish", "Drought directly reduces expected crop yield."),
        ImpactRule(("EVENT", "FARMLAND", "CROP_YIELD", "SOYBEANS"), "ZS=F", 0.55, "bullish", "Drought stress lowers soybean yield forecasts."),
    ],
    "pipeline_disruption": [
        ImpactRule(("EVENT", "PIPELINE", "REGIONAL_SUPPLY", "CRUDE"), "CL=F", 0.65, "bullish", "Pipeline outages strand regional crude supply."),
        ImpactRule(("EVENT", "PIPELINE", "REGIONAL_SUPPLY", "NATURAL_GAS"), "NG=F", 0.4, "bullish", "Gas pipeline disruptions tighten regional balances."),
    ],
    "refinery_disruption": [
        ImpactRule(("EVENT", "REFINERY", "GASOLINE_SUPPLY", "GASOLINE"), "RB=F", 0.65, "bullish", "Refinery outages reduce gasoline production directly."),
        ImpactRule(("EVENT", "REFINERY", "CRUDE_DEMAND", "CRUDE"), "CL=F", 0.3, "bearish", "Refinery downtime temporarily softens crude intake."),
    ],
    "mine_disruption": [
        ImpactRule(("EVENT", "MINE", "ORE_PRODUCTION", "COPPER"), "HG=F", 0.7, "bullish", "Mine strikes/outages directly cut ore output."),
        ImpactRule(("EVENT", "MINE", "ORE_PRODUCTION", "GOLD"), "GC=F", 0.3, "bullish", "Precious-metal mine disruptions tighten physical supply."),
    ],
    "power_outage": [
        ImpactRule(("EVENT", "GRID", "INDUSTRIAL_OUTPUT", "SEMICONDUCTOR_EQUITIES"), "SOXX", 0.5, "bearish", "Fab power outages halt chip production runs."),
    ],
    "industrial_accident": [
        ImpactRule(("EVENT", "FACILITY", "SECTOR_OUTPUT", "ENERGY_EQUITIES"), "XLE", 0.35, "bearish", "Petrochemical incidents raise sector-wide safety/regulatory risk."),
    ],
    "strike": [
        ImpactRule(("EVENT", "PORT", "CONTAINER_THROUGHPUT", "FREIGHT_RATES", "LOGISTICS_EQUITIES"), "FDX", 0.45, "bearish", "Labor action halts terminal operations."),
    ],
    "embargo": [
        ImpactRule(("EVENT", "TRADE_FLOW", "REGIONAL_SUPPLY", "CRUDE"), "CL=F", 0.6, "bullish", "Embargoes remove supply from the global market."),
        ImpactRule(("EVENT", "TRADE_FLOW", "SAFE_HAVEN_DEMAND", "GOLD"), "GC=F", 0.25, "bullish", "Geopolitical trade restrictions boost safe-haven demand."),
    ],
    "geopolitical_disruption": [
        ImpactRule(("EVENT", "SHIPPING_LANE", "TANKER_ROUTING", "CRUDE"), "CL=F", 0.55, "bullish", "Chokepoint tension raises shipping risk premia on crude."),
        ImpactRule(("EVENT", "RISK_SENTIMENT", "SAFE_HAVEN_DEMAND", "GOLD"), "GC=F", 0.35, "bullish", "Geopolitical escalation typically lifts gold."),
    ],
    "airport_disruption": [
        ImpactRule(("EVENT", "AIRPORT", "AIR_FREIGHT", "LOGISTICS_EQUITIES"), "FDX", 0.3, "bearish", "Air cargo hub outages delay high-value freight."),
    ],
    "extreme_weather": [
        ImpactRule(("EVENT", "REGIONAL_DEMAND", "HEATING_DEMAND", "NATURAL_GAS"), "NG=F", 0.45, "bullish", "Extreme cold/heat swings heating/cooling demand sharply."),
    ],
    "volcanic_activity": [
        ImpactRule(("EVENT", "AIRSPACE", "AIR_FREIGHT", "LOGISTICS_EQUITIES"), "FDX", 0.3, "bearish", "Ash clouds can ground regional air traffic."),
    ],
}


def rules_for(event_type: str) -> list[ImpactRule]:
    return IMPACT_RULES.get(event_type, [])
