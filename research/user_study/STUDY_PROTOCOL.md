# User study protocol: does the system's explanation help people understand a CSE stock?

**Project:** R26-IT-076, Component 1 (market behaviour and deviation patterns)
**Status:** Draft for supervisor and ethics review. Do not recruit until approved.
**Pre-registration:** Commit this file, `study.html`, `answer_key.json` and `analyse_study.py` to the repository *before the first participant*. The commit date is the pre-registration date. Do not change the questions, answer key or analysis afterwards; if a change is unavoidable, record it under "Deviations" below with the date and reason.

## 1. Question and hypotheses

Can people who are not market experts understand a stock's recent behaviour better when the price chart is accompanied by the system's explanation (accumulated gap from expected price, unusual-movement flags, plain-language summary in English, Sinhala or Tamil) than when they see the price chart alone?

- **H1 (primary):** Comprehension score (0–5) is higher with the system explanation than with the chart only.
- **H2 (secondary):** The interpretation subscore (Q2–Q4) is higher with the system explanation.
- **H3 (secondary):** Self-rated understanding, usefulness and ease (1–7) and confidence (1–5) are higher with the system explanation.
- Exploratory: time taken, use of "Not sure", stated preference, differences by investing experience and language.

## 2. Design

Within-subjects, two conditions × two stocks, counterbalanced with a Latin square:

| Group | First | Second |
|---|---|---|
| 1 (P01, P05, …) | Company P, chart only | Company Q, system |
| 2 (P02, P06, …) | Company P, system | Company Q, chart only |
| 3 (P03, P07, …) | Company Q, chart only | Company P, system |
| 4 (P04, P08, …) | Company Q, system | Company P, chart only |

Stimuli are real data for 8 May–28 Aug 2026: Company P = John Keells Holdings (JKH.N0000), which stayed near its expected price (−3.9%); Company Q = Browns Investments (BIL.N0000), which drifted down in small steps (−21.9%). Names are hidden during the task to avoid prior-knowledge effects and revealed in the debrief.

## 3. Participants

- **Target n = 20** (minimum 16, five per group). With a within-subjects design, n = 16 gives about 80% power to detect a large effect (dz ≈ 0.75) at α = 0.05, two-sided. This study cannot detect small effects; report it as a pilot-scale evaluation.
- **Inclusion:** aged 18+, able to read English, Sinhala or Tamil, and consents.
- **Recruitment:** aim for at least half with no share-buying experience (the system's target users). Record but do not exclude finance students or professionals.
- **Not eligible:** members of the project team.

## 4. Materials

- `study.html`: offline study app (open in Chrome or Edge on the study laptop; no internet needed).
- `CONSENT_FORM.md`: printed information sheet and consent form (the app repeats the key points).
- Sinhala and Tamil text in the app are drafts. **Before recruitment, a native speaker of each language must check every string.** Ideally, replace the system-explanation paragraphs with the application's own translated output for the same stock and period, so the study tests the real system. Record who checked each language.

## 5. Procedure (researcher script)

1. Before each session, open `study.html` and confirm no other session is running.
2. Give the participant the printed information sheet. Answer questions. Obtain signed consent (keep signed forms separate from responses).
3. Type the participant ID (P01, P02, … in order of arrival) and press **Start session**. The group is assigned automatically.
4. Hand over the laptop. Say only: *"Please follow the instructions on the screen. There is no time limit. I can't help with the questions, but tell me if something on the screen doesn't work."*
5. Do not explain charts, terms or answers during the task.
6. At the end, the app shows the debrief and downloads `<ID>_<date>.json`. Move that file to `research/user_study/responses/` at the end of the day. Use **Download all** as a backup.
7. If a participant withdraws, delete their file and note the ID under "Withdrawals".

## 6. Measures

Per company: five multiple-choice comprehension questions (each includes "Not sure"); confidence (1–5); three agreement items (1–7: understood, useful, easy); time on page. At the end: preference, age band, whether they have bought shares, self-rated market knowledge (1–5) and an optional comment.

| Question | Company P answer | Company Q answer | Answerable from chart alone? |
|---|---|---|---|
| Q1 Price change | Changed by less than 5% | Fell about 20% | Yes |
| Q2 Behaviour vs. usual pattern | Stayed close | Drifted steadily below | Partly |
| Q3 Calm day means no problem? | No | No | No (concept) |
| Q4 Future prices | Uncertain; persistence beat model | Same | No |
| Q5 Buy/sell advice? | No | No | Yes (by reasoning) |

Answer keys are generated from the data by `build_study.py` (`answer_key.json`).

## 7. Analysis plan (fixed before data collection)

Run `python research/user_study/analyse_study.py`.

- **Primary:** comprehension score, system vs. chart only, Wilcoxon signed-rank (two-sided, α = 0.05); report the mean difference with participant-bootstrap 95% CI and matched-pairs rank-biserial r.
- **Secondary:** interpretation subscore and subjective ratings, same test; Holm correction across the secondary outcomes.
- **Carry-over check:** compare chart-only scores of participants who saw the system first with those who saw the chart first (Mann–Whitney). Seeing the explanation first may teach concepts (Q3–Q5) that raise later chart-only scores; this would shrink, not inflate, the measured difference.
- **Pre-specified exclusions:** a part completed in under 20 seconds is flagged and reported; the primary analysis includes all complete sessions, with a sensitivity analysis excluding flagged parts.
- Report every participant, group sizes, language split and the number without share-buying experience.

## 8. Ethics and data handling

- Obtain approval from the SLIIT ethics review process (or as your supervisors direct) before recruitment; quote the approval reference in the paper.
- No names are stored with responses. Signed consent forms are stored separately and securely.
- Response files contain only the participant ID, answers, timings and the demographic bands above.
- Participants may stop at any time; their data are deleted on request (by participant ID).
- The study gives no investment advice; the debrief repeats this.
- Keep files on an access-controlled drive; delete raw files when the research project ends unless the ethics approval states otherwise.

## 9. Known limitations to report

- The system condition presents information the chart lacks, so the study measures the value of that information as presented, not the reading skill of participants.
- Two stocks and one period; small sample; mostly convenience recruitment.
- Comprehension is measured immediately after viewing, not in real investment decisions.

## Deviations

| Date | Change | Reason |
|---|---|---|
| | | |

## Withdrawals

| ID | Date |
|---|---|
| | |

## Translation checks

| Language | Checked by | Date |
|---|---|---|
| Sinhala | | |
| Tamil | | |
