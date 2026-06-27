"""
End-to-End Fraud Detection Pipeline
====================================
Steps:
  1. Load & clean data
  2. Feature engineering
  3. Exploratory Data Analysis (EDA) + visualizations
  4. Anomaly detection  (Isolation Forest)  -> unsupervised risk score
  5. Classification     (Random Forest)     -> supervised fraud probability
  6. Transaction-risk scoring + export (CSV / Excel)
  7. Persist trained models
Author: Data Analyst  |  Matches resume: anomaly detection, feature engineering,
        classification models, transaction-risk reports, KPI alerts.
"""
import warnings, json, time, joblib
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, confusion_matrix, roc_auc_score,
                             roc_curve, precision_recall_curve, average_precision_score,
                             precision_score, recall_score, f1_score)

# ---------- aesthetics ----------
sns.set_style("whitegrid")
PALETTE = {"blue":"#185FA5","green":"#3B6D11","red":"#A32D2D","amber":"#854F0B",
           "blue_l":"#E6F1FB","grey":"#5a5a56"}
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,
                     "axes.titleweight":"bold","axes.titlesize":13,
                     "figure.facecolor":"white","axes.edgecolor":"#cccccc"})
SRC   = "uploads/Synthetic_Financial_Fraud_Dataset.csv"
CHART = "fraud_project/charts/"
DATA  = "fraud_project/data/"
MODEL = "fraud_project/models/"
metrics = {}
t0 = time.time()

# ================================================================== 1. LOAD & CLEAN
print("STEP 1  Loading & cleaning ...")
df = pd.read_csv(SRC)
raw_rows = len(df)
df = df.drop_duplicates()
# logical balance flags (data-quality / engineered signal)
df["amount"] = df["amount"].astype(float)
metrics["raw_rows"]      = raw_rows
metrics["clean_rows"]    = len(df)
metrics["dup_removed"]   = raw_rows - len(df)
metrics["fraud_count"]   = int(df.isFraud.sum())
metrics["fraud_rate"]    = round(df.isFraud.mean()*100, 4)

