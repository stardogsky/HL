---
source: https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/aligned-quote-assets.md
title: "Aligned quote assets"
category: hypercore
synced_at: 2026-05-04T14:38:59+00:00
content_hash: 34e18a5297cb
---

# Aligned quote assets

The Hyperliquid protocol will support “aligned stablecoins” as a permissionless primitive for stablecoin issuers to leverage Hyperliquid’s unique distribution and scale together with the protocol. Aligned stablecoins offer lower trading fees, better market maker rebates, and higher volume contribution toward fee tiers when used as the quote asset for a spot pair or the collateral asset for HIP-3 perps.&#x20;

Hyperliquid will continue to support a wide variety of permissionless quote assets for spot and perps trading. There will be continual technical developments to ensure that the Hyperliquid L1 is the most performant infrastructure for general purpose asset issuance, liquidity, and building.

To be clear, the motivation behind alignment is not to exclude any issuers, but rather to introduce an opt-in setting for new stablecoin teams to bootstrap their network effects and share upside proportionally with the protocol. Aligned stables and other assets serve different purposes and audiences, and will coexist and complement each other. Similar to the builder-protocol synergy of permissionless spot listings, HIP-3, and builder codes, aligned stablecoins are part of the infrastructure to move all of finance onchain.

**Onchain requirements:**

1. Enabled as a permissionless quote token
2. 800k additional staked HYPE by deployer, meaning a total of 1M staked HYPE including the 200k staked HYPE for the quote token deployment. This is to give builders and users assurance to use the aligned stablecoin.
3. 50% of the deployer’s offchain reserve income must flow to the protocol. Validators may vote to update the calculation methodology as regulatory standards evolve. There will be follow-up work on the precise definition of risk-free rate, which will be updated according to an onchain stake-weighted median of validator reported values. A CoreWriter action will allow the deployer to reflect the exact minted balance from HyperEVM directly to HyperCore, which will allow a fully automated fee share mechanism as part of L1 execution.

**Offchain requirements, enforced through onchain quorum of validator votes:**

1. The stablecoin is 1:1 backed by cash, short-term US treasuries, and tokenized US treasury or money market funds to the extent permitted under applicable regulatory frameworks. Aligned issuers must also provide par redemption at all times, with a publicly disclosed and timely redemption service consistent with their applicable regulatory regime. These conditions can be revisited by the validators, in the spirit of building a regulatorily compliant chain for payments and banking opportunities. The guiding requirement is that a large percentage of the world's circulating dollars could compliantly be converted to the aligned stablecoin in the context of existing businesses and use cases in the financial world.
2. The full supply is natively minted on HyperEVM. Any supply on other chains or offchain must first be minted on HyperEVM as the source chain.
3. The deployer can only deploy assets that directly support the aligned stablecoin. For example, the underlying treasuries could be issued onchain. The net effect is that the deployer must share half of its offchain yield income through the existence of the aligned stablecoin. The deployer and its affiliates may not receive any economic benefits tied to conversion of the aligned stablecoin into another asset. "Benefit" includes but is not limited to revenue share, order-flow payments or any form of rate-linked compensation.
4. The team building an aligned stablecoin must be independent and dedicated to building on Hyperliquid.&#x20;

**Aligned stable benefits, applied to spot and perp trading:**

1. 20% lower taker fees&#x20;
2. 50% better maker rebates
3. 20% more volume contribution toward fee tiers

Offchain conditions are ultimately voted upon by validator quorum, as any such conditions are not able to be reflected directly in protocol execution. Like on most other blockchains, independent validators on Hyperliquid achieve consensus on a self-contained state machine’s execution. This state machine’s evolution is entirely onchain. In the case of the offchain conditions for an aligned stablecoin, this evolution is driven by validator vote.


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/aligned-quote-assets.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
