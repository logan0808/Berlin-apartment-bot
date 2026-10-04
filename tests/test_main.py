import unicodedata
import unittest

from src.parser import (
    extract_price,
    extract_rooms,
    extract_size,
    extract_district,
    detect_wbs,
)

from src.filters import matches_requirements
from src.scoring import calculate_score


class TestApartmentParser(unittest.TestCase):

    def test_price_german_decimal(self):
        self.assertAlmostEqual(
            extract_price("855,20 € warm"),
            855.20
        )

    def test_price_german_thousands(self):
        self.assertAlmostEqual(
            extract_price("1.200 EUR warm"),
            1200.0
        )

    def test_price_large_amount(self):
        self.assertAlmostEqual(
            extract_price("2.500 EUR warm"),
            2500.0
        )

    def test_price_normal_euro(self):
        self.assertAlmostEqual(
            extract_price("1500 € warm"),
            1500.0
        )

    def test_price_missing_returns_none(self):
        self.assertIsNone(extract_price(""))
        self.assertIsNone(
            extract_price("Schöne Wohnung ohne Preisangabe")
        )

    def test_rooms(self):
        self.assertEqual(
            extract_rooms("3 Zimmer Wohnung"),
            3.0
        )

    def test_rooms_english(self):
        self.assertEqual(
            extract_rooms("2 rooms apartment"),
            2.0
        )

    def test_rooms_missing_returns_none(self):
        self.assertIsNone(
            extract_rooms("Schöne Wohnung")
        )

    def test_size(self):
        self.assertEqual(
            extract_size("Wohnung mit 65 sqm"),
            65.0
        )

    def test_size_square_meters(self):
        self.assertEqual(
            extract_size("Wohnung mit 75 m²"),
            75.0
        )

    def test_size_missing_returns_none(self):
        self.assertIsNone(
            extract_size("Schöne Wohnung")
        )

    def test_district(self):
        self.assertEqual(
            extract_district("Schöne Wohnung in Neukölln"),
            "neukölln"
        )

    def test_district_unicode_normalization(self):
        text = unicodedata.normalize(
            "NFD",
            "Schöne Wohnung in Neukölln"
        )

        district = extract_district(text)

        self.assertEqual(
            unicodedata.normalize("NFC", district),
            "neukölln"
        )

    def test_wbs_detected(self):
        self.assertTrue(
            detect_wbs("Wohnung nur mit WBS")
        )

    def test_wbs_required_detected(self):
        self.assertTrue(
            detect_wbs("WBS erforderlich")
        )

    def test_wbs_not_detected(self):
        self.assertFalse(
            detect_wbs("Normale Wohnung")
        )

    def test_wbs_not_required(self):
        self.assertFalse(
            detect_wbs("WBS nicht erforderlich")
        )


class TestApartmentFilters(unittest.TestCase):

    def test_good_listing_matches(self):
        matches, reason = matches_requirements(
            title="2 Zimmer Wohnung in Kreuzberg",
            summary="58 sqm, 1100 EUR warm",
            price=1100,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=False,
        )

        self.assertTrue(matches)
        self.assertEqual(
            reason,
            "matches requirements"
        )

    def test_wg_is_excluded(self):
        matches, reason = matches_requirements(
            title="WG Zimmer in Berlin",
            summary="Nice room, 550 EUR",
            price=550,
            rooms=None,
            size=None,
            district="",
            wbs_required=False,
        )

        self.assertFalse(matches)
        self.assertIn(
            "excluded keyword",
            reason
        )

    def test_zwischenmiete_is_excluded(self):
        matches, reason = matches_requirements(
            title="Zwischenmiete Neukölln",
            summary="2 Zimmer, 1000 EUR",
            price=1000,
            rooms=2,
            size=65,
            district="neukölln",
            wbs_required=False,
        )

        self.assertFalse(matches)
        self.assertIn(
            "excluded keyword",
            reason
        )

    def test_expensive_listing_is_rejected(self):
        matches, reason = matches_requirements(
            title="3 Zimmer Penthouse Mitte",
            summary="110 sqm, 2500 EUR warm",
            price=2500,
            rooms=3,
            size=110,
            district="mitte",
            wbs_required=False,
        )

        self.assertFalse(matches)
        self.assertIn(
            "rent too high",
            reason
        )

    def test_missing_price_does_not_crash(self):
        matches, _ = matches_requirements(
            title="2 Zimmer Wohnung in Kreuzberg",
            summary="58 sqm",
            price=None,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=False,
        )

        self.assertIsInstance(matches, bool)

    def test_wbs_listing_allowed_when_wbs_is_any(self):
        matches, _ = matches_requirements(
            title="2 Zimmer Wohnung in Kreuzberg",
            summary="58 sqm, 900 EUR warm, WBS erforderlich",
            price=900,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=True,
        )

        self.assertTrue(matches)

    def test_small_listing_allowed_when_min_size_is_zero(self):
        matches, _ = matches_requirements(
            title="1 Zimmer Wohnung in Kreuzberg",
            summary="25 sqm, 800 EUR warm",
            price=800,
            rooms=1,
            size=25,
            district="kreuzberg",
            wbs_required=False,
        )

        self.assertTrue(matches)

    def test_any_berlin_district_allowed_when_no_district_filter(self):
        matches, _ = matches_requirements(
            title="2 Zimmer Wohnung in Spandau",
            summary="58 sqm, 1000 EUR warm",
            price=1000,
            rooms=2,
            size=58,
            district="spandau",
            wbs_required=False,
        )

        self.assertTrue(matches)


class TestApartmentScoring(unittest.TestCase):

    def setUp(self):
        self.perfect = calculate_score(
            price=1100,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=False,
        )

        self.lower = calculate_score(
            price=1450,
            rooms=3,
            size=75,
            district="mitte",
            wbs_required=False,
        )

    def test_perfect_beats_lower(self):
        self.assertGreater(
            self.perfect,
            self.lower
        )

    def test_score_within_bounds(self):
        for score in (
            self.perfect,
            self.lower
        ):
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_wbs_required_scores_lower(self):
        wbs_score = calculate_score(
            price=1100,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=True,
        )

        self.assertLess(
            wbs_score,
            self.perfect
        )

    def test_cheaper_scores_at_least_as_high(self):
        cheaper = calculate_score(
            price=900,
            rooms=2,
            size=58,
            district="kreuzberg",
            wbs_required=False,
        )

        self.assertGreaterEqual(
            cheaper,
            self.perfect
        )


if __name__ == "__main__":
    unittest.main()
