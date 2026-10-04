"""
Apartment listing scoring.

The score is between 0 and 100.

Weights:
- Budget: 30 points
- Rooms: 25 points
- Size: 20 points
- District: 15 points
- WBS: 10 points
"""

def calculate_score(
    price,
    rooms,
    size,
    district="",
    wbs_required=False,
    max_rent=1500,
    min_rooms=1,
    max_rooms=3,
    min_size=0,
    preferred_districts=None,
):
    """Calculate a match score from 0 to 100."""

    score = 0

    # ---------------------------------------------------------
    # Budget: 30 points
    # ---------------------------------------------------------
    if price is not None and max_rent > 0:
        if price <= max_rent * 0.80:
            score += 30
        elif price <= max_rent * 0.90:
            score += 25
        elif price <= max_rent:
            score += 20

    # ---------------------------------------------------------
    # Rooms: 25 points
    # ---------------------------------------------------------
    if rooms is not None:
        if min_rooms <= rooms <= max_rooms:
            score += 25

    # ---------------------------------------------------------
    # Size: 20 points
    # ---------------------------------------------------------
    if size is not None:
        if min_size <= size:
            score += 20

    # ---------------------------------------------------------
    # District: 15 points
    # ---------------------------------------------------------
    if preferred_districts:
        district_normalized = (district or "").strip().lower()

        preferred = {
            item.strip().lower()
            for item in preferred_districts
            if item.strip()
        }

        if district_normalized in preferred:
            score += 15
    else:
        # If the user has no preferred districts,
        # the listing is not penalized.
        score += 15

    # ---------------------------------------------------------
    # WBS: 10 points
    # ---------------------------------------------------------
    # Normal apartment = full points.
    # WBS-required apartment = lower score because
    # it requires an additional eligibility condition.
    if not wbs_required:
        score += 10

    return min(score, 100)
