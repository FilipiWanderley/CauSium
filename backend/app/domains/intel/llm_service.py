from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.domains.intel.schemas import ExplainCostCause, ExplainCostChangeOut


class LlmService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def explain_cost_change(self, context: dict[str, Any]) -> ExplainCostChangeOut:
        provider = (self.settings.ai_provider or "mock").lower()
        language = _normalize_language(context.get("language"))
        if provider == "mock":
            return _mock_explain_cost_change(context, language=language)
        if provider == "openai":
            return await self._openai_explain_cost_change(context, language=language)
        raise ValueError(f"Unsupported AI provider: {provider}")

    async def _openai_explain_cost_change(
        self, context: dict[str, Any], *, language: str
    ) -> ExplainCostChangeOut:
        if not self.settings.ai_openai_api_key:
            raise ValueError("AI provider is openai, but AI_OPENAI_API_KEY is not set")

        language_instruction = (
            "Respond in Brazilian Portuguese."
            if language == "pt"
            else "Respond in English."
        )
        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a FinOps assistant for a cloud cost intelligence platform. "
                        "You receive structured telemetry about cost changes and relevant events. "
                        "Return only valid JSON matching the required schema. "
                        f"{language_instruction}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": (
                                "Explain cost change for a workspace and propose actions."
                                if language == "en"
                                else "Explique a variacao de custo do workspace e proponha acoes."
                            ),
                            "required_json_schema": {
                                "summary": "string",
                                "causes": [
                                    {
                                        "cause": "string",
                                        "evidence": ["string"],
                                        "estimated_impact_usd": "number|null",
                                    }
                                ],
                                "impact": "string",
                                "recommendation": "string",
                                "confidence": "number between 0 and 1",
                            },
                            "context": context,
                        },
                        default=str,
                    ),
                },
            ],
        }

        headers = {"Authorization": f"Bearer {self.settings.ai_openai_api_key}"}
        base_url = self.settings.ai_openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self.settings.ai_timeout_seconds) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = _parse_llm_json(content)
        out = _coerce_out(parsed, language=language)
        out.model = self.settings.ai_model
        return out


def _parse_llm_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _coerce_out(payload: dict[str, Any], *, language: str = "en") -> ExplainCostChangeOut:
    causes_raw = payload.get("causes") or []
    causes: list[ExplainCostCause] = []
    for item in causes_raw[:10]:
        if not isinstance(item, dict):
            continue
        causes.append(
            ExplainCostCause(
                cause=str(item.get("cause") or "").strip()
                or ("Driver desconhecido" if language == "pt" else "Unknown driver"),
                evidence=[str(e) for e in (item.get("evidence") or []) if str(e).strip()][:8],
                estimated_impact_usd=(
                    float(item["estimated_impact_usd"])
                    if item.get("estimated_impact_usd") is not None
                    else None
                ),
            )
        )

    confidence = payload.get("confidence")
    try:
        confidence_f = float(confidence) if confidence is not None else 0.5
    except Exception:
        confidence_f = 0.5
    confidence_f = max(0.0, min(1.0, confidence_f))

    return ExplainCostChangeOut(
        summary=str(payload.get("summary") or "").strip()
        or ("Resumo nao disponivel." if language == "pt" else "No summary provided."),
        causes=causes,
        impact=str(payload.get("impact") or "").strip()
        or ("Impacto nao disponivel." if language == "pt" else "Impact not available."),
        recommendation=str(payload.get("recommendation") or "").strip()
        or (
            "Revise os drivers de custo e valide mudancas recentes de deploy e escalabilidade."
            if language == "pt"
            else "Review the cost drivers and validate scaling and deployment changes."
        ),
        confidence=confidence_f,
    )


def _mock_explain_cost_change(
    context: dict[str, Any], *, language: str = "en"
) -> ExplainCostChangeOut:
    pct = context.get("delta", {}).get("change_pct")
    top_increases = context.get("drivers", {}).get("top_increases") or []
    top_service = (
        (top_increases[0].get("service") if top_increases else None)
        or ("servico desconhecido" if language == "pt" else "unknown service")
    )
    summary = (
        (
            f"O custo variou {pct}% puxado principalmente por {top_service} e mudancas recentes de carga."
            if language == "pt"
            else f"Cost changed by {pct}% driven primarily by {top_service} and recent workload changes."
        )
        if pct is not None
        else (
            "O custo variou no periodo selecionado por mudancas de uso e comportamento de recursos."
            if language == "pt"
            else "Cost changed in the selected period due to workload and resource usage shifts."
        )
    )
    causes = []
    if top_increases:
        d = top_increases[0]
        causes.append(
            ExplainCostCause(
                cause=(
                    f"Aumento de gasto em {d.get('service')}"
                    if language == "pt"
                    else f"Increased spend in {d.get('service')}"
                ),
                evidence=(
                    [f"Delta USD: {d.get('delta_usd')}"]
                    if d.get("delta_usd") is not None
                    else []
                ),
                estimated_impact_usd=float(d["delta_usd"]) if d.get("delta_usd") is not None else None,
            )
        )
    return ExplainCostChangeOut(
        summary=summary,
        causes=causes,
        impact=(
            "Os principais fatores mostram aumentos de custo concentrados em poucos servicos."
            if language == "pt"
            else "Top drivers indicate service-level increases concentrated in a small set of services."
        ),
        recommendation=(
            "Valide implantacoes e eventos de escala recentes, depois faca dimensionamento adequado e ajuste de autoescalonamento."
            if language == "pt"
            else "Validate recent deploys and scaling events, then right-size or adjust autoscaling policies."
        ),
        confidence=0.35,
        model="mock",
    )


def _normalize_language(value: Any) -> str:
    v = str(value or "en").strip().lower()
    return "pt" if v.startswith("pt") else "en"
