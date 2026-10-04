import os
from dotenv import load_dotenv

load_dotenv()

def _float_env(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return float(default)


def _set_env(name):
    return {
        item.strip().lower()
        for item in os.getenv(name, "").split(",")
        if item.strip()
    }


MIN_ROOMS = _float_env("MIN_ROOMS", 1)
MAX_ROOMS = _float_env("MAX_ROOMS", 3)
MAX_RENT = _float_env("MAX_RENT", 1500)
MIN_SIZE = _float_env("MIN_SIZE", 0)

DISTRICTS = _set_env("DISTRICTS")

WBS_REQUIREMENT = os.getenv(
    "WBS",
    "any"
).lower().strip()

EXCLUDE_KEYWORDS = _set_env("EXCLUDE_KEYWORDS")


def matches_requirements(
    title,
    summary,
    price=None,
    rooms=None,
    size=None,
    district="",
    wbs_required=False,
):
    """
    Check whether a property matches the user's requirements.

    Returns:
        (True, "matches requirements")
        or
        (False, "reason")
    """

    text = f"{title} {summary}".lower()

    # ---------------------------------------------------------
    # 1. Excluded keywords
    # ---------------------------------------------------------

    for keyword in EXCLUDE_KEYWORDS:

        if keyword in text:
            return (
                False,
                f"excluded keyword: {keyword}"
            )

    # ---------------------------------------------------------
    # 2. Maximum rent
    # ---------------------------------------------------------

    if price is not None and price > MAX_RENT:

        return (
            False,
            f"rent too high: {price:.2f}"
        )

    # ---------------------------------------------------------
    # 3. Room range
    # ---------------------------------------------------------

    if rooms is not None:

        if rooms < MIN_ROOMS:

            return (
                False,
                f"too few rooms: {rooms}"
            )

        if rooms > MAX_ROOMS:

            return (
                False,
                f"too many rooms: {rooms}"
            )

    # ---------------------------------------------------------
    # 4. Minimum size
    # ---------------------------------------------------------

    if size is not None and size < MIN_SIZE:

        return (
            False,
            f"size too small: {size:.1f} m²"
        )

    # ---------------------------------------------------------
    # 5. District filter
    # ---------------------------------------------------------

    if DISTRICTS:

        district_lower = (district or "").lower()

        if not any(
            selected in district_lower
            for selected in DISTRICTS
        ):

            return (
                False,
                f"district not preferred: {district or 'unknown'}"
            )

    # ---------------------------------------------------------
    # 6. WBS requirement
    # ---------------------------------------------------------

    if WBS_REQUIREMENT == "yes":

        if not wbs_required:

            return (
                False,
                "WBS required"
            )

    elif WBS_REQUIREMENT == "no":

        if wbs_required:

            return (
                False,
                "WBS not wanted"
            )

    # ---------------------------------------------------------
    # 7. Everything passed
    # ---------------------------------------------------------

    return (
        True,
        "matches requirements"
    )
