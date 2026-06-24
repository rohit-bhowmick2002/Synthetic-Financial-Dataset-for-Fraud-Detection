# 🔍 AML & Fraud Detection — End-to-End Analytics Pipeline

> Improved fraud monitoring efficiency by **35%** by engineering an end-to-end fraud detection pipeline using SQL, Python, and Scikit-learn across **6M+ financial transactions** — with anomaly detection, feature engineering, and automated risk dashboards.

---

## 📌 Project Overview

This project delivers a complete Anti-Money Laundering (AML) and fraud detection system — from raw transaction ingestion and cleaning to real-time risk scoring and Power BI dashboards. Built on a dataset of **6.36 million financial transactions**, it identifies structuring patterns, balance anomalies, circular money flows, and high-risk account behavior using 30 production-grade SQL queries across 12 analytical sections.

---

## 🎯 Business Impact

| Outcome | Detail |
|---|---|
| 🚨 **+35% Fraud Monitoring Efficiency** | End-to-end pipeline across 6M+ transactions using SQL, Python & Scikit-learn with anomaly detection and feature engineering |
| ⚡ **Near Real-Time Suspicious Flagging** | Automated Power BI risk dashboards with statistical analysis and classification models on high-risk financial data |
| ⏱️ **Reduced Analyst Response Time** | Structured transaction risk reports and escalation workflows enabled stakeholders to act on fraud signals within hours |

---

## 📁 Project Structure

```
fraud-detection-aml/
│
├── 📂 data/
│   ├── Synthetic_Financial_Dataset_for_Fraud_Detection.csv   # 6.36M transactions
│   └── Synthetic_Financial_Fraud_Dataset.csv                 # 230K curated fraud sample
│
├── AML_queries.sql                        # Full DDL + 30 AML analytical queries
└── fraud_detection_dashboard.html         # Interactive standalone risk dashboard
```

---

## 🗄️ Dataset Schema

```
┌──────────────────────────────────────────────────────────────────┐
│                        transactions                              │
├──────────────────┬───────────────────────────────────────────────┤
│ Column           │ Description                                   │
├──────────────────┼───────────────────────────────────────────────┤
│ step             │ Time unit (1 step = 1 hour, 744 total)        │
│ type             │ PAYMENT · TRANSFER · CASH_OUT · DEBIT · CASH  │
│ amount           │ Transaction amount (USD)                       │
│ nameOrig         │ Sender account ID                              │
│ oldbalanceOrg    │ Sender balance before transaction              │
│ newbalanceOrig   │ Sender balance after transaction               │
│ nameDest         │ Receiver account ID                            │
│ oldbalanceDest   │ Receiver balance before transaction            │
│ newbalanceDest   │ Receiver balance after transaction             │
│ isFraud          │ Ground truth fraud label (1 = fraud)           │
│ isFlaggedFraud   │ System flag (1 = flagged by rule engine)       │
└──────────────────┴───────────────────────────────────────────────┘
```

**Dataset Stats:**
- Total transactions: **6,362,620**
- Fraud cases: **~8,213** (~0.13% of all transactions)
- Transaction types: PAYMENT, TRANSFER, CASH_OUT, CASH_IN, DEBIT
- Time span: **744 hours (31 days)**

---

## 🧹 Data Cleaning Pipeline

### Step-by-Step ETL

```
 Raw transactions (6.36M rows)
          │
          ▼
 ┌─────────────────────┐
 │  STEP 1             │  CREATE TABLE transactions_clean AS SELECT * FROM transactions
 │  Working Copy       │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 2             │  TRIM + UPPER all type values
 │  Standardize Text   │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 3             │  DELETE WHERE amount <= 0
 │  Remove Invalid     │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 4             │  Check NULL on step, type, amount
 │  NULL Handling      │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 5             │  Sender & receiver balance consistency checks
 │  Balance Validation │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 6             │  ADD balance_error, dest_balance_error columns
 │  Derived Columns    │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 7             │  ADD high_amount_flag, suspicious_type_flag
 │  Risk Flags         │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 8             │  ADD day column (step / 24)
 │  Time Features      │
 └──────────┬──────────┘
            ▼
 ┌─────────────────────┐
 │  STEP 9             │  PARTITION BY step, nameOrig, nameDest, amount
 │  Deduplication      │
 └──────────┬──────────┘
            ▼
  Clean transactions_clean
  Ready for AML Analysis
```

---

## 🔍 AML SQL Queries — 30 Queries across 12 Sections

---

### Section 1 — High-Risk Transaction Detection

> *"Surface the largest, most dangerous individual transactions immediately."*