# ================================================================== 2. FEATURE ENGINEERING
print("STEP 2  Feature engineering ...")
df["errorBalanceOrig"] = df.newbalanceOrig + df.amount - df.oldbalanceOrg
df["errorBalanceDest"] = df.oldbalanceDest + df.amount - df.newbalanceDest
df["origZeroedOut"]    = ((df.oldbalanceOrg > 0) & (df.newbalanceOrig == 0)).astype(int)
df["destWasEmpty"]     = (df.oldbalanceDest == 0).astype(int)
df["amtToOrigBal"]     = df.amount / (df.oldbalanceOrg + 1)
df["isMerchantDest"]   = df.nameDest.str.startswith("M").astype(int)
df["hour"]             = df.step % 24
df["day"]              = (df.step // 24).astype(int)
df["highAmount"]       = (df.amount > df.amount.quantile(0.99)).astype(int)

NUM_FEATS = ["amount","oldbalanceOrg","newbalanceOrig","oldbalanceDest","newbalanceDest",
             "errorBalanceOrig","errorBalanceDest","origZeroedOut","destWasEmpty",
             "amtToOrigBal","isMerchantDest","hour","highAmount"]
df_model = pd.get_dummies(df, columns=["type"], prefix="type")
TYPE_COLS = [c for c in df_model.columns if c.startswith("type_")]
FEATURES  = NUM_FEATS + TYPE_COLS

X = df_model[FEATURES].fillna(0)
y = df_model["isFraud"]

# ================================================================== 3. EDA CHARTS
print("STEP 3  Building EDA visualizations ...")

# 3.1 Fraud vs legit distribution
fig, ax = plt.subplots(figsize=(6,4.2))
vc = df.isFraud.value_counts().sort_index()
bars = ax.bar(["Legitimate","Fraud"], vc.values, color=[PALETTE["blue"],PALETTE["red"]])
for b,v in zip(bars, vc.values):
    ax.text(b.get_x()+b.get_width()/2, v, f"{v:,}", ha="center", va="bottom", fontweight="bold")
ax.set_title("Transaction Class Distribution (Imbalanced)")
ax.set_ylabel("Count"); ax.set_yscale("log")
plt.tight_layout(); plt.savefig(CHART+"01_class_distribution.png"); plt.close()

# 3.2 Transactions by type + fraud overlay
fig, ax = plt.subplots(figsize=(7,4.2))
tt = df.type.value_counts()
ax.bar(tt.index, tt.values, color=PALETTE["blue"], label="All txns")
fr = df[df.isFraud==1].type.value_counts().reindex(tt.index).fillna(0)
ax.bar(fr.index, fr.values*200, color=PALETTE["red"], label="Fraud (x200 scale)")
ax.set_title("Transactions by Type (fraud only in TRANSFER & CASH_OUT)")
ax.set_ylabel("Count"); ax.legend(); plt.xticks(rotation=20)
plt.tight_layout(); plt.savefig(CHART+"02_txn_by_type.png"); plt.close()

# 3.3 Fraud rate by type
fig, ax = plt.subplots(figsize=(7,4.2))
frate = (df.groupby("type").isFraud.mean()*100).sort_values(ascending=False)
b = ax.bar(frate.index, frate.values, color=PALETTE["amber"])
for bar,v in zip(b,frate.values):
    ax.text(bar.get_x()+bar.get_width()/2, v, f"{v:.3f}%", ha="center", va="bottom", fontsize=9)
ax.set_title("Fraud Rate by Transaction Type"); ax.set_ylabel("Fraud rate (%)")
plt.xticks(rotation=20); plt.tight_layout(); plt.savefig(CHART+"03_fraud_rate_by_type.png"); plt.close()

# 3.4 Amount distribution fraud vs legit
fig, ax = plt.subplots(figsize=(7,4.2))
ax.hist(np.log1p(df[df.isFraud==0].amount), bins=60, alpha=.6, color=PALETTE["blue"], label="Legit", density=True)
ax.hist(np.log1p(df[df.isFraud==1].amount), bins=30, alpha=.7, color=PALETTE["red"], label="Fraud", density=True)
ax.set_title("Transaction Amount Distribution (log scale)")
ax.set_xlabel("log(1 + amount)"); ax.set_ylabel("Density"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"04_amount_distribution.png"); plt.close()

# 3.5 Correlation heatmap
fig, ax = plt.subplots(figsize=(9,7))
corr = df[NUM_FEATS+["isFraud"]].corr()
sns.heatmap(corr, cmap="RdBu_r", center=0, annot=False, ax=ax, cbar_kws={"shrink":.8})
ax.set_title("Feature Correlation Heatmap")
plt.tight_layout(); plt.savefig(CHART+"05_correlation_heatmap.png"); plt.close()

# 3.6 Fraud over time (by day)
fig, ax = plt.subplots(figsize=(8,4))
daily = df.groupby("day").isFraud.sum()
ax.plot(daily.index, daily.values, color=PALETTE["red"], lw=1.5)
ax.fill_between(daily.index, daily.values, color=PALETTE["red"], alpha=.15)
ax.set_title("Fraudulent Transactions Over Time"); ax.set_xlabel("Day"); ax.set_ylabel("Fraud count")
plt.tight_layout(); plt.savefig(CHART+"06_fraud_over_time.png"); plt.close()

# ================================================================== 4 & 5  MODELS
print("STEP 4  Train/test split & scaling ...")
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
scaler = StandardScaler().fit(X_tr)
X_tr_s, X_te_s = scaler.transform(X_tr), scaler.transform(X_te)

# ---- 4a Isolation Forest (anomaly detection / unsupervised) ----
print("STEP 4a Isolation Forest (anomaly detection) ...")
iso = IsolationForest(n_estimators=200, contamination=df.isFraud.mean(),
                      random_state=42, n_jobs=-1)
iso.fit(X_tr_s)
iso_score_te = -iso.score_samples(X_te_s)          # higher = more anomalous
iso_pred_te  = (iso.predict(X_te_s) == -1).astype(int)
metrics["iso_auc"]    = round(roc_auc_score(y_te, iso_score_te), 4)
metrics["iso_recall"] = round(recall_score(y_te, iso_pred_te), 4)

# ---- 5a Random Forest (supervised classification) ----
print("STEP 5a Random Forest classifier ...")
rf = RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced",
                            random_state=42, n_jobs=-1)
rf.fit(X_tr_s, y_tr)
rf_proba_te = rf.predict_proba(X_te_s)[:,1]
rf_pred_te  = rf.predict(X_te_s)
metrics["rf_auc"]       = round(roc_auc_score(y_te, rf_proba_te), 4)
metrics["rf_ap"]        = round(average_precision_score(y_te, rf_proba_te), 4)
metrics["rf_precision"] = round(precision_score(y_te, rf_pred_te), 4)
metrics["rf_recall"]    = round(recall_score(y_te, rf_pred_te), 4)
metrics["rf_f1"]        = round(f1_score(y_te, rf_pred_te), 4)

print("\nRandom Forest report:\n", classification_report(y_te, rf_pred_te, digits=4))

# ---- 5b Model evaluation charts ----
# Confusion matrix
fig, ax = plt.subplots(figsize=(5,4.2))
cm = confusion_matrix(y_te, rf_pred_te)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
            xticklabels=["Legit","Fraud"], yticklabels=["Legit","Fraud"])
ax.set_title("Random Forest — Confusion Matrix"); ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
plt.tight_layout(); plt.savefig(CHART+"07_confusion_matrix.png"); plt.close()

# ROC curves (both models)
fig, ax = plt.subplots(figsize=(6,5))
for score, name, col in [(rf_proba_te,"Random Forest",PALETTE["blue"]),
                         (iso_score_te,"Isolation Forest",PALETTE["amber"])]:
    fpr,tpr,_ = roc_curve(y_te, score)
    ax.plot(fpr,tpr,lw=2,color=col,label=f"{name} (AUC={roc_auc_score(y_te,score):.3f})")
