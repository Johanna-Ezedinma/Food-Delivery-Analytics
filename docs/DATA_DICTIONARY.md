# Data Dictionary

**Theme:** Golden Wok Delivery Radius and Urban Traffic Friction Matrix
**Generated:** 2026-07-11 07:43:47
**Date Range:** 2023-01-01 to 2024-12-31
**Currency:** NGN

---

## Table of Contents

- [dim_delivery_zone](#dim_delivery_zone)
- [dim_kitchen](#dim_kitchen)
- [dim_rider](#dim_rider)
- [dim_time_slot](#dim_time_slot)
- [fact_orders](#fact_orders)

---

## dim_delivery_zone

**Type:** DIMENSION
**Primary Key:** `zone_id`
**Estimated Rows:** 20

### Description

Captures key business metrics and dimensions.

### Columns

| Column Name | Data Type | Nullable | Unique | Description |
|---|---|---|---|---|
| `zone_id` | integer | No | No | Zone surrogate key |
| `zone_name` | string | No | No | Delivery zone label |
| `zone_lga` | string | No | No | Zone local govt area |
| `zone_tier` | string | No | No | Inner mid or outer ring |
| `avg_zone_traffic_index` | float | No | No | Historical congestion index |
| `zone_population_density` | string | No | No | High medium or low density |
| `baseline_delivery_min` | integer | No | No | Typical minutes no traffic |
| `is_restricted_zone` | boolean | No | No | Access restriction flag |

### Data Generation

| Column | Generator | Parameters |
|---|---|---|
| `zone_id` | sequence | — |
| `zone_name` | faker | — |
| `zone_lga` | faker | — |
| `zone_tier` | static | values=['Inner', 'Mid', 'Outer'] |
| `avg_zone_traffic_index` | numpy | distribution=uniform, low=2.0, high=9.0 |
| `zone_population_density` | static | values=['High', 'Medium', 'Low'] |
| `baseline_delivery_min` | numpy | distribution=uniform, low=15, high=55 |
| `is_restricted_zone` | faker | — |

## dim_kitchen

**Type:** DIMENSION
**Primary Key:** `kitchen_id`
**Estimated Rows:** 4

### Description

Captures key business metrics and dimensions.

### Columns

| Column Name | Data Type | Nullable | Unique | Description |
|---|---|---|---|---|
| `kitchen_id` | integer | No | No | Kitchen surrogate key |
| `kitchen_name` | string | No | No | Kitchen location name |
| `lga` | string | No | No | Lagos local govt area |
| `latitude` | float | No | No | Kitchen GPS latitude |
| `longitude` | float | No | No | Kitchen GPS longitude |
| `kitchen_capacity_orders_hr` | integer | No | No | Max orders per hour |
| `date_opened` | date | No | No | Kitchen launch date |
| `is_active` | boolean | No | No | Currently operating flag |

### Data Generation

| Column | Generator | Parameters |
|---|---|---|
| `kitchen_id` | sequence | — |
| `kitchen_name` | static | values=['Golden Wok Yaba', 'Golden Wok Lekki', 'Golden Wok Ikeja', 'Golden Wok Surulere'] |
| `lga` | static | values=['Yaba', 'Lekki', 'Ikeja', 'Surulere'] |
| `latitude` | static | values=[6.5158, 6.4698, 6.6018, 6.5022] |
| `longitude` | static | values=[3.3796, 3.5852, 3.3515, 3.3561] |
| `kitchen_capacity_orders_hr` | numpy | distribution=uniform, low=30, high=60 |
| `date_opened` | faker | — |
| `is_active` | static | values=[True] |

## dim_rider

**Type:** DIMENSION
**Primary Key:** `rider_id`
**Estimated Rows:** 60

### Description

Captures key business metrics and dimensions.

### Columns

| Column Name | Data Type | Nullable | Unique | Description |
|---|---|---|---|---|
| `rider_id` | integer | No | No | Rider surrogate key |
| `rider_name` | string | No | No | Rider full name |
| `assigned_kitchen_id` | integer | No | No | Primary kitchen base |
| `vehicle_type` | string | No | No | Motorcycle or bicycle |
| `experience_months` | integer | No | No | Months on platform |
| `avg_speed_kmh` | float | No | No | Rider average speed |
| `avg_rider_rating` | float | Yes | No | Historical rider rating |
| `is_active` | boolean | No | No | Currently active rider |

### Data Generation

| Column | Generator | Parameters |
|---|---|---|
| `rider_id` | sequence | — |
| `rider_name` | faker | — |
| `assigned_kitchen_id` | faker | — |
| `vehicle_type` | static | values=['Motorcycle', 'Bicycle', 'Motorcycle', 'Motorcycle'] |
| `experience_months` | numpy | distribution=uniform, low=1, high=48 |
| `avg_speed_kmh` | numpy | distribution=normal, mean=22, std=5 |
| `avg_rider_rating` | numpy | distribution=normal, mean=4.1, std=0.5 |
| `is_active` | faker | — |

## dim_time_slot

**Type:** DIMENSION
**Primary Key:** `time_slot_id`
**Estimated Rows:** 48

### Description

Captures key business metrics and dimensions.

### Columns

| Column Name | Data Type | Nullable | Unique | Description |
|---|---|---|---|---|
| `time_slot_id` | integer | No | No | Time slot surrogate key |
| `slot_label` | string | No | No | E.g. 07:30-08:00 |
| `hour_of_day` | integer | No | No | Hour 0 to 23 |
| `day_of_week` | string | No | No | Monday through Sunday |
| `is_weekend` | boolean | No | No | Weekend flag |
| `is_rush_hour` | boolean | No | No | AM PM peak flag |
| `meal_period` | string | No | No | Breakfast lunch dinner late |
| `weather_condition` | string | No | No | Clear rain harmattan |

### Data Generation

| Column | Generator | Parameters |
|---|---|---|
| `time_slot_id` | sequence | — |
| `slot_label` | faker | — |
| `hour_of_day` | numpy | distribution=uniform, low=0, high=23 |
| `day_of_week` | faker | — |
| `is_weekend` | faker | — |
| `is_rush_hour` | faker | — |
| `meal_period` | static | values=['Breakfast', 'Lunch', 'Dinner', 'Late Night'] |
| `weather_condition` | static | values=['Clear', 'Rain', 'Heavy Rain', 'Harmattan', 'Cloudy'] |

## fact_orders

**Type:** FACT
**Primary Key:** `order_id`
**Estimated Rows:** 5,000
**Grain:** one row per customer delivery order

### Description

Captures key business metrics and dimensions.

### Columns

| Column Name | Data Type | Nullable | Unique | Description |
|---|---|---|---|---|
| `order_id` | integer | No | No | Unique order identifier |
| `kitchen_id` | integer | No | No | Source dark kitchen |
| `zone_id` | integer | No | No | Delivery destination zone |
| `rider_id` | integer | No | No | Assigned delivery rider |
| `time_slot_id` | integer | No | No | Time-of-day slot key |
| `order_date` | date | No | No | Date order was placed |
| `order_value_ngn` | float | No | No | Gross order revenue NGN |
| `delivery_distance_km` | float | No | No | Kitchen to door distance |
| `promised_delivery_min` | integer | No | No | Quoted delivery minutes |
| `actual_delivery_min` | integer | No | No | Actual delivery minutes |
| `traffic_friction_score` | float | No | No | 0-10 congestion severity |
| `food_temp_on_arrival_c` | float | Yes | No | Celsius at doorstep |
| `customer_rating` | float | Yes | No | 1-5 star rating |
| `delivery_cost_ngn` | float | No | No | Rider fuel and time cost |
| `order_profit_ngn` | float | No | No | Profit after delivery cost |

### Data Generation

| Column | Generator | Parameters |
|---|---|---|
| `order_id` | sequence | — |
| `kitchen_id` | faker | — |
| `zone_id` | faker | — |
| `rider_id` | faker | — |
| `time_slot_id` | faker | — |
| `order_date` | faker | — |
| `order_value_ngn` | numpy | distribution=normal, mean=4800, std=1600 |
| `delivery_distance_km` | numpy | distribution=uniform, low=0.8, high=12.5 |
| `promised_delivery_min` | numpy | distribution=uniform, low=25, high=45 |
| `actual_delivery_min` | numpy | distribution=normal, mean=52, std=18 |
| `traffic_friction_score` | numpy | distribution=uniform, low=1.0, high=10.0 |
| `food_temp_on_arrival_c` | numpy | distribution=normal, mean=58, std=12 |
| `customer_rating` | numpy | distribution=uniform, low=1.0, high=5.0 |
| `delivery_cost_ngn` | numpy | distribution=normal, mean=1200, std=400 |
| `order_profit_ngn` | numpy | distribution=normal, mean=800, std=950 |

---

## Relationships

### Foreign Key Constraints

| From Table | From Column | To Table | To Column | Type |
|---|---|---|---|---|
| fact_orders | `kitchen_id` | dim_kitchen | `kitchen_id` | Many To One |
| fact_orders | `zone_id` | dim_delivery_zone | `zone_id` | Many To One |
| fact_orders | `rider_id` | dim_rider | `rider_id` | Many To One |
| fact_orders | `time_slot_id` | dim_time_slot | `time_slot_id` | Many To One |
| dim_rider | `assigned_kitchen_id` | dim_kitchen | `kitchen_id` | Many To One |

### Relationship Descriptions

- **fact_orders** has many to one **dim_kitchen**: `fact_orders.kitchen_id` references `dim_kitchen.kitchen_id`
- **fact_orders** has many to one **dim_delivery_zone**: `fact_orders.zone_id` references `dim_delivery_zone.zone_id`
- **fact_orders** has many to one **dim_rider**: `fact_orders.rider_id` references `dim_rider.rider_id`
- **fact_orders** has many to one **dim_time_slot**: `fact_orders.time_slot_id` references `dim_time_slot.time_slot_id`
- **dim_rider** has many to one **dim_kitchen**: `dim_rider.assigned_kitchen_id` references `dim_kitchen.kitchen_id`

---

## Data Quality & Characteristics

### Missing Values
Columns marked as 'Nullable: Yes' may contain null values representing missing data.

### Unique Constraints
Columns marked as 'Unique: Yes' have no duplicate values (excluding nulls).

### Primary Keys
Primary keys are unique identifiers with no null values.

### Temporal Coverage
All dates fall within: 2023-01-01 to 2024-12-31

---

*Dictionary generated on 2026-07-11 07:43:47*