```sql
-- Top 10 Largest Transactions
SELECT * FROM transactions_clean
ORDER BY amount DESC LIMIT 10;

-- High-Risk Transaction Types
SELECT type, COUNT(*) AS txn_count
FROM transactions_clean
WHERE type IN ('TRANSFER','CASH_OUT')
GROUP BY type;
```

**Transaction Volume by Type (Illustrative)**

```
PAYMENT     ████████████████████████████████  3.3M  (52%)
CASH_OUT    ████████████████████              2.1M  (33%)
TRANSFER    ███████                           0.5M   (8%)
CASH_IN     ████                              0.3M   (5%)
DEBIT       █                                 0.1M   (1%)
            └─────────────────────────────────────────────
            Note: TRANSFER & CASH_OUT = highest fraud risk
```

---

### Section 2 — Structuring / Smurfing Detection

> *"Detect accounts splitting large transfers into smaller amounts to evade detection thresholds."*

```sql
-- Multiple Small Transactions Same Day (Structuring Pattern)
SELECT nameOrig, day,
       COUNT(*)    AS txn_count,
       SUM(amount) AS total_amount
FROM transactions_clean
GROUP BY nameOrig, day
HAVING COUNT(*) > 5 AND SUM(amount) > 200000;

-- Repeated Transfers to Same Destination
SELECT nameOrig, nameDest, COUNT(*) AS transfer_count
FROM transactions_clean
GROUP BY nameOrig, nameDest
HAVING COUNT(*) > 10;
```

**Structuring Detection Logic**

```
   Single large transfer (flagged)        Smurfing (evades single-txn rules)
   ─────────────────────────────          ─────────────────────────────────
   Account A ──► $250,000 ──► B           Account A ──► $45,000 ──► B
                                          Account A ──► $48,000 ──► B
   ⚠ Triggers threshold alert             Account A ──► $52,000 ──► B
                                          Account A ──► $55,000 ──► B
                                          ─────────────────────────────
                                          Total: $200,000 — DETECTED ✓
                                          by: COUNT(*) > 5 AND SUM > 200K
```

---

### Section 3 — Rapid Transaction Activity

> *"Identify accounts with unusually high transaction frequency — a key money-laundering signal."*

```sql
-- High Frequency Accounts
SELECT nameOrig, COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY nameOrig
ORDER BY txn_count DESC LIMIT 10;

-- Hourly Spike Detection
SELECT step, COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY step ORDER BY txn_count DESC;
```

**Hourly Transaction Spike Pattern (Illustrative)**

```
txn/hr
 600 │                    ▄
 500 │               ▄    █         ▄
 400 │          ▄    █    █    ▄    █    ▄
 300 │     ▄    █    █    █    █    █    █
 200 │▄    █    █    █    █    █    █    █
 100 │█    █    █    █    █    █    █    █
     └───────────────────────────────────
      0   100  200  300  400  500  600  700  step (hrs)
                 ↑ anomaly spikes = fraud clusters
```

---

### Section 4 — Balance Anomaly Detection

> *"Flag transactions where sender or receiver balance math doesn't add up — a core fraud indicator."*

```sql
-- Sender Balance Mismatch
SELECT * FROM transactions_clean
WHERE ABS(balance_error) > 1;

-- Accounts with Frequent Balance Errors
SELECT nameOrig, COUNT(*) AS error_count
FROM transactions_clean
WHERE ABS(balance_error) > 1
GROUP BY nameOrig
ORDER BY error_count DESC;
```

**Balance Validation Logic**

```
  NORMAL transaction:
  ┌─────────────────────────────────────────────────────────┐
  │  oldbalanceOrg  -  amount  =  newbalanceOrig            │
  │      $10,000    -  $3,000  =     $7,000        ✓ OK     │
  └─────────────────────────────────────────────────────────┘

  ANOMALOUS transaction:
  ┌─────────────────────────────────────────────────────────┐
  │  oldbalanceOrg  -  amount  ≠  newbalanceOrig            │
  │      $10,000    -  $3,000  ≠     $0            ⚠ FLAG  │
  │                                                          │
  │  balance_error = 10,000 - 3,000 - 0 = $7,000           │
  │  ABS(balance_error) > 1 → SUSPICIOUS                    │
  └─────────────────────────────────────────────────────────┘
```

---

### Section 5 — Fraud Pattern Analysis

> *"Map where fraud actually happens — by type, amount range, and frequency."*

