"""Build PDF report from charts + metrics."""
import json
from fpdf import FPDF

m = json.load(open("fraud_project/data/metrics.json"))
C = "fraud_project/charts/"
BLUE=(24,95,165); DARK=(22,32,44); GREY=(90,107,123); RED=(163,45,45)

pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(True, margin=15)

def header(title, sub=""):
    pdf.set_fill_color(*BLUE); pdf.rect(0,0,210,30,"F")
    pdf.set_xy(12,8); pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica","B",17); pdf.cell(0,8,title,ln=1)
    if sub:
        pdf.set_x(12); pdf.set_font("Helvetica","",10); pdf.cell(0,6,sub,ln=1)
    pdf.set_text_color(*DARK); pdf.ln(8)

def h2(t):
    pdf.ln(2); pdf.set_text_color(*BLUE); pdf.set_font("Helvetica","B",13)
    pdf.cell(0,8,t,ln=1); pdf.set_text_color(*DARK)

def body(t):
    pdf.set_font("Helvetica","",10.5); pdf.set_text_color(*DARK)
    pdf.multi_cell(0,5.5,t); pdf.ln(1)

def chart(path,w=180):
    pdf.image(path,x=(210-w)/2,w=w); pdf.ln(3)

# ---------- PAGE 1 : cover + summary ----------
pdf.add_page()
header("Fraud Detection Analysis Report","End-to-end anomaly detection & transaction-risk scoring")
h2("Executive Summary")
body(
 "This report documents an end-to-end fraud-detection pipeline applied to a synthetic financial "
 f"transaction dataset of {m['raw_rows']:,} records. The pipeline performs data cleaning, feature "
 "engineering, exploratory analysis, unsupervised anomaly detection (Isolation Forest) and supervised "
 "classification (Random Forest), then scores every transaction with a composite risk score and routes "
 "high-risk activity to an analyst escalation queue.\n\n"
 f"Across the portfolio, {m['fraud_count']} confirmed fraudulent transactions were identified "
 f"({m['fraud_rate']}% fraud rate). The supervised model achieved an ROC-AUC of {m['rf_auc']} with "
 f"{int(m['rf_recall']*100)}% recall on a held-out test set, while the anomaly-detection model provided "
 f"an independent unsupervised signal (AUC {m['iso_auc']}). The risk-scoring layer flagged "
 f"{m['high_risk_flagged']} high/critical transactions for review, including {m['critical_flagged']} "
 "critical-priority cases.")

h2("Key Performance Indicators")
rows=[
 ("Transactions scored", f"{m['raw_rows']:,}"),
 ("Confirmed fraud detected", f"{m['fraud_count']}"),
 ("Overall fraud rate", f"{m['fraud_rate']}%"),
 ("High / Critical risk flagged", f"{m['high_risk_flagged']}"),
 ("Random Forest ROC-AUC", f"{m['rf_auc']}"),
 ("Random Forest recall", f"{m['rf_recall']}"),
 ("Random Forest precision", f"{m['rf_precision']}"),
 ("Isolation Forest ROC-AUC", f"{m['iso_auc']}"),
 ("Pipeline runtime", f"{m['runtime_sec']} sec"),
]
pdf.set_font("Helvetica","",10.5)
for i,(a,b) in enumerate(rows):
    pdf.set_fill_color(240,242,246) if i%2==0 else pdf.set_fill_color(255,255,255)
    pdf.cell(120,8,"  "+a,border=0,fill=True)
    pdf.set_font("Helvetica","B",10.5); pdf.cell(60,8,b,border=0,fill=True,ln=1)
    pdf.set_font("Helvetica","",10.5)

# ---------- PAGE 2 : EDA ----------
pdf.add_page(); header("Exploratory Data Analysis")
h2("1. Class Distribution & Transaction Types")
body("The dataset is highly imbalanced; fraud occurs exclusively within TRANSFER and CASH_OUT channels, "
     "which focuses monitoring effort on those two payment types.")
chart(C+"01_class_distribution.png",150)
chart(C+"02_txn_by_type.png",160)

pdf.add_page(); header("Exploratory Data Analysis (cont.)")
h2("2. Fraud Rate & Amount Behaviour")
chart(C+"03_fraud_rate_by_type.png",160)
chart(C+"04_amount_distribution.png",160)

