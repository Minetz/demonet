"""Tests for the server-side fingerprint SVG generation."""
from app.share import _generate_fingerprint_svg


class TestFingerprintSvg:
    def test_generates_valid_svg(self):
        svg = _generate_fingerprint_svg("a7f3c9d2e1b84056")
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_deterministic_output(self):
        svg1 = _generate_fingerprint_svg("a7f3c9d2e1b84056")
        svg2 = _generate_fingerprint_svg("a7f3c9d2e1b84056")
        assert svg1 == svg2

    def test_different_hashes_produce_different_svgs(self):
        svg1 = _generate_fingerprint_svg("a7f3c9d2e1b84056")
        svg2 = _generate_fingerprint_svg("ff00ff00ff00ff00")
        assert svg1 != svg2

    def test_returns_empty_for_short_hash(self):
        assert _generate_fingerprint_svg("abc") == ""
        assert _generate_fingerprint_svg("") == ""
        assert _generate_fingerprint_svg(None) == ""

    def test_contains_structural_elements(self):
        svg = _generate_fingerprint_svg("1234567890abcdef")
        assert "<circle" in svg
        assert "<line" in svg
        assert "radialGradient" in svg
