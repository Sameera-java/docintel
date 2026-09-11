"""
Defines, per document type, the minimum required fields (from the spec table)
plus instructions telling the LLM to also capture every OTHER visible field.
These are used to build the Gemini prompt — not to restrict what can be
extracted, only to guarantee the minimum set is always attempted.
"""

# Minimum required fields per document type (section 4 / Table 4 of the spec).
# The LLM is instructed to extract these AND any other meaningful fields/tables
# it sees — this list is a floor, not a ceiling.
MINIMUM_FIELDS = {
    "invoice": [
        "invoice_number", "invoice_date", "vendor_name", "customer_name",
        "currency", "subtotal", "tax_amount", "discount", "total_amount",
    ],
        "balance_sheet": [
        "total_assets", "total_liabilities", "total_equity", "total_capital_and_liabilities",
    ],
    "profit_and_loss": [
        "revenue", "cost_of_sales", "gross_profit", "operating_expenses",
        "operating_profit", "tax", "net_profit",
    ],
        "cash_flow_statement": [
        "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
        "opening_cash", "net_change_in_cash", "closing_cash",
        "fx_translation_effect",
    ],
}

DOCUMENT_DESCRIPTIONS = {
    "invoice": "a commercial invoice, including any line-item table (description, quantity, unit price, amount)",
    "balance_sheet": "a company balance sheet, including all asset/liability/equity line items, for every period/year shown",
    "profit_and_loss": "a profit & loss (income) statement, including every income/expense line item, for every period/year shown",
    "cash_flow_statement": "a cash flow statement, including operating/investing/financing sections, for every period shown",
}


def build_extraction_prompt(document_type: str, source_text: str) -> str:
    """Builds the instruction sent to the LLM for structured extraction."""
    min_fields = MINIMUM_FIELDS.get(document_type, [])
    description = DOCUMENT_DESCRIPTIONS.get(document_type, "a financial document")

    return f"""You are a financial document extraction engine. You will be given the raw
text (from OCR / PDF text extraction) of {description}.

Extract ALL meaningful fields, values, and tables visible in the text — not just a
fixed short list. At minimum, attempt to extract these fields if present: {min_fields}.

STRICT RULES:
1. Return ONLY valid JSON, no markdown, no commentary.
2. If a value is not present or not legible in the text, set its "value" to null.
   NEVER invent, guess, or infer a value that is not supported by the text.
3. For every scalar field, return an object: {{"value": <value or null>, "source_text": "<verbatim snippet supporting it, or null>", "page_number": <int or null>}}.
4. For tables/line items (e.g. invoice line items, balance sheet line items), return
   an array of objects with the columns present in the source document.
5. If the document shows multiple periods/years (common in balance sheets, P&L,
   cash flow statements): the top-level "fields" object must contain ONLY the
   MOST RECENT period's value for each field, in the flat scalar shape described
   in rule 3 above (never nested by period, never a dict of periods). Put the
   FULL multi-period breakdown (every period, every line item) as a table in
   "tables" instead — this keeps "fields" predictable for automated checks while
   still capturing every period's data in "tables". Do not lose any information;
   just don't nest multiple periods under a field name in "fields".6. Preserve the sign of bracketed/parenthesised numbers as negative.
7. Use numbers (not strings) for numeric values, after removing currency symbols and thousands separators.

Return a single JSON object with two top-level keys:
- "fields": object mapping field_name -> {{"value":..., "source_text":..., "page_number":...}}
- "tables": object mapping table_name -> array of row objects (empty object if no tables)

SOURCE TEXT:
---
{source_text}
---
"""