pdf.add_page(); header("Exploratory Data Analysis (cont.)")
h2("3. Correlations & Temporal Trend")
chart(C+"05_correlation_heatmap.png",150)
chart(C+"06_fraud_over_time.png",165)

# ---------- PAGE : Models ----------
pdf.add_page(); header("Model Performance")
h2("4. Classification Results (Random Forest)")
body("Engineered balance-error features are strongly predictive of fraud, yielding near-perfect separation "
     "on this synthetic dataset. On real-world data, expect lower but still strong performance; the same "
     "pipeline and thresholds transfer directly.")
chart(C+"07_confusion_matrix.png",110)
chart(C+"08_roc_curve.png",120)

pdf.add_page(); header("Model Performance (cont.)")
h2("5. Precision-Recall & Feature Importance")
chart(C+"09_precision_recall.png",120)
chart(C+"10_feature_importance.png",165)

# ---------- PAGE : Risk scoring ----------
pdf.add_page(); header("Risk Scoring & Escalation")
h2("6. Composite Risk Segmentation")
body("Every transaction receives a composite risk score (0-100) blending the supervised fraud probability "
     "(70%) and the normalized anomaly score (30%). Scores map to four tiers used to drive KPI alerts and "
     "analyst escalation in near real time.")
chart(C+"11_risk_level_distribution.png",150)
h2("Methodology Note")
body("Pipeline: pandas (cleaning + feature engineering) -> scikit-learn IsolationForest & "
     "RandomForestClassifier -> composite scoring -> CSV/Excel exports + interactive dashboard. "
     "Models are persisted with joblib for production scoring. The same architecture scales to 6M+ "
     "transactions in batch.")

# ---------- PAGE : Threshold tuning & cost-based alerting ----------
import os as _os
_ar = "fraud_project/data/alert_rules.json"
if _os.path.exists(_ar):
    ar = json.load(open(_ar))
    rec = ar["at_recommended"]; ca = ar["cost_assumptions"]
    pdf.add_page(); header("Threshold Tuning & Cost-Based Alerting")
    h2("7. Choosing the Optimal Decision Threshold")
    body(
      "Rather than defaulting to a 0.50 probability cutoff, the operating threshold is chosen to "
      "MINIMIZE expected business cost. Each missed fraud (false negative) is assigned an average "
      f"loss of ${ca['missed_fraud_FN_usd']:.0f}, while each false alarm (false positive) costs "
      f"${ca['false_alarm_FP_usd']:.0f} in analyst review time.\n\n"
      f"The cost-minimizing threshold is {ar['recommended_threshold']}, which catches "
      f"{rec['frauds_caught']} of {rec['frauds_caught']+rec['frauds_missed']} frauds "
      f"(recall {rec['recall']}), generates {rec['alerts_per_period']} alerts per period, and yields "
      f"an expected cost of ${rec['expected_cost_usd']:,.0f} - versus "
      f"${ar['baseline_cost_ignore_everything']:,.0f} if fraud were ignored entirely "
      f"({ar['cost_saving_vs_ignore_pct']}% cost reduction).")
    chart(C+"12_cost_curve.png",165)
    pdf.add_page(); header("Threshold Tuning & Cost-Based Alerting (cont.)")
    h2("8. Metric Trade-offs & Analyst Workload")
    chart(C+"13_metric_vs_threshold.png",165)
    chart(C+"14_alert_volume.png",165)
    h2("KPI Alert Tiers (near real-time escalation)")
    pdf.set_font("Helvetica","",10)
    for tier,desc in ar["kpi_alert_tiers"].items():
        pdf.set_font("Helvetica","B",10)
        pdf.multi_cell(0,6,tier+":  "+desc)
        pdf.ln(0.5)
    pdf.ln(2); h2("Power BI Deliverable")
    body("A star-schema dataset (fact_transactions + dimension tables + KPI measures) is exported to "
         "the powerbi/ folder, ready to import into Power BI Desktop with documented relationships and "
         "suggested DAX measures (see powerbi/DATA_MODEL.md).")

pdf.output("fraud_project/reports/Fraud_Detection_Report.pdf")
print("PDF written -> fraud_project/reports/Fraud_Detection_Report.pdf")
