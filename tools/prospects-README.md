# Miami-Dade Investor-Entity Prospect List

**File:** `prospects-miami.csv` — **117 rows** (entities with 2+ purchases). Pulled **2026-07-19**.

## Method
1. Pulled all qualified single-family sales (DOR code 0101, price > $150k, heated area > 800 sqft,
   sale date >= 2025-07-01, site ZIP 330xx/331xx) from the Miami-Dade Property Appraiser GIS layer
   (PaGISView FeatureServer 0). Result: 9166 sale records / 9166 distinct folios.
2. Looked up the current owner of each folio on the Miami-Dade MD_LandInformation MapServer layer 24
   (batches of 40, paced). Owners resolved: 9164. Skipped batches: 0 (0 folios).
3. Kept owners whose name matches entity keywords (LLC / CORP / INC / INVEST / PROPERTIES / HOLDINGS /
   HOMES / CAPITAL / GROUP / VENTURES / REALTY); excluded institutional mega-landlords, government/bank
   entities, and national homebuilders. Grouped by normalized name; kept entities with **2+ purchases**
   in the window; sorted by count descending. 1828 entity buyers total before the 2+ filter.
4. `sunbiz_search_url` is a **search link** into Florida Sunbiz for the entity name — not a verified
   registration or registered-agent claim.

## Honest caveats
- **12-month window only** (sales on/after 2025-07-01). County recording lag means the most recent
  weeks are undercounted.
- The owner layer shows the **current** owner. For a sale inside the window that is almost always the
  buyer at that sale, but if a property already resold, the current owner is the newer buyer.
- Some of these entities are **buy-and-hold landlords, lenders taking title, or family LLCs**, not
  flippers. Purchase count is activity, not intent — qualify each one before outreach.
- Mailing addresses are whatever the county has on record (often a registered agent, PO box, or
  attorney's office).
- Price/date/address fields are verbatim from county records; nothing here is enriched or inferred.

## Outreach reminder
This list is for **manual, personal outreach** (direct mail, a real one-to-one note, a phone call).
Do **not** mass-email these entities — unsolicited bulk email to a scraped list is both ineffective
and a CAN-SPAM liability.
