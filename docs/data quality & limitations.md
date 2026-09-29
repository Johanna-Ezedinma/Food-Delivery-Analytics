# Data Quality, Profiling & Limitations

This document covers everything that happened before a single chart got built. It's here because the honest version of this project isn't just "here's a dashboard," it's "here's a dashboard, and here's exactly what I checked before trusting the numbers in it."

The challenge brief made several specific claims about this data (rush hour delays, weather effects, a distance cutoff, a losing delivery corridor). Before building anything around those claims, I checked them against the actual numbers. Some held up. Most didn't. This document walks through what I found, how I checked it, and where this dataset genuinely can't tell us more, no matter how hard you look.

---

## Why check at all

The data dictionary that came with this challenge described specific ranges for several columns, promised delivery times between 25 and 45 minutes, food temperature averaging around 58°C, delivery distances up to 12.5 km. Before building a single measure, I compared what the dictionary said against what the actual CSV files contained.

They didn't match.

## Row level problems: values that can't be real

**Delivery times.** The dictionary said promised delivery time should sit between 25 and 45 minutes. The real data ranges from 0 to 1,000 minutes, a "promised" delivery of over 16 hours. Actual delivery time shows the same pattern.

**Food temperature.** Documented to average around 58°C. The real column ranges from 0.6°C to 999.9°C. Water boils at 100°C. There is no version of "food delivered to a customer's door" that reaches 999°C. I checked how much of the column falls outside a realistic 10 to 100°C range: 4,566 of 5,000 rows, 91%. That's not a handful of typos. That column is unusable as a real measurement, and nothing built on this dashboard treats it as one.

**Rider speed.** Some riders in the dataset average up to 992 km/h. No motorcycle or bicycle averages that in city traffic.

None of these rows were deleted. Each got a flag column instead (`Delivery Times Plausible?`, `Food Temp Plausible?`, `Speed Plausible?`), so the decision to include or exclude them stays visible and reversible rather than silently baked in.

## Entity level problems: things that should agree with each other, and don't

**Kitchen location.** Each of the 4 kitchens has three separate location signals: its name (e.g. "Golden Wok Lekki Phase 1"), its recorded LGA (e.g. "Yaba"), and its GPS coordinates. I checked all three against each other, and against real-world coordinates for the actual Lagos neighborhoods involved. In 3 of 4 kitchens, all three signals disagree with each other. There is no reliable way to say where any of these kitchens are actually located, beyond their name being a label of convenience, not a verified fact.

**Zone names aren't unique.** Ajegunle, Bariga, Shomolu, Ogudu, and Egbeda each appear twice among the 20 delivery zones, attached to different underlying zone IDs. Grouping or charting by zone name alone would silently merge two different real places into one bar.

**Category sprawl.** Weather condition had 8 overlapping raw values (Sunny, Thunderstorm, Heavy Rain, Light Rain, Harmattan (Dusty), Humid/Hazy, Overcast, Partly Cloudy) where the dictionary expected 5. Meal period had a similar problem. Both were consolidated into cleaner groups with the mapping decisions documented as they were made.

## The bigger discovery: the data doesn't correlate with itself

This is the most important finding in the whole project, and it's not a data entry error, it's structural.

I checked the correlation between every pair of numeric columns that the brief implied should be related: delivery distance and profit, traffic friction and delay, promised time and actual time. Every single one came back at or near zero (distance to profit: -0.00002. Friction to delay: -0.003. Promised to actual: 0.01). These aren't small effects. They're statistically indistinguishable from no relationship at all.

**This meant the brief's claims needed testing one by one, not assuming.**

