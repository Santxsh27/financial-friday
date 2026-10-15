# Artificial statement for trying Financial Friday

Use `friday-artificial-statement.csv`. Every row is fictional and explicitly
labelled ARTIFICIAL. There are no real names, accounts, bank identifiers or funds.

1. Open Home and choose **Add a statement**.
2. Select this CSV; use nickname **Fictional main**, type **Bank account**.
3. Read and confirm the processing notice, then choose **Read my statement**.
4. Expect an **unsaved** preview of **19 transactions**, August–September 2026.
   Review the labels; confirm review only if you want to save this test history.
5. Choose **Save & see my spending** to explore categories and months. For chat,
   choose **Choose what I can use → Share my saved statement totals → Done**, then
   send: `Explain my spending and suggest one realistic next step.`

With the supplied local interpretation labels unchanged:

| Measure | Expected total |
| --- | ---: |
| Identified income | INR 90,000.00 |
| Classified spending | INR 43,999.00 |
| Loan repayments | INR 10,000.00 |
| Card repayments (not new spending) | INR 6,000.00 |
| Loan received (not earned income) | INR 50,000.00 |

Housing is the largest spending category at INR 24,000.00. Card purchases are
not included, so Friday should warn about missing card coverage. These are not a
bank balance, a savings guarantee, a fraud verdict, or evidence of outstanding debt.

CSV parsing and the initial label proposals use deterministic local rules, not a
Gemini call. The optional conversation uses live Gemini only when configured.
Re-uploading the exact file does not add it twice. After saving, use **Manage
imports → Exclude from analysis** to keep this fictional file out of your totals;
the exclusion is reversible. Do not mix this example into real financial analysis.
