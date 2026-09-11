from app.services.financial_validation_service import run_validation


def _field(value):
    return {"value": value, "source_text": None, "page_number": None}


def test_invoice_total_check_passes():
    fields = {
        "subtotal": _field(12500.00),
        "tax_amount": _field(625.00),
        "discount": _field(0.00),
        "total_amount": _field(13125.00),
    }
    result = run_validation("invoice", fields, {})
    check = result["checks"][0]
    assert check["status"] == "PASS"
    assert result["overall_status"] == "PASS"


def test_invoice_total_check_fails_on_mismatch():
    fields = {
        "subtotal": _field(12500.00),
        "tax_amount": _field(625.00),
        "discount": _field(0.00),
        "total_amount": _field(10000.00),  # wrong on purpose
    }
    result = run_validation("invoice", fields, {})
    assert result["checks"][0]["status"] == "FAIL"
    assert result["overall_status"] == "FAIL"


def test_invoice_missing_field_is_not_applicable():
    fields = {
        "subtotal": _field(None),
        "tax_amount": _field(625.00),
        "total_amount": _field(13125.00),
    }
    result = run_validation("invoice", fields, {})
    assert result["checks"][0]["status"] == "NOT_APPLICABLE"


def test_balance_sheet_equation():
    fields = {
        "total_assets": _field(1000.0),
        "total_liabilities": _field(600.0),
        "total_equity": _field(400.0),
    }
    result = run_validation("balance_sheet", fields, {})
    assert result["overall_status"] == "PASS"


def test_cash_flow_statement_checks():
    fields = {
        "operating_cash_flow": _field(500.0),
        "investing_cash_flow": _field(-200.0),
        "financing_cash_flow": _field(-50.0),
        "net_change_in_cash": _field(250.0),
        "opening_cash": _field(1000.0),
        "closing_cash": _field(1250.0),
    }
    result = run_validation("cash_flow_statement", fields, {})
    assert result["overall_status"] == "PASS"