| Brief's claim                                                                                              | What I actually found                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rush hour + outer-ring orders take 90+ minutes, triple SLA, lose over ₦500                                 | Tested for orders matching every one of these conditions at once, negligible volume, not a real segment                                                                                                                                        |
| Rain/heavy rain increases traffic friction by 1.8x                                                         | Real gap across weather groups: 0.31 points on a 10 point scale. Chance of seeing a gap this size from pure luck: 23.5%. Not a real effect                                                                                                     |
| Orders over 8km show structurally negative profit                                                          | Profit per order across distance bands stays within ₦20 of each other (₦485 to ₦505). No cliff at 8km or anywhere else                                                                                                                         |
| Food temp drops below 45°C when delay exceeds 60 min, tied to low ratings                                  | Can't be tested. The food temperature column itself is 91% physically impossible, see above                                                                                                                                                    |
| The Lekki kitchen serving VI and Ikoyi is an unprofitable corridor due to bridge and expressway congestion | "VI" doesn't exist as a zone anywhere in this dataset. Ikoyi is a mid-tier zone, not outer-ring. The Lekki-named kitchen's own location can't be verified (see above). Profit for this corridor sits within a few naira of the network average |

## A deeper find: profit was never actually calculated from cost

The `order_profit_ngn` column is supposed to represent revenue minus delivery cost. I checked this directly: computed `order_value_ngn` minus `delivery_cost_ngn` myself, and compared it row by row against the actual profit column.

Zero of 5,000 rows matched. The correlation between the two is 0.025, essentially nothing. On top of that, delivery cost itself doesn't scale with distance either (correlation 0.016). The profit figure behaves like its own independent random number, not something computed from the other columns in its row.

This explains why no distance-to-profit cliff exists in this data. The mechanism the brief describes (distance drives up cost, which eats into profit) was simply never built into how this dataset was generated. This isn't a bug in the dashboard's measures. `SUM(order_profit_ngn)` is exactly the correct way to total the column as given. The gap is in the source data, not the formula.

## How "is this real or noise" was actually decided

A gap between two numbers isn't automatically meaningful just because it exists. Throughout this project, any comparison worth reporting was checked with a permutation test: take the real values, shuffle which group each one belongs to thousands of times, and see how often a gap this size shows up purely by chance with no real cause behind it.

The rule used throughout: under 5% chance by luck, treat it as real. Over 10%, treat it as noise. In between, call it a lead worth investigating further, not a finding.

This caught several things that looked real at first glance and weren't:

- A 64 minute weather delay gap (comparing whichever two weather types looked most extreme): 41% chance by luck. Noise.
- A 24 minute delay gap by vehicle type: 49% chance by luck. Noise.
- An average rider speed correlation with zone-level breach rate: looked real in the raw data, vanished once the impossible speed values (see above) were filtered out.
- A profit gap between meal periods (Lunch highest, Late Night lowest): 59% chance by luck. Noise.

## What's genuinely still unexplained, and why

One finding survived every check: Lekki Phase 2 misses its promised delivery time 56.35% of the time. Ilupeju, handling the exact same order volume (252 orders each), misses only 45.63% of the time. That's a real, specific, 10.7 point gap between two zones with identical workloads.

I checked every explanatory column available: rush hour timing, weather, zone tier, each zone's traffic index, average rider experience serving that zone, average rider speed. None of them explain the gap. This isn't a failure to look hard enough. It's a genuine limitation of what this dataset contains.

What's missing, and what would actually be needed to explain it: route level detail, specific road or access conditions, live congestion data, delivery point complexity (gated estates, security checks). None of that exists in these five tables. The honest next step isn't more dashboarding, it's field verification, which is exactly what the dashboard recommends.

## Summary of what this means for trusting the dashboard

Every number on the dashboard is real and drawn straight from the source data. What changed, based on everything above, is which claims get stated as fact versus flagged as untested:

- Profit margin (0.65%), SLA breach rate (50%), the Lekki Phase 2 vs Ilupeju gap: real, tested, reportable as findings.
- Weather effects, vehicle type effects, meal period effects, rush hour effects: tested and found to be noise, reported as "no meaningful difference" rather than a driver.
- Food temperature analysis, the specific VI/Ikoyi corridor claim, a distance-driven profit cliff: not supported by this data at all, and not presented as if they were.