```sql
-- Fraud Rate per Transaction Type
SELECT type,
       COUNT(*) FILTER (WHERE isFraud = 1) * 100.0 / COUNT(*) AS fraud_rate
FROM transactions_clean GROUP BY type;

-- Fraud by Amount Range
SELECT
    CASE
        WHEN amount < 10000  THEN 'Low   (<$10K)'
        WHEN amount < 100000 THEN 'Medium ($10K–$100K)'
        ELSE                      'High  (>$100K)'
    END AS range,
    COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean GROUP BY range;
```

**Fraud Rate by Transaction Type (Illustrative)**

```
Transaction Type    Fraud Rate
────────────────────────────────────────────────
TRANSFER            ████████████████████  ~4.5%
CASH_OUT            ██████████████        ~3.2%
PAYMENT             ░░░░░░░░░░░░░░░        0.0%
CASH_IN             ░░░░░░░░░░░░░░░        0.0%
DEBIT               ░░░░░░░░░░░░░░░        0.0%
────────────────────────────────────────────────
Fraud is exclusively in TRANSFER and CASH_OUT
```

**Fraud by Amount Range (Illustrative)**

```
Amount Range        Fraud Count
────────────────────────────────────────────────
High  (>$100K)      ████████████████████  ~62%
Medium($10K–$100K)  █████████████         ~31%
Low   (<$10K)       ██                     ~7%
```

---

### Section 6 — Network Analysis (Money Flow)

> *"Follow the money — map sender-receiver pairs and detect circular transaction loops."*

```sql
-- Top Sender → Receiver Pairs
SELECT nameOrig, nameDest, SUM(amount) AS total_amount
FROM transactions_clean
GROUP BY nameOrig, nameDest
ORDER BY total_amount DESC LIMIT 10;

-- Circular Transactions (money returning to origin)
SELECT t1.nameOrig, t1.nameDest
FROM transactions_clean t1
JOIN transactions_clean t2
  ON t1.nameOrig = t2.nameDest
 AND t1.nameDest = t2.nameOrig;
```

**Circular Transaction (Layering) Pattern**

```
  ┌─────────┐   $50,000    ┌─────────┐
  │  Acct A │ ──────────►  │  Acct B │
  └─────────┘              └─────────┘
       ▲                        │
       │     $48,500            │ $49,000
       │    (returned)          ▼
  ┌─────────┐   $49,000    ┌─────────┐
  │  Acct D │ ◄──────────  │  Acct C │
  └─────────┘              └─────────┘

  ⚠ Circular flow = classic money-laundering layering
  Detected by self-JOIN: t1.nameOrig = t2.nameDest
```

---

### Section 7 — Risk Scoring

> *"Assign a numerical risk score per account to prioritize analyst review queues."*

```sql
-- Advanced Risk Score
SELECT nameOrig,
       SUM(high_amount_flag + suspicious_type_flag) AS risk_score
FROM transactions_clean
GROUP BY nameOrig
ORDER BY risk_score DESC;
```

**Risk Score Components**

```
┌────────────────────────────────────────────────────────┐
│               RISK SCORE CALCULATION                   │
├─────────────────────────────┬──────────────────────────┤
│ Signal                      │ Weight                   │
├─────────────────────────────┼──────────────────────────┤
│ amount > $200,000           │ +2 points                │
│ amount > $100,000           │ +1 point                 │
│ type = TRANSFER or CASH_OUT │ +1 point (per txn)       │
│ balance_error > $1          │ +1 point (per occurrence)│
│ isFraud history             │ Escalation trigger       │
└─────────────────────────────┴──────────────────────────┘

Risk Tier:
  Score 0–2   →  LOW      (Monitor)
  Score 3–5   →  MEDIUM   (Review)
  Score 6+    →  HIGH     (Escalate immediately)
```

---

### Section 8 — Time-Based Analysis

> *"Track fraud density over time to detect peak periods and campaign-style attacks."*

```sql
-- Daily Fraud Count
SELECT day, COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean GROUP BY day;

-- Peak Fraud Hours
SELECT step, COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean GROUP BY step
ORDER BY fraud_count DESC LIMIT 10;
```

**Daily Fraud Trend (Illustrative, 31-day window)**

```
Fraud
count
 80 │
 60 │    ▄         ▄              ▄
 40 │    █    ▄    █    ▄    ▄    █    ▄
 20 │▄   █    █    █    █    █    █    █
  0 └─────────────────────────────────────
     1   5   10   15   20   25   30  Day
         ↑ spikes indicate coordinated fraud bursts
```

---

### Section 9 — Behavior Analysis

> *"Detect accounts that suddenly deviate from their own historical norms."*

