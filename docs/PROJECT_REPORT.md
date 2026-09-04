# BankSathi — Final Project Report & Architectural Specification

## 1. Problem Statement & Motivation
Indian retail banking customers face steep challenges when choosing accounts, understanding fluctuating loan rates, navigating dozens of government financial-inclusion schemes, and securing their money against cyber scams. Information is siloed across separate bank portals with confusing jargon.

**BankSathi** solves this by providing a **One-Stop Banking Decision & Problem Assistant** that combines:
1. Explainable NLP Intent Classification with English, Hindi, and Hinglish query support.
2. Structured real-world benchmark data across **8 major Indian banks** (*State Bank of India, HDFC Bank, ICICI Bank, Punjab National Bank, Bank of Baroda, Axis Bank, Kotak Mahindra Bank, and Canara Bank*).
3. Side-by-side comparison across Savings MAB, Fixed Deposit (FD) returns, Loan APRs, and ATM limits.
4. Personalized Government Scheme Matching (*PMJDY, MUDRA, PMSBY, PMJJBY, APY, Sukanya, KCC*).
5. Transparent Loan EMI estimation.
6. 24x7 Emergency Desk for instant SMS card blocking and cybercrime (1930) reporting.

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User Interface (Web)                            │
│  [💬 Conversational Assistant] [⇋ Bank Plan Selector] [⌕ Scheme Finder] │
│  [▣ Loan EMI Planner]          [🚨 Emergency & Fraud Desk]             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / Local Store
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Layer                           │
│  - GET /api/banks               - POST /api/banks/compare              │
│  - GET /api/banks/{bank_id}     - GET  /api/rates/best                 │
│  - POST /api/intent/predict     - GET  /health                         │
└───────────────────┬───────────────────────────────┬────────────────────┘
                    │                               │
                    ▼                               ▼
┌──────────────────────────────────────┐ ┌───────────────────────────────┐
│     NLP & Intent Engine              │ │     Data & Knowledge Store    │
│  - Language Detector (English/Hindi) │ │  - data/banks-data.json       │
│  - Preprocessing & Entity Extractor  │ │  - data/banking-knowledge.json│
│  - TF-IDF + Logistic Regression      │ │  - Schema Validators          │
│  - 29 Fine-Grained Banking Intents   │ │                               │
└──────────────────────────────────────┘ └───────────────────────────────┘
```

---

## 3. Dataset Design

1. **`data/banks-data.json`**:
   - Covers 8 top Indian banks with verified benchmark fields: Minimum Average Balance (Metro/Urban/Rural), Savings rates, 1-Yr / 3-Yr / 5-Yr FD rates (General & Senior Citizens), Home/Personal/Education/Car loan starting rates, ATM daily limits, 24x7 toll-free contacts, and instant SMS card-block templates.

2. **`data/banking-knowledge.json`**:
   - 18 curated, source-attributed entries covering financial inclusion, insurance, pension, business loans, and consumer protection.

---

## 4. NLP Methodology & Performance

- **Preprocessing**: Multi-word phrase canonicalization, abbreviation normalization (KCC, APY, PMJDY, FD, RD), and financial number extraction (Lakhs, Crores, percentages, tenures).
- **Intent Classifier**: TF-IDF + Logistic Regression trained on 223 multi-lingual samples across 29 classes.
- **Evaluation Benchmark** (on 45 held-out test queries):
  - **Top-1 Accuracy**: **91.11%** (41 / 45)
  - **Top-3 Accuracy**: **95.56%** (43 / 45)
  - **Total Mismatches**: 4

---

## 5. Security, Ethics & Governance

- **Zero-Storage of Sensitive Data**: The application collects no account numbers, PINs, passwords, or OTPs.
- **Clear Disclaimers**: Answers are strictly educational and decision-supportive, not loan approval confirmations or investment advice.
- **Direct Official Verification**: Every single bank and scheme result includes clickable links to official bank portals and government websites.
