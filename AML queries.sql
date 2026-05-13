CREATE TABLE transactions (
    step INT,
    type VARCHAR(20),
    amount DECIMAL(15,2),
    nameOrig VARCHAR(50),
    oldbalanceOrg DECIMAL(15,2),
    newbalanceOrig DECIMAL(15,2),
    nameDest VARCHAR(50),
    oldbalanceDest DECIMAL(15,2),
    newbalanceDest DECIMAL(15,2),
    isFraud INT,
    isFlaggedFraud INT
);


select * from transactions limit 10;



-- STEP-BY-STEP CLEANING

-- STEP 1: Create a Working Copy
CREATE TABLE transactions_clean AS
SELECT * FROM transactions;



-- STEP 2: Standardize Text Columns
UPDATE transactions_clean
SET type = TRIM(UPPER(type));



-- STEP 3: Remove Invalid Transactions
DELETE FROM transactions_clean
WHERE amount <= 0;



-- STEP 4: Check & Handle NULL Values
SELECT * FROM transactions_clean
WHERE step IS NULL
   OR type IS NULL
   OR amount IS NULL;



-- STEP 5: Validate Balance Consistency

-- Sender Balance Check
SELECT * FROM transactions_clean
WHERE type IN ('TRANSFER','CASH_OUT')
AND oldbalanceOrg - amount != newbalanceOrig;



-- Receiver Balance Check
SELECT * FROM transactions_clean
WHERE type IN ('TRANSFER','CASH_OUT')
AND newbalanceDest - oldbalanceDest != amount;



-- STEP 6: Add Derived Columns

-- Balance Error Feature
ALTER TABLE transactions_clean
ADD COLUMN balance_error DECIMAL(15,2);

UPDATE transactions_clean
SET balance_error = oldbalanceOrg - amount - newbalanceOrig;



-- Destination Balance Error
ALTER TABLE transactions_clean
ADD COLUMN dest_balance_error DECIMAL(15,2);

UPDATE transactions_clean
SET dest_balance_error = newbalanceDest - oldbalanceDest - amount;



-- STEP 7: Create Risk Flags

--  High Amount Flag
ALTER TABLE transactions_clean
ADD COLUMN high_amount_flag INT;

UPDATE transactions_clean
SET high_amount_flag = CASE 
    WHEN amount > 200000 THEN 1
    ELSE 0
END;



-- Suspicious Transaction Type
ALTER TABLE transactions_clean
ADD COLUMN suspicious_type_flag INT;

UPDATE transactions_clean
SET suspicious_type_flag = CASE 
    WHEN type IN ('TRANSFER','CASH_OUT') THEN 1
    ELSE 0
END;



-- STEP 8: Convert Step to Time Features
ALTER TABLE transactions_clean
ADD COLUMN day INT;

UPDATE transactions_clean
SET day = step / 24;



-- STEP 9: Detect Duplicate Rows
SELECT *,
       COUNT(*) OVER (
           PARTITION BY step, nameOrig, nameDest, amount
       ) AS dup_count
FROM transactions_clean;



-- For remove duplicates
DELETE FROM transactions_clean
WHERE ctid NOT IN (
    SELECT MIN(ctid)
    FROM transactions_clean
    GROUP BY step, nameOrig, nameDest, amount
);




-- AML SQL QUERIES


-- SECTION 1: HIGH-RISK TRANSACTION DETECTION

-- 1. Large Transactions
SELECT *
FROM transactions_clean
WHERE amount > 200000;



-- 2. Top 10 Largest Transactions
SELECT *
FROM transactions_clean
ORDER BY amount DESC
LIMIT 10;



-- 3. High-Risk Transaction Types
SELECT type, COUNT(*) AS txn_count
FROM transactions_clean
WHERE type IN ('TRANSFER','CASH_OUT')
GROUP BY type;



-- SECTION 2: STRUCTURING (SMURFING DETECTION)

-- 4. Multiple Small Transactions Same Day
SELECT nameOrig,
       day,
       COUNT(*) AS txn_count,
       SUM(amount) AS total_amount
FROM transactions_clean
GROUP BY nameOrig, day
HAVING COUNT(*) > 5 AND SUM(amount) > 200000;



-- 5. Repeated Transfers to Same Destination
SELECT nameOrig, nameDest, COUNT(*) AS transfer_count
FROM transactions_clean
GROUP BY nameOrig, nameDest
HAVING COUNT(*) > 10;



-- SECTION 3: RAPID TRANSACTION ACTIVITY

-- 6. High Frequency Accounts
SELECT nameOrig, COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY nameOrig
ORDER BY txn_count DESC
LIMIT 10;



-- 7. Transactions per Hour (Spike Detection)
SELECT step, COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY step
ORDER BY txn_count DESC;



-- SECTION 4: BALANCE ANOMALY DETECTION

-- 8. Sender Balance Mismatch
SELECT *
FROM transactions_clean
WHERE ABS(balance_error) > 1;



-- 9. Receiver Balance Mismatch
SELECT *
FROM transactions_clean
WHERE ABS(dest_balance_error) > 1;



