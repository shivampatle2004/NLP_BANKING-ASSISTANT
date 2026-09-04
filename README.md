# BankSathi — One-Stop Banking Decision & Problem Assistant

An AI-powered, explainable, India-focused conversational assistant and decision-support system for retail banking, multi-bank plan comparisons, government welfare schemes, loan calculations, and fraud emergency safety.

---

## 🌟 Key Features

1. **Conversational NLP Assistant (Multilingual & Hinglish)**:
   - Understands queries in **English, Devanagari Hindi, and romanized Hinglish** (*"Mujhe dukaan ke liye loan chahiye"*, *"SBI 1 year FD rate for senior citizens"*).
   - Scikit-Learn TF-IDF + Logistic Regression covering **29 fine-grained banking intents** with financial entity preservation (amounts in Lakhs/Crores, rates, tenures).

2. **Multi-Bank Plan Selector & Comparison Engine**:
   - Real, verified benchmark data for **8 major Indian banks** (*State Bank of India, HDFC Bank, ICICI Bank, Punjab National Bank, Bank of Baroda, Axis Bank, Kotak Mahindra Bank, Canara Bank*).
   - Side-by-side comparison across:
     - **Savings Account**: Minimum Average Balance (Metro/Urban/Rural) and interest rates.
     - **Fixed Deposits**: 1-Yr, 3-Yr, 5-Yr rates (General vs Senior Citizen extra interest) and peak special schemes (e.g. SBI Amrit Kalash, Kotak 390D).
     - **Loans**: Starting benchmark rates for Home Loans, Personal Loans, Education Loans (with female student concessions), and Car Loans.
     - **ATM Limits**: Daily cash withdrawal and POS limits.

3. **Government Financial Inclusion Scheme Finder**:
   - Personalized shortlists for *PMJDY, MUDRA (Shishu/Kishor/Tarun), Stand-Up India, PMSBY, PMJJBY, APY, Sukanya Samriddhi, and KCC*.

4. **Transparent Loan EMI Calculator**:
   - Computes monthly EMIs, total interest payable, and displays benchmark comparisons against the top 6 Indian banks.

5. **24x7 Emergency Help Desk & Cybercrime Action**:
   - 1-click toll-free customer support numbers.
   - Pre-formatted SMS card-blocking templates for instant card freeze.
   - Direct integration with **National Cyber Crime Helpline (1930)** and `cybercrime.gov.in`.

---

## 🚀 How to Run

### Option 1: Standalone Browser Mode (Zero Install)
Open `index.html` in any modern web browser. The assistant runs with high-performance client-side intelligence and loaded bank datasets out of the box.

### Option 2: Full-Stack Mode with FastAPI Backend
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI backend server:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
3. Open `index.html` in your browser. The UI will automatically connect to the live ML backend (Status indicator turns green).

---

## 🧪 Testing & Validation

Run the complete test suite (96 automated tests):
```bash
python -m pytest -o pythonpath=.
```

Run specific validation suites:
```bash
python knowledge/validate_banks.py      # Bank data integrity
python knowledge/validate_knowledge.py  # Scheme knowledge validation
python evaluation/evaluate_intents.py   # Intent classification benchmark (91.1% Top-1, 95.6% Top-3)
```

---

## 📁 Project Structure

```
NLP_BANKING-ASSISTANT/
├── backend/
│   ├── main.py                     # FastAPI application & REST endpoints
│   └── services/
│       ├── bank_service.py         # Multi-bank comparison, lookup & ranker
│       └── intent_service.py       # Intent classifier singleton manager
├── data/
│   ├── banks-data.json             # Verified profiles for 8 major banks
│   └── banking-knowledge.json      # Curated government & retail schemes
├── docs/
│   └── PROJECT_REPORT.md           # Methodology, architecture & evaluation
├── evaluation/
│   ├── evaluate_intents.py         # Benchmark accuracy evaluator
│   ├── test_queries.json           # 45 held-out test cases
│   └── training_intents.json       # 223 multi-lingual training examples
├── knowledge/
│   ├── validate_banks.py           # Multi-bank schema validator
│   └── validate_knowledge.py       # Scheme schema validator
├── models/
│   ├── intent_classifier.joblib    # Serialized ML pipeline artifact
│   └── intent_metadata.json        # Training metadata and class labels
├── nlp/
│   ├── intent_classifier.py        # ML Intent Classifier engine
│   ├── language.py                 # Script & language detector
│   └── preprocessing.py            # Normalization, synonyms & entity extractor
├── outputs/
│   └── intent_evaluation_report.json # Benchmark evaluation results
├── tests/
│   ├── test_banks_api.py           # REST endpoints integration tests
│   ├── test_banks_service.py       # Bank service & ranking unit tests
│   ├── test_phase1_backend.py      # Backend foundation tests
│   ├── test_phase2_knowledge.py    # Scheme data validation tests
│   ├── test_phase4_intent.py       # Intent classification ML tests
│   └── test_preprocessing.py       # NLP normalization tests
├── app.js                          # UI logic, dual-mode execution & comparator
├── index.html                      # One-stop responsive web UI
├── styles.css                      # Modern responsive styling & design system
└── requirements.txt                # Python dependencies
```
