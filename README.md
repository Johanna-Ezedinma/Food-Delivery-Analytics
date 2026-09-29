# Golden Wok Food Delivery Analytics

Analyzing two years of delivery data for Golden Wok, a 4-kitchen food delivery operation serving 20 zones across Lagos, Nigeria.

---

## The story

Golden Wok operates a 4-kitchen food delivery network serving 20 zones across Lagos, Nigeria.

Between 2023 and 2024, the business processed 5,000 orders, averaging 208 orders and roughly ₦103,500 in profit every month.

While taking home over ₦100k a month sounds decent at first glance, looking under the hood reveals a paper-thin profit margin. Golden Wok keeps just 0.65% of every naira that comes through the door. Put another way, out of every ₦100 generated in revenue, less than 1 naira remains as profit.

![Executive Overview](<aassets/Executive Overview.jpg>)

Operational efficiency tells a similar story. Across the entire operation, roughly half of all orders, about 104 every month, miss their promised delivery time. But these delays aren't spread evenly:

- Lekki Phase 2 sits at the bottom, missing its SLA 56% of the time.
- Ilupeju, by contrast, handles the exact same volume (252 orders) but misses 46% of the time.

That 10 point gap between two zones handling identical workloads pointed to room for improvement worth digging into.

![Delivery & SLA Performance](<aassets/Delivery & SLA Performance.jpg>)

Digging into the data to find obvious culprits, rush hour traffic, weather disruptions, distance from kitchens, area congestion, or rider experience, turned up no clear answers. The performance gap between Lekki Phase 2 and Ilupeju isn't explained by any of the usual operational variables. Every one of these was tested statistically, not just eyeballed, more on that in the data quality doc linked below.

![Profitability & Corridors](<aassets/Profitability & Corridors.jpg>)

---

![Kitchen & Zone](<aassets/Kitchen & Zone.jpg>)

## Actionable takeaways:

1. **The thin margin is a systemic, company-wide issue, not a local zone problem.** Profit per order barely changes regardless of how you slice it, by distance, kitchen, or time of day. Fixing profitability requires structural shifts across the entire business, such as raising average order value or lowering unit delivery costs.
2. **The delay gap points to unmeasured ground realities.** The bottleneck in Lekki Phase 2 is likely driven by factors the current metrics don't capture, specific road conditions, estate access delays, or local delivery friction.

## Recommendations

**Address profitability systemically.** Because profit per order barely changes regardless of kitchen, distance, or time of day, margin improvement has to be handled company-wide. Golden Wok should focus on driving up average order value (meal bundles, upsells) and reducing unit delivery costs across all 4 kitchens.

**Benchmark on the ground realities.** Conduct a direct field comparison between Ilupeju and Lekki Phase 2. Study what Ilupeju's team gets right under the exact same volume, and track uncaptured ground factors in Lekki Phase 2, such as estate gates, security checks, street access, and known high-congestion corridors like the Lekki-Epe Expressway and Third Mainland Bridge. The dataset's own traffic friction metric shows no measurable link to delay, so if congestion is genuinely a factor here, it isn't currently being captured and needs direct, on-the-ground verification, not just more dashboarding.

## What's in this repo

| File                              | What it is                                                                                                                      |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `golden_wok_dashboard.pbix`       | The full Power BI file, all 4 pages, all DAX measures                                                                           |
| `README.md`                       | This file                                                                                                                       |
| `DATA_QUALITY_AND_LIMITATIONS.md` | A full walkthrough of the cleaning process, every judgment call made along the way, and what this dataset can and can't tell us |
| `data/`                           | The 5 source CSVs used to build the model                                                                                       |

## Tools used

Power BI (Power Query, DAX), Python (pandas, for verifying findings before they made it onto a chart)

## A note on the numbers

Every claim on this dashboard was checked against the raw data before it was written down, not assumed from the challenge brief. Several things the brief expected to find (a distance-profit cliff, a weather-driven delay spike, a specific congestion corridor) turned out not to hold up once tested properly. Rather than build a dashboard around claims the data doesn't support, this project reports what's actually there, including the parts that turned out to be dead ends. The full breakdown of what was tested, how, and what didn't survive the check, is in `DATA_QUALITY_AND_LIMITATIONS.md`.
