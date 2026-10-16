"""One labelled artificial CSV for the statement upload flow and its checks."""
from pathlib import Path

STATEMENT_EXAMPLE_NAME = "friday-statement-example-artificial.csv"
STATEMENT_EXAMPLE_CSV = (Path(__file__).parent / "assets" / STATEMENT_EXAMPLE_NAME).read_text(encoding="utf-8")
