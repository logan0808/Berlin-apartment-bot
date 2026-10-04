# Telco Customer Churn Prediction

Predicting which telecom customers are likely to cancel their contract, so a retention team can contact them before they leave.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-orange) ![Status](https://img.shields.io/badge/status-complete-brightgreen)

## 1. Business problem

Acquiring a new customer costs far more than keeping an existing one. A telecom company wants to identify customers at high risk of churning so it can offer targeted retention actions (discounts, contract upgrades, support calls).

**Goal:** build a classifier that flags likely churners and identify the main drivers of churn.

## 2. Dataset

- **Source:** IBM Telco Customer Churn sample dataset (available on Kaggle)
- **Size:** 7,043 customers, 21 columns
- **Target:** `Churn` (Yes/No), about 26.5% of customers churned (imbalanced)
- **Features:** demographics, account information (tenure, contract, payment method), subscribed services, monthly and total charges

## 3. Approach

1. **Data cleaning:** fixed 11 blank `TotalCharges` values (customers with tenure 0), corrected data types, removed `customerID`
2. **Exploratory analysis:** distributions, churn rate by contract type, tenure, internet service, payment method
3. **Preprocessing:** stratified train/test split first, then encoding and SMOTE inside a pipeline (no data leakage)
4. **Modeling:** Decision Tree, Random Forest, XGBoost compared with stratified 5-fold cross-validation
5. **Tuning:** randomized hyperparameter search optimizing F1 for the churn class
6. **Evaluation:** confusion matrix, precision, recall, F1, ROC-AUC, PR-AUC on a held-out test set
7. **Interpretation:** feature importance and business recommendations

## 4. Results

Held-out test set (1,409 customers):

| Model | Accuracy | Churn recall | Churn precision | Churn F1 | ROC-AUC |
|---|---|---|---|---|---|
| Baseline (always "No churn") | [fill in] | 0.00 | n/a | 0.00 | 0.50 |
| Random Forest (default) | 0.78 | 0.59 | 0.58 | 0.58 | [fill in] |
| XGBoost (default) | 0.77 | 0.56 | 0.56 | 0.56 | [fill in] |
| **Tuned final model** | [fill in] | [fill in] | [fill in] | [fill in] | [fill in] |

![ROC curve](images/roc_curve.png)
![Feature importance](images/feature_importance.png)

## 5. Key insights

- [fill in: e.g. month-to-month customers churn at X% vs Y% for two-year contracts]
- [fill in: e.g. churn is highest in the first N months of tenure]
- [fill in: e.g. fiber optic customers churn more than DSL customers]
- [fill in: e.g. customers paying by electronic check churn more]

## 6. Business recommendations

- [fill in: e.g. offer discounts to move month-to-month customers to annual contracts]
- [fill in: e.g. run an onboarding program for customers in their first months]
- [fill in: e.g. investigate service quality for fiber optic customers]

## 7. Repository structure

```
telco-customer-churn/
├── data/
│   └── Telco-Customer-Churn.csv
├── notebooks/
│   └── telco_customer_churn.ipynb
├── models/
│   └── churn_pipeline.joblib
├── images/
│   ├── roc_curve.png
│   └── feature_importance.png
├── requirements.txt
├── .gitignore
└── README.md
```

## 8. How to run

```bash
git clone https://github.com/<your-username>/telco-customer-churn.git
cd telco-customer-churn
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook notebooks/telco_customer_churn.ipynb
```

Run all cells from top to bottom. The notebook trains the model and saves it to `models/`.

### Predict for a new customer

```python
import joblib, pandas as pd

pipe = joblib.load("models/churn_pipeline.joblib")
customer = {
    "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "No",
    "tenure": 1, "PhoneService": "No", "MultipleLines": "No phone service",
    "InternetService": "DSL", "OnlineSecurity": "No", "OnlineBackup": "Yes",
    "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "No",
    "StreamingMovies": "No", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 29.85, "TotalCharges": 29.85,
}
print(pipe.predict_proba(pd.DataFrame([customer]))[0, 1])
```

## 9. Tech stack

Python, pandas, NumPy, scikit-learn, imbalanced-learn, XGBoost, matplotlib, seaborn, Jupyter

## 10. Limitations and next steps

- The dataset is a single snapshot, so the model cannot capture how behavior changes over time
- No cost model: a real deployment should weigh the cost of a retention offer against the value of a saved customer
- Next steps: SHAP explanations, probability calibration, a Streamlit app for live predictions, and monitoring for data drift

## 11. Author

**[Your name]** · [LinkedIn](https://www.linkedin.com/in/your-profile) · [GitHub](https://github.com/your-username)