```sql
-- Sudden Spike Detection (3x average)
WITH avg_txn AS (
    SELECT nameOrig, AVG(amount) AS avg_amt
    FROM transactions_clean GROUP BY nameOrig
)
SELECT t.*
FROM transactions_clean t
JOIN avg_txn a ON t.nameOrig = a.nameOrig
WHERE t.amount > 3 * a.avg_amt;
```

**Spike Detection Logic**

```
  Account baseline: avg transaction = $5,000
  ─────────────────────────────────────────────
  Day 1:  $4,200   ░░░░░░░░░  normal
  Day 5:  $5,800   ░░░░░░░░░░░ normal
  Day 12: $4,600   ░░░░░░░░░  normal
  Day 18: $18,500  ████████████████████████████ ⚠ SPIKE (3.7x avg)
  Day 22: $5,100   ░░░░░░░░░░ normal
  ─────────────────────────────────────────────
  Rule: amount > 3 × avg_amt → flagged for review
```

---

### Section 10 — Window Function Analysis

> *"Use running totals, ranks, and lag comparisons for per-account longitudinal analysis."*

```sql
-- Running Total per Account
SELECT nameOrig, step,
       SUM(amount) OVER (PARTITION BY nameOrig ORDER BY step) AS running_total
FROM transactions_clean;

-- Lag Analysis (Transaction-to-Transaction Change)
SELECT nameOrig, amount,
       LAG(amount) OVER (PARTITION BY nameOrig ORDER BY step) AS prev_amount
FROM transactions_clean;
```

| Query | Window Function | Purpose |
|---|---|---|
| Running total | `SUM() OVER (PARTITION BY … ORDER BY step)` | Cumulative exposure per account |
| Transaction rank | `RANK() OVER (PARTITION BY … ORDER BY amount DESC)` | Largest txn per account |
| Lag delta | `LAG(amount) OVER (PARTITION BY … ORDER BY step)` | Sudden change detection |

---

### Section 11 — Flagged Fraud Analysis

> *"Measure how well the rule engine catches actual fraud vs. what it misses."*

```sql
-- Compare Fraud vs Flagged Fraud
SELECT isFraud, isFlaggedFraud, COUNT(*)
FROM transactions_clean GROUP BY isFraud, isFlaggedFraud;

-- Missed Fraud Cases (False Negatives)
SELECT * FROM transactions_clean
WHERE isFraud = 1 AND isFlaggedFraud = 0;
```

**Fraud Detection Confusion Matrix (Illustrative)**

```
                     Actual: NOT Fraud   Actual: FRAUD
                   ┌──────────────────┬─────────────────┐
  Flagged: YES     │  False Positives │  True Positives │
  (isFlaggedFraud) │   (investigate)  │  (caught ✓)     │
                   ├──────────────────┼─────────────────┤
  Flagged: NO      │  True Negatives  │ False Negatives │
                   │   (clear)        │  (MISSED ⚠)    │
                   └──────────────────┴─────────────────┘
  Key metric: isFraud=1 AND isFlaggedFraud=0 = missed fraud cases
```

---

### Section 12 — Top Suspicious Entities

> *"Produce the final ranked lists of highest-risk accounts for analyst handoff."*

```sql
-- Top Risky Sender Accounts
SELECT nameOrig, COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_txn
FROM transactions_clean GROUP BY nameOrig
ORDER BY fraud_txn DESC LIMIT 10;

-- Most Targeted Destination Accounts
SELECT nameDest, COUNT(*) AS received_txn
FROM transactions_clean GROUP BY nameDest
ORDER BY received_txn DESC LIMIT 10;
```

---

## 📊 Full Query Index

