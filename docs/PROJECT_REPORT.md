# BankSathi — Final Year Project Brief

## Problem statement

People frequently need help choosing banking products or identifying government financial-inclusion schemes, but information is scattered and product language is difficult. BankSathi is an educational, India-focused chatbot that translates a user’s plain-language goal into a short, source-linked list of relevant banking options.

## Proposed solution

The client-side single-page application has three modules: an NLP chatbot, a profile-based scheme finder and an EMI planner. It stores no personal data and makes no real-time bank decision. The system treats every answer as an explanation and routes the user to the relevant official authority to verify current terms.

## NLP methodology

1. **Normalisation:** query is lower-cased, punctuation is removed and tokens are extracted.
2. **Hinglish synonym expansion:** words such as `khata`, `dukkan`, `bima`, `kisan` and `udhaar` map to common banking concepts.
3. **Intent classification:** deterministic rules identify safety, EMI, recommendation, greeting and knowledge intents.
4. **Entity/relevance scoring:** query terms are compared with each scheme’s name, category, tags, summary and eligibility field. Highest-scoring entries are returned.
5. **Explainable response:** answer displays the selected scheme, reason/eligibility summary and an official source rather than hiding the basis in a black-box model.

## Dataset design

`data/banking-knowledge.json` contains 18 records across financial inclusion, deposits, loans, government schemes, insurance, pension, investments and consumer protection. Each record has an ID, tags, human-readable eligibility, benefits, official source, authority and verification date. Live rates and changing fees are deliberately excluded.

## Safety and ethics

- No user data is sent to a server or retained.
- The interface warns against sharing OTP, PIN, CVV, passwords and account numbers.
- It never claims loan approval, confirms scheme eligibility, or gives personalised investment/tax/legal advice.
- Sources, last-verification dates and limitations are visible in the dataset.
- Production use requires a scheduled review of each official source and accessibility/usability tests with diverse users.

## Evaluation plan

Create a labelled set of 50 test questions (10 per intent). Measure intent accuracy and top-3 scheme retrieval accuracy. Conduct a small usability study asking participants to complete tasks such as finding a zero-balance account, a farmer credit option and the correct complaint route. Track task completion, time and perceived clarity. Analyse unmatched questions to extend synonyms/tags.

## Limitations and future work

This demonstrator uses rules rather than a trained transformer and does not integrate bank APIs. Future versions can add multilingual Indian-language models, retrieval from officially maintained APIs, authentication with consent, a database audit trail, accessibility localisation and human banker escalation.
