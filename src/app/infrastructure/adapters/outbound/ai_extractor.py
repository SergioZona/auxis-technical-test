import base64
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.application.ports.outbound.ai_extractor_port import AiExtractorPort
from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# Chain-of-Thought extraction prompt — 10 canonical fields + extras
PROMPT_TEMPLATE = """\
You are an expert document analyst specializing in Colombian tax withholding certificates (DIAN).

## Step 1 — Understand the document
Read the content carefully. Identify:
- Is this a Form 220 (Certificado de Ingresos y Retenciones)?
- Who is the employer (pagador/empresa)?
- Who is the employee (beneficiario)?
- What tax year does it cover?
- What is the certification period (start and end dates)?
- What are the two most important financial figures: total gross income and income tax withheld?

## Step 2 — Locate each field
For each required field below, think through where in the document it appears and what value it holds.
- Monetary values in Colombian documents use period as thousands separator and comma as decimal (e.g. $72.221.000 = 72221000.0).
- NIT numbers may appear as "NIT 901638314-5" or just "901638314 5".
- Employee names in Form 220 appear as: Primer apellido | Segundo apellido | Primer nombre | Otros nombres.
- Dates should be strictly parsed in YYYY-MM-DD format.

## Step 3 — Output ONLY valid JSON
Return exactly this JSON object and nothing else. No markdown, no explanation, no extra keys.

Required fields (10 canonical + extras):
{
  "form_type": "<\"220\"|\"210\"|\"2516\"|\"110\"|\"invoice\"|null>",
  "tax_year": <integer|null>,
  "nit_employer": "<NIT with DV e.g. \"901638314-5\"|null>",
  "employer_name": "<legal company name only — no description|null>",
  "employee_document_id": "<CC/NIT number string|null>",
  "employee_name": "<full name — no description|null>",
  "period_start": "<YYYY-MM-DD|null>",
  "period_end": "<YYYY-MM-DD|null>",
  "total_gross_income": <float|null>,
  "income_tax_withheld": <float|null>,
  "extras": {
    "form_number": "<string|null>",
    "location": "<city string|null>",
    "salary_payments": <float|null>,
    "social_benefits": <float|null>,
    "other_income_payments": <float|null>,
    "health_contributions": <float|null>,
    "pension_contributions": <float|null>,
    "average_monthly_income": <float|null>,
    "total_annual_withholding": <float|null>,
    "description": "<concise visual/layout summary of the page>"
  }
}
"""

_FLOAT_EXTRAS = [
    "salary_payments",
    "social_benefits",
    "other_income_payments",
    "health_contributions",
    "pension_contributions",
    "average_monthly_income",
    "total_annual_withholding",
]


class LlmAiExtractor(AiExtractorPort):
    """
    Adapter implementing AI extraction via Gemini or OpenAI APIs using LangChain.
    Uses a Chain-of-Thought prompt for higher accuracy on the 10 canonical fields.
    Secondary fields go into the nested `extras` dict.
    """

    def __init__(self, settings: Settings):
        self._settings = settings

    def _get_llm(self) -> Any:
        gemini_key = self._settings.gemini_api_key
        openai_key = self._settings.openai_api_key

        if gemini_key:
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=gemini_key,
                temperature=0,
            )
        elif openai_key:
            openai_kwargs: dict[str, Any] = {
                "model": "gpt-4o-mini",
                "api_key": openai_key,
                "temperature": 0,
            }
            return ChatOpenAI(**openai_kwargs)
        else:
            raise ValueError(
                "No LLM API keys configured (GEMINI_API_KEY or OPENAI_API_KEY required)."
            )

    def _parse_response_content(self, content: Any) -> str:
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    parts.append(part["text"])
            return "".join(parts).strip()
        return str(content).strip()

    def _clean_json_string(self, raw: str) -> str:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return raw.strip()

    def _coerce_types(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure numeric fields are correct Python types, not strings."""
        float_top = ["total_gross_income", "income_tax_withheld"]
        for f in float_top:
            if result.get(f) is not None:
                try:
                    result[f] = float(result[f])
                except ValueError, TypeError:
                    result[f] = None

        if result.get("tax_year") is not None:
            try:
                result["tax_year"] = int(result["tax_year"])
            except ValueError, TypeError:
                result["tax_year"] = None

        extras = result.get("extras") or {}
        for f in _FLOAT_EXTRAS:
            if extras.get(f) is not None:
                try:
                    extras[f] = float(extras[f])
                except ValueError, TypeError:
                    extras[f] = None
        result["extras"] = extras
        return result

    async def extract_metadata(
        self,
        text: str | None = None,
        image_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        try:
            llm = self._get_llm()
        except ValueError as exc:
            logger.warning(str(exc))
            return {}

        prompt = PROMPT_TEMPLATE
        if text:
            prompt += f"\n\n## Document/Page Content\n{text}"

        content_list: list[Any] = [{"type": "text", "text": prompt}]

        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            content_list.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )

        try:
            if isinstance(llm, ChatOpenAI):
                llm = llm.bind(response_format={"type": "json_object"})

            response = await llm.ainvoke([HumanMessage(content=content_list)])
            raw = self._parse_response_content(response.content)
            raw = self._clean_json_string(raw)
            result = self._coerce_types(json.loads(raw))

            logger.info(
                f"AI extraction OK '{filename}': "
                f"employee={result.get('employee_name')}, "
                f"gross={result.get('total_gross_income')}, "
                f"withheld={result.get('income_tax_withheld')}"
            )
            return result

        except Exception as exc:
            logger.error(f"AI extraction failed for '{filename}': {exc}")
            return {}
