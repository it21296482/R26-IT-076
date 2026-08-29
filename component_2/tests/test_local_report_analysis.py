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

