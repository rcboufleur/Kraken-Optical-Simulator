from pathlib import Path


REPORT = Path(__file__).with_name("test_report.txt")


def write_report(lines):
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    lines = []

    try:
        import KrakenOS as Kos

        lines.append("PASS import KrakenOS")
        lines.append(f"INFO KrakenOS file: {Kos.__file__}")

        surface = Kos.surf()
        surface.Glass = "BK7"
        surface.Rc = 100
        surface.Diameter = 30

        assert surface.Glass == "BK7"
        assert surface.Rc == 100
        assert surface.Diameter == 30
        lines.append("PASS create and edit Kos.surf")

        config = Kos.Setup()
        first_catalog = Path(config.GlassCat[0]).name
        lines.append(f"INFO first catalog: {first_catalog}")
        assert first_catalog == "SCHOTT.AGF"
        lines.append("PASS default catalog priority uses SCHOTT.AGF first")

        package_root = Path(Kos.__file__).resolve().parent
        required_files = [
            package_root / "Cat" / "SCHOTT.AGF",
            package_root / "Cat" / "Gold.csv",
            package_root / "Examples" / "R1064_F1800.txt",
            package_root / "LensCat" / "THORLABS.ZMF",
            package_root / "AstroAtmosphere" / "__init__.py",
        ]

        for required_file in required_files:
            assert required_file.exists(), f"Missing required file: {required_file}"
            lines.append(f"PASS found data file: {required_file.relative_to(package_root)}")

        lines.append("RESULT PASS")
        write_report(lines)
        return 0

    except Exception as exc:
        lines.append(f"RESULT FAIL: {type(exc).__name__}: {exc}")
        write_report(lines)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
