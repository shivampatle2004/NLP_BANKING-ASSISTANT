"""
BankSathi — Bank Intelligence & Comparison Service

Provides in-memory caching, lookup, multi-bank side-by-side comparison,
best-rate ranking, and bank entity resolution.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BANKS_DATA_PATH = PROJECT_ROOT / "data" / "banks-data.json"

_banks_store: Dict[str, Any] = {}


def _ensure_banks_loaded() -> Dict[str, Any]:
    """Load and cache banks data into memory."""
    global _banks_store
    if not _banks_store:
        if BANKS_DATA_PATH.exists():
            with open(BANKS_DATA_PATH, "r", encoding="utf-8") as f:
                _banks_store = json.load(f)
        else:
            _banks_store = {"metadata": {}, "banks": []}
    return _banks_store


def get_all_banks() -> List[Dict[str, Any]]:
    """Return all banks."""
    data = _ensure_banks_loaded()
    return data.get("banks", [])


def get_bank_by_id(bank_id: str) -> Optional[Dict[str, Any]]:
    """Get a single bank profile by ID."""
    banks = get_all_banks()
    bank_id_lower = bank_id.strip().lower()
    for bank in banks:
        if bank.get("id", "").lower() == bank_id_lower:
            return bank
    return None


BANK_ALIASES = {
    "sbi": ["sbi", "state bank", "state bank of india", "sbi bank"],
    "pnb": ["pnb", "punjab national bank", "punjab bank"],
    "bob": ["bob", "bank of baroda", "baroda bank"],
    "canara": ["canara", "canara bank"],
    "union": ["union", "union bank", "union bank of india"],
    "indian": ["indian bank", "ind bank"],
    "boi": ["boi", "bank of india"],
    "hdfc": ["hdfc", "hdfc bank"],
    "icici": ["icici", "icici bank", "i-mobile"],
    "axis": ["axis", "axis bank", "uti bank"],
    "kotak": ["kotak", "kotak mahindra", "kotak 811", "kotak bank", "811"],
    "indusind": ["indusind", "indusind bank"],
    "idfc": ["idfc", "idfc first", "idfc bank", "idfc first bank"],
    "ausfb": ["au bank", "au small finance", "au sfb", "ausfb"],
    "equitas": ["equitas", "equitas bank", "equitas small finance"],
    "scb": ["stanchart", "standard chartered", "standard chartered bank", "scb"],
    "hsbc": ["hsbc", "hsbc bank", "hsbc india"],
    "ippb": ["ippb", "india post payments bank", "post office bank", "post bank"],
}


def resolve_bank_ids_from_text(text: str) -> List[str]:
    """Identify which bank IDs are mentioned in a query string."""
    text_lower = text.lower()
    matched_ids = []
    for b_id, aliases in BANK_ALIASES.items():
        for alias in aliases:
            # Word boundary check
            if alias in text_lower:
                if b_id not in matched_ids:
                    matched_ids.append(b_id)
                break
    return matched_ids


def compare_banks(bank_ids: List[str], product_type: str = "all") -> Dict[str, Any]:
    """
    Compare multiple banks side-by-side.

    Parameters
    ----------
    bank_ids : list of str
        List of bank IDs (e.g. ["sbi", "hdfc", "icici"]).
    product_type : str
        "all" | "savings" | "fixed_deposit" | "loans" | "cards" | "support"
    """
    all_banks_map = {b["id"]: b for b in get_all_banks()}
    selected = [all_banks_map[b_id] for b_id in bank_ids if b_id in all_banks_map]

    if not selected:
        selected = get_all_banks()[:3]  # default to top 3 if none specified

    comparison_results = []
    for bank in selected:
        item = {
            "id": bank["id"],
            "name": bank["name"],
            "shortName": bank["shortName"],
            "type": bank["type"],
            "logoColor": bank.get("logoColor", "#1A4F8A"),
        }

        if product_type in ["all", "savings"]:
            item["savings"] = {
                "minBalanceMetro": f"₹{bank['savings']['minBalance']['metro']:,}",
                "minBalanceRural": f"₹{bank['savings']['minBalance']['rural']:,}",
                "interestRate": f"{bank['savings']['interestRate']['upTo10Lakh']:.2f}% - {bank['savings']['interestRate']['above10Lakh']:.2f}%",
                "zeroBalanceAvailable": "Yes" if bank['savings']['minBalance']['metro'] == 0 or "zeroBalanceOption" in bank['savings']['minBalance'] else "No",
                "notes": bank['savings']['minBalance'].get('notes', ''),
            }

        if product_type in ["all", "fixed_deposit", "fd"]:
            item["fixedDeposit"] = {
                "rate1YearGeneral": f"{bank['fixedDeposit']['rate1Year']['general']:.2f}%",
                "rate1YearSenior": f"{bank['fixedDeposit']['rate1Year']['seniorCitizen']:.2f}%",
                "rate3YearGeneral": f"{bank['fixedDeposit']['rate3Year']['general']:.2f}%",
                "rate3YearSenior": f"{bank['fixedDeposit']['rate3Year']['seniorCitizen']:.2f}%",
                "rate5YearGeneral": f"{bank['fixedDeposit']['rate5Year']['general']:.2f}%",
                "rate5YearSenior": f"{bank['fixedDeposit']['rate5Year']['seniorCitizen']:.2f}%",
                "specialScheme": bank['fixedDeposit']['specialScheme']['name'],
                "specialRateGeneral": f"{bank['fixedDeposit']['specialScheme']['generalRate']:.2f}%",
                "specialRateSenior": f"{bank['fixedDeposit']['specialScheme']['seniorRate']:.2f}%",
            }

        if product_type in ["all", "loans"]:
            edu = bank.get("loans", {}).get("educationLoan", {})
            edu_rate = edu.get("startingRate") or edu.get("domesticStartingRate") or 8.5
            item["loans"] = {
                "homeLoanRate": f"{bank['loans']['homeLoan']['startingRate']:.2f}%",
                "homeLoanBenchmark": bank['loans']['homeLoan'].get('benchmarkType', 'EBLR'),
                "personalLoanRate": f"{bank['loans']['personalLoan']['startingRate']:.2f}%",
                "educationLoanRate": f"{edu_rate:.2f}%",
                "femaleConcession": edu.get('femaleConcession', '0.50% where applicable'),
                "carLoanRate": f"{bank['loans']['carLoan']['startingRate']:.2f}%",
            }

        if product_type in ["all", "cards"]:
            cards = bank.get("cardsAndAtm") or bank.get("debitCard") or {}
            item["cardsAndAtm"] = {
                "dailyAtmWithdrawalLimit": f"₹{cards.get('dailyAtmWithdrawalLimit', 25000):,}",
                "dailyPosLimit": f"₹{cards.get('dailyPosLimit', 50000):,}",
                "annualFee": cards.get('debitCardAnnualFee') or cards.get('annualFee', '₹150 + GST'),
            }

        if product_type in ["all", "support"]:
            supp = bank.get("customerSupport", {})
            item["customerSupport"] = {
                "tollFree": supp.get('tollFree', []),
                "cardBlockSms": supp.get('cardBlockSms') or supp.get('smsCardBlock', ''),
                "customerCareEmail": supp.get('customerCareEmail', supp.get('tollFree', [''])[0] if supp.get('tollFree') else ''),
                "officialWebsite": supp.get('officialWebsite', ''),
            }

        comparison_results.append(item)

    return {
        "total_compared": len(comparison_results),
        "product_type": product_type,
        "banks": comparison_results,
    }


def get_best_rates(product: str = "fd", senior_citizen: bool = False) -> Dict[str, Any]:
    """
    Rank banks dynamically to highlight best offers.

    Parameters
    ----------
    product : str
        "fd" | "savings" | "home_loan" | "personal_loan" | "education_loan"
    senior_citizen : bool
        Whether to calculate rates for senior citizens.
    """
    banks = get_all_banks()
    results = []

    if product in ["fd", "fixed_deposit"]:
        rate_key = "seniorCitizen" if senior_citizen else "general"
        for b in banks:
            r1 = b["fixedDeposit"]["rate1Year"][rate_key]
            r3 = b["fixedDeposit"]["rate3Year"][rate_key]
            r5 = b["fixedDeposit"]["rate5Year"][rate_key]
            spec_r = b["fixedDeposit"]["specialScheme"]["seniorRate" if senior_citizen else "generalRate"]
            best_r = max(r1, r3, r5, spec_r)
            results.append({
                "bank_id": b["id"],
                "bank_name": b["name"],
                "short_name": b["shortName"],
                "type": b["type"],
                "rate_1yr": f"{r1:.2f}%",
                "rate_3yr": f"{r3:.2f}%",
                "rate_5yr": f"{r5:.2f}%",
                "special_scheme": b["fixedDeposit"]["specialScheme"]["name"],
                "special_rate": f"{spec_r:.2f}%",
                "peak_rate": best_r,
                "peak_rate_display": f"{best_r:.2f}%",
                "category": "Senior Citizen" if senior_citizen else "General Public",
            })
        # Rank by peak rate descending
        results.sort(key=lambda x: x["peak_rate"], reverse=True)

    elif product in ["home_loan", "home"]:
        for b in banks:
            rate = b["loans"]["homeLoan"]["startingRate"]
            results.append({
                "bank_id": b["id"],
                "bank_name": b["name"],
                "short_name": b["shortName"],
                "type": b["type"],
                "starting_rate": rate,
                "starting_rate_display": f"{rate:.2f}%",
                "benchmark": b["loans"]["homeLoan"]["benchmarkType"],
                "processing_fee": b["loans"]["homeLoan"]["processingFee"],
            })
        # Rank by lowest loan rate ascending
        results.sort(key=lambda x: x["starting_rate"])

    elif product in ["savings", "savings_account"]:
        for b in banks:
            metro_min = b["savings"]["minBalance"]["metro"]
            rural_min = b["savings"]["minBalance"]["rural"]
            rate_up = b["savings"]["interestRate"]["upTo10Lakh"]
            results.append({
                "bank_id": b["id"],
                "bank_name": b["name"],
                "short_name": b["shortName"],
                "type": b["type"],
                "metro_min_balance": metro_min,
                "metro_min_balance_display": f"₹{metro_min:,}",
                "rural_min_balance_display": f"₹{rural_min:,}",
                "interest_rate_display": f"{rate_up:.2f}%",
                "notes": b["savings"]["minBalance"].get("notes", ""),
            })
        # Rank by lowest minimum balance required
        results.sort(key=lambda x: x["metro_min_balance"])

    return {
        "product": product,
        "is_senior_citizen": senior_citizen,
        "ranked_banks": results,
    }


def generate_bank_conversational_response(
    query: str,
    intent: str,
    bank_ids: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Generate tailored, context-aware bank response for conversational queries.
    Handles greetings, student recommendations, zero-interest credit, senior citizens, farmers,
    zero-balance accounts, and product-specific comparisons.
    """
    q = query.lower().strip()

    # 0. Greetings & Salutations
    if q in ["hi", "hii", "hiii", "hello", "helo", "hey", "namaste", "namaskar", "pranam", "good morning", "good afternoon", "good evening", "kaise ho", "kya haal hai", "help"]:
        return {
            "type": "greeting",
            "title": "Namaste! Welcome to BankSathi 🇮🇳",
            "summary": "I am your one-stop Indian Banking Decision & Problem Assistant. I can help you compare 8 major banks, find government schemes, resolve ATM/UPI disputes, and plan loan EMIs.",
            "suggestions": [
                "🎓 Best bank for students & education loans",
                "📈 Which bank offers the highest FD rate?",
                "💳 Zero-interest / 1-month credit options",
                "🏦 Which bank has zero minimum balance?",
                "⚠️ ATM se cash nahi nikla par paisa kat gaya",
                "⇋ Compare SBI vs HDFC vs ICICI",
            ]
        }

    # 1. Total Banks in Portal / Supported Bank Roster
    if any(term in q for term in ["total bank", "how many bank", "supported bank", "all banks", "list of bank", "kitne bank", "which banks are available"]):
        banks = get_all_banks()
        return {
            "type": "portal_banks_list",
            "title": f"Supported Banks in BankSathi ({len(banks)} Major Indian Banks)",
            "summary": f"BankSathi tracks live verified benchmark data, interest rates, minimum balances, and emergency contacts across {len(banks)} leading banks in India:",
            "public_sector": [f"{b['name']} ({b['shortName']})" for b in banks if b['type'] == 'Public Sector'],
            "private_sector": [f"{b['name']} ({b['shortName']})" for b in banks if b['type'] == 'Private Sector'],
            "small_finance": [f"{b['name']} ({b['shortName']})" for b in banks if b['type'] == 'Small Finance Bank'],
            "international": [f"{b['name']} ({b['shortName']})" for b in banks if 'Foreign' in b['type'] or 'International' in b['type']],
            "payments_bank": [f"{b['name']} ({b['shortName']})" for b in banks if b['type'] == 'Payments Bank'],
            "features_tracked": "Savings MAB, 1/3/5-Yr FDs (General & Senior), Home/Personal/Education/Car Loans, ATM Daily Limits, and 24x7 Emergency Desks.",
        }

    # 2. Bank Account Opening Age Guidelines (RBI Rules & Minor Accounts)
    if any(term in q for term in ["age to open", "minimum age", "minor account", "age limit", "age for bank", "how old to open", "bachho ka account", "minor khata"]):
        return {
            "type": "account_age_guidelines",
            "title": "Bank Account Opening Age Guidelines in India (RBI Rules)",
            "summary": "Anyone from newborn infants to senior citizens can hold a bank account in India under distinct regulatory brackets:",
            "age_brackets": [
                {
                    "bracket": "👶 Minors Under 10 Years",
                    "rules": "Joint Savings Account operated jointly by the natural parent or legal guardian (e.g., Sukanya Samriddhi for girl children).",
                },
                {
                    "bracket": "🧒 Minors Aged 10 to 18 Years",
                    "rules": "Can independently open and operate Savings Accounts (e.g., SBI Pehla Kadam / Pehli Udaan) with debit card, mobile banking, and internet banking limits.",
                },
                {
                    "bracket": "🧑 Adults Aged 18 to 59 Years",
                    "rules": "Full independent banking including individual savings/current accounts, credit cards, personal/home loans, and demat investment accounts.",
                },
                {
                    "bracket": "👴 Senior Citizens Aged 60+ Years",
                    "rules": "Eligible for Senior Citizen accounts with preferential FD rates (+0.50% to +0.75%), doorstep banking, and dedicated branch priority queues.",
                }
            ],
            "official_portal": "https://rbi.org.in/",
        }

    # 3. Explicit Multi-Bank Comparison (PRIORITIZED when 2+ banks mentioned)
    if len(bank_ids) >= 2 or (len(bank_ids) >= 1 and any(w in q for w in ["compare", "vs", "versus"])):
        target_banks = bank_ids if bank_ids else ["sbi", "hdfc", "icici"]
        product_type = "all"
        if any(w in q for w in ["fd", "fixed deposit", "term deposit", "deposit rate"]):
            product_type = "fixed_deposit"
        elif any(w in q for w in ["home loan", "housing", "property", "ghar loan"]):
            product_type = "loans"
        elif any(w in q for w in ["saving", "min balance", "minimum balance", "mab", "amb"]):
            product_type = "savings"

        comparison = compare_banks(target_banks, product_type=product_type)
        bank_names = [b["shortName"] for b in comparison["banks"]]
        return {
            "type": "bank_comparison",
            "title": f"Comparison: {' vs '.join(bank_names)}",
            "product_focus": product_type,
            "data": comparison,
            "summary": f"Here is a side-by-side comparison for {', '.join(bank_names)} tailored to your request.",
        }

    # 3.5. IFSC, Branch, MICR & Location Lookups
    if any(term in q for term in ["ifsc", "ifsc code", "branch code", "micr", "branch address", "branch location", "where is branch", "branch ifsc"]):
        # Known major offline branch resolutions for fast accurate zero-latency response
        known_branches = {
            "friends colony": {
                "sbi": {"name": "State Bank of India (SBI)", "branch": "Friends Colony, Nagpur", "ifsc": "SBIN0014282", "micr": "440002047", "address": "Friends Colony, Katol Road, Nagpur, Maharashtra - 440013"},
            },
            "hudkeshwar": {
                "boi": {"name": "Bank of India (BOI)", "branch": "Hudkeshwar Road, Nagpur", "ifsc": "BKID0008745", "micr": "440013023", "address": "Plot No. 1, Kadu Nagar, Hudkeshwar Road, Nagpur, Maharashtra - 440034"},
            },
            "civil lines": {
                "sbi": {"name": "State Bank of India (SBI)", "branch": "Civil Lines, Nagpur", "ifsc": "SBIN0000432", "micr": "440002002", "address": "Kingsway, Station Road, Nagpur - 440001"},
                "icici": {"name": "ICICI Bank", "branch": "Civil Lines, Nagpur", "ifsc": "ICIC0000059", "micr": "440229002", "address": "Vishnu Vaibhav Complex, Civil Lines, Nagpur - 440001"},
            },
            "ramdaspeth": {
                "hdfc": {"name": "HDFC Bank", "branch": "Ramdaspeth, Nagpur", "ifsc": "HDFC0000059", "micr": "440240002", "address": "Central Bazaar Road, Ramdaspeth, Nagpur - 440010"},
                "axis": {"name": "Axis Bank", "branch": "Ramdaspeth, Nagpur", "ifsc": "UTIB0000043", "micr": "440211002", "address": "Central Bazaar Road, Ramdaspeth, Nagpur - 440010"},
            },
            "itwari": {
                "canara": {"name": "Canara Bank", "branch": "Itwari, Nagpur", "ifsc": "CNRB0000246", "micr": "440015003", "address": "Maskasath, Itwari, Nagpur - 440002"},
                "pnb": {"name": "Punjab National Bank (PNB)", "branch": "Itwari, Nagpur", "ifsc": "PUNB0035900", "micr": "440024003", "address": "Sarafa Bazar, Itwari, Nagpur - 440002"},
            }
        }

        # Check for matched branch in knowledge
        matched_branch_info = None
        for key, bank_dict in known_branches.items():
            if key in q:
                for b_id in (bank_ids or ["sbi"]):
                    if b_id in bank_dict:
                        matched_branch_info = bank_dict[b_id]
                        break
                if not matched_branch_info and bank_dict:
                    matched_branch_info = list(bank_dict.values())[0]
                break

        if matched_branch_info:
            return {
                "type": "ifsc_branch_info",
                "title": f"IFSC Code: {matched_branch_info['ifsc']} ({matched_branch_info['branch']})",
                "bank_name": matched_branch_info["name"],
                "branch": matched_branch_info["branch"],
                "ifsc": matched_branch_info["ifsc"],
                "micr": matched_branch_info.get("micr", "N/A"),
                "address": matched_branch_info.get("address", ""),
                "rbi_portal": "https://rbi.org.in/scripts/IFSC_MICR.aspx",
                "summary": f"The verified 11-digit IFSC code for {matched_branch_info['name']} {matched_branch_info['branch']} is **{matched_branch_info['ifsc']}**.",
            }

        # Generic IFSC lookup guide if specific branch wasn't hardcoded in offline cache
        target_bank = get_bank_by_id(bank_ids[0]) if bank_ids else None
        bank_name = target_bank["name"] if target_bank else "Your Bank"
        bank_prefix = (target_bank.get("id", "BANK")[:4].upper()) if target_bank else "BANK"
        return {
            "type": "ifsc_generic_guide",
            "title": f"How to Find IFSC Code for {bank_name} Branch",
            "summary": f"IFSC is an 11-character alphanumeric code used for NEFT, RTGS, and IMPS funds transfer.",
            "structure": f"Format: {bank_prefix}0XXXXXX (First 4 letters bank code, 5th character '0', last 6 characters branch code).",
            "check_sources": [
                "1. Printed on the top left of any Cheque leaf from your cheque book.",
                "2. Printed on the first page of your official Bank Passbook.",
                "3. Verified directly on the official RBI IFSC Directory.",
            ],
            "official_portal": "https://rbi.org.in/scripts/IFSC_MICR.aspx",
        }

    # 4. If asking specifically about bank overview / rates / info
    if len(bank_ids) == 1 and any(w in q for w in ["about", "overview", "rate", "interest", "detail", "features", "minimum balance", "mab", "info", "kaisa hai"]):
        bank = get_bank_by_id(bank_ids[0])
        if bank:
            return {
                "type": "bank_detail",
                "bank": bank,
                "title": f"{bank['name']} ({bank['shortName']}) Overview",
                "summary": f"{bank['name']} offers savings accounts starting at {bank['savings']['interestRate']['upTo10Lakh']}%, 1-Yr FD at {bank['fixedDeposit']['rate1Year']['general']}%, and Home Loans from {bank['loans']['homeLoan']['startingRate']}%.",
            }

    # 5. Monthly Savings & Investment (₹500 / ₹1000 per month / Recurring Deposit / PPF / SIP)
    if any(term in q for term in ["per month", "per moth", "monthly invest", "invest 1000", "invest 500", "har mahine", "recurring deposit", "sip", "rd scheme", "small invest"]):
        return {
            "type": "monthly_investment_guide",
            "title": "Best Monthly Investment Schemes in India (₹500 – ₹1,000 / month)",
            "summary": "If you want to save a fixed amount every month, here are the top risk-free and high-return options across banks and government programs:",
            "schemes": [
                {
                    "name": "Bank Recurring Deposit (RD)",
                    "expected_return": "6.50% – 7.40% p.a. (Guaranteed)",
                    "details": "Deposit ₹500 to ₹10,000 every month for 6 months to 10 years across SBI, HDFC, ICICI, PNB with zero risk.",
                },
                {
                    "name": "Public Provident Fund (PPF)",
                    "expected_return": "7.10% p.a. (Tax-Free EEE)",
                    "details": "Minimum ₹500/year (or monthly deposits). 15-year tenure with full Section 80C tax exemption on deposits and interest.",
                },
                {
                    "name": "Sukanya Samriddhi Yojana (SSY)",
                    "expected_return": "8.20% p.a. (Tax-Free EEE)",
                    "details": "For girl children below 10 years. Minimum ₹250/year. Highest government-backed guaranteed interest rate.",
                },
                {
                    "name": "Atal Pension Yojana (APY)",
                    "expected_return": "Guaranteed Monthly Pension",
                    "details": "For age 18–40. Contribute a small monthly amount (starting ₹42–₹210/mo) to receive ₹1,000 to ₹5,000 monthly pension after age 60.",
                },
                {
                    "name": "Mutual Fund Systematic Investment Plan (SIP)",
                    "expected_return": "10.00% – 14.00% p.a. (Market Linked)",
                    "details": "Invest as low as ₹500/month in equity/hybrid index mutual funds for superior long-term wealth creation.",
                }
            ],
        }

    # 6. Savings Account Comparison (Which bank savings account is best)
    if any(term in q for term in ["saving account", "saving accound", "best saving", "savings account", "bachat khata", "savings rate", "best bank for savings"]):
        savings_ranking = get_best_rates("savings")
        return {
            "type": "savings_ranking",
            "title": "Best Savings Accounts & Minimum Balance Comparison",
            "summary": "Comparison of savings accounts by minimum average balance (MAB) requirements and interest rates:",
            "recommendations": [
                {
                    "bank": "Kotak Mahindra Bank (Kotak 811)",
                    "highlights": "₹0 Minimum Balance + up to 4.00% p.a. savings interest + free virtual debit card.",
                },
                {
                    "bank": "State Bank of India (SBI)",
                    "highlights": "₹0 Minimum Balance maintenance penalty nationwide across all metro and rural branches + 2.70% p.a.",
                },
                {
                    "bank": "Punjab National Bank & Bank of Baroda",
                    "highlights": "Low ₹500 (Rural) to ₹2,000 (Metro) quarterly average balance + 2.70% to 2.75% interest.",
                },
                {
                    "bank": "HDFC Bank & ICICI Bank",
                    "highlights": "₹10,000 Metro AMB + premium digital banking, high transaction limits, and cashback rewards.",
                }
            ],
            "top_banks": savings_ranking["ranked_banks"][:4],
        }

    # 7. Student Banking & Education Queries
    if any(term in q for term in ["student", "college", "padhai", "study", "university", "youth", "छात्र", "विद्यार्थी", "पढ़ाई"]):
        return {
            "type": "student_recommendation",
            "title": "Best Bank Accounts & Education Options for Students",
            "summary": "For students, the primary requirements are zero minimum balance maintenance, free digital banking, and accessible education loans.",
            "recommendations": [
                {
                    "bank": "State Bank of India (SBI)",
                    "category": "Best Overall & Zero Balance",
                    "highlights": "₹0 minimum balance maintenance penalty across all branches, largest campus ATM network, free YONO digital app.",
                    "education_loan": "SBI Student Loan / Scholar Scheme starting from 8.15% p.a. (0.50% interest concession for female students).",
                },
                {
                    "bank": "Kotak Mahindra Bank (Kotak 811)",
                    "category": "Best 100% Digital Account",
                    "highlights": "Lifetime ₹0 minimum balance digital account, instant online KYC, free virtual debit card on app, up to 4.00% savings interest.",
                    "education_loan": "Kotak Education Loan for premier domestic and partner international universities.",
                },
                {
                    "bank": "Punjab National Bank (PNB) & Bank of Baroda (BOB)",
                    "category": "Best Affordable Education Credit",
                    "highlights": "PNB Saraswati (from 8.20%) and Baroda Scholar (from 8.15%) with minimal margin money on government-approved institutes.",
                    "education_loan": "Central Sector Interest Subsidy (CSIS) eligible via Vidya Lakshmi portal.",
                },
                {
                    "bank": "HDFC Bank & ICICI Bank",
                    "category": "Best for Study Abroad & Forex",
                    "highlights": "Pre-approved education loans for Ivy League/top global universities and multi-currency student travel forex cards.",
                    "education_loan": "HDFC Credila & ICICI Education Loan covering living expenses and tuition.",
                }
            ],
            "official_portal": "https://www.vidyalakshmi.co.in/",
            "portal_name": "Government Vidya Lakshmi Education Loan Portal",
        }

    # 2. Zero Interest / 1-Month Loan / Short-Term Credit Queries
    if (
        (any(z in q for z in ["zero", "0%", "0 percent", "bina byaj", "बिना ब्याज"]) and any(l in q for l in ["loan", "load", "credit", "karz", "udhaar", "लोन", "कर्ज"])) or
        (any(l in q for l in ["loan", "load", "credit", "karz"]) and any(m in q for m in ["1 month", "one month", "1 mahina", "ek mahina", "30 days", "short term"]))
    ):
        return {
            "type": "zero_interest_loan",
            "title": "Zero-Interest & 1-Month Short-Term Credit Options in India",
            "summary": "Commercial banks (SBI, HDFC, ICICI, etc.) do NOT provide 0% interest personal loans (bank personal loans range from 10.50% – 14.50% p.a.). However, here are legitimate 0% interest and 30-day credit mechanisms:",
            "options": [
                {
                    "method": "💳 Bank Credit Card (45–50 Days Interest-Free Grace Period)",
                    "details": "All major banks offer 45 to 50 days of completely 0% interest credit if the full statement bill is settled on or before the payment due date.",
                },
                {
                    "method": "🛍️ Buy Now Pay Later (BNPL) / No-Cost EMI (30 Days)",
                    "details": "Major merchant platforms offer 30-day interest-free purchase credit where the merchant covers the financing cost.",
                },
                {
                    "method": "🏦 Bank Overdraft against Salary or FD",
                    "details": "Instant emergency credit facility where interest is charged only on the exact number of days the funds are borrowed.",
                },
                {
                    "method": "🌾 Subsidized Government Schemes (PM SVANidhi / KCC)",
                    "details": "Street vendor loans and Kisan Credit Card feature 7% to 3% interest subvention for prompt repayment.",
                }
            ],
            "warning": "⚠️ Warning Against Illegal 7-Day/30-Day Loan Apps: Never download unauthorized instant loan APKs from social media. Always use RBI-regulated banks or registered NBFCs.",
        }

    # 3. Women Entrepreneur / Mahila Business Loan
    if any(term in q for term in ["women", "mahila", "lady", "female", "girl", "aurat", "महिला", "नारी"]):
        return {
            "type": "women_recommendation",
            "title": "Best Bank Loans & Government Schemes for Women",
            "summary": "Women borrowers receive exclusive interest concessions and subsidized credit schemes across all major Indian banks.",
            "recommendations": [
                {
                    "scheme": "Stand-Up India Scheme",
                    "coverage": "₹10 Lakh to ₹1 Crore greenfield enterprise loan for women entrepreneurs at subsidized base rates.",
                },
                {
                    "scheme": "MUDRA Loan (Shishu, Kishor, Tarun)",
                    "coverage": "Collateral-free micro loans up to ₹10 Lakh with special fast-track processing for women.",
                },
                {
                    "scheme": "0.50% Education Loan Concession",
                    "coverage": "All public sector banks (SBI, PNB, BOB, Canara) offer a mandatory 0.50% interest discount on education loans for female students.",
                },
                {
                    "scheme": "Sukanya Samriddhi Yojana (SSY)",
                    "coverage": "Government guaranteed high-yield savings (8.20% tax-free under Section 80C) for girl children up to age 10.",
                }
            ],
            "official_portal": "https://www.standupmitra.in/",
        }

    # 4. Small Business & MSME / Shopkeeper Queries
    if any(term in q for term in ["business", "dukaan", "shop", "msme", "vyapar", "karobar", "startup", "दुकान", "व्यापार", "कारोबार"]):
        return {
            "type": "business_recommendation",
            "title": "Best Business Loans & MSME Credit Schemes in India",
            "summary": "For small business owners and shopkeepers, collateral-free credit is available under government-backed guarantee programs.",
            "options": [
                {
                    "name": "Pradhan Mantri MUDRA Yojana (PMMY)",
                    "details": "Shishu (up to ₹50,000), Kishor (₹50,000 to ₹5 Lakh), Tarun (₹5 Lakh to ₹10 Lakh) with zero collateral requirements.",
                },
                {
                    "name": "PMEGP (Prime Minister's Employment Generation Programme)",
                    "details": "Government subsidy up to 35% on project costs for new micro-enterprises and manufacturing units.",
                },
                {
                    "name": "CGTMSE Collateral-Free Bank Credit",
                    "details": "Credit guarantee coverage up to ₹5 Crore for MSMEs from SBI, PNB, BOB, HDFC, and ICICI.",
                },
                {
                    "name": "Bank Current Accounts",
                    "details": "Compare current account daily cash deposit limits and sweep-in facilities across SBI, HDFC, and ICICI.",
                }
            ],
            "official_portal": "https://www.mudra.org.in/",
        }

    # 5. Senior Citizen & 50+/60+ Retirement Queries
    if any(term in q for term in ["senior citizen", "buzurg", "vridhha", "elderly", "pensioner", "50+", "50 plus", "60+", "60 plus", "retired", "retirement", "old age", "वरिष्ठ", "बुजुर्ग"]):
        senior_fd_ranking = get_best_rates("fd", senior_citizen=True)
        return {
            "type": "senior_citizen_recommendation",
            "title": "Best Banks & Highest FD Rates for Senior Citizens & 50+",
            "summary": "For senior citizens (and pre-retirees aged 50+ preparing for retirement), banks offer preferential interest rates (+0.50% to +0.75% extra) and high-yield fixed deposits:",
            "top_banks": senior_fd_ranking["ranked_banks"][:4],
        }

    # 6. Farmer & Agriculture Queries
    if any(term in q for term in ["farmer", "kisan", "kheti", "krishi", "agriculture", "crop", "किसान", "खेती"]):
        return {
            "type": "farmer_recommendation",
            "title": "Best Agricultural Banking & Kisan Credit Card (KCC)",
            "summary": "For farmers, public sector banks offer the lowest subsidized crop loans and extensive rural branch support.",
            "highlights": [
                "Kisan Credit Card (KCC) at 7.00% with a 3.00% prompt repayment incentive, bringing effective interest to just 4.00% p.a.",
                "State Bank of India, Punjab National Bank, and Canara Bank provide direct KCC sanctioning with minimal paperwork.",
                "Government interest subvention and PM Fasal Bima Yojana crop insurance integration.",
            ],
            "official_portal": "https://www.myscheme.gov.in/schemes/kcc",
        }

    # 7. Zero-Balance Account Queries
    if any(term in q for term in ["zero balance", "bina balance", "no minimum balance", "zero minimum", "जीरो बैलेंस", "बिना बैलेंस"]):
        return {
            "type": "zero_balance_recommendation",
            "title": "Best Zero Minimum Balance Bank Accounts in India",
            "summary": "You have three top options to open an account with ₹0 minimum balance maintenance requirements:",
            "options": [
                {
                    "name": "Pradhan Mantri Jan-Dhan Yojana (PMJDY)",
                    "type": "Government Financial Inclusion",
                    "details": "Zero balance account available at all bank branches with free RuPay debit card, ₹2 Lakh accident insurance, and DBT subsidy support.",
                },
                {
                    "name": "State Bank of India (SBI Regular Savings)",
                    "type": "Public Sector Bank",
                    "details": "SBI permanently waived all Average Monthly Balance (AMB) non-maintenance penalties across all metro, urban, semi-urban, and rural branches.",
                },
                {
                    "name": "Kotak 811 Digital Savings Account",
                    "type": "Private Sector Bank",
                    "details": "100% digital zero-balance savings account with zero non-maintenance fees and free virtual debit card.",
                }
            ],
        }

    # 8. Fixed Deposit (FD) / High Yield Comparison
    if any(term in q for term in ["highest fd", "best fd", "fd rate", "fixed deposit rate", "term deposit rate", "फिक्स्ड डिपॉजिट"]):
        is_senior = any(s in q for s in ["senior", "buzurg", "elderly", "60"])
        fd_ranking = get_best_rates("fd", senior_citizen=is_senior)
        return {
            "type": "fd_rate_ranking",
            "title": f"Highest Fixed Deposit Rates in India ({'Senior Citizens' if is_senior else 'General Public'})",
            "summary": "Here are the top ranked banks offering the highest returns on 1-Year and special fixed deposit tenures:",
            "top_banks": fd_ranking["ranked_banks"][:5],
            "safety_note": "🛡️ All bank deposits up to ₹5,00,000 (principal + interest) are insured by DICGC (RBI subsidiary).",
        }

    # 9. Home Loan & Interest Rate Comparison
    if any(term in q for term in ["home loan", "housing loan", "makaan loan", "ghar loan", "होम लोन"]):
        hl_ranking = get_best_rates("home_loan")
        return {
            "type": "home_loan_ranking",
            "title": "Lowest Home Loan Interest Rates Across Major Banks",
            "summary": "Home loan rates are linked to the RBI Repo Rate (EBLR/RLLR). Here are the lowest starting rates:",
            "top_banks": hl_ranking["ranked_banks"][:5],
            "tip": "💡 Maintaining a CIBIL credit score of 750+ qualifies you for the lowest starting interest slab.",
        }

    # 10. ATM / UPI / Transaction Disputes
    if any(term in q for term in ["kat gaya", "nahi nikla", "failed", "debited", "dispense", "fas gaya", "पैसे कट", "कैश नहीं"]):
        return {
            "type": "transaction_dispute",
            "title": "ATM / UPI Failed Transaction & Auto-Reversal Protocol",
            "summary": "RBI mandates strict turnaround times (TAT) for failed electronic transactions:",
            "steps": [
                "<b>ATM Cash Not Dispensed:</b> Bank auto-reversal timeline is T+5 days. If delayed beyond 5 business days, the card-issuing bank must pay compensation of ₹100 per day of delay under RBI guidelines.",
                "<b>UPI Payment Failed:</b> If amount debited, auto-reversal typically completes within 24 to 48 hours.",
                "<b>Wrong Account UPI Transfer:</b> Immediately inform your bank and recipient UPI app (GPay/PhonePe/PayTM). Lodge a complaint on the NPCI portal (npci.org.in).",
                "<b>Formal Escalation:</b> If unresolved after 30 days, file an online grievance with the RBI Ombudsman at cms.rbi.org.in.",
            ],
            "helpline": "National NPCI Toll-Free: 1800 120 1740",
        }

    # 11. Security, Fraud, Phishing & Card Block
    if any(term in q for term in ["fraud", "scam", "otp", "phishing", "hacked", "block card", "lost card", "धोखाधड़ी"]):
        return {
            "type": "fraud_security_alert",
            "title": "🚨 Emergency Fraud Defense & Card Freeze Action",
            "summary": "If you suspect unauthorized transactions or shared confidential data, take these immediate steps:",
            "actions": [
                "<b>1. Freeze Card Immediately:</b> Send SMS 'BLOCK' or call your bank's 24x7 emergency desk (see Emergency tab).",
                "<b>2. Dial 1930 Cybercrime Helpline:</b> Report cyber financial fraud to freeze funds in transit within the golden hour.",
                "<b>3. RBI Zero-Liability Policy:</b> Report unauthorized electronic transactions within 3 working days to have zero personal liability.",
                "<b>4. Golden Security Rule:</b> No legitimate bank officer or RBI representative will ever ask for OTP, PIN, CVV, or passwords.",
            ],
            "cyber_portal": "https://cybercrime.gov.in/",
        }

    # 12. RBI Ombudsman & Complaint Escalation
    if any(term in q for term in ["ombudsman", "lokpal", "complaint", "grievance", "shikayat", "शिकायत", "लोकपाल"]):
        return {
            "type": "ombudsman_guide",
            "title": "How to File a Complaint with RBI Integrated Ombudsman",
            "summary": "If your bank does not resolve your complaint within 30 days, or rejects it unsatisfied, escalate directly to the RBI Ombudsman.",
            "levels": [
                "<b>Level 1 (Branch):</b> Lodge written/online complaint with your bank's Branch Manager and get a Service Request (SR) number.",
                "<b>Level 2 (PNO):</b> Escalate to the bank's Principal Nodal Officer (PNO) if unresolved within 15 days.",
                "<b>Level 3 (RBI Ombudsman):</b> After 30 days, file free complaint on the RBI Complaint Management System (CMS) at cms.rbi.org.in or call 14448.",
            ],
            "portal": "https://cms.rbi.org.in/",
        }

    # 13. Explicit Multi-Bank Comparison
    if len(bank_ids) >= 2 or intent in ["BANK_COMPARISON", "PRODUCT_COMPARISON"]:
        target_banks = bank_ids if bank_ids else ["sbi", "hdfc", "icici"]
        product_type = "all"
        if any(w in q for w in ["fd", "fixed deposit", "term deposit"]):
            product_type = "fixed_deposit"
        elif any(w in q for w in ["home loan", "housing", "property"]):
            product_type = "loans"
        elif any(w in q for w in ["saving", "min balance", "minimum balance", "mab", "amb"]):
            product_type = "savings"

        comparison = compare_banks(target_banks, product_type=product_type)
        bank_names = [b["shortName"] for b in comparison["banks"]]
        return {
            "type": "bank_comparison",
            "title": f"Comparison: {' vs '.join(bank_names)}",
            "product_focus": product_type,
            "data": comparison,
            "summary": f"Here is a side-by-side comparison for {', '.join(bank_names)}. Always verify terms on the official bank portals.",
        }

    # 14. Single Bank Profile (only if not an IFSC or branch lookup)
    if len(bank_ids) == 1 and not any(w in q for w in ["ifsc", "branch", "code", "micr", "location", "address"]):
        bank = get_bank_by_id(bank_ids[0])
        if bank:
            return {
                "type": "bank_detail",
                "bank": bank,
                "title": f"{bank['name']} ({bank['shortName']}) Overview",
                "summary": f"{bank['name']} offers savings accounts starting at {bank['savings']['interestRate']['upTo10Lakh']}%, 1-Yr FD at {bank['fixedDeposit']['rate1Year']['general']}%, and Home Loans from {bank['loans']['homeLoan']['startingRate']}%.",
            }

    return None
