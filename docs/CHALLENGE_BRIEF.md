# Data Challenge

## 🎯 Your Role

Step into the role of a data analyst investigating golden wok delivery radius and urban traffic friction matrix. 
You've been provided with a dataset spanning multiple dimensions and time periods. 
Your mission is to create an analytical report that uncovers patterns, drives insights, 
and delivers actionable recommendations to stakeholders.

## 📊 The Scenario

Analyze this dataset.

### Dataset Overview
- **Dimensions**: 4 dimension tables tracking key entities
- **Facts**: 1 fact tables recording transactions and events
- **Scope**: Spans 2023-01-01 to 2024-12-31
- **Currency**: NGN

## 🔍 Analysis Areas

Look for patterns and insights across these key areas:

• Orders placed during rush hours (07:00-09:00, 16:30-19:30) to outer-ring zones exceed 90 min actual delivery time, triple promised SLA, and yield average order_profit_ngn below -500.
• When weather_condition is Rain or Heavy Rain, traffic_friction_score is 1.8x higher and actual_delivery_min increases by ~28 min on average versus Clear days.
• Orders with delivery_distance_km above 8 km show structurally negative order_profit_ngn regardless of order value, as delivery_cost_ngn rises faster than revenue scales.
• food_temp_on_arrival_c drops below 45 Celsius for orders where actual_delivery_min exceeds 60, correlated with customer_rating below 2.5.
• The Lekki kitchen serving VI and Ikoyi zones consistently records negative corridor profitability due to Third Mainland Bridge and Lekki-Epe Expressway congestion compounding delivery costs.

## ❓ Guiding Questions

Use these questions to guide your analysis. They're starting points—feel free to explore further:

### Temporal Trends
• How do key metrics change over time?
• Are there seasonal or cyclical patterns?
• When do peaks and valleys occur, and why?
• What events or conditions trigger significant changes?

### Entity Analysis
• Which entities (customers, products, vendors, etc.) drive the most activity?
• How do different segments perform relative to each other?
• What characteristics distinguish high-performing entities from others?
• Are there geographic or categorical hotspots?

### Transaction Patterns
• What are the most common transaction types and volumes?
• How are transactions distributed across dimensions?
• What correlations exist between different metrics?
• Are there anomalies or unexpected patterns?

### Cross-Dimensional Insights
• How do dimensions interact to affect outcomes?
• Which combinations of attributes are most or least common?
• Do certain entity pairs have stronger relationships than others?
• What can you learn from relationships and associations?

## 💡 Impact & Purpose

Your analysis should help stakeholders:
- Identify opportunities and areas of concern
- Make data-driven strategic decisions
- Understand what drives business performance
- Predict future trends based on historical patterns
- Optimize operations and resource allocation

## 📋 Deliverables

Create a professional analytical report that includes:

1. **Executive Summary**
   - Key findings and recommendations
   - High-impact insights in plain language

2. **Detailed Analysis**
   - Visualizations showing trends and patterns
   - Statistical summaries and breakdowns
   - Answers to the guiding questions

3. **Actionable Insights**
   - What you discovered and why it matters
   - Recommended next steps or actions
   - Areas for deeper investigation

## 📁 Data Dictionary

See `DATA_DICTIONARY.md` for detailed descriptions of all tables and columns.

## 🚀 Getting Started

1. **Explore the data**: Start with summary statistics and distributions
2. **Check for issues**: Look for missing values, outliers, and data quality concerns
3. **Visualize relationships**: Create charts to explore patterns and correlations
4. **Test hypotheses**: Use your guiding questions to structure your analysis
5. **Synthesize insights**: Connect findings across dimensions to tell a coherent story

---
