"""Build the offline user-study app (study.html) from the Component 1 walk-forward results.

    python research/user_study/build_study.py

Stimuli are real JKH (shown as "Company P") and BIL ("Company Q") data for
8 May - 28 Aug 2026. Answer keys are derived from the same data and written to
answer_key.json so that scoring never depends on hand-entered values.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "component1" / "artifacts" / "paper_v2" / "per_stock"
WINDOW = ("2026-05-08", "2026-08-28")
STOCKS = {"P": "JKH", "Q": "BIL"}


def stimulus(code: str) -> dict:
    wf = pd.read_csv(RUNS / code / "walk_forward_residuals.csv", parse_dates=["date"])
    w = wf[(wf["date"] >= WINDOW[0]) & (wf["date"] <= WINDOW[1])].reset_index(drop=True)
    cum = (np.exp(np.log1p(w["rel_resid"]).cumsum()) - 1) * 100
    start, end = float(w["prev_close"].iloc[0]), float(w["actual_price"].iloc[-1])
    chg = (end / start - 1) * 100
    alarms = w["daily_alarm"].astype(bool)
    open_share = float(((w["cusum_plus"] > 0) | (w["cusum_minus"] > 0)).mean() * 100)
    drift = cum.iloc[-1] <= -10
    # Answer key from data (option indices match the question order in TEXT).
    q1 = 0 if chg >= 10 else 1 if abs(chg) < 5 else 2 if chg > -30 else 3
    q2 = 1 if drift else (3 if cum.iloc[-1] >= 10 else 0)
    return {
        "days": int(len(w)), "dates": w["date"].dt.strftime("%Y-%m-%d").tolist(),
        "close": [round(float(x), 2) for x in w["actual_price"]],
        "cum": [round(float(x), 2) for x in cum],
        "alarm": [int(x) for x in alarms],
        "start": round(start, 2), "end": round(end, 2), "chg": round(chg, 1), "cum_end": round(float(cum.iloc[-1]), 1),
        "alarms": int(alarms.sum()), "last": w["date"].iloc[-1].strftime("%d %b %Y"),
        "last_alarm": bool(alarms.iloc[-1]), "open_share": round(open_share), "kind": "drift" if drift else "close",
        "key": {"q1": q1, "q2": q2, "q3": 1, "q4": 1, "q5": 2},
    }


# ---------------------------------------------------------------- text (EN / SI / TA)
# Sinhala and Tamil are DRAFTS: a native speaker must check them before the study,
# and the system-explanation paragraphs should be replaced with the app's own
# translated output for the same stock and period where possible.
TEXT = {
 "en": {
  "lang_name": "English", "title": "Understanding a stock: a short study",
  "choose_lang": "Choose your language",
  "consent_title": "Before you start",
  "consent": "This study takes about 15 minutes. You will look at information about two companies listed on the Colombo Stock Exchange and answer short questions. This is not a test of you. We record your answers and how long you take, but not your name. You can stop at any time without giving a reason. Nothing here is investment advice.",
  "consent_check": "I am 18 or older, I have read the above, and I agree to take part.",
  "start": "Start", "next": "Next", "finish": "Finish", "company": "Company", "part": "Part {i} of 2",
  "view_chart": "Price chart", "view_system": "Price chart with the system's explanation",
  "instr": "Look at the information for as long as you like, then answer the questions below it. You can scroll back up while answering.",
  "period": "8 May – 28 Aug 2026 (76 trading days). Prices in LKR.",
  "legend_price": "Closing price (LKR)", "legend_gap": "Accumulated gap from expected price (%)", "legend_alarm": "Unusual-movement flag",
  "latest": "Latest price", "change": "Change over the period",
  "explain_title": "What the system says",
  "questions": "Questions", "answer_all": "Please answer every question to continue.",
  "q": [
   ["About how much did the price change over the period?", ["Rose about 20%", "Changed by less than 5%", "Fell about 20%", "Fell about 40%", "Not sure"]],
   ["Compared with its own usual pattern, how did the stock behave?", ["Stayed close to its usual pattern", "Drifted steadily below its usual pattern", "One sudden crash, then recovered", "Moved above its usual pattern", "Not sure"]],
   ["If the latest day shows no unusual movement, does that mean the stock has no ongoing problem?", ["Yes", "No – a slow decline can continue without any single unusual day", "Not sure"]],
   ["Which statement about future prices is correct?", ["A forecast line shows where the price will be", "Future prices are uncertain; in testing, assuming the price stays the same was more accurate than the model's forecast", "The price cannot fall below the lower range", "Not sure"]],
   ["Does this information tell you to buy or sell the stock?", ["Yes, buy", "Yes, sell", "No – it gives evidence, not buy or sell advice", "Not sure"]],
  ],
  "confidence": "How confident are you in your answers for this company?", "conf": ["1 Not at all", "2", "3", "4", "5 Very"],
  "agree": "How much do you agree?", "likert": ["1 Strongly disagree", "2", "3", "4", "5", "6", "7 Strongly agree"],
  "lik": ["I understood what happened to this stock during the period.", "This information would help me decide whether to look into this stock further.", "The information was easy to understand."],
  "final_title": "Last few questions",
  "pref": "Which presentation helped you understand a stock better?", "pref_opts": ["Chart only", "Chart with the system's explanation", "No difference"],
  "age": "Your age group", "age_opts": ["18–24", "25–34", "35–44", "45–54", "55+"],
  "bought": "Have you ever bought shares?", "yesno": ["Yes", "No"],
  "knowledge": "How would you rate your knowledge of the stock market?", "know_opts": ["1 None", "2", "3", "4", "5 Expert"],
  "comment": "Any comments? (optional)",
  "done": "Thank you! Please hand the laptop back to the researcher.",
  "debrief": "Company P was John Keells Holdings PLC (JKH) and Company Q was Browns Investments PLC (BIL).",
  "sys": {
   "what_close": "What happened: The price moved from LKR {start} to LKR {end} ({chg}%) over 76 trading days. It stayed close to its expected price: the accumulated gap was {cum_end}%.",
   "what_drift": "What happened: The price fell from LKR {start} to LKR {end} ({chg}%) over 76 trading days. It drifted below its expected price in small steps: the accumulated gap reached {cum_end}%.",
   "unusual": "Unusual movement: {alarms} of 76 days were flagged as unusual. The latest day ({last}) was {laststatus}.",
   "last_no": "not unusual", "last_yes": "unusual",
   "pattern_close": "Pattern: No persistent drift, sudden shock or burst of volatility stood out.",
   "pattern_drift": "Pattern: A slow, continuing decline. No single sharp day explains the fall, so daily flags alone would understate it.",
   "future": "Future prices: Treat any forecast as an uncertain range, not a target. In testing on this market, assuming the price stays the same was more accurate than the model's forecast.",
   "note": "Please note: This is evidence to help you understand the stock, not advice to buy or sell. A calm day does not mean there is no ongoing problem."},
 },
 "si": {
  "lang_name": "සිංහල", "title": "කොටසක් තේරුම් ගැනීම: කෙටි අධ්‍යයනයක්",
  "choose_lang": "ඔබේ භාෂාව තෝරන්න",
  "consent_title": "ආරම්භ කිරීමට පෙර",
  "consent": "මෙම අධ්‍යයනයට විනාඩි 15ක් පමණ ගත වේ. කොළඹ කොටස් හුවමාරුවේ ලැයිස්තුගත සමාගම් දෙකක් පිළිබඳ තොරතුරු බලා කෙටි ප්‍රශ්නවලට පිළිතුරු දීමට ඔබට සිදු වේ. මෙය ඔබව පරීක්ෂා කිරීමක් නොවේ. අපි ඔබේ පිළිතුරු සහ ගත වන කාලය සටහන් කරන නමුත් ඔබේ නම සටහන් නොකරමු. කිසිදු හේතුවක් නොදක්වා ඕනෑම වේලාවක නතර කිරීමට ඔබට හැකිය. මෙහි ඇති කිසිවක් ආයෝජන උපදෙස් නොවේ.",
  "consent_check": "මගේ වයස අවුරුදු 18 හෝ ඊට වැඩි ය; මම ඉහත කරුණු කියවා ඇති අතර සහභාගී වීමට එකඟ වෙමි.",
  "start": "ආරම්භ කරන්න", "next": "ඊළඟ", "finish": "අවසන් කරන්න", "company": "සමාගම", "part": "කොටස {i} / 2",
  "view_chart": "මිල ප්‍රස්තාරය", "view_system": "පද්ධතියේ පැහැදිලි කිරීම සමඟ මිල ප්‍රස්තාරය",
  "instr": "තොරතුරු ඔබට අවශ්‍ය තරම් වේලාවක් බලා, ඊට පහළින් ඇති ප්‍රශ්නවලට පිළිතුරු දෙන්න. පිළිතුරු දෙන අතරතුර ඔබට නැවත ඉහළට යා හැකිය.",
  "period": "2026 මැයි 8 – අගෝස්තු 28 (වෙළඳ දින 76). මිල ගණන් රුපියල්වලින්.",
  "legend_price": "වසා දැමීමේ මිල (රු.)", "legend_gap": "අපේක්ෂිත මිලෙන් එකතු වූ පරතරය (%)", "legend_alarm": "අසාමාන්‍ය චලන සලකුණ",
  "latest": "නවතම මිල", "change": "කාල සීමාව තුළ වෙනස",
  "explain_title": "පද්ධතිය පවසන දේ",
  "questions": "ප්‍රශ්න", "answer_all": "ඉදිරියට යාමට කරුණාකර සියලු ප්‍රශ්නවලට පිළිතුරු දෙන්න.",
  "q": [
   ["කාල සීමාව තුළ මිල ආසන්න වශයෙන් කොපමණ වෙනස් වූයේද?", ["20% පමණ ඉහළ ගියේය", "5% ට වඩා අඩුවෙන් වෙනස් විය", "20% පමණ පහළ ගියේය", "40% පමණ පහළ ගියේය", "විශ්වාස නැත"]],
   ["එහි සාමාන්‍ය රටාවට සාපේක්ෂව කොටස හැසිරුණේ කෙසේද?", ["එහි සාමාන්‍ය රටාවට ආසන්නව පැවතුණි", "එහි සාමාන්‍ය රටාවට වඩා ක්‍රමයෙන් පහළට ගියේය", "එක්වරම තියුණු ලෙස පහත වැටී, පසුව යථා තත්ත්වයට පත් විය", "එහි සාමාන්‍ය රටාවට වඩා ඉහළ ගියේය", "විශ්වාස නැත"]],
   ["නවතම දිනයේ අසාමාන්‍ය චලනයක් නොපෙන්වයි නම්, එයින් අදහස් වන්නේ කොටසට කිසිදු දිගුකාලීන ගැටලුවක් නොමැති බවද?", ["ඔව්", "නැත – කිසිදු අසාමාන්‍ය දිනයක් නොමැතිව වුවද සෙමින් පහත වැටීමක් දිගටම සිදු විය හැකිය", "විශ්වාස නැත"]],
   ["අනාගත මිල ගණන් පිළිබඳ නිවැරදි ප්‍රකාශය කුමක්ද?", ["පුරෝකථන රේඛාව මිල කොතැනට යයිදැයි පෙන්වයි", "අනාගත මිල අවිනිශ්චිතයි; පරීක්ෂණවලදී, මිල නොවෙනස්ව පවතී යැයි උපකල්පනය කිරීම ආකෘතියේ පුරෝකථනයට වඩා නිවැරදි විය", "මිල පහළ පරාසයට වඩා අඩු විය නොහැක", "විශ්වාස නැත"]],
   ["මෙම තොරතුරු ඔබට කොටස මිලදී ගැනීමට හෝ විකිණීමට කියනවාද?", ["ඔව්, මිලදී ගන්න", "ඔව්, විකුණන්න", "නැත – එය සාක්ෂි ලබා දෙයි, මිලදී ගැනීමේ හෝ විකිණීමේ උපදෙස් නොවේ", "විශ්වාස නැත"]],
  ],
  "confidence": "මෙම සමාගම සඳහා ඔබේ පිළිතුරු ගැන ඔබට කොතරම් විශ්වාසද?", "conf": ["1 කිසිසේත් නැත", "2", "3", "4", "5 ඉතා විශ්වාසයි"],
  "agree": "ඔබ කොතරම් එකඟද?", "likert": ["1 දැඩි ලෙස එකඟ නොවේ", "2", "3", "4", "5", "6", "7 දැඩි ලෙස එකඟ වේ"],
  "lik": ["මෙම කාලය තුළ මෙම කොටසට සිදු වූ දේ මට තේරුණා.", "මෙම කොටස ගැන තවදුරටත් සොයා බැලිය යුතුද යන්න තීරණය කිරීමට මෙම තොරතුරු මට උපකාරී වේ.", "තොරතුරු තේරුම් ගැනීමට පහසු විය."],
  "final_title": "අවසාන ප්‍රශ්න කිහිපය",
  "pref": "කොටසක් වඩා හොඳින් තේරුම් ගැනීමට ඔබට උපකාරී වූයේ කුමන ඉදිරිපත් කිරීමද?", "pref_opts": ["ප්‍රස්තාරය පමණක්", "පද්ධතියේ පැහැදිලි කිරීම සමඟ ප්‍රස්තාරය", "වෙනසක් නැත"],
  "age": "ඔබේ වයස් කාණ්ඩය", "age_opts": ["18–24", "25–34", "35–44", "45–54", "55+"],
  "bought": "ඔබ කවදා හෝ කොටස් මිලදී ගෙන තිබේද?", "yesno": ["ඔව්", "නැත"],
  "knowledge": "කොටස් වෙළඳපොළ පිළිබඳ ඔබේ දැනුම ඔබ ඇගයීමට ලක් කරන්නේ කෙසේද?", "know_opts": ["1 කිසිවක් නැත", "2", "3", "4", "5 විශේෂඥ"],
  "comment": "අදහස් තිබේද? (අත්‍යවශ්‍ය නොවේ)",
  "done": "ස්තූතියි! කරුණාකර ලැප්ටොප් පරිගණකය පර්යේෂකයාට නැවත ලබා දෙන්න.",
  "debrief": "සමාගම P යනු John Keells Holdings PLC (JKH) වන අතර සමාගම Q යනු Browns Investments PLC (BIL) වේ.",
  "sys": {
   "what_close": "සිදු වූ දේ: වෙළඳ දින 76ක් තුළ මිල රු. {start} සිට රු. {end} දක්වා ({chg}%) වෙනස් විය. එය අපේක්ෂිත මිලට ආසන්නව පැවතුණි: එකතු වූ පරතරය {cum_end}% විය.",
   "what_drift": "සිදු වූ දේ: වෙළඳ දින 76ක් තුළ මිල රු. {start} සිට රු. {end} දක්වා ({chg}%) පහත වැටුණි. එය කුඩා පියවරෙන් අපේක්ෂිත මිලට වඩා පහළට ගියේය: එකතු වූ පරතරය {cum_end}% දක්වා ළඟා විය.",
   "unusual": "අසාමාන්‍ය චලනය: දින 76න් දින {alarms}ක් අසාමාන්‍ය ලෙස සලකුණු කෙරිණි. නවතම දිනය ({last}) {laststatus}.",
   "last_no": "අසාමාන්‍ය නොවීය", "last_yes": "අසාමාන්‍ය විය",
   "pattern_close": "රටාව: දිගටම පවතින පහත වැටීමක්, හදිසි කම්පනයක් හෝ අස්ථාවරත්වයේ ඉහළ යාමක් කැපී පෙනුණේ නැත.",
   "pattern_drift": "රටාව: සෙමින්, දිගටම සිදු වන පහත වැටීමකි. කිසිදු තනි තියුණු දිනයක් මෙම වැටීම පැහැදිලි නොකරයි, එබැවින් දෛනික සලකුණු පමණක් එය අඩුවෙන් පෙන්වයි.",
   "future": "අනාගත මිල: ඕනෑම පුරෝකථනයක් ඉලක්කයක් ලෙස නොව අවිනිශ්චිත පරාසයක් ලෙස සලකන්න. මෙම වෙළඳපොළේ පරීක්ෂණවලදී, මිල නොවෙනස්ව පවතී යැයි උපකල්පනය කිරීම ආකෘතියේ පුරෝකථනයට වඩා නිවැරදි විය.",
   "note": "සැලකිය යුතුයි: මෙය කොටස තේරුම් ගැනීමට උපකාරී වන සාක්ෂියකි, මිලදී ගැනීමට හෝ විකිණීමට උපදෙස් නොවේ. සන්සුන් දිනයක් යනු දිගටම පවතින ගැටලුවක් නොමැති බව නොවේ."},
 },
 "ta": {
  "lang_name": "தமிழ்", "title": "ஒரு பங்கைப் புரிந்துகொள்ளுதல்: சிறு ஆய்வு",
  "choose_lang": "உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்",
  "consent_title": "தொடங்குவதற்கு முன்",
  "consent": "இந்த ஆய்வுக்கு சுமார் 15 நிமிடங்கள் ஆகும். கொழும்பு பங்குச் சந்தையில் பட்டியலிடப்பட்ட இரண்டு நிறுவனங்கள் பற்றிய தகவல்களைப் பார்த்து சிறு கேள்விகளுக்குப் பதிலளிப்பீர்கள். இது உங்களைச் சோதிப்பதற்கானது அல்ல. உங்கள் பதில்களையும் எடுத்துக்கொள்ளும் நேரத்தையும் பதிவு செய்கிறோம், ஆனால் உங்கள் பெயரைப் பதிவு செய்வதில்லை. எந்தக் காரணமும் கூறாமல் எந்த நேரத்திலும் நிறுத்தலாம். இங்குள்ள எதுவும் முதலீட்டு ஆலோசனை அல்ல.",
  "consent_check": "எனக்கு 18 வயது அல்லது அதற்கு மேல்; மேலே உள்ளதைப் படித்தேன்; பங்கேற்க ஒப்புக்கொள்கிறேன்.",
  "start": "தொடங்கு", "next": "அடுத்து", "finish": "முடி", "company": "நிறுவனம்", "part": "பகுதி {i} / 2",
  "view_chart": "விலை வரைபடம்", "view_system": "அமைப்பின் விளக்கத்துடன் விலை வரைபடம்",
  "instr": "தகவல்களை நீங்கள் விரும்பும் வரை பாருங்கள், பின்னர் அதன் கீழே உள்ள கேள்விகளுக்குப் பதிலளியுங்கள். பதிலளிக்கும்போது மீண்டும் மேலே செல்லலாம்.",
  "period": "8 மே – 28 ஆகஸ்ட் 2026 (76 வர்த்தக நாட்கள்). விலைகள் இலங்கை ரூபாயில்.",
  "legend_price": "இறுதி விலை (ரூ.)", "legend_gap": "எதிர்பார்க்கப்பட்ட விலையிலிருந்து திரண்ட இடைவெளி (%)", "legend_alarm": "அசாதாரண நகர்வுக் குறி",
  "latest": "சமீபத்திய விலை", "change": "காலப்பகுதியில் மாற்றம்",
  "explain_title": "அமைப்பு கூறுவது",
  "questions": "கேள்விகள்", "answer_all": "தொடர, தயவுசெய்து எல்லாக் கேள்விகளுக்கும் பதிலளிக்கவும்.",
  "q": [
   ["காலப்பகுதியில் விலை ஏறத்தாழ எவ்வளவு மாறியது?", ["சுமார் 20% உயர்ந்தது", "5% க்கும் குறைவாக மாறியது", "சுமார் 20% குறைந்தது", "சுமார் 40% குறைந்தது", "உறுதியாகத் தெரியவில்லை"]],
   ["அதன் வழக்கமான போக்குடன் ஒப்பிடுகையில் பங்கு எவ்வாறு நடந்துகொண்டது?", ["அதன் வழக்கமான போக்குக்கு அருகிலேயே இருந்தது", "அதன் வழக்கமான போக்கை விட படிப்படியாகக் கீழே சென்றது", "திடீரென்று கடுமையாக வீழ்ந்து, பின்னர் மீண்டது", "அதன் வழக்கமான போக்கை விட மேலே சென்றது", "உறுதியாகத் தெரியவில்லை"]],
   ["சமீபத்திய நாளில் அசாதாரண நகர்வு எதுவும் இல்லையென்றால், பங்குக்குத் தொடர்ந்து வரும் பிரச்சினை எதுவும் இல்லை என்று அர்த்தமா?", ["ஆம்", "இல்லை – எந்த ஒரு நாளும் அசாதாரணமாக இல்லாமலேயே மெதுவான வீழ்ச்சி தொடரலாம்", "உறுதியாகத் தெரியவில்லை"]],
   ["எதிர்கால விலைகள் பற்றிய சரியான கூற்று எது?", ["முன்னறிவிப்புக் கோடு விலை எங்கே செல்லும் என்பதைக் காட்டுகிறது", "எதிர்கால விலைகள் நிச்சயமற்றவை; சோதனைகளில், விலை மாறாமல் இருக்கும் என்று கருதுவது மாதிரியின் முன்னறிவிப்பை விடத் துல்லியமாக இருந்தது", "விலை குறைந்த வரம்புக்குக் கீழே செல்ல முடியாது", "உறுதியாகத் தெரியவில்லை"]],
   ["இந்தத் தகவல் பங்கை வாங்கவோ விற்கவோ சொல்கிறதா?", ["ஆம், வாங்கவும்", "ஆம், விற்கவும்", "இல்லை – இது சான்றுகளைத் தருகிறது, வாங்க அல்லது விற்க ஆலோசனை அல்ல", "உறுதியாகத் தெரியவில்லை"]],
  ],
  "confidence": "இந்த நிறுவனம் தொடர்பான உங்கள் பதில்களில் எவ்வளவு நம்பிக்கை உள்ளது?", "conf": ["1 சிறிதும் இல்லை", "2", "3", "4", "5 மிக அதிகம்"],
  "agree": "நீங்கள் எவ்வளவு உடன்படுகிறீர்கள்?", "likert": ["1 முற்றிலும் உடன்படவில்லை", "2", "3", "4", "5", "6", "7 முற்றிலும் உடன்படுகிறேன்"],
  "lik": ["இந்தக் காலப்பகுதியில் இந்தப் பங்குக்கு என்ன நடந்தது என்பதைப் புரிந்துகொண்டேன்.", "இந்தப் பங்கை மேலும் ஆராய வேண்டுமா என்பதைத் தீர்மானிக்க இந்தத் தகவல் உதவும்.", "தகவல் புரிந்துகொள்ள எளிதாக இருந்தது."],
  "final_title": "இறுதிக் கேள்விகள் சில",
  "pref": "ஒரு பங்கை நன்றாகப் புரிந்துகொள்ள எந்த முறை உங்களுக்கு உதவியது?", "pref_opts": ["வரைபடம் மட்டும்", "அமைப்பின் விளக்கத்துடன் வரைபடம்", "வேறுபாடு இல்லை"],
  "age": "உங்கள் வயதுப் பிரிவு", "age_opts": ["18–24", "25–34", "35–44", "45–54", "55+"],
  "bought": "நீங்கள் எப்போதாவது பங்குகளை வாங்கியுள்ளீர்களா?", "yesno": ["ஆம்", "இல்லை"],
  "knowledge": "பங்குச் சந்தை பற்றிய உங்கள் அறிவை எவ்வாறு மதிப்பிடுவீர்கள்?", "know_opts": ["1 எதுவும் இல்லை", "2", "3", "4", "5 நிபுணர்"],
  "comment": "ஏதேனும் கருத்துகள்? (விருப்பத்தேர்வு)",
  "done": "நன்றி! தயவுசெய்து மடிக்கணினியை ஆய்வாளரிடம் திருப்பிக் கொடுக்கவும்.",
  "debrief": "நிறுவனம் P என்பது John Keells Holdings PLC (JKH), நிறுவனம் Q என்பது Browns Investments PLC (BIL).",
  "sys": {
   "what_close": "என்ன நடந்தது: 76 வர்த்தக நாட்களில் விலை ரூ. {start} இலிருந்து ரூ. {end} ஆக ({chg}%) மாறியது. அது எதிர்பார்க்கப்பட்ட விலைக்கு அருகிலேயே இருந்தது: திரண்ட இடைவெளி {cum_end}%.",
   "what_drift": "என்ன நடந்தது: 76 வர்த்தக நாட்களில் விலை ரூ. {start} இலிருந்து ரூ. {end} ஆக ({chg}%) வீழ்ந்தது. அது சிறு படிகளாக எதிர்பார்க்கப்பட்ட விலைக்குக் கீழே சென்றது: திரண்ட இடைவெளி {cum_end}% ஐ எட்டியது.",
   "unusual": "அசாதாரண நகர்வு: 76 நாட்களில் {alarms} நாட்கள் அசாதாரணமானவை எனக் குறிக்கப்பட்டன. சமீபத்திய நாள் ({last}) {laststatus}.",
   "last_no": "அசாதாரணமானது அல்ல", "last_yes": "அசாதாரணமானது",
   "pattern_close": "போக்கு: தொடர்ச்சியான சரிவு, திடீர் அதிர்ச்சி அல்லது ஏற்ற இறக்க அதிகரிப்பு எதுவும் தனித்துத் தெரியவில்லை.",
   "pattern_drift": "போக்கு: மெதுவான, தொடர்ந்து நிகழும் வீழ்ச்சி. எந்த ஒரு கடுமையான நாளும் இந்த வீழ்ச்சியை விளக்கவில்லை; எனவே தினசரிக் குறிகள் மட்டும் அதைக் குறைத்துக் காட்டும்.",
   "future": "எதிர்கால விலைகள்: எந்த முன்னறிவிப்பையும் இலக்காக அல்ல, நிச்சயமற்ற வரம்பாகக் கருதுங்கள். இந்தச் சந்தையில் நடத்திய சோதனைகளில், விலை மாறாமல் இருக்கும் என்று கருதுவது மாதிரியின் முன்னறிவிப்பை விடத் துல்லியமாக இருந்தது.",
   "note": "கவனிக்கவும்: இது பங்கைப் புரிந்துகொள்ள உதவும் சான்று, வாங்க அல்லது விற்க ஆலோசனை அல்ல. அமைதியான ஒரு நாள் தொடர்ந்து வரும் பிரச்சினை இல்லை என்று அர்த்தமல்ல."},
 },
}


def main() -> None:
    stim = {label: stimulus(code) for label, code in STOCKS.items()}
    key = {label: s.pop("key") for label, s in stim.items()}
    (HERE / "answer_key.json").write_text(json.dumps({"stocks": STOCKS, "window": WINDOW, "key": key,
                                                      "note": "Option indices are 0-based in the order shown."}, indent=2))
    template = (HERE / "study_template.html").read_text(encoding="utf-8")
    html = (template.replace("/*__STIMULI__*/null", json.dumps(stim))
                    .replace("/*__TEXT__*/null", json.dumps(TEXT, ensure_ascii=False))
                    .replace("/*__KEY__*/null", json.dumps(key)))
    (HERE / "study.html").write_text(html, encoding="utf-8")
    for label, s in stim.items():
        print(f"Company {label} ({STOCKS[label]}): {s['start']} -> {s['end']} ({s['chg']}%), gap {s['cum_end']}%, "
              f"{s['alarms']} flags, last day flagged={s['last_alarm']}, kind={s['kind']}, key={key[label]}")
    print("wrote", HERE / "study.html")


if __name__ == "__main__":
    main()
