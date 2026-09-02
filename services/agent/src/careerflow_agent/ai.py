from __future__ import annotations

from time import monotonic
from typing import TypeVar

from openai import AsyncOpenAI
from openai.types.shared_params import Reasoning
from opentelemetry import metrics, trace
from pydantic import BaseModel

from .config import Settings

StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)
TRACER = trace.get_tracer("careerflow.openai")
METER = metrics.get_meter("careerflow.openai")
MODEL_REQUESTS = METER.create_counter("model_requests_total")
MODEL_LATENCY = METER.create_histogram("model_latency_ms", unit="ms")
INPUT_TOKENS = METER.create_counter("model_input_tokens", unit="token")
OUTPUT_TOKENS = METER.create_counter("model_output_tokens", unit="token")
STRUCTURED_FAILURES = METER.create_counter("structured_output_failures_total")


class GroundedOpenAIClient:
    """Tool-less, stateless structured-output boundary for grounded proposals."""

    def __init__(self, *, api_key: str, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = settings.model
        self._reasoning_effort = settings.reasoning_effort

    async def parse(
        self,
        *,
        instructions: str,
        input_text: str,
        output_type: type[StructuredOutput],
        prompt_version: str,
    ) -> StructuredOutput:
        started = monotonic()
        attributes = {"model": self._model, "prompt_version": prompt_version}
        with TRACER.start_as_current_span("openai.response", attributes=attributes) as span:
            try:
                response = await self._client.responses.parse(
                    model=self._model,
                    reasoning=Reasoning(effort=self._reasoning_effort),
                    instructions=instructions,
                    input=input_text,
                    text_format=output_type,
                    store=False,
                )
                parsed = response.output_parsed
                if parsed is None:
                    STRUCTURED_FAILURES.add(1, attributes)
                    raise ValueError("OpenAI response did not contain parsed structured output")
                usage = response.usage
                if usage:
                    INPUT_TOKENS.add(usage.input_tokens, attributes)
                    OUTPUT_TOKENS.add(usage.output_tokens, attributes)
                    span.set_attribute("gen_ai.usage.input_tokens", usage.input_tokens)
                    span.set_attribute("gen_ai.usage.output_tokens", usage.output_tokens)
                MODEL_REQUESTS.add(1, {**attributes, "result": "success"})
                return parsed
            except Exception:
                MODEL_REQUESTS.add(1, {**attributes, "result": "error"})
                raise
            finally:
                MODEL_LATENCY.record((monotonic() - started) * 1000, attributes)
