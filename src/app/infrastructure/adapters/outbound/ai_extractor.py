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

# Chain-of-Thought extraction prompt — 7 canonical fields + tables + unconstrained extras
PROMPT_TEMPLATE = """\
You are an expert document analyst specializing in invoices, receipts, and general business documents.

## Step 1 — Understand the document
Read the content carefully. Identify:
- What type of document is this? (e.g. "invoice", "receipt", "certificate", "other")
- When was it issued? (doc_date)
- What is the identifier? (doc_number/invoice number)
- Who is issuing the document? (vendor_name)
- Who is receiving the document? (client_name)
- What are the financial sums? (total_amount and tax_amount)

## Step 2 — Locate and parse each field
For each required field below, think through where in the document it appears and what value it holds.
- Monetary values and amounts should be carefully parsed as floats. Remove currency symbols, parentheses, spaces, and commas/periods as separators (e.g., "$ 20.27" or "($20.27)" -> 20.27).
- Dates should be strictly parsed in YYYY-MM-DD format (convert formats like "8/8/2024" to "2024-08-08").

## Step 3 — Extract Tables / Line Items
If there is tabular data or line items (such as product descriptions, quantities, unit prices, and row totals), extract them as objects in the `tables` list.
Each row should typically contain:
- `description`: product/service description
- `qty`: quantity ordered/shipped (number)
- `unit_price`: price per unit (float)
- `total`: total line amount (float)

## Step 4 — Extract Extras (Unconstrained)
Any other key-value pairs not covered by the 7 canonical fields should be extracted into the `extras` dictionary.
Feel free to generate new custom keys dynamically based on the document's content (e.g. "subtotal", "discount", "shipping", "payment_terms", "payment_instructions", "venmo_account", "paypal_account", "remarks", etc.).
Always include a concise visual/layout summary of the page under the "description" key inside `extras`.

## Step 5 — Output ONLY valid JSON
Return exactly this JSON object and nothing else. No markdown wrapping, no explanation, no extra keys outside this schema:

{
  "document_type": "<\"invoice\"|\"receipt\"|\"certificate\"|\"other\">",
  "doc_date": "<YYYY-MM-DD|null>",
  "doc_number": "<string|null>",
  "vendor_name": "<string|null>",
  "client_name": "<string|null>",
  "total_amount": <float|null>,
  "tax_amount": <float|null>,
  "tables": [
    {
      "description": "<string>",
      "qty": <number|null>,
      "unit_price": <float|null>,
      "total": <float|null>
    }
  ],
  "extras": {
    "description": "<concise visual/layout summary of the page>",
    "custom_key_1": "value"
  }
}
"""


class LlmAiExtractor(AiExtractorPort):
    """
    Adapter implementing AI extraction via Gemini or OpenAI APIs using LangChain.
    Uses a Chain-of-Thought prompt for higher accuracy on the 7 canonical fields.
    Secondary fields go into the nested `extras` dict, and tabular items go into `tables`.
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

    def _coerce_float(self, val: Any) -> float | None:
        if val is None:
            return None
        try:
            # Handle string formatting like ($2.00) or $ 20.27
            if isinstance(val, str):
                cleaned = val.replace("$", "").replace(" ", "").replace(",", "")
                if cleaned.startswith("(") and cleaned.endswith(")"):
                    cleaned = cleaned[1:-1]
                return float(cleaned)
            return float(val)
        except ValueError, TypeError:
            return None

    def _coerce_int(self, val: Any) -> int | None:
        if val is None:
            return None
        try:
            return int(val)
        except ValueError, TypeError:
            return None

    def _coerce_table_row(self, row: dict[str, Any]) -> dict[str, Any]:
        coerced = {**row}
        for k in ["qty", "unit_price", "total"]:
            if k in coerced:
                coerced[k] = self._coerce_float(coerced[k])
        return coerced

    def _coerce_tables(self, tables: Any) -> list[dict[str, Any]]:
        if not isinstance(tables, list):
            return []
        coerced = []
        for row in tables:
            if isinstance(row, dict):
                coerced.append(self._coerce_table_row(row))
        return coerced

    def _coerce_types(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure numeric fields are correct Python types, not strings."""
        for f in ["total_amount", "tax_amount"]:
            if f in result:
                result[f] = self._coerce_float(result[f])

        result["tables"] = self._coerce_tables(result.get("tables"))

        if "extras" not in result or not isinstance(result["extras"], dict):
            result["extras"] = {}
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
                f"document_type={result.get('document_type')}, "
                f"vendor={result.get('vendor_name')}, "
                f"total={result.get('total_amount')}"
            )
            return result

        except Exception as exc:
            logger.error(f"AI extraction failed for '{filename}': {exc}")
            return {}
