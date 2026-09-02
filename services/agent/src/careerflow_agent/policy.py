from __future__ import annotations

from opentelemetry import metrics, trace

from .contracts import FieldMapping, MappingDecision, PolicyDecision, Sensitivity

TRACER = trace.get_tracer("careerflow.policy")
METER = metrics.get_meter("careerflow.policy")
MAPPINGS = METER.create_counter("field_mappings_total")


def evaluate_mapping(mapping: FieldMapping) -> PolicyDecision:
    with TRACER.start_as_current_span("policy.evaluate") as span:
        if mapping.sensitivity in {
            Sensitivity.SENSITIVE,
            Sensitivity.LEGAL,
            Sensitivity.DEMOGRAPHIC,
        }:
            decision = MappingDecision.HUMAN_REQUIRED
            reason = "sensitive_field"
        elif mapping.source == "model":
            decision = MappingDecision.REVIEW
            reason = "model_mapping_requires_review"
        elif mapping.confidence >= 0.95:
            decision = MappingDecision.AUTO_FILL
            reason = "high_confidence_deterministic_mapping"
        elif mapping.confidence >= 0.75:
            decision = MappingDecision.REVIEW
            reason = "medium_confidence_mapping"
        else:
            decision = MappingDecision.HUMAN_REQUIRED
            reason = "low_confidence_mapping"

        span.set_attribute("careerflow.policy.decision", decision)
        MAPPINGS.add(
            1,
            {
                "source": mapping.source,
                "sensitivity": mapping.sensitivity,
                "decision": decision,
            },
        )
        return PolicyDecision(
            allowed=decision is MappingDecision.AUTO_FILL,
            decision=decision,
            reason_code=reason,
            explanation=reason.replace("_", " ").capitalize(),
        )
