# 🔍 Financial Fraud Detection & AML Analytics — SQL Intelligence System

> **Production-grade Anti-Money Laundering (AML) analytics platform** — analyzing 6.3M+ financial transactions worth over $1.14 Trillion to detect fraud patterns, identify structuring behavior, uncover balance anomalies, and build multi-layer risk scoring systems using advanced SQL.

---

## 📌 Project Overview

This project delivers a **comprehensive financial crime detection framework** built entirely in SQL, modeled on real-world AML compliance workflows used by financial institutions. It covers the full analytical pipeline — data ingestion, cleaning, feature engineering, risk flag creation, and 30 structured detection queries — across 12 analytical sections mimicking a real fraud investigation unit.

**Domain:** Financial Crime · Anti-Money Laundering · Risk Analytics  
**Stack:** SQL (PostgreSQL) · Python · HTML/CSS/JS · Interactive Dashboard  
**Data Scope:** 30-day simulation · 6.36M transactions · $1.14T total financial volume · Dual-dataset validation

---

## 📊 Key Business Impact

| Metric | Value |
|--------|-------|
| 💰 Total Financial Volume Analyzed | **$1.14 Trillion** |
| 🔄 Total Transactions | **6,362,620** |
| 🚨 Confirmed Fraud Transactions | **8,213 (0.129% fraud rate)** |
| 💸 Average Fraud Transaction Value | **$1,467,967** — 8.2× higher than legitimate avg |
| 🏦 Average Legitimate Transaction | **$178,197** |
| 📈 Max Single Transaction | **$92,445,517** |
| ⚠️ High-Value Transactions (>$200K) | **1,673,570 flagged** |
| 🔴 Balance Anomalies Detected | **2,488,652 records** |
| 🎯 System Flagged Fraud | **Only 16 of 8,213** — **99.8% miss rate exposed** |
| 🕳️ Missed Fraud Cases Identified | **8,197** — critical detection gap |
| ✅ False Positives | **0** — precision maintained |
| ⏱️ Simulation Duration | **743 hours (30 days)** |

---

## 🚨 Critical Finding

> The baseline fraud flagging system **missed 8,197 out of 8,213 actual fraud cases** — a **99.8% miss rate**. This project's SQL-based multi-signal detection framework was built specifically to close this gap using balance anomaly analysis, network pattern detection, behavioral spike alerts, and composite risk scoring.

---

## 🗂️ Data Architecture

```
transactions (raw)
│
├── Step 1: Create transactions_clean (working copy)
├── Step 2: Standardize text — TRIM + UPPER normalization
├── Step 3: Remove invalid records — amount <= 0 deleted
├── Step 4: NULL validation across all critical fields
├── Step 5: Balance consistency checks (sender + receiver)
├── Step 6: Derived columns — balance_error, dest_balance_error
├── Step 7: Risk flags — high_amount_flag, suspicious_type_flag
├── Step 8: Time features — step → day conversion
└── Step 9: Duplicate detection & removal via window functions
```

**Schema Fields:**
```sql
step              → Time unit (1 hour per step, 743 steps = 30 days)
type              → CASH_IN | CASH_OUT | TRANSFER | PAYMENT | DEBIT
amount            → Transaction value (up to $92.4M per transaction)
nameOrig          → Sender account ID
nameDest          → Receiver account ID
oldbalanceOrg     → Sender balance before transaction
newbalanceOrig    → Sender balance after transaction
oldbalanceDest    → Receiver balance before transaction
newbalanceDest    → Receiver balance after transaction
isFraud           → Ground truth fraud label (1 = fraud)
isFlaggedFraud    → System-generated flag (exposed as severely incomplete)
```

---

## 🔍 Fraud by Transaction Type

| Transaction Type | Volume | Fraud Cases | Fraud Rate |
|---|---|---|---|
| TRANSFER | 532,909 | **4,097** | **0.77%** |
| CASH_OUT | 2,237,500 | **4,116** | **0.18%** |
| PAYMENT | 2,151,495 | 0 | 0.00% |
| CASH_IN | 1,399,284 | 0 | 0.00% |
| DEBIT | 41,432 | 0 | 0.00% |

> **100% of all fraud occurs in TRANSFER and CASH_OUT** — the two highest-risk transaction types, forming the core of AML detection logic.

---

## 🔍 Analytical Framework — 12 Sections, 30 Detection Queries

### 🔴 Section 1 · High-Risk Transaction Detection
- Large transaction identification (threshold: $200K+)
- Top 10 largest transactions by value
- High-risk type filtering: TRANSFER & CASH_OUT isolation

### 🟠 Section 2 · Structuring / Smurfing Detection
- Multiple small transactions same day from same account
- Repeated transfer patterns to identical destinations (>10 times)
- Aggregate daily flow exceeding $200K from single origin

### 🟡 Section 3 · Rapid Transaction Activity
- High-frequency account identification
- Hourly spike detection across all 743 time steps
- Velocity monitoring for burst pattern flagging

### 🟢 Section 4 · Balance Anomaly Detection
- **2,488,652 sender balance mismatches** identified
- Receiver balance inconsistency detection
- Account-level error frequency ranking for investigation priority