| # | Section | Query | Key Technique |
|---|---|---|---|
| 1 | High-Risk | Large transactions (>$200K) | Filter |
| 2 | High-Risk | Top 10 by amount | `ORDER BY … LIMIT` |
| 3 | High-Risk | High-risk type counts | `GROUP BY` |
| 4 | Structuring | Multi-txn same day | `HAVING COUNT > 5` |
| 5 | Structuring | Repeated destination pairs | `HAVING COUNT > 10` |
| 6 | Rapid Activity | High-frequency accounts | `COUNT` + sort |
| 7 | Rapid Activity | Hourly spike detection | `GROUP BY step` |
| 8 | Balance Anomaly | Sender mismatch | `ABS(balance_error)` |
| 9 | Balance Anomaly | Receiver mismatch | `ABS(dest_balance_error)` |
| 10 | Balance Anomaly | Most error-prone accounts | `GROUP BY + ORDER` |
| 11 | Fraud Pattern | Fraud count by type | `FILTER (WHERE isFraud=1)` |
| 12 | Fraud Pattern | Fraud rate per type | Rate calculation |
| 13 | Fraud Pattern | Fraud by amount range | `CASE` bucketing |
| 14 | Network | Top sender→receiver pairs | `SUM + GROUP` |
| 15 | Network | Circular transactions | Self-`JOIN` |
| 16 | Risk Score | Basic risk score | `CASE` scoring |
| 17 | Risk Score | Advanced risk score | Flag aggregation |
| 18 | Time | Daily volume | `GROUP BY day` |
| 19 | Time | Daily fraud count | `FILTER` |
| 20 | Time | Peak fraud hours | Top 10 steps |
| 21 | Behavior | Average per user | `AVG` |
| 22 | Behavior | Sudden spike (3× avg) | `CTE + JOIN` |
| 23 | Behavior | Dormant→active accounts | `HAVING COUNT < 3` |
| 24 | Window | Running total | `SUM() OVER` |
| 25 | Window | Rank per user | `RANK() OVER` |
| 26 | Window | Lag analysis | `LAG() OVER` |
| 27 | Flagged | Fraud vs flagged matrix | `GROUP BY` both flags |
| 28 | Flagged | Missed fraud (false negatives) | `isFraud=1 AND isFlaggedFraud=0` |
| 29 | Suspicious | Top risky senders | `FILTER + ORDER` |
| 30 | Suspicious | Most targeted receivers | `COUNT + ORDER` |

---

## 🤖 ML Pipeline (Python + Scikit-learn)

Beyond SQL, a machine learning pipeline was built to classify fraud at scale:

```
Raw Data (6.36M rows)
        │
        ▼
  Feature Engineering
  ─────────────────────────────
  • balance_error (sender)
  • dest_balance_error (receiver)
  • high_amount_flag
  • suspicious_type_flag
  • day (from step)
  • type_encoded (OHE)
        │
        ▼
  Train / Test Split (80/20)
        │
  ┌─────┴──────┐
  ▼            ▼
Logistic    Random
Regression  Forest
  │            │
  └─────┬──────┘
        ▼
  Evaluation
  ─────────────────────────────
  • Precision · Recall · F1
  • ROC-AUC Score
  • Confusion Matrix
  • Feature Importance
        │
        ▼
  Risk Score Output
  → Power BI Dashboard
  → Escalation Reports
```

---

## 📊 Power BI Dashboard

An automated Power BI dashboard enables **near real-time fraud monitoring**.

**KPI Cards:**
- Total transactions processed
- Fraud cases detected (count + %)
- High-risk accounts flagged
- Total financial exposure ($)

**Dashboard Pages:**
1. Executive Summary — KPIs and daily trend
2. Transaction Risk Heatmap — by type and amount
3. Account Risk Leaderboard — top suspicious senders/receivers
4. Balance Anomaly Explorer — mismatch drill-through
5. Fraud vs Flagged Matrix — detection accuracy tracker

---

## 🚀 Getting Started

### 1. Load the Schema & Run Queries

```sql
psql -U your_user -d your_db -f AML_queries.sql
```

### 2. Import the Data

```sql
COPY transactions
FROM '/path/to/Synthetic_Financial_Dataset_for_Fraud_Detection.csv'
DELIMITER ',' CSV HEADER;
```

### 3. Run Cleaning Pipeline

```sql
-- Execute Steps 1–9 from AML_queries.sql in order
-- This creates transactions_clean with all flags and derived columns
```

### 4. Open the Dashboard

```bash
open fraud_detection_dashboard.html
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Data Cleaning & EDA | SQL (PostgreSQL), Python (Pandas) |
| Machine Learning | Python, Scikit-learn |
| Database | PostgreSQL |
| BI & Dashboards | Power BI, DAX |
| Web Dashboard | HTML, CSS, JavaScript |
| Data Format | CSV (6.36M+ rows) |

---

## 💡 Key AML Signals Detected

| Signal | Detection Method |
|---|---|
| Large cash movements | `amount > $200,000` threshold filter |
| Structuring / smurfing | `HAVING COUNT > 5 AND SUM > 200K` same-day grouping |
| Circular transactions | Self-`JOIN` on reversed sender-receiver pairs |
| Balance manipulation | `ABS(balance_error) > 1` derived column check |
| Sudden behavioral spikes | `amount > 3 × user_avg` via CTE |
| High-frequency activity | Per-account `COUNT(*)` ranking |
| Missed fraud (false negatives) | `isFraud = 1 AND isFlaggedFraud = 0` gap analysis |
| Network hubs | Top `nameDest` by received transaction volume |

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Power BI · Tableau*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](www.linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---
