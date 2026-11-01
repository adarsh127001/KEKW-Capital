import re
ORDER=re.compile(r"^!(buy|sell)\s+\$?([A-Za-z0-9_]+)\s+(\d+|all)\s*$",re.I)
def parse_order(text):
    m=ORDER.match(text.strip())
    if not m:return None
    side,ticker,qty=m.groups(); return side.lower(),ticker.upper(),None if qty.lower()=="all" else int(qty)