-- 10. Accounts with Frequent Errors
SELECT nameOrig,
       COUNT(*) AS error_count
FROM transactions_clean
WHERE ABS(balance_error) > 1
GROUP BY nameOrig
ORDER BY error_count DESC;



-- SECTION 5: FRAUD PATTERN ANALYSIS

-- 11. Fraud by Transaction Type
SELECT type,
       COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean
GROUP BY type;



-- 12. Fraud Rate per Type
SELECT type,
       COUNT(*) FILTER (WHERE isFraud = 1) * 100.0 / COUNT(*) AS fraud_rate
FROM transactions_clean
GROUP BY type;



-- 13. Fraud by Amount Range
SELECT 
    CASE 
        WHEN amount < 10000 THEN 'Low'
        WHEN amount < 100000 THEN 'Medium'
        ELSE 'High'
    END AS range,
    COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean
GROUP BY range;



-- SECTION 6: NETWORK ANALYSIS (MONEY FLOW)

-- 14. Top Sender → Receiver Pairs
SELECT nameOrig, nameDest, SUM(amount) AS total_amount
FROM transactions_clean
GROUP BY nameOrig, nameDest
ORDER BY total_amount DESC
LIMIT 10;



-- 15. Circular Transactions
SELECT t1.nameOrig, t1.nameDest
FROM transactions_clean t1
JOIN transactions_clean t2
ON t1.nameOrig = t2.nameDest
AND t1.nameDest = t2.nameOrig;



-- SECTION 7: RISK SCORING

-- 16. Basic Risk Score
SELECT nameOrig,
       SUM(
           CASE 
               WHEN amount > 200000 THEN 2
               WHEN amount > 100000 THEN 1
               ELSE 0
           END
       ) AS risk_score
FROM transactions_clean
GROUP BY nameOrig
ORDER BY risk_score DESC;



-- 17. Advanced Risk Score
SELECT nameOrig,
       SUM(high_amount_flag + suspicious_type_flag) AS risk_score
FROM transactions_clean
GROUP BY nameOrig
ORDER BY risk_score DESC;



-- SECTION 8: TIME-BASED ANALYSIS

-- 18. Daily Transaction Volume
SELECT day, COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY day;



-- 19. Daily Fraud Count
SELECT day,
       COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean
GROUP BY day;



-- 20. Peak Fraud Time
SELECT step,
       COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_count
FROM transactions_clean
GROUP BY step
ORDER BY fraud_count DESC
LIMIT 10;



-- SECTION 9: BEHAVIOR ANALYSIS

-- 21. Average Transaction per User
SELECT nameOrig,
       AVG(amount) AS avg_txn
FROM transactions_clean
GROUP BY nameOrig;



-- 22. Sudden Spike Detection
WITH avg_txn AS (
    SELECT nameOrig, AVG(amount) AS avg_amt
    FROM transactions_clean
    GROUP BY nameOrig
)
SELECT t.*
FROM transactions_clean t
JOIN avg_txn a ON t.nameOrig = a.nameOrig
WHERE t.amount > 3 * a.avg_amt;



-- 23. Dormant → Active Accounts
SELECT nameOrig,
       COUNT(*) AS txn_count
FROM transactions_clean
GROUP BY nameOrig
HAVING COUNT(*) < 3;



-- SECTION 10: WINDOW FUNCTION ANALYSIS

-- 24. Running Total per Account
SELECT nameOrig,
       step,
       SUM(amount) OVER (PARTITION BY nameOrig ORDER BY step) AS running_total
FROM transactions_clean;



-- 25. Rank Transactions per User
SELECT nameOrig,
       amount,
       RANK() OVER (PARTITION BY nameOrig ORDER BY amount DESC) AS rank
FROM transactions_clean;



-- 26. Lag Analysis (Previous Transaction)
SELECT nameOrig,
       amount,
       LAG(amount) OVER (PARTITION BY nameOrig ORDER BY step) AS prev_amount
FROM transactions_clean;



-- SECTION 11: FLAGGED FRAUD ANALYSIS

-- 27. Compare Fraud vs Flagged Fraud
SELECT isFraud, isFlaggedFraud, COUNT(*)
FROM transactions_clean
GROUP BY isFraud, isFlaggedFraud;



-- 28. Missed Fraud Cases
SELECT *
FROM transactions_clean
WHERE isFraud = 1 AND isFlaggedFraud = 0;



-- SECTION 12: TOP SUSPICIOUS ENTITIES

-- 29. Top Risky Accounts
SELECT nameOrig,
       COUNT(*) FILTER (WHERE isFraud = 1) AS fraud_txn
FROM transactions_clean
GROUP BY nameOrig
ORDER BY fraud_txn DESC
LIMIT 10;



-- 30. Most Targeted Destination Accounts
SELECT nameDest,
       COUNT(*) AS received_txn
FROM transactions_clean
GROUP BY nameDest
ORDER BY received_txn DESC
LIMIT 10;





