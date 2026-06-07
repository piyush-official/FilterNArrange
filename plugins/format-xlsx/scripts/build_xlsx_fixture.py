"""One-shot helper that produces `tests/fixtures/two_sheets.xlsx`.

Run from the plugin directory:

    cd plugins/format-xlsx
    uv run python scripts/build_xlsx_fixture.py

NOT executed in CI — the produced xlsx is committed alongside the test files.
"""
import pathlib
from openpyxl import Workbook


def main() -> None:
    wb = Workbook()
    s1 = wb.active
    s1.title = "people"
    s1.append(["id", "name", "age"])
    s1.append([1, "Ada", 37])
    s1.append([2, "Grace", 85])

    s2 = wb.create_sheet("orders")
    s2.append(["order_id", "total"])
    s2.append([1001, 25.5])

    here = pathlib.Path(__file__).resolve().parents[1]
    out = here / "tests" / "fixtures" / "two_sheets.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
