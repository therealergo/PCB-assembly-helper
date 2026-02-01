import csv
from pathlib import Path

from .models import Component, Side


def parse_pickplace_csv(path: str | Path) -> list[Component]:
    components: list[Component] = []

    encodings = ["utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"]
    lines = None

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding, newline="") as f:
                lines = f.readlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if lines is None:
        raise ValueError(f"Could not decode file with any supported encoding")

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('"Designator"'):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find header row with 'Designator' column")

    csv_content = "".join(lines[header_idx:])
    reader = csv.DictReader(csv_content.splitlines())

    fieldnames = reader.fieldnames or []
    units_mm = "Center-X(mm)" in fieldnames
    x_col = "Center-X(mm)" if units_mm else "Center-X(mil)"
    y_col = "Center-Y(mm)" if units_mm else "Center-Y(mil)"

    for row in reader:
        if not row.get("Designator"):
            continue

        layer = row.get("Layer", "").strip()
        if "Top" in layer:
            side = Side.TOP
        elif "Bottom" in layer:
            side = Side.BOTTOM
        else:
            continue

        try:
            x_val = float(row.get(x_col, 0))
            y_val = float(row.get(y_col, 0))
            rotation = float(row.get("Rotation", 0) or 0)

            if units_mm:
                x_mm = x_val
                y_mm = y_val
            else:
                x_mm = x_val * 0.0254
                y_mm = y_val * 0.0254
        except ValueError:
            continue

        components.append(
            Component(
                designator=row.get("Designator", "").strip(),
                comment=row.get("Comment", "").strip(),
                side=side,
                footprint=row.get("Footprint", "").strip(),
                x_mm=x_mm,
                y_mm=y_mm,
                rotation_deg=rotation,
                description=row.get("Description", "").strip(),
            )
        )

    return components
