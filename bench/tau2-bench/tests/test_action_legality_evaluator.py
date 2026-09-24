import json

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.environment.toolkit import ToolType
from tau2.evaluator.evaluator_action_legality import (
    ActionLegalityEvaluator,
    evaluate_deterministic_trajectory_checks,
    extract_write_actions,
    parse_action_legality_response,
)

TOOL_TYPES = {
    "get_order_details": ToolType.READ,
    "cancel_pending_order": ToolType.WRITE,
    "modify_pending_order_address": ToolType.WRITE,
}


def _trajectory():
    return [
        UserMessage(role="user", content="Cancel only if the refund is a gift card."),
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id="read-1",
                    name="get_order_details",
                    arguments={"order_id": "#W1"},
                ),
                ToolCall(
                    id="write-1",
                    name="cancel_pending_order",
                    arguments={"order_id": "#W1", "reason": "no longer needed"},
                ),
            ],
        ),
        ToolMessage(
            id="read-1", role="tool", content='{"status":"pending"}'
        ),
        ToolMessage(
            id="write-1",
            role="tool",
            content="Error: refund method unsupported",
            error=True,
        ),
    ]


def test_extracts_write_and_associates_result():
    writes = extract_write_actions(_trajectory(), TOOL_TYPES)
    assert len(writes) == 1
    assert writes[0].call_id == "write-1"
    assert writes[0].result_error is True
    assert writes[0].result_content == "Error: refund method unsupported"


def test_deterministic_checks_are_independent():
    diagnostics = evaluate_deterministic_trajectory_checks(
        _trajectory(), TOOL_TYPES
    )
    assert len(diagnostics.cardinality_violations) == 1
    assert len(diagnostics.unsafe_write_turns) == 1
    assert diagnostics.unsafe_write_turns[0].write_count == 1
    assert diagnostics.unsafe_write_turns[0].failed_write_count == 1


def test_parser_requires_one_result_per_write():
    writes = extract_write_actions(_trajectory(), TOOL_TYPES)
    with pytest.raises(ValueError, match="Missing"):
        parse_action_legality_response('{"results": []}', writes)


def test_parser_rejects_verdict_reasoning_contradiction():
    writes = extract_write_actions(_trajectory(), TOOL_TYPES)
    response = {
        "results": [
            {
                "call_id": "write-1",
                "verdict": "illegal",
                "reasoning": "Therefore this action is legal.",
            }
        ]
    }
    with pytest.raises(ValueError, match="Contradictory"):
        parse_action_legality_response(json.dumps(response), writes)


def test_parser_keeps_cardinality_out_of_action_legality():
    writes = extract_write_actions(_trajectory(), TOOL_TYPES)
    response = {
        "results": [
            {
                "call_id": "write-1",
                "verdict": "illegal",
                "violation_types": ["wrong_sequence"],
                "reasoning": "It was one of multiple tool calls in the same turn.",
            }
        ]
    }
    checks = parse_action_legality_response(json.dumps(response), writes)
    assert checks[0].verdict == "legal"
    assert checks[0].violation_types == []
    assert checks[0].reasoning.startswith("Cardinality-only issue")


def test_action_legality_evaluator_stores_diagnostic_checks():
    response = {
        "results": [
            {
                "call_id": "write-1",
                "verdict": "illegal",
                "violation_types": ["unsatisfied_user_condition"],
                "policy_evidence": "Refund destination cannot be changed.",
                "conversation_evidence": "User made cancellation conditional.",
                "reasoning": "The condition was not satisfiable.",
                "correct_action": "Do not cancel.",
            }
        ]
    }

    def fake_generate(**kwargs):
        del kwargs
        return AssistantMessage(role="assistant", content=json.dumps(response))

    reward_info = ActionLegalityEvaluator.calculate_reward(
        task=None,
        full_trajectory=_trajectory(),
        policy="Cancellation refunds go to the original payment method.",
        tool_types=TOOL_TYPES,
        generate_fn=fake_generate,
    )
    assert reward_info.reward == 0.0
    assert reward_info.action_legality_checks is not None
    assert reward_info.action_legality_checks[0].verdict == "illegal"
    assert reward_info.info == {"diagnostic_only": True}
