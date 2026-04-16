import logging
from seed_data import SEED_RESPONSE

logger = logging.getLogger(__name__)

async def scrape_gaf_leads(zipcode="10013"):
    leads = []
    for result in SEED_RESPONSE.get("results", [])[:25]:
        raw = result.get("raw", {})
        name = result.get("title") or raw.get("gaf_navigation_title") or "Unknown Contractor"
        city = raw.get("gaf_f_city", "")
        state = raw.get("gaf_f_state_code", "")

        gaf_tier = "none"
        certifications = raw.get("gaf_f_contractor_certifications_and_awards_residential") or raw.get("gaf_f_contractor_designations_residential") or []
        if isinstance(certifications, list):
            tier_text = " ".join(map(str, certifications)).lower()
        else:
            tier_text = str(certifications).lower()

        if "master elite" in tier_text or "master_elite" in tier_text:
            gaf_tier = "master_elite"
        elif "certified plus" in tier_text or "certified_plus" in tier_text:
            gaf_tier = "certified_plus"
        elif "certified" in tier_text:
            gaf_tier = "certified"

        leads.append({
            "name": name,
            "address": raw.get("gaf_f_address_line_1", ""),
            "city": city,
            "state": state,
            "zip_code": raw.get("gaf_postal_code", ""),
            "phone": raw.get("gaf_phone", ""),
            "website": raw.get("uri", ""),
            "gaf_tier": gaf_tier,
            "distance_miles": float(raw.get("distanceinmiles", 0.0) or 0.0),
            "review_count": int(raw.get("gaf_number_of_reviews", 0) or 0),
            "avg_rating": float(raw.get("gaf_rating", 0.0) or 0.0),
            "years_in_business": int(raw.get("gaf_f_years_in_business", 1) or 1),
        })

    logger.info(f"Seed scraper: loaded {len(leads)} contractors from seed data")
    return leads
