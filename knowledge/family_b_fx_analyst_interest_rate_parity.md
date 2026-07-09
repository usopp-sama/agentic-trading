---
family: B
source: Interest Rate Parity (FX fundamentals)
doc_type: note
reliability: 95
tickers: []
---

## The core idea
**Interest Rate Parity (IRP)** links exchange rates and interest rates via
no-arbitrage: you cannot earn a risk-free gain just by borrowing in a
low-rate currency and lending in a high-rate one, because the **forward
exchange rate adjusts to offset the interest-rate differential**. It is the
anchor for pricing currency forwards and understanding carry.

## Covered IRP (CIP) - the arbitrage condition
With a forward contract locking the future rate: the **forward premium/discount
equals the interest-rate differential**. Roughly, a currency with **higher
interest rates trades at a forward discount** (expected to depreciate) versus a
low-rate currency. CIP holds tightly in liquid markets because deviations are
arbitraged away. This is how INR forwards/hedging costs are priced off the
India-vs-US rate gap.

## Uncovered IRP (UIP) - the theory and its failure
UIP says the **expected spot change** should equal the rate differential (high-
rate currencies should depreciate enough to wipe out the yield advantage). In
practice **UIP fails empirically** - high-rate currencies often do *not*
depreciate as predicted, which is exactly why the **FX carry trade** (borrow
low-yield, invest high-yield) earns returns on average... until it crashes in
risk-off episodes.

## Practical takeaways
- The **cost of hedging** a foreign exposure ≈ the interest-rate differential
  (CIP). For INR, higher domestic rates mean a forward discount / hedging cost.
- **Carry** is compensation for risk, not free money - it suffers sharp drawdowns
  when volatility spikes and risk appetite reverses.

## How an SME should use it
Read currency moves and hedging costs through the **rate-differential lens**:
when the India-US (or India-DM) rate gap widens, expect a larger INR forward
discount and richer carry; carry trades into INR are vulnerable to global
risk-off. Use IRP to sanity-check FX expectations and hedging decisions, and
treat **high carry as a risk premium** that can unwind violently - size FX and
currency-sensitive positions accordingly.
