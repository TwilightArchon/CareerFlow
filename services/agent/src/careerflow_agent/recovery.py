from __future__ import annotations

from enum import StrEnum

from .contracts import ApplicationRun, Platform, WorkflowState


class RecoveryAction(StrEnum):
    IGNORE = "ignore"
    REAPPLY_PAUSE = "reapply_pause"
    REPLAY_NAVIGATION = "replay_navigation"
    REPLAY_SYNTHETIC_FORM = "replay_synthetic_form"
    PAUSE_FOR_REVIEW = "pause_for_review"
    MARK_OUTCOME_UNCERTAIN = "mark_outcome_uncertain"


TERMINAL_STATES = frozenset(
    {
        WorkflowState.SUBMITTED,
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
        WorkflowState.OUTCOME_UNCERTAIN,
    }
)

SYNTHETIC_REPLAY_STATES = frozenset(
    {
        WorkflowState.OPENING_APPLICATION,
        WorkflowState.FILLING,
        WorkflowState.VALIDATING,
        WorkflowState.AWAITING_HUMAN,
    }
)

REAL_NAVIGATION_REPLAY_STATES = frozenset(
    {
        WorkflowState.OPENING_APPLICATION,
        WorkflowState.FILLING,
    }
)

BROWSER_SIDE_EFFECT_STATES = frozenset(
    {
        WorkflowState.AUTHENTICATING,
        WorkflowState.REGISTERING,
        WorkflowState.VERIFYING_EMAIL,
        WorkflowState.READY_TO_SUBMIT,
    }
)


def classify_recovery(run: ApplicationRun) -> RecoveryAction:
    """Choose a recovery action without replaying an ambiguous external side effect."""

    if run.latest_outcome is not None or run.state in TERMINAL_STATES:
        return RecoveryAction.IGNORE
    if run.state is WorkflowState.PAUSED:
        return RecoveryAction.REAPPLY_PAUSE
    if run.state is WorkflowState.SUBMITTING:
        return RecoveryAction.MARK_OUTCOME_UNCERTAIN
    if run.platform is Platform.SYNTHETIC and run.state in SYNTHETIC_REPLAY_STATES:
        return RecoveryAction.REPLAY_SYNTHETIC_FORM
    if run.state in REAL_NAVIGATION_REPLAY_STATES:
        return RecoveryAction.REPLAY_NAVIGATION
    if run.state in BROWSER_SIDE_EFFECT_STATES:
        return RecoveryAction.PAUSE_FOR_REVIEW
    return RecoveryAction.IGNORE
