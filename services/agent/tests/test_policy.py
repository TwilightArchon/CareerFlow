from careerflow_agent.contracts import FieldMapping, MappingDecision, Sensitivity
from careerflow_agent.policy import evaluate_mapping


def test_sensitive_field_always_requires_human() -> None:
    mapping = FieldMapping(
        control_id="disability",
        canonical_path="demographic.disability",
        source="deterministic",
        confidence=1.0,
        sensitivity=Sensitivity.DEMOGRAPHIC,
        decision=MappingDecision.AUTO_FILL,
        rationale="Fixture",
    )
    decision = evaluate_mapping(mapping)
    assert decision.allowed is False
    assert decision.decision == MappingDecision.HUMAN_REQUIRED


def test_model_mapping_requires_review_even_at_high_confidence() -> None:
    mapping = FieldMapping(
        control_id="name",
        canonical_path="identity.full_name",
        source="model",
        confidence=0.99,
        sensitivity=Sensitivity.ORDINARY,
        decision=MappingDecision.AUTO_FILL,
        rationale="Fixture",
    )
    decision = evaluate_mapping(mapping)
    assert decision.decision == MappingDecision.REVIEW
