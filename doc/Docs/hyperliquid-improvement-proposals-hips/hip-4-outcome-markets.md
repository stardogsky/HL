---
source: https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-4-outcome-markets.md
title: "HIP-4: Outcome markets"
category: hips
synced_at: 2026-05-04T14:38:59+00:00
content_hash: 869350b8fb96
---

# HIP-4: Outcome markets

Outcomes are fully collateralized contracts that settle within a fixed range. They are a general-purpose primitive that are useful for applications such as prediction markets and bounded options-like instruments.&#x20;

Outcomes bring non-linearity, dated contracts, and an alternative form of derivative trading that does not involve leverage or liquidations. The outcome primitive expands the expressivity of HyperCore, while composing with other primitives such as portfolio margin and the HyperEVM.

The first market is a recurring binary outcome that settles daily at 06:00 UTC to the BTC mark price on HyperCore mark prices. See the spec [here](/hyperliquid-docs/trading/contract-specifications.md#recurring-outcomes). Multi-outcome markets will be supported but not part of the initial mainnet release. Additional features and markets will be rolled out in stages.

The outcome trading API is similar to spot, with key differences highlighted here: <https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids>.


---

# Agent Instructions: Querying This Documentation

If you need additional information that is not directly available in this page, you can query the documentation dynamically by asking a question.

Perform an HTTP GET request on the current page URL with the `ask` query parameter:

```
GET https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-4-outcome-markets.md?ask=<question>
```

The question should be specific, self-contained, and written in natural language.
The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
