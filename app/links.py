"""
Tool links -- both the static "always open these" bar and per-property deep
links. Every deep link here was checked against a real, observed URL before
being hardcoded; where no real working query-parameter pattern could be
verified, this deliberately falls back to a plain homepage link instead of
guessing at a URL that might not actually work.

Verified real deep links:
  - Google Maps: documented, stable public API pattern -- safe to build directly.
  - SunBiz (search.sunbiz.org): confirmed against real example search-result
    URLs (e.g. ".../SearchResults?inquiryType=EntityName&searchTerm=API+PRIDE,+LLC"),
    not fabricated.

NOT deep-linkable as of this writing -- fell back to the homepage, don't
"upgrade" these to a guessed query-string without re-verifying first:
  - True People Search: no publicly documented URL pattern found, and the
    site blocks direct automated fetches (403), so nothing here could be
    confirmed against a real result page.
  - LoopNet / CREXi: search results are gated behind an opaque, per-session
    "sk" search-key token, not a plain constructible query string.
  - EarthPlat: has per-county static search pages (e.g. /brevard-property-search)
    but no documented general address/owner query parameter.
"""

from urllib.parse import quote_plus

# The persistent "always open these" bar -- shown on every page.
STATIC_TOOLS = [
    ("LoopNet", "https://www.loopnet.com"),
    ("CREXi", "https://www.crexi.com"),
    ("EarthPlat", "https://earthplat.com"),
    ("True People Search", "https://www.truepeoplesearch.com"),
    ("SunBiz", "https://search.sunbiz.org"),
    ("Google Sheets", "https://sheets.google.com"),
    ("Gmail", "https://mail.google.com"),
]


def maps_search_url(address):
    if not address:
        return None
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"


def sunbiz_name_search_url(name):
    if not name:
        return None
    return (
        "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
        f"?inquiryType=EntityName&searchTerm={quote_plus(name)}"
    )


def property_deep_links(prop):
    """Returns an ordered list of (label, url, verified: bool, kind: str) for
    one property. verified=False entries are homepage-only fallbacks -- the
    template shows those slightly de-emphasized so it's honest about which
    links actually target this specific property vs. just open the tool.

    kind is "map" for the one entry that can stay fully inside the page (it
    just pans/zooms the Leaflet map already embedded on this page) or "tool"
    for everything else. Every "tool" target here (Google Maps itself,
    SunBiz, True People Search, LoopNet, CREXi, Gmail) was checked with a
    real request and sends back an explicit X-Frame-Options/CSP
    frame-ancestors header refusing to be iframed -- that's each site's own
    anti-clickjacking policy, not something fixable from this app's side.
    So "tool" links open as a same-named popup window (via openTool() in
    base.html) that reuses one window per tool instead of piling up tabs,
    which is the closest real approximation of "stays with the page"."""
    links = []

    if prop.get("lat") and prop.get("lng"):
        links.append(("Center map on this address", None, True, "map"))
    else:
        maps_url = maps_search_url(prop.get("address"))
        if maps_url:
            links.append(("Map this address (no pin set yet)", maps_url, True, "tool"))

    owner_name = (prop.get("owner_name") or "").strip()
    if owner_name:
        links.append((f"SunBiz: “{owner_name}”", sunbiz_name_search_url(owner_name), True, "tool"))

    business_name = (prop.get("business_name") or "").strip()
    if business_name:
        links.append((f"SunBiz: “{business_name}”", sunbiz_name_search_url(business_name), True, "tool"))

    # Homepage-only fallbacks -- no verified per-property deep link exists.
    links.append(("Look up owner on True People Search", "https://www.truepeoplesearch.com", False, "tool"))
    if prop.get("earthplat_url"):
        links.append(("EarthPlat (saved link)", prop["earthplat_url"], True, "tool"))
    else:
        links.append(("Look up on EarthPlat", "https://earthplat.com", False, "tool"))

    return links
