"""
lib/llm.py
──────────
Azure OpenAI analyser for HNW lead extraction.
"""

import json
import logging
from openai import AzureOpenAI
from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)

logger = logging.getLogger(__name__)

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a Senior Financial Intelligence Analyst specializing in identifying
High Net Worth (HNW) individuals across ALL categories.

CATEGORIES (choose exactly one):
- CELEBRITY
- SPORTS_STAR
- TECH_FOUNDER
- BUSINESS_OWNER
- C_SUITE_EXECUTIVE
- INVESTOR
- REAL_ESTATE
- HNW_INDIVIDUAL

PRIMARY OBJECTIVE:
Identify real individuals whose stated or reasonably inferable net worth
qualifies them as High Net Worth (HNW).

HNW DEFINITION:
- Explicit net worth mentioned in text, OR
- Clear financial indicators suggesting significant wealth
  (e.g., large ownership stake, major contracts, large-scale assets, funding raised, enterprise value).

STRICT EXTRACTION RULES:
1. Extract ONLY real human individuals.
2. Do NOT extract companies, brands, or fictional characters.
3. Never fabricate or guess specific financial numbers.
4. Estimate net worth ONLY if reasonably inferable from the text using:
   - Company valuation × ownership %
   - Executive compensation + stock holdings
   - Athlete contracts + endorsements
   - Celebrity royalties + endorsements + assets
   - Real estate or business asset descriptions
5. If estimation is not clearly supported by text:
   - Set "net_worth": null
   - Set "net_worth_currency": null
6. DO NOT perform currency conversion.
7. Use the exact currency mentioned in the text.
8. Formatting rules:
   - If text says "40+ crore" → return:
     "net_worth": "40+ crore",
     "net_worth_currency": "rupee"
   - If text says "10 million dollars" → return:
     "net_worth": "10 million",
     "net_worth_currency": "dollar"
    
   - Do NOT add zeros.
   - Do NOT convert crore to million or vice versa.
9. If no qualifying HNW individual is found → return: {}
10. Output ONLY valid JSON. No markdown. No explanation. No extra text.

LOCATION FILTERING (MANDATORY):
**Target Location is not mentioned in the lead data You should skip that lead data please Don't assume.
For example Target location is Delhi, then Gautam Adani is not a valid lead even though he is a billionaire because his wealth is primarily associated with Gujarat and Mumbai, not Delhi.** similarly Ambani is not a valid lead because his wealth is primarily associated with Mumbai, not Delhi. You must strictly filter by TARGET LOCATION.And also Assume pretrained knowledge will they belong to particular city or not.
You must strictly filter by TARGET LOCATION.And also Assume pretrained knowledge will they belong to particular city or not.
Skip the lead whose Networth is not mentioned in the text but you can infer it based on the person's profile and background knowledge.
Return an individual ONLY if:
- Their wealth is generated in that city, OR
- They own significant business/assets in that city, OR
- They reside in that city AND operate wealth activity there.

DO NOT return individuals if:
- They are merely mentioned.
- They are from the city but built wealth elsewhere.
- They only own a passive house there.
- Their economic activity is clearly centered in another city.

If a lead qualifies:
- ALWAYS set "city" = TARGET LOCATION.
- Add a short "reasoning" explaining the economic connection.

Return ONLY structured JSON.
"""

# NOTE: prompt is built via _build_prompt() to avoid .format() clashing
# with curly braces inside the JSON schema example and inside scraped text.
_PROMPT_HEADER = """\
Analyse the text below and extract every qualifying High Net Worth individual.

Return ONLY a valid JSON object.
If none qualify, return: {{}}

TARGET LOCATION: {city}

TEXT:
{chunk_text}

Return this EXACT JSON format (repeat lead_2, lead_3 … for each person found):
"""

_PROMPT_SCHEMA = '''
{
  "lead_1": {
    "full_name": "string or null",
    "category": "CELEBRITY|SPORTS_STAR|TECH_FOUNDER|BUSINESS_OWNER|C_SUITE_EXECUTIVE|INVESTOR|REAL_ESTATE|HNW_INDIVIDUAL",
    "company_name": "string or null",
    "title": "string or null",
    "known_for": "brief 1-sentence description",
    "age": null,
    "gender": "string or null",
    "city": "string",
    "state": "string",
    "country": "string",
    "reasoning": "why you believe they are in this location",
    "nri_status": "RESIDENT|NRI|OCI|UNKNOWN",
    "industry": "string",
    "years_in_business": null,
    "net_worth": string or null,
    "net_worth_currency": "Based on the lead data",
    "net_worth_source": "PUBLIC_REPORT|ESTIMATED|SELF_DECLARED|MEDIA",
    "annual_income": null,
    "income_type": "SALARY|BUSINESS|INVESTMENTS|MIXED",
    "liquid_assets_estimate": null,
    "real_estate_value_estimate": null,
    "business_valuation_estimate": null,
    "insurance_existing_coverage_estimate": null,
    "insurance_gap_estimate": null,
    "annual_premium_capacity_estimate": null,
    "estate_planning_status": "NONE|BASIC_WILL|TRUST_STRUCTURE|FAMILY_OFFICE|UNKNOWN",
    "has_children": "true|false|unknown",
    "number_of_dependents": null,
    "keyman_insurance_potential": "HIGH|MEDIUM|LOW|NA",
    "buy_sell_agreement_potential": "HIGH|MEDIUM|LOW|NA",
    "director_liability_exposure": "HIGH|MEDIUM|LOW|NA",
    "international_travel_frequency": "HIGH|MEDIUM|LOW|UNKNOWN",
    "luxury_asset_indicator": "HIGH|MEDIUM|LOW|UNKNOWN",
    "club_membership_indicator": "YES|NO|UNKNOWN",
    "philanthropy_involvement": "YES|NO|UNKNOWN",
    "public_visibility_level": "HIGH|MEDIUM|LOW",
    "data_confidence_score": 0,
    "lead_source": "LINKEDIN|ROC|PROPERTY_DATA|NEWS|REFERRAL|MANUAL_RESEARCH",
    "last_verified_date": "YYYY-MM-DD",
    "insurance_priority_type": "LIFE|HEALTH|ESTATE|KEYMAN|LIABILITY|GLOBAL_MEDICAL|WEALTH_TRANSFER|MULTI_LINE",
    "overall_hni_score": 0,
    "qualification_status": "HOT|WARM|COLD|DISQUALIFIED",
    "source_url": "SOURCE_URL_PLACEHOLDER",
    "other_notes": "string or null"
  }
}
'''


def _build_prompt(chunk: str, source_url: str, city: str) -> str:
    """
    Build the final prompt safely — avoids .format() touching the JSON schema
    or any curly braces that may appear inside scraped text.
    """
    header = _PROMPT_HEADER.format(
        source_url=source_url,
        city=city,
        chunk_text=chunk,
    )
    schema = _PROMPT_SCHEMA.replace("SOURCE_URL_PLACEHOLDER", source_url)
    return header + schema


# ── Analyser class ────────────────────────────────────────────────────────────

class AzureAnalyser:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )

    def analyse_chunk(self, chunk: str, source_url: str, city: str) -> dict:
        """
        Send one text chunk to Azure OpenAI.
        Returns a dict of {lead_N: {...}} or {} on failure / no leads found.
        """
        prompt = _build_prompt(chunk=chunk, source_url=source_url, city=city)
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user",   "content":SYSTEM_PROMPT + prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned)
        except Exception as e:
            logger.error(f"[LLM] analysis failed: {e}")
            return {}
        
