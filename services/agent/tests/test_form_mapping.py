from uuid import uuid4

from careerflow_agent.contracts import (
    CandidateFact,
    CandidateProfile,
    FactState,
    FormControl,
    MappingDecision,
    ObservedForm,
    Sensitivity,
)
from careerflow_agent.form_mapping import map_control, plan_form_fill


def control(
    control_id: str,
    label: str,
    sensitivity: Sensitivity,
    *,
    required: bool = False,
    autocomplete: str | None = None,
) -> FormControl:
    return FormControl(
        control_id=control_id,
        label=label,
        kind="text",
        required=required,
        sensitivity=sensitivity,
        autocomplete=autocomplete,
    )


def test_deterministic_form_mapping_obeys_sensitive_and_legal_policy() -> None:
    first_name = control(
        "first-name",
        "First name",
        Sensitivity.ORDINARY,
        required=True,
        autocomplete="given-name",
    )
    email = control(
        "email",
        "Email address",
        Sensitivity.ORDINARY,
        required=True,
    )
    sponsorship = control(
        "sponsorship",
        "Will you require sponsorship?",
        Sensitivity.LEGAL,
        required=True,
    )

    assert map_control(first_name).decision is MappingDecision.AUTO_FILL
    assert map_control(first_name).confidence == 0.99
    assert map_control(email).decision is MappingDecision.HUMAN_REQUIRED
    assert map_control(email).sensitivity is Sensitivity.SENSITIVE
    assert map_control(sponsorship).decision is MappingDecision.HUMAN_REQUIRED


def test_fill_plan_contains_values_only_for_policy_approved_verified_facts() -> None:
    first_evidence = uuid4()
    email_evidence = uuid4()
    profile = CandidateProfile(
        facts=[
            CandidateFact(
                canonical_path="identity.first_name",
                value="Synthetic",
                state=FactState.VERIFIED,
                evidence_ids=[first_evidence],
                sensitivity=Sensitivity.ORDINARY,
            ),
            CandidateFact(
                canonical_path="contact.email",
                value="synthetic@example.com",
                state=FactState.VERIFIED,
                evidence_ids=[email_evidence],
                sensitivity=Sensitivity.SENSITIVE,
            ),
        ]
    )
    form = ObservedForm(
        page_url="https://synthetic.careerflow.invalid/application",
        page_state_hash="abc12345",
        controls=[
            control(
                "first-name",
                "First name",
                Sensitivity.ORDINARY,
                required=True,
                autocomplete="given-name",
            ),
            control("email", "Email address", Sensitivity.SENSITIVE, required=True),
            control("unknown", "Favorite editor", Sensitivity.ORDINARY, required=True),
        ],
    )

    fills, mappings, blocked = plan_form_fill(form, profile)

    assert [(item.canonical_path, item.value) for item in fills] == [
        ("identity.first_name", "Synthetic")
    ]
    assert fills[0].evidence_ids == [first_evidence]
    assert len(mappings) == 3
    assert {item.control_id: item.decision for item in blocked} == {
        "email": MappingDecision.HUMAN_REQUIRED,
        "unknown": MappingDecision.UNSUPPORTED,
    }
