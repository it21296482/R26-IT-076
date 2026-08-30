from src.local_report_analysis import build_local_report_insight


def test_local_report_summary_uses_verified_statement_rows():
    extracted = {
        "pdf_name": "bil-quarterly.pdf",
        "pages": [
            {
                "page_number": 1,
                "text": "Browns Investments PLC\nPeriod ended 31st March 2023",
            },
            {
                "page_number": 2,
                "text": """Revenue/ Income
9,919,660
9,758,167
2%
42,015,935
22,329,590
88%
Gross profit
82,555
2,225,549
11,438,464
5,164,673
Finance cost
(11,287,449)
(5,015,679)
(38,034,034)
(9,419,417)
Profit/(loss) for the period
(8,248,035)
33,084,669
(12,120,675)
31,598,389
Earnings/(loss) per Share - Rs.
(0.44)
2.34
(0.63)
2.19""",
            },
            {
                "page_number": 4,
                "text": """Total Assets
415,902,450
372,781,268
123,030,016
102,692,938
Total Equity
171,743,937
182,585,933
26,162,741
37,620,992""",
            },
            {
                "page_number": 5,
                "text": """Net cash generated from/(used in) operating activities
26,915,860
30,864,318
1,340,314
19,562,455""",
            },
        ],
    }

    result = build_local_report_insight(
        extracted, "Browns Investments PLC", "BIL.N0000", "prompt_08"
    )

    summary = result["investor_friendly_insight"]["summary"]
    assert "Revenue was LKR 42.02 billion" in summary
    assert "loss of LKR 12.12 billion" in summary
    assert len(result["source_evidence"]) == 8
    assert all(item["source_quote"] for item in result["source_evidence"])


def test_bil_quarterly_summary_surfaces_operating_cash_and_segment_recovery():
    extracted = {
        "pdf_name": "bil-june-2026.pdf",
        "pages": [
            {"page_number": 1, "text": "Browns Investments PLC\nThree months ended 30 June 2026"},
            {"page_number": 4, "text": """Revenue / Income
28,535,094
19,670,957
28,535,094
19,670,957
Gross profit
7,171,985
3,128,924
7,171,985
3,128,924
Results from operating activities
4,617,323
2,291,529
4,617,323
2,291,529
Finance cost
(10,390,534)
(9,713,811)
(10,390,534)
(9,713,811)
Profit / (Loss) after tax for the period
(5,872,957)
(7,051,013)
(5,872,957)
(7,051,013)
Basic / diluted earnings per share (Rs.)
(0.34)
(0.45)
(0.34)
(0.45)"""},
            {"page_number": 7, "text": """Cash generated from / (used in) operations
3,618,350
(9,749,833)
Net cash generated from / (used in) operating activities
(409,056)
(13,679,196)
Acquisition and construction of property, plant and equipment
(4,929,552)
(1,265,626)"""},
            {"page_number": 10, "text": """Segment Information - Group
Leisure
Plantation
Revenue / income
1
1
2
2
3
3
18,952,989
12,735,646
5
5
6
6
7
7
Gross profit
1
1
2
2
3
3
3,374,863
710,028
5
5
6
6
7
7
Results from Operating Activities
1
1
2,089,410
(128,796)
885,713
(435,314)
4
4
5
5
6
6
7
7
Profit after taxation from continuing operations
1
1
2
2
125,445
(970,448)
4
4
5
5
6
6
7
7"""},
        ],
    }

    result = build_local_report_insight(extracted, "Browns Investments PLC", "BIL.N0000", "prompt_08")
    strengths = " ".join(result["investor_friendly_insight"]["key_strengths"])

    assert "Gross profit increased by about 129%" in strengths
    assert "group loss after tax narrowed by about 17%" in strengths
    assert "Cash generated from operations" in strengths
    assert "Leisure and Travel moved" in strengths
    assert "Plantation revenue increased 49%" in strengths