ax.plot([0,1],[0,1],"--",color="grey")
ax.set_title("ROC Curve — Model Comparison"); ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate"); ax.legend(loc="lower right")
plt.tight_layout(); plt.savefig(CHART+"08_roc_curve.png"); plt.close()

# Precision-Recall curve
fig, ax = plt.subplots(figsize=(6,5))
pr,rc,_ = precision_recall_curve(y_te, rf_proba_te)
ax.plot(rc,pr,lw=2,color=PALETTE["green"],label=f"RF (AP={metrics['rf_ap']:.3f})")
ax.set_title("Precision–Recall Curve (Random Forest)")
ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"09_precision_recall.png"); plt.close()

# Feature importance
fig, ax = plt.subplots(figsize=(7,5))
fi = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=True).tail(12)
ax.barh(fi.index, fi.values, color=PALETTE["blue"])
ax.set_title("Top Feature Importances (Random Forest)"); ax.set_xlabel("Importance")
plt.tight_layout(); plt.savefig(CHART+"10_feature_importance.png"); plt.close()

# ================================================================== 6. SCORE ALL TXNS
print("STEP 6  Scoring all transactions & exporting ...")
X_all_s = scaler.transform(X)
df["fraud_probability"] = rf.predict_proba(X_all_s)[:,1]
df["anomaly_score"]     = -iso.score_samples(X_all_s)
# normalize anomaly score to 0-100
amin,amax = df.anomaly_score.min(), df.anomaly_score.max()
df["anomaly_score_norm"] = ((df.anomaly_score-amin)/(amax-amin)*100).round(2)
df["risk_score"]   = (0.7*df.fraud_probability*100 + 0.3*df.anomaly_score_norm).round(2)
df["risk_level"]   = pd.cut(df.risk_score, bins=[-1,25,50,75,101],
                            labels=["Low","Medium","High","Critical"])
df["predicted_fraud"] = (df.fraud_probability>=0.5).astype(int)

metrics["high_risk_flagged"] = int((df.risk_level.isin(["High","Critical"])).sum())
metrics["critical_flagged"]  = int((df.risk_level=="Critical").sum())

# risk distribution chart
fig, ax = plt.subplots(figsize=(6.5,4.2))
rl = df.risk_level.value_counts().reindex(["Low","Medium","High","Critical"])
cols=[PALETTE["green"],PALETTE["amber"],"#d97706",PALETTE["red"]]
b=ax.bar(rl.index, rl.values, color=cols)
for bar,v in zip(b,rl.values):
    ax.text(bar.get_x()+bar.get_width()/2,v,f"{v:,}",ha="center",va="bottom",fontsize=9)
ax.set_title("Transactions by Risk Level"); ax.set_ylabel("Count"); ax.set_yscale("log")
plt.tight_layout(); plt.savefig(CHART+"11_risk_level_distribution.png"); plt.close()

# Save full scored data
out_cols = ["step","type","amount","nameOrig","nameDest","oldbalanceOrg","newbalanceOrig",
            "oldbalanceDest","newbalanceDest","fraud_probability","anomaly_score_norm",
            "risk_score","risk_level","predicted_fraud","isFraud"]
df_scored = df[out_cols].copy()
df_scored.to_csv(DATA+"scored_transactions.csv", index=False)

# Top high-risk report (for stakeholders)
top = df_scored.sort_values("risk_score", ascending=False).head(500)
top.to_csv(DATA+"top_high_risk_transactions.csv", index=False)

# Excel workbook with multiple sheets
with pd.ExcelWriter(DATA+"fraud_analysis_report.xlsx", engine="openpyxl") as xl:
    pd.DataFrame([metrics]).T.rename(columns={0:"value"}).to_excel(xl, sheet_name="KPI_Summary")
    df.groupby("type").agg(txns=("amount","count"), total_amount=("amount","sum"),
        frauds=("isFraud","sum"), avg_risk=("risk_score","mean")).round(2).to_excel(xl, sheet_name="By_Type")
    df.risk_level.value_counts().reindex(["Low","Medium","High","Critical"]).to_excel(xl, sheet_name="Risk_Levels")
    top.head(200).to_excel(xl, sheet_name="Top_HighRisk", index=False)
    pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=False).to_excel(xl, sheet_name="Feature_Importance")

# ================================================================== 7. PERSIST MODELS
joblib.dump(rf, MODEL+"random_forest_fraud.joblib")
joblib.dump(iso, MODEL+"isolation_forest.joblib")
joblib.dump(scaler, MODEL+"scaler.joblib")
json.dump({"features":FEATURES}, open(MODEL+"features.json","w"), indent=2)

metrics["runtime_sec"] = round(time.time()-t0,1)
json.dump(metrics, open(DATA+"metrics.json","w"), indent=2)
print("\n=== METRICS ===")
print(json.dumps(metrics, indent=2))
print("\nDONE. Charts in charts/, data in data/, models in models/")
