from src.translate_insights import protect_text, restore_text


def test_protects_names_currency_amounts_signs_and_tickers_as_whole_values():
    original = "John Keells Holdings PLC (JKH.N0000) is LKR 18.00, +5.00%; USD 4.00 is not LKR 4.00."
    masked, replacements = protect_text(original, ["John Keells Holdings PLC"])
    assert "John Keells" not in masked
    assert "LKR" not in masked
    assert "18.00" not in masked
    assert "LKR 18.00" in replacements.values()
    assert restore_text(masked, replacements) == original


def test_missing_duplicate_and_unknown_placeholders_are_rejected():
    masked, replacements = protect_text("Price LKR 18.00", [])
    marker = next(iter(replacements))
    assert restore_text(masked.replace(marker, ""), replacements) is None
    assert restore_text(masked + marker, replacements) is None
    assert restore_text(masked + " [[KEEP9999]]", replacements) is None


def test_iso_dates_are_preserved_as_one_value():
    masked, replacements = protect_text("Checked on 2026-10-19, price LKR 18.00.", [])
    assert "2026-10-19" in replacements.values()
    assert restore_text(masked, replacements) == "Checked on 2026-10-19, price LKR 18.00."


def test_fiscal_years_quarters_and_currency_names_are_not_split_into_unrelated_numbers():
    text = "In 2026/27 Q1 a US Dollar loan was reported; 8-pct changed."
    masked, replacements = protect_text(text, [])
    assert {"2026/27", "Q1", "US Dollar", "8-pct"} <= set(replacements.values())
    assert restore_text(masked, replacements) == text
