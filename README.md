# BankSathi — Banking Decision Assistant

A final-year-project prototype for an India-focused banking help chatbot. It combines a small, explainable NLP intent engine with a locally stored, source-attributed knowledge base.

## Run

Open `index.html` in any modern browser. No installation, API key, database, or server is required.

## Features

- Natural-language banking questions with tokenisation, synonym expansion and scored intent/entity matching
- Scheme finder that uses age, occupation, income and need to rank applicable programmes
- Product comparison and a transparent loan EMI calculator
- 18 curated banking, government, investment and consumer-protection entries in `data/banking-knowledge.json`
- English/Hinglish query support and clickable official sources
- Safety-first answers: no account data is collected, and the bot never presents an eligibility result as approval or investment advice

## Project structure

```
index.html                  Application shell
styles.css                  Responsive visual design
app.js                      NLP, ranking, calculator and UI logic
data/banking-knowledge.json Source-attributed knowledge base
docs/PROJECT_REPORT.md      Problem statement, methodology and evaluation plan
```

## Data governance

The supplied data captures scheme summaries and stable eligibility concepts, not live interest rates or bank-specific terms. Every entry includes an official source and a `lastVerified` date. Before a production/demo evaluation, validate every time-sensitive field (rates, premiums, limits and eligibility) on the linked authority website.