### 🔵 Section 5 · Fraud Pattern Analysis
- Fraud count and fraud rate by transaction type
- Fraud segmentation by amount range (Low / Medium / High)
- Cross-type comparison for model validation

### 🟣 Section 6 · Network Analysis (Money Flow)
- Top sender → receiver pairs by total flow
- **Circular transaction detection** — A sends to B, B sends to A (layering pattern)
- Network concentration mapping for hub account identification

### ⚫ Section 7 · Risk Scoring
- **Basic risk score** — amount-threshold weighted scoring per account
- **Advanced risk score** — composite flag aggregation (high_amount + suspicious_type)
- Account-level risk ranking for SAR (Suspicious Activity Report) prioritization

### 🔴 Section 8 · Time-Based Analysis
- Daily transaction volume trend over 30-day window
- Daily fraud count timeline for temporal pattern recognition
- Peak fraud hour identification for operational alert scheduling

### 🟠 Section 9 · Behavioral Analysis
- Per-user average transaction baseline computation
- **Sudden spike detection** — flags transactions >3× personal average (CTE-based)
- Dormant-to-active account identification (low-history accounts suddenly transacting)

### 🟡 Section 10 · Window Function Analysis
- Running total per account using `SUM() OVER PARTITION BY`
- Transaction ranking per user with `RANK() OVER`
- Lag analysis — previous transaction comparison with `LAG()` for behavioral drift

### 🟢 Section 11 · Flagged Fraud Audit
- Fraud vs. flagged fraud cross-tabulation — **exposes the 99.8% system miss rate**
- Missed fraud case extraction (isFraud=1, isFlaggedFraud=0)
- False positive audit (isFraud=0, isFlaggedFraud=1) — **zero false positives confirmed**

### 🔵 Section 12 · Top Suspicious Entities
- Most fraud-active sender accounts for investigation list
- Most targeted destination accounts — potential money mule identification

---

## 🛠️ Technical Implementation

```sql
-- Full DDL with appropriate data types (DECIMAL(15,2) for financial precision)
-- Multi-step ETL cleaning pipeline with derived feature engineering
-- ALTER TABLE + UPDATE patterns for iterative feature addition
-- Advanced window functions: SUM OVER, RANK OVER, LAG OVER, COUNT OVER
-- CTE-based spike detection with self-join behavioral analysis
-- Circular flow detection via self-join on sender-receiver reversal
-- FILTER WHERE aggregation for conditional fraud counting
-- Duplicate detection via PARTITION BY + ctid deduplication
```

**SQL Techniques Demonstrated:**
- ✅ DDL: CREATE TABLE, ALTER TABLE, schema design
- ✅ DML: UPDATE, DELETE, data cleaning pipelines
- ✅ Window functions: SUM/RANK/LAG/COUNT OVER PARTITION BY
- ✅ CTEs for multi-step behavioral analysis
- ✅ Self-joins for circular transaction detection
- ✅ Conditional aggregation with FILTER WHERE
- ✅ Risk scoring with CASE WHEN weighted logic
- ✅ Duplicate detection using system columns (ctid)

---

## 📁 Repository Structure

```
├── AML_queries.sql                                    # Full cleaning pipeline + 30 detection queries
├── fraud_detection_dashboard_interactive.html         # Interactive AML dashboard
├── Synthetic_Financial_Dataset_for_Fraud_Detection.csv  # 6.36M transaction dataset
├── Synthetic_Financial_Fraud_Dataset.csv              # 230K validation dataset
```

---

## 🚀 Getting Started

**Set up the database:**
```sql
-- Run AML_queries.sql in PostgreSQL
-- Import CSV using COPY command:
COPY transactions FROM 'Synthetic_Financial_Dataset_for_Fraud_Detection.csv'
DELIMITER ',' CSV HEADER;
```

**View the dashboard:**
```bash
open fraud_detection_dashboard_interactive.html
```

**Quick metric check:**
```python
import pandas as pd
df = pd.read_csv("Synthetic_Financial_Dataset_for_Fraud_Detection.csv")
print(f"Fraud rate: {df['isFraud'].mean()*100:.3f}%")
print(f"Avg fraud amount: ${df[df['isFraud']==1]['amount'].mean():,.0f}")
```

---

## 💡 Key Investigative Findings

- 🎯 **Fraud is exclusively concentrated** in TRANSFER and CASH_OUT — zero fraud in PAYMENT, CASH_IN, or DEBIT
- 💸 **Fraud transactions are 8.2× larger** than legitimate ones on average — amount is a primary signal
- 🕳️ **The system's built-in flag missed 99.8% of fraud** — single-signal detection is dangerously insufficient
- 🔄 **Circular transaction patterns** detected — classic money laundering layering behavior
- 📊 **2.48M balance anomalies** uncovered — many accounts show mathematically impossible balance transitions
- 🏦 **Smurfing patterns** identified — multiple accounts sending small amounts to aggregate above reporting thresholds
- ⏰ **Temporal clustering** of fraud events — certain hours show disproportionately high fraud concentration

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Tableau · Power BI*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---

*Built to demonstrate financial crime analytics competency: AML data modelling, multi-signal fraud detection, SQL feature engineering, risk scoring, behavioral anomaly detection, and regulatory investigation support.*
