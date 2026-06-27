"""
Threshold Tuning & Cost-Based Alerting
======================================
Finds the optimal fraud-probability cutoff that MINIMIZES expected business cost,
not just maximizes accuracy. Produces:
  - cost curve across thresholds
  - precision/recall/F1 vs threshold
  - alert-volume vs threshold (analyst workload)
  - recommended operating point + KPI alert rules
Also exports a Power BI-ready star-schema dataset (fact + dimension CSVs).
"""
import warnings, json, joblib
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

PALETTE={"blue":"#185FA5","green":"#3B6D11","red":"#A32D2D","amber":"#854F0B","orange":"#d97706"}
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,
                     "axes.titleweight":"bold","axes.titlesize":13,"figure.facecolor":"white"})
CHART="fraud_project/charts/"; DATA="fraud_project/data/"; PBI="fraud_project/powerbi/"
import os; os.makedirs(PBI, exist_ok=True)

# ---- cost assumptions (editable business inputs) ----
# Average loss per missed fraud (false negative) vs. cost of reviewing a flagged txn (false positive)
COST_FN = 500.0   # $ avg loss when a fraud slips through
COST_FP = 8.0     # $ analyst review cost per false alarm
print(f"Cost model: missed fraud (FN)=${COST_FN}, false alarm review (FP)=${COST_FP}")

df = pd.read_csv(DATA+"scored_transactions.csv")
y = df["isFraud"].values
p = df["fraud_probability"].values

# ===================================================== 1. sweep thresholds
ths = np.linspace(0.01, 0.99, 99)
rows=[]
for t in ths:
    pred = (p>=t).astype(int)
    tn,fp,fn,tp = confusion_matrix(y,pred,labels=[0,1]).ravel()
    cost = fn*COST_FN + fp*COST_FP
    rows.append({
        "threshold":round(float(t),3),
        "tp":int(tp),"fp":int(fp),"fn":int(fn),"tn":int(tn),
        "alerts":int(tp+fp),
        "precision":round(precision_score(y,pred,zero_division=0),4),
        "recall":round(recall_score(y,pred,zero_division=0),4),
        "f1":round(f1_score(y,pred,zero_division=0),4),
        "expected_cost":round(float(cost),2),
    })
sweep = pd.DataFrame(rows)
sweep.to_csv(DATA+"threshold_sweep.csv", index=False)

# baseline: alert on EVERY txn vs alert on none
cost_review_all = len(df)*COST_FP
cost_miss_all   = int(y.sum())*COST_FN
best = sweep.loc[sweep.expected_cost.idxmin()]
best_f1 = sweep.loc[sweep.f1.idxmax()]
print(f"\nMin-cost threshold = {best.threshold}  -> cost ${best.expected_cost:,.0f}, "
      f"recall {best.recall}, precision {best.precision}, alerts {int(best.alerts)}")

# ===================================================== 2. charts
# 2a cost curve
fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.plot(sweep.threshold, sweep.expected_cost, color=PALETTE["red"], lw=2)
ax.axvline(best.threshold, ls="--", color=PALETTE["green"],
           label=f"Optimal t={best.threshold} (${best.expected_cost:,.0f})")
ax.scatter([best.threshold],[best.expected_cost],color=PALETTE["green"],zorder=5,s=60)
ax.set_title("Expected Business Cost vs Decision Threshold")
ax.set_xlabel("Fraud-probability threshold"); ax.set_ylabel("Expected cost ($)")
ax.legend(); plt.tight_layout(); plt.savefig(CHART+"12_cost_curve.png"); plt.close()

# 2b precision/recall/F1 vs threshold
fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.plot(sweep.threshold,sweep.precision,label="Precision",color=PALETTE["blue"],lw=2)
ax.plot(sweep.threshold,sweep.recall,label="Recall",color=PALETTE["green"],lw=2)
ax.plot(sweep.threshold,sweep.f1,label="F1",color=PALETTE["amber"],lw=2)
ax.axvline(best.threshold,ls="--",color="grey",alpha=.7)
ax.set_title("Precision / Recall / F1 vs Threshold")
ax.set_xlabel("Threshold"); ax.set_ylabel("Score"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"13_metric_vs_threshold.png"); plt.close()

# 2c alert volume (analyst workload)
fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.plot(sweep.threshold,sweep.alerts,color=PALETTE["orange"],lw=2)
ax.fill_between(sweep.threshold,sweep.alerts,color=PALETTE["orange"],alpha=.12)
ax.axvline(best.threshold,ls="--",color=PALETTE["green"],
           label=f"Optimal: {int(best.alerts)} alerts/period")
ax.set_title("Alert Volume vs Threshold (Analyst Workload)")
ax.set_xlabel("Threshold"); ax.set_ylabel("Transactions flagged"); ax.set_yscale("log"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"14_alert_volume.png"); plt.close()

