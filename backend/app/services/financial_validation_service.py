"""
Stage 4: Financial calculation validation (section 4.4 / Table 7 of the spec).

Rule that governs everything here: a check runs ONLY if all the fields it needs
are present (not null). If any required input is missing, the check's status
is NOT_APPLICABLE — we never assume or invent a value to force a PASS/FAIL.
"""
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _val(fields: Dict[str, Any], name: str) -> Optional[float]:
    """Pulls a numeric field's value out of the {"value":..., ...} shape."""
    field = fields.get(name)
    if not isinstance(field, dict):
        return None
    v = field.get("value")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _check(name: str, formula: str, operands: Dict[str, Optional[float]],
           calculated: Optional[float], reported: Optional[float]) -> Dict[str, Any]:
    """Builds one validation check result, applying NOT_APPLICABLE / PASS / FAIL logic."""
    if calculated is None or reported is None or any(v is None for v in operands.values()):
        return {
            "name": name,
            "formula": formula,
            "operands": operands,
            "calculated_value": calculated,
            "reported_value": reported,
            "variance": None,
            "status": "NOT_APPLICABLE",
        }

    variance = round(calculated - reported, 2)
    status = "PASS" if abs(variance) <= settings.VALIDATION_TOLERANCE else "FAIL"
    return {
        "name": name,
        "formula": formula,
        "operands": operands,
        "calculated_value": round(calculated, 2),
        "reported_value": round(reported, 2),
        "variance": variance,
        "status": status,
    }


def _summarize(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    statuses = [c["status"] for c in checks]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif all(s == "NOT_APPLICABLE" for s in statuses) and statuses:
        overall = "NOT_APPLICABLE"
    else:
        overall = "PASS"
    issues = [c["name"] for c in checks if c["status"] == "FAIL"]
    return {"checks": checks, "overall_status": overall, "issues": issues}


def validate_invoice(fields: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    subtotal = _val(fields, "subtotal")
    tax = _val(fields, "tax_amount")
    discount = _val(fields, "discount") or 0.0
    total = _val(fields, "total_amount")

    checks = [
        _check(
            "invoice_total_check",
            "subtotal + tax_amount - discount",
            {"subtotal": subtotal, "tax_amount": tax, "discount": discount},
            None if subtotal is None or tax is None else subtotal + tax - discount,
            total,
        )
    ]

    # Line items reconciliation, if a line_items table is present
    line_items = tables.get("line_items")
    if isinstance(line_items, list) and line_items:
        try:
            line_sum = sum(float(li.get("amount", 0) or 0) for li in line_items)
            checks.append(_check(
                "line_items_sum_check",
                "sum(line_items.amount) ≈ subtotal",
                {"line_items_sum": line_sum},
                line_sum,
                subtotal,
            ))
        except (TypeError, ValueError):
            logger.warning("Could not sum line_items amounts; skipping that check")

    return _summarize(checks)


def validate_balance_sheet(fields: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    assets = _val(fields, "total_assets")
    liabilities = _val(fields, "total_liabilities")
    equity = _val(fields, "total_equity")

    checks = []

    if liabilities is not None and equity is not None:
        checks.append(_check(
            "balance_sheet_equation",
            "total_liabilities + total_equity ≈ total_assets",
            {"total_liabilities": liabilities, "total_equity": equity},
            liabilities + equity,
            assets,
        ))
    else:
        # Some balance sheets (notably banks/financial institutions) report a
        # single combined "Capital and Liabilities" figure instead of
        # splitting liabilities and equity separately. The universal rule
        # that always holds is: Total Assets = Total Capital and Liabilities.
        capital_and_liabilities = _val(fields, "total_capital_and_liabilities")
        checks.append(_check(
            "balance_sheet_equation_combined",
            "total_capital_and_liabilities ≈ total_assets",
            {"total_capital_and_liabilities": capital_and_liabilities},
            capital_and_liabilities,
            assets,
        ))

    return _summarize(checks)


def validate_profit_and_loss(fields: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    revenue = _val(fields, "revenue")
    cogs = _val(fields, "cost_of_sales")
    gross_profit = _val(fields, "gross_profit")
    opex = _val(fields, "operating_expenses")
    operating_profit = _val(fields, "operating_profit")
    tax = _val(fields, "tax")
    net_profit = _val(fields, "net_profit")

    checks = [
        _check(
            "gross_profit_check",
            "revenue - cost_of_sales ≈ gross_profit",
            {"revenue": revenue, "cost_of_sales": cogs},
            None if revenue is None or cogs is None else revenue - cogs,
            gross_profit,
        ),
        _check(
            "operating_profit_check",
            "gross_profit - operating_expenses ≈ operating_profit",
            {"gross_profit": gross_profit, "operating_expenses": opex},
            None if gross_profit is None or opex is None else gross_profit - opex,
            operating_profit,
        ),
        _check(
            "net_profit_check",
            "operating_profit - tax ≈ net_profit",
            {"operating_profit": operating_profit, "tax": tax},
            None if operating_profit is None or tax is None else operating_profit - tax,
            net_profit,
        ),
    ]
    return _summarize(checks)

def validate_cash_flow_statement(fields: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    ocf = _val(fields, "operating_cash_flow")
    icf = _val(fields, "investing_cash_flow")
    fcf = _val(fields, "financing_cash_flow")
    net_change = _val(fields, "net_change_in_cash")
    opening = _val(fields, "opening_cash")
    closing = _val(fields, "closing_cash")
    # Optional: some companies (especially those with foreign operations) have
    # a 4th adjustment — FX translation effect — between the three cash flow
    # categories and the net change in cash. Include it if present; default to
    # 0 (i.e. no effect) if this document doesn't report one, so the check
    # still runs normally for companies without foreign currency exposure.
    fx_effect = _val(fields, "fx_translation_effect") or 0.0

    net_change_calc = None
    if ocf is not None and icf is not None and fcf is not None:
        net_change_calc = ocf + icf + fcf + fx_effect

    closing_calc = None
    if opening is not None and net_change is not None:
        closing_calc = opening + net_change

    checks = [
        _check(
            "net_change_in_cash_check",
            "operating_cash_flow + investing_cash_flow + financing_cash_flow (+ fx_translation_effect, if any) ≈ net_change_in_cash",
            {"operating_cash_flow": ocf, "investing_cash_flow": icf, "financing_cash_flow": fcf, "fx_translation_effect": fx_effect},
            net_change_calc,
            net_change,
        ),
        _check(
            "closing_cash_check",
            "opening_cash + net_change_in_cash ≈ closing_cash",
            {"opening_cash": opening, "net_change_in_cash": net_change},
            closing_calc,
            closing,
        ),
    ]
    return _summarize(checks)



VALIDATORS = {
    "invoice": validate_invoice,
    "balance_sheet": validate_balance_sheet,
    "profit_and_loss": validate_profit_and_loss,
    "cash_flow_statement": validate_cash_flow_statement,
}


def run_validation(document_type: str, fields: Dict[str, Any], tables: Dict[str, Any]) -> Dict[str, Any]:
    validator = VALIDATORS.get(document_type)
    if validator is None:
        return {"checks": [], "overall_status": "NOT_APPLICABLE", "issues": []}
    return validator(fields, tables)