"""Fetch actual CSELK daily candles for historical opening-price corroboration.

CSE's public chart omits openings. The server uses only the opening field from
this secondary feed, and only when its date and high/low agree with CSE. Closing
prices and total share volume always come from CSE, not this feed.
"""

import argparse
import json
import re
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from websocket import create_connection


def decode_frames(frame):
    for text in re.split(r"~m~\d+~m~", frame):
        if text:
            yield text


def fetch_candles(symbol, bars=260):
    if not re.fullmatch(r"[A-Z0-9]+\.[NX][0-9]{4}", symbol):
        raise ValueError("A CSE security symbol is required.")
    session = "cs_" + uuid.uuid4().hex[:12]
    ws = create_connection(
        "wss://data.tradingview.com/socket.io/websocket",
        origin="https://www.tradingview.com", timeout=15,
    )

    def send(method, arguments):
        body = json.dumps({"m": method, "p": arguments}, separators=(",", ":"))
        ws.send(f"~m~{len(body)}~m~{body}")

    rows = {}
    deadline = time.monotonic() + 40
    try:
        send("set_auth_token", ["unauthorized_user_token"])
        send("chart_create_session", [session, ""])
        send("resolve_symbol", [session, "symbol_1", "=" + json.dumps({
            "symbol": "CSELK:" + symbol, "adjustment": "splits", "session": "regular",
        })])
        send("create_series", [session, "s1", "s1", "symbol_1", "1D", bars])
        while time.monotonic() < deadline:
            for text in decode_frames(ws.recv()):
                if text.startswith("~h~"):
                    ws.send(f"~m~{len(text)}~m~{text}")
                    continue
                message = json.loads(text)
                method = message.get("m")
                if method in ("critical_error", "series_error", "symbol_error", "protocol_error"):
                    raise RuntimeError("The public opening-price source could not supply this security.")
                if method == "timescale_update":
                    for candle in message["p"][1].get("s1", {}).get("s", []):
                        values = candle["v"]
                        day = datetime.fromtimestamp(values[0], ZoneInfo("Asia/Colombo")).date().isoformat()
                        rows[day] = {"date": day, "open": values[1], "high": values[2],
                                     "low": values[3], "close": values[4], "volume": values[5]}
                if method == "series_completed":
                    if not rows:
                        raise ValueError("The public opening-price source returned no daily candles.")
                    return {"symbol": symbol, "provider": "TradingView CSELK daily candles",
                            "rows": sorted(rows.values(), key=lambda row: row["date"])}
        raise TimeoutError("The public opening-price history did not complete in time.")
    finally:
        ws.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--bars", type=int, default=260, choices=range(1, 5001), metavar="1..5000")
    args = parser.parse_args()
    print(json.dumps(fetch_candles(args.symbol, args.bars)))