# ===================================================== 3. KPI alert rules
alert_rules = {
  "cost_assumptions":{"missed_fraud_FN_usd":COST_FN,"false_alarm_FP_usd":COST_FP},
  "recommended_threshold":float(best.threshold),
  "at_recommended":{
     "recall":float(best.recall),"precision":float(best.precision),"f1":float(best.f1),
     "alerts_per_period":int(best.alerts),"expected_cost_usd":float(best.expected_cost),
     "frauds_caught":int(best.tp),"frauds_missed":int(best.fn),"false_alarms":int(best.fp)},
  "max_f1_threshold":float(best_f1.threshold),
  "baseline_cost_review_everything":float(cost_review_all),
  "baseline_cost_ignore_everything":float(cost_miss_all),
  "cost_saving_vs_ignore_pct":round((1-best.expected_cost/max(cost_miss_all,1))*100,1),
  "kpi_alert_tiers":{
     "CRITICAL":"risk_score >= 75  -> page on-call analyst immediately",
     "HIGH":"risk_score 50-75      -> add to priority review queue (SLA 1h)",
     "MEDIUM":"risk_score 25-50    -> daily batch review",
     "LOW":"risk_score < 25        -> auto-approve, sample 1%"},
}
json.dump(alert_rules, open(DATA+"alert_rules.json","w"), indent=2)
print("\nAlert rules saved.")

# ===================================================== 4. POWER BI star-schema export
print("\nBuilding Power BI-ready dataset (star schema)...")
df["day"]  = df["step"]//24
df["hour"] = df["step"]%24
# --- Fact table ---
fact = df[["step","day","hour","type","amount","fraud_probability","anomaly_score_norm",
           "risk_score","risk_level","predicted_fraud","isFraud","nameOrig","nameDest"]].copy()
fact.insert(0,"transaction_id", range(1,len(fact)+1))
fact = fact.rename(columns={"isFraud":"is_fraud_actual","type":"type_key",
                            "risk_level":"risk_level_key"})
fact.to_csv(PBI+"fact_transactions.csv", index=False)

# --- Dim: transaction type ---
dim_type = (df.groupby("type").agg(transactions=("amount","count"),
            total_amount=("amount","sum"), frauds=("isFraud","sum"),
            avg_risk=("risk_score","mean")).round(2).reset_index()
            .rename(columns={"type":"type_key"}))
dim_type["fraud_rate_pct"]=(dim_type.frauds/dim_type.transactions*100).round(4)
dim_type.to_csv(PBI+"dim_transaction_type.csv", index=False)

# --- Dim: risk level ---
dim_risk = pd.DataFrame({
  "risk_level_key":["Low","Medium","High","Critical"],
  "risk_order":[1,2,3,4],
  "score_min":[0,25,50,75],"score_max":[25,50,75,100],
  "action":["Auto-approve (sample 1%)","Daily batch review",
            "Priority queue (SLA 1h)","Immediate escalation / page on-call"],
  "sla_hours":[None,24,1,0]})
dim_risk.to_csv(PBI+"dim_risk_level.csv", index=False)

# --- Dim: date/step ---
dim_date = (df[["step","day","hour"]].drop_duplicates().sort_values("step")
            .reset_index(drop=True))
dim_date["week"]=(dim_date.day//7)+1
dim_date.to_csv(PBI+"dim_date.csv", index=False)

# --- KPI measures table (for Power BI cards) ---
m = json.load(open(DATA+"metrics.json"))
kpi = pd.DataFrame([
  {"metric":"Total Transactions","value":len(df)},
  {"metric":"Total Volume USD","value":round(df.amount.sum(),2)},
  {"metric":"Fraud Detected","value":int(df.isFraud.sum())},
  {"metric":"Fraud Rate %","value":m["fraud_rate"]},
  {"metric":"High+Critical Flagged","value":int(df.risk_level.isin(['High','Critical']).sum())},
  {"metric":"Model Recall","value":m["rf_recall"]},
  {"metric":"Model Precision","value":m["rf_precision"]},
  {"metric":"Model ROC AUC","value":m["rf_auc"]},
  {"metric":"Recommended Threshold","value":float(best.threshold)},
  {"metric":"Expected Cost USD","value":float(best.expected_cost)},
])
kpi.to_csv(PBI+"kpi_measures.csv", index=False)

# data model doc
open(PBI+"DATA_MODEL.md","w").write(f"""# Power BI Data Model (Star Schema)

Import these CSVs into Power BI Desktop (Get Data > Text/CSV) and create relationships.

## Tables
- **fact_transactions** (grain: 1 row per transaction) — central fact table
- **dim_transaction_type** — descriptive attributes per payment channel
- **dim_risk_level** — risk tiers, SLA, escalation actions
- **dim_date** — step / day / week / hour calendar
- **kpi_measures** — pre-computed KPI card values

## Relationships (Model view)
| From (fact) | To (dim) | Cardinality |
|---|---|---|
| fact_transactions[type_key] | dim_transaction_type[type_key] | Many-to-One |
| fact_transactions[risk_level_key] | dim_risk_level[risk_level_key] | Many-to-One |
| fact_transactions[step] | dim_date[step] | Many-to-One |

## Suggested DAX measures
```
Total Fraud = SUM(fact_transactions[is_fraud_actual])
Fraud Rate % = DIVIDE([Total Fraud], COUNTROWS(fact_transactions)) * 100
High Risk Alerts = CALCULATE(COUNTROWS(fact_transactions), fact_transactions[risk_score] >= 50)
Total Amount = SUM(fact_transactions[amount])
Avg Risk Score = AVERAGE(fact_transactions[risk_score])
Recommended Threshold = {best.threshold}
```

## Suggested visuals
1. KPI cards: Total Fraud, Fraud Rate %, High Risk Alerts, Total Amount
2. Bar: Total Amount & Frauds by dim_transaction_type
3. Donut: transactions by dim_risk_level
4. Line: [Total Fraud] over dim_date[day]
5. Table: top transactions by risk_score with conditional formatting
6. Gauge: model recall vs target
""")

print("Power BI dataset written to", PBI)
print("Done.")
