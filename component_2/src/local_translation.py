"""Offline NLLB presentation translation; never generates financial analysis.

The separately downloaded NLLB weights are CC-BY-NC-4.0 (research use only).
No model download or remote request is made during an analysis request.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANGUAGES = {"si": "sin_Sinh", "ta": "tam_Taml"}


def split_sentences(text, encode, maximum=160):
    """Keep every word, splitting before the model's input limit, not truncating."""
    parts = re.split(r"(?<=[.!?;])\s+(?=[A-Z\[\d])", text)
    chunks = []
    for part in parts:
        if len(encode(part)) <= maximum:
            chunks.append(part)
            continue
        chunk = []
        for word in part.split():
            candidate = " ".join([*chunk, word])
            if chunk and len(encode(candidate)) > maximum:
                chunks.append(" ".join(chunk))
                chunk = []
            if len(encode(word)) > maximum:
                raise ValueError("A translation input token is too long")
            chunk.append(word)
        if chunk:
            chunks.append(" ".join(chunk))
    return chunks


def target_language_text(text, language):
    """Reject empty, English-only, mixed-script garbage and repeated loops."""
    if not isinstance(text, str) or not text.strip():
        return False
    remaining = re.sub(r"\[\[KEEP\d{4}\]\]", "", text)
    script = r"[\u0D80-\u0DFF]" if language == "si" else r"[\u0B80-\u0BFF]"
    target = len(re.findall(script, remaining))
    latin = len(re.findall(r"[A-Za-z]", remaining))
    if target < 2 or latin > max(20, target * 0.3):
        return False
    words = remaining.split()
    # Forecast lists legitimately repeat wording. Reject consecutive generation
    # loops, not the same phrase used in separate, meaningful sentences.
    for width in range(3, min(25, len(words) // 3) + 1):
        if any(words[start:start + width] * 3 == words[start:start + width * 3]
               for start in range(len(words) - width * 3 + 1)):
            return False
    return True


def normalize_local_output(text):
    # NLLB sometimes collapses a double bracket; never guess a changed marker ID.
    text = re.sub(r"\[{1,2}\s*KEEP\s*(\d{4})\s*\]{1,2}", r"[[KEEP\1]]", text)
    for separated, joined in {"අසාමාන් ය": "අසාමාන්‍ය", "සාමාන් ය": "සාමාන්‍ය",
                              "අවශ් ය": "අවශ්‍ය", "සත් ය": "සත්‍ය", "සංක් රාන්ති": "සංක්‍රාන්ති"}.items():
        text = text.replace(separated, joined)
    # SentencePiece may insert a space inside a Sinhala consonant conjunct.
    return re.sub("(?<![\u0d80-\u0dff])([\u0d9a-\u0dc6])\u0dca\\s+([\u0dbb\u0dba])",
                  "\\1\u0dca\u200d\\2", text)


def encode_markers(text):
    # Translation models copy numbers more reliably than instruction-style tags.
    # These are internal sentinels, never displayed as financial values.
    return re.sub(r"\[\[KEEP(\d{4})\]\]", lambda match: str(47123 + int(match[1])), text)


def decode_markers(text):
    return re.sub(r"(?<!\d)\d{5}(?!\d)",
                  lambda match: f"[[KEEP{int(match[0]) - 47123:04d}]]" if 47123 <= int(match[0]) <= 57122 else match[0], text)


def valid_piece(source, value, language):
    pattern = r"\[\[KEEP\d{4}\]\]"
    return (target_language_text(value, language)
            and Counter(re.findall(pattern, source)) == Counter(re.findall(pattern, value))
            and not re.search(r"\d", re.sub(pattern, "", value)))


def financial_phrase(text, language):
    """Fixed wording for metadata and score comparisons with no inferred claims."""
    fixed = {
        "This was not flagged as an unusual move.": (
            "මෙය අසාමාන්‍ය මිල චලනයක් ලෙස හඳුනාගෙන නැත.",
            "இது அசாதாரண விலை நகர்வாக அடையாளம் காணப்படவில்லை."),
        "No new unusual daily movement was detected.": (
            "අලුත් අසාමාන්‍ය දෛනික මිල චලනයක් හඳුනාගෙන නැත.",
            "புதிய அசாதாரண தினசரி விலை நகர்வு எதுவும் கண்டறியப்படவில்லை."),
        "The range was not calibrated to a ceasefire or recovery event and must not be read as the price effect of one.": (
            "මෙම මිල පරාසය සටන් විරාමයක් හෝ යථා තත්ත්වයට පත්වීමක් පදනම් කර ගණනය කර නැත. එබැවින් එවැනි සිදුවීමකින් මිලට ඇති වන බලපෑම ලෙස මෙය නොසලකන්න.",
            "இந்த விலை வரம்பு போர் நிறுத்தம் அல்லது மீட்பு நிகழ்வின் அடிப்படையில் கணக்கிடப்படவில்லை. அத்தகைய நிகழ்வு விலையை எவ்வளவு மாற்றும் என்பதை இது காட்டுவதாகக் கருத வேண்டாம்."),
        "This describes the available indicators now, not a prediction of loss or proof that conflict and disaster risks have ended.": (
            "මෙය දැනට ඇති දර්ශක පිළිබඳ විස්තරයකි. අනාගත අලාභයක් පිළිබඳ අනාවැකියක් හෝ ගැටුම් සහ ආපදා අවදානම් අවසන් වූ බවට සාක්ෂියක් නොවේ.",
            "இது தற்போது கிடைக்கும் குறிகாட்டிகளின் விளக்கம். எதிர்கால இழப்பின் கணிப்போ, மோதல் மற்றும் பேரிடர் அபாயங்கள் முடிந்துவிட்டன என்பதற்கான சான்றோ அல்ல."),
    }
    if text in fixed:
        return fixed[text][0 if language == "si" else 1]
    marker = r"(\[\[KEEP\d{4}\]\])"
    match = re.fullmatch(r"The latest price was " + marker + r", compared with an expected " + marker + r"\.", text)
    if match:
        actual, expected = match.groups()
        return (f"අවසන් වරට වාර්තා වූ මිල {actual} වේ. අපේක්ෂිත මිල {expected} වේ." if language == "si"
                else f"சமீபத்தில் பதிவான விலை {actual}. கணிக்கப்பட்ட விலை {expected}.")
    match = re.fullmatch(r"Gross profit increased by about " + marker + r", while gross margin moved from about " + marker + r" to " + marker + r"\.", text)
    if match:
        change, before, after = match.groups()
        return (f"දළ ලාභය ආසන්න වශයෙන් {change} කින් වැඩි විය. දළ ලාභ ආන්තිකය {before} සිට {after} දක්වා වෙනස් විය." if language == "si"
                else f"மொத்த லாபம் சுமார் {change} அதிகரித்தது. மொத்த லாப விகிதம் {before} இலிருந்து {after} ஆக மாறியது.")
    match = re.fullmatch(r"Operating profit increased by about " + marker + r" to " + marker + r" (billion|million)\.", text)
    if match:
        change, amount, unit = match.groups()
        units = {"billion": ("බිලියන", "பில்லியன்"), "million": ("මිලියන", "மில்லியன்")}
        return (f"මෙහෙයුම් ලාභය ආසන්න වශයෙන් {change} කින් වැඩි වී {amount} {units[unit][0]} දක්වා ඉහළ ගියේය." if language == "si"
                else f"செயல்பாட்டு லாபம் சுமார் {change} அதிகரித்து {amount} {units[unit][1]} ஆனது.")
    match = re.fullmatch(marker + r" for the period ended " + marker + r"\.", text)
    if match:
        company, date = match.groups()
        return (f"{company}: {date} දිනෙන් අවසන් වූ කාල සීමාව සඳහා. " if language == "si"
                else f"{company}: {date} அன்று முடிவடைந்த காலத்திற்கான அறிக்கை.")
    match = re.fullmatch(r"Its unusual-movement score was " + marker + r", against a warning level of " + marker + r"\.", text)
    if match:
        score, threshold = match.groups()
        return (f"අසාමාන්‍ය මිල චලන ලකුණ {score} වේ. අනතුරු ඇඟවීමේ සීමාව {threshold} වේ." if language == "si"
                else f"அசாதாரண விலை நகர்வு மதிப்பெண் {score}. எச்சரிக்கை வரம்பு {threshold}.")
    return None


class LocalTranslator:
    def __init__(self):
        # An optional project-local install keeps the main Python environment untouched.
        runtime = ROOT / "output/translation-runtime"
        if runtime.is_dir():
            sys.path.insert(0, str(runtime))
        import ctranslate2
        import sentencepiece

        directory = Path(os.getenv("TRANSLATION_MODEL_DIR") or ROOT / "output/local-models/nllb-600m-int8")
        if not (directory / "model.bin").is_file():
            raise ValueError("Local translation model is not installed")
        self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(directory / "sentencepiece.bpe.model"))
        self.model = ctranslate2.Translator(str(directory), device="cpu", compute_type="int8",
                                           inter_threads=1, intra_threads=4)

    def translate(self, texts, language):
        if language not in LANGUAGES:
            raise ValueError("Unsupported translation language")
        pieces = []
        indexes = []
        sources = []
        output = {}
        for key, text in texts.items():
            output[key] = []
            chunks = split_sentences(text, lambda value: self.tokenizer.encode(encode_markers(value), out_type=str))
            for chunk in chunks:
                position = len(output[key])
                preset = financial_phrase(chunk, language)
                output[key].append(preset)
                if preset is None:
                    indexes.append((key, position))
                    sources.append(chunk)
                    pieces.append(["eng_Latn", *self.tokenizer.encode(encode_markers(chunk), out_type=str), "</s>"])
        results = self.model.translate_batch(pieces, target_prefix=[[LANGUAGES[language]]] * len(pieces),
                                             beam_size=2, max_batch_size=8, max_input_length=0,
                                             max_decoding_length=400, repetition_penalty=1.05)
        for index, ((key, position), result) in enumerate(zip(indexes, results)):
            tokens = result.hypotheses[0]
            if tokens and tokens[0] == LANGUAGES[language]:
                tokens = tokens[1:]
            value = normalize_local_output(decode_markers(self.tokenizer.decode(tokens)))
            if len(tokens) >= 400 or not valid_piece(sources[index], value, language):
                value = None
                # Retry only the rejected sentence, not the entire report. Wider
                # decoding must still pass identical financial-value checks.
                for beam in (4, 6):
                    retry = self.model.translate_batch([pieces[index]], target_prefix=[[LANGUAGES[language]]],
                                                       beam_size=beam, max_input_length=0, max_decoding_length=400)[0]
                    candidate = normalize_local_output(decode_markers(self.tokenizer.decode(retry.hypotheses[0][1:])))
                    if len(retry.hypotheses[0]) < 400 and valid_piece(sources[index], candidate, language):
                        value = candidate
                        break
            output[key][position] = value
        return {key: " ".join(values) for key, values in output.items() if values and all(values)}
