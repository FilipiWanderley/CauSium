from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.domains.intel.schemas import (
    ExplainCostCause,
    ExplainCostChangeOut,
    ExplainRecommendationOut,
    IntelInsightsOut,
)


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

    async def generate_insights(self, context: dict[str, Any]) -> IntelInsightsOut:
        provider = (self.settings.ai_provider or "mock").lower()
        language = _normalize_language(context.get("language"))
        if provider == "mock":
            return _mock_generate_insights(context, language=language)
        if provider == "openai":
            return await self._openai_generate_insights(context, language=language)
        raise ValueError(f"Unsupported AI provider: {provider}")

    async def explain_recommendation(self, context: dict[str, Any]) -> ExplainRecommendationOut:
        provider = (self.settings.ai_provider or "mock").lower()
        language = _normalize_language(context.get("language"))
        if provider == "mock":
            return _mock_explain_recommendation(context, language=language)
        if provider == "openai":
            return await self._openai_explain_recommendation(context, language=language)
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

    async def _openai_generate_insights(
        self, context: dict[str, Any], *, language: str
    ) -> IntelInsightsOut:
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
                        "You are a FinOps copilot. "
                        "Given structured workspace signals, return one actionable decision summary. "
                        "Return only valid JSON matching the required schema. "
                        f"{language_instruction}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": (
                                "Generate actionable cloud cost insights and one prioritized recommendation."
                                if language == "en"
                                else "Gere insights acionaveis de custo cloud e uma recomendacao priorizada."
                            ),
                            "required_json_schema": {
                                "top_saving_opportunity": "string",
                                "main_risk": "string",
                                "cost_trend_summary": "string",
                                "recommended_action": "string",
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
        out = _coerce_insights_out(parsed, language=language)
        out.model = self.settings.ai_model
        return out

    async def _openai_explain_recommendation(
        self, context: dict[str, Any], *, language: str
    ) -> ExplainRecommendationOut:
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
                        "You are a cloud optimization copilot for FinOps and platform teams. "
                        "You receive a recommendation plus resource behavior telemetry. "
                        "Return only valid JSON matching the required schema. "
                        f"{language_instruction}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": (
                                "Explain this optimization recommendation and provide an actionable execution plan."
                                if language == "en"
                                else "Explique esta recomendacao de otimizacao e forneca um plano de execucao acionavel."
                            ),
                            "required_json_schema": {
                                "summary": "string",
                                "why_now": "string",
                                "expected_impact": "string",
                                "risks": ["string"],
                                "recommended_steps": ["string"],
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
        out = _coerce_recommendation_out(parsed, language=language)
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
        model="rule-based",
    )


def _coerce_insights_out(payload: dict[str, Any], *, language: str = "en") -> IntelInsightsOut:
    confidence = payload.get("confidence")
    try:
        confidence_f = float(confidence) if confidence is not None else 0.6
    except Exception:
        confidence_f = 0.6
    confidence_f = max(0.0, min(1.0, confidence_f))

    return IntelInsightsOut(
        top_saving_opportunity=str(payload.get("top_saving_opportunity") or "").strip()
        or (
            "No significant saving opportunity identified."
            if language == "en"
            else "Nenhuma oportunidade relevante de economia identificada."
        ),
        main_risk=str(payload.get("main_risk") or "").strip()
        or (
            "No relevant financial risk detected."
            if language == "en"
            else "Nenhum risco financeiro relevante detectado."
        ),
        cost_trend_summary=str(payload.get("cost_trend_summary") or "").strip()
        or (
            "Insufficient data to summarize cost trend."
            if language == "en"
            else "Dados insuficientes para resumir tendencia de custos."
        ),
        recommended_action=str(payload.get("recommended_action") or "").strip()
        or (
            "Review top opportunities and monitor anomaly signals."
            if language == "en"
            else "Revise as principais oportunidades e monitore sinais de anomalia."
        ),
        confidence=confidence_f,
    )


def _mock_generate_insights(context: dict[str, Any], *, language: str = "en") -> IntelInsightsOut:
    fallback = context.get("fallback") or {}
    return IntelInsightsOut(
        top_saving_opportunity=str(fallback.get("top_saving_opportunity") or ""),
        main_risk=str(fallback.get("main_risk") or ""),
        cost_trend_summary=str(fallback.get("cost_trend_summary") or ""),
        recommended_action=str(fallback.get("recommended_action") or ""),
        confidence=float(fallback.get("confidence") or 0.6),
        model="rule-based",
    )


def _coerce_recommendation_out(
    payload: dict[str, Any], *, language: str = "en"
) -> ExplainRecommendationOut:
    confidence = payload.get("confidence")
    try:
        confidence_f = float(confidence) if confidence is not None else 0.6
    except Exception:
        confidence_f = 0.6
    confidence_f = max(0.0, min(1.0, confidence_f))

    risks = [str(i).strip() for i in (payload.get("risks") or []) if str(i).strip()][:8]
    steps = [str(i).strip() for i in (payload.get("recommended_steps") or []) if str(i).strip()][:10]

    return ExplainRecommendationOut(
        summary=str(payload.get("summary") or "").strip()
        or (
            "Unable to summarize this recommendation with the current data."
            if language == "en"
            else "Nao foi possivel resumir esta recomendacao com os dados atuais."
        ),
        why_now=str(payload.get("why_now") or "").strip()
        or (
            "Recent telemetry indicates this action can reduce waste in the current workload profile."
            if language == "en"
            else "A telemetria recente indica que esta acao pode reduzir desperdicio no perfil atual de carga."
        ),
        expected_impact=str(payload.get("expected_impact") or "").strip()
        or (
            "Potential cost reduction with controlled execution risk."
            if language == "en"
            else "Potencial de reducao de custo com risco controlado de execucao."
        ),
        risks=risks,
        recommended_steps=steps,
        confidence=confidence_f,
    )


def _mock_explain_recommendation(
    context: dict[str, Any], *, language: str = "en"
) -> ExplainRecommendationOut:
    recommendation = context.get("recommendation") or {}
    title = str(recommendation.get("title") or recommendation.get("category") or "Optimization")
    monthly = float(recommendation.get("estimated_monthly_savings_usd") or 0.0)
    if language == "pt":
        return ExplainRecommendationOut(
            summary=f"A recomendacao '{title}' tem boa relacao custo-beneficio para o momento atual.",
            why_now="Os sinais recentes de utilizacao mostram capacidade ociosa e espaco para ajuste seguro.",
            expected_impact=(
                f"Economia potencial aproximada de US${monthly:,.2f}/mes com menor desperdicio de recursos."
                if monthly > 0
                else "Economia potencial com melhor eficiencia operacional."
            ),
            risks=[
                "Risco de underprovisioning se a carga aumentar abruptamente.",
                "Necessidade de validar janelas e dependencias antes da mudanca.",
            ],
            recommended_steps=[
                "Executar canario em recurso representativo.",
                "Monitorar latencia/erro e uso de CPU/rede por 24h.",
                "Aplicar rollout gradual e manter plano de rollback.",
            ],
            confidence=0.55,
            model="rule-based",
        )
    return ExplainRecommendationOut(
        summary=f"The recommendation '{title}' is timely and likely to deliver positive efficiency gains.",
        why_now="Recent utilization signals indicate sustained waste and a low-risk optimization window.",
        expected_impact=(
            f"Potential savings around ${monthly:,.2f}/month with improved utilization."
            if monthly > 0
            else "Potential savings with better operational efficiency."
        ),
        risks=[
            "Under-provisioning risk if traffic spikes unexpectedly.",
            "Operational risk if changes are applied without phased validation.",
        ],
        recommended_steps=[
            "Run a canary on a representative resource first.",
            "Track latency/error and CPU/network trends for 24h.",
            "Roll out gradually and keep rollback ready.",
        ],
        confidence=0.55,
        model="rule-based",
    )


def _normalize_language(value: Any) -> str:
    v = str(value or "en").strip().lower()
    return "pt" if v.startswith("pt") else "en"
