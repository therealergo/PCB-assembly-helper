from dataclasses import dataclass
from pathlib import Path


@dataclass
class GerberSet:
    gtl: Path | None = None  # Top copper
    gbl: Path | None = None  # Bottom copper
    gto: Path | None = None  # Top silkscreen
    gbo: Path | None = None  # Bottom silkscreen
    gts: Path | None = None  # Top soldermask
    gbs: Path | None = None  # Bottom soldermask
    outline: Path | None = None  # Board outline (GM, GM1, GKO, etc.)


def discover_gerbers(folder: str | Path) -> GerberSet:
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Gerber folder does not exist: {folder}")

    def find_ext(ext: str) -> Path | None:
        for p in folder.iterdir():
            if p.suffix.upper() == f".{ext.upper()}":
                return p
        return None

    def find_outline() -> Path | None:
        for ext in ["GM1", "GM", "GKO", "GML"]:
            result = find_ext(ext)
            if result:
                return result
        return None

    return GerberSet(
        gtl=find_ext("GTL"),
        gbl=find_ext("GBL"),
        gto=find_ext("GTO"),
        gbo=find_ext("GBO"),
        gts=find_ext("GTS"),
        gbs=find_ext("GBS"),
        outline=find_outline(),
    )
