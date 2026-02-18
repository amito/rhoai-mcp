"""HTTP client for Neural Navigator API."""

from __future__ import annotations

from typing import Any

import httpx

from rhoai_mcp.composites.neuralnav.models import (
    DeploymentIntent,
    ModelRecommendation,
    RecommendationResult,
)


class NeuralNavConnectionError(Exception):
    """Raised when NeuralNav service is unreachable."""


class NeuralNavAPIError(Exception):
    """Raised when NeuralNav API returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"NeuralNav API error ({status_code}): {detail}")


class NeuralNavClient:
    """HTTP client for Neural Navigator API.

    Provides methods for each NeuralNav endpoint and a high-level
    `recommend()` method that chains the full flow.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to NeuralNav."""
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                kwargs: dict[str, Any] = {"params": params}
                if method.upper() in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = json
                http_method = getattr(client, method.lower())
                response = http_method(url, **kwargs)
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
        except httpx.TimeoutException as e:
            raise NeuralNavConnectionError(
                f"Neural Navigator request timed out at {self._base_url}{path}"
            ) from e
        except httpx.ConnectError as e:
            raise NeuralNavConnectionError(
                f"Neural Navigator service unavailable at {self._base_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise NeuralNavAPIError(
                status_code=e.response.status_code,
                detail=e.response.text,
            ) from e

    def extract_intent(self, text: str) -> DeploymentIntent:
        """Extract deployment intent from natural language."""
        data = self._request("POST", "/api/v1/extract", json={"text": text})
        return DeploymentIntent(**data)

    def get_slo_defaults(self, use_case: str) -> dict[str, Any]:
        """Get SLO default values for a use case."""
        return self._request("GET", f"/api/v1/slo-defaults/{use_case}")

    def get_workload_profile(self, use_case: str) -> dict[str, Any]:
        """Get workload profile for a use case."""
        return self._request("GET", f"/api/v1/workload-profile/{use_case}")

    def get_expected_rps(self, use_case: str, user_count: int) -> dict[str, Any]:
        """Calculate expected RPS for a use case and user count."""
        return self._request(
            "GET",
            f"/api/v1/expected-rps/{use_case}",
            params={"user_count": user_count},
        )

    def get_recommendations(
        self,
        use_case: str,
        user_count: int,
        prompt_tokens: int,
        output_tokens: int,
        expected_qps: float,
        ttft_target_ms: int,
        itl_target_ms: int,
        e2e_target_ms: int,
        preferred_gpu_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get ranked recommendations from a specification."""
        payload: dict[str, Any] = {
            "use_case": use_case,
            "user_count": user_count,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "expected_qps": expected_qps,
            "ttft_target_ms": ttft_target_ms,
            "itl_target_ms": itl_target_ms,
            "e2e_target_ms": e2e_target_ms,
            "percentile": "p95",
            "include_near_miss": True,
        }
        if preferred_gpu_types:
            payload["preferred_gpu_types"] = preferred_gpu_types
        return self._request("POST", "/api/v1/ranked-recommend-from-spec", json=payload)

    def recommend(
        self,
        text: str,
        use_case_override: str | None = None,
        user_count_override: int | None = None,
        gpu_types_override: list[str] | None = None,
    ) -> RecommendationResult:
        """Run the full recommendation flow.

        1. Extract intent from text
        2. Apply overrides
        3. Fetch SLO defaults + workload profile + expected RPS
        4. Get ranked recommendations
        5. Return balanced top-5 with specification
        """
        # Step 1: Extract intent
        intent = self.extract_intent(text)

        # Step 2: Apply overrides
        use_case = use_case_override or intent.use_case
        user_count = user_count_override or intent.user_count
        gpu_types = gpu_types_override or intent.preferred_gpu_types

        # Step 3: Fetch defaults
        slo_data = self.get_slo_defaults(use_case)
        workload_data = self.get_workload_profile(use_case)
        rps_data = self.get_expected_rps(use_case, user_count)

        # Extract values
        slo_defaults = slo_data["slo_defaults"]
        workload_profile = workload_data["workload_profile"]
        expected_qps = rps_data["expected_rps"]

        ttft_target = slo_defaults["ttft_ms"]["default"]
        itl_target = slo_defaults["itl_ms"]["default"]
        e2e_target = slo_defaults["e2e_ms"]["default"]
        prompt_tokens = workload_profile["prompt_tokens"]
        output_tokens = workload_profile["output_tokens"]

        # Step 4: Get recommendations
        ranked = self.get_recommendations(
            use_case=use_case,
            user_count=user_count,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            expected_qps=expected_qps,
            ttft_target_ms=ttft_target,
            itl_target_ms=itl_target,
            e2e_target_ms=e2e_target,
            preferred_gpu_types=gpu_types if gpu_types else None,
        )

        # Step 5: Extract balanced list and build result
        balanced_recs = [
            ModelRecommendation(
                model_id=r.get("model_id"),
                model_name=r.get("model_name"),
                gpu_config=r.get("gpu_config"),
                predicted_ttft_p95_ms=r.get("predicted_ttft_p95_ms"),
                predicted_itl_p95_ms=r.get("predicted_itl_p95_ms"),
                predicted_e2e_p95_ms=r.get("predicted_e2e_p95_ms"),
                predicted_throughput_qps=r.get("predicted_throughput_qps"),
                cost_per_hour_usd=r.get("cost_per_hour_usd"),
                cost_per_month_usd=r.get("cost_per_month_usd"),
                meets_slo=r.get("meets_slo", False),
                reasoning=r.get("reasoning", ""),
                scores=r.get("scores"),
            )
            for r in ranked.get("balanced", [])
        ]

        return RecommendationResult(
            specification={
                "use_case": use_case,
                "user_count": user_count,
                "slo_targets": {
                    "ttft_ms": ttft_target,
                    "itl_ms": itl_target,
                    "e2e_ms": e2e_target,
                },
                "traffic_profile": {
                    "prompt_tokens": prompt_tokens,
                    "output_tokens": output_tokens,
                    "expected_qps": expected_qps,
                },
            },
            recommendations=balanced_recs,
            total_configs_evaluated=ranked.get("total_configs_evaluated", 0),
            configs_after_filters=ranked.get("configs_after_filters", 0),
        )

    def health_check(self) -> tuple[bool, str]:
        """Check if NeuralNav service is available."""
        try:
            self._request("GET", "/api/v1/")
            return True, "Neural Navigator available"
        except (NeuralNavConnectionError, NeuralNavAPIError) as e:
            return False, f"Neural Navigator unavailable: {e}"
