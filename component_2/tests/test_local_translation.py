import re

import pytest

from src.local_translation import split_sentences, target_language_text, normalize_local_output, encode_markers, decode_markers, financial_phrase, valid_piece
from src.translate_insights import translate_payload


def test_chunking_preserves_every_word_including_long_overviews():
    original = "Revenue may improve. " + "Higher transport costs could reduce profit. " * 80
    chunks = split_sentences(original, str.split, maximum=20)
    assert " ".join(" ".join(chunks).split()) == " ".join(original.split())
    assert all(len(chunk.split()) <= 20 for chunk in chunks)


def test_normalizes_only_marker_brackets_not_missing_or_changed_ids():
    assert normalize_local_output("[KEEP0001] [[KEEP0002]]") == "[[KEEP0001]] [[KEEP0002]]"
    assert normalize_local_output("[KEEP99]") == "[KEEP99]"
    assert normalize_local_output("ප් රවාහන") == "ප්‍රවාහන"
    assert normalize_local_output("කොටස් මිල") == "කොටස් මිල"


def test_internal_numeric_sentinels_round_trip_but_never_guess_changed_values():
    text = "Revenue [[KEEP0000]], price [[KEEP0042]]."
    assert decode_markers(encode_markers(text)) == text
    assert decode_markers("47165") == "[[KEEP0042]]"
    assert decode_markers("47,165") == "47,165"


@pytest.mark.parametrize("language", ["si", "ta"])
def test_financial_comparison_templates_preserve_values_without_guessing_direction(language):
    source = "Gross profit increased by about [[KEEP0000]], while gross margin moved from about [[KEEP0001]] to [[KEEP0002]]."
    result = financial_phrase(source, language)
    assert valid_piece(source, result, language)
    # Only the first clause asserts growth; the margin clause stays neutral.
    assert result.count("වැඩි") == (1 if language == "si" else 0)
    assert result.count("அதிகரித்தது") == (1 if language == "ta" else 0)


def test_sentence_validation_rejects_new_numbers_and_omitted_financial_markers():
    source = "The price is [[KEEP0000]]."
    assert valid_piece(source, "මිල [[KEEP0000]] වේ.", "si")
    assert not valid_piece(source, "මිල වැඩි විය.", "si")
    assert not valid_piece(source, "මිල [[KEEP0000]] වේ. 99%", "si")


@pytest.mark.parametrize("language,translated", [
    ("si", "ආදායම වැඩි විය. මෙය ආයෝජන උපදෙසක් නොවේ."),
    ("ta", "வருவாய் அதிகரித்தது. இது முதலீட்டு ஆலோசனை அல்ல."),
])
def test_checks_target_script_and_rejects_english_or_repeated_garbage(language, translated):
    assert target_language_text(translated, language)
    assert not target_language_text("Revenue increased significantly.", language)
    assert not target_language_text(translated + " The current price might decline if oil prices rise. " * 4, language)
    assert not target_language_text((translated + " ") * 8, language)


def test_legitimate_repeated_forecast_wording_is_not_a_generation_loop():
    text = " ".join(f"மாதம் [[KEEP{index:04d}]] தற்போதைய விலையில் இருந்து மாற்றம். வெவ்வேறு காலம் {index}." for index in range(8))
    assert target_language_text(text, "ta")


def test_nllb_restores_names_and_figures_without_invoking_explanation_model(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "nllb")

    class Translator:
        def translate(self, texts, language):
            assert language == "si"
            return {key: "ආදායම වැඩි විය. " + " ".join(re.findall(r"\[\[KEEP\d{4}\]\]", value))
                    for key, value in texts.items()}

    result = translate_payload({"language": "si", "texts": ["JKH.N0000 revenue increased 24%."], "names": []}, Translator())
    assert result["failureCode"] is None
    assert "JKH.N0000" in result["translations"]["0"]
    assert "24%" in result["translations"]["0"]


def test_a_rejected_translation_does_not_erase_other_valid_entries(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "nllb")

    class Translator:
        def translate(self, texts, language):
            return {"0": "ආදායම වැඩි විය. [[KEEP0000]]", "1": "Price changed to 99%."}

    result = translate_payload({"language": "si", "texts": ["Revenue increased 24%.", "Price fell 3%."], "names": []}, Translator())
    assert result["translations"] == {"0": "ආදායම වැඩි විය. 24%"}
    assert result["failureCode"] == "TRANSLATION_VALIDATION_FAILED"
