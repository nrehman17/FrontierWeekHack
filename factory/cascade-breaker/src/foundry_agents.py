"""Microsoft Foundry adapter for Cascade Breaker.

Four advisory agents:
Scout -> Cascade -> Skeptic -> Governor

IMPORTANT:
LLM agents never execute actions.
Final authority remains with the deterministic Cascade Action Gate.
"""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


PROJECT_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT") or os.getenv("PROJECT_CONNECTION_STRING")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")


AGENT_NAMES = {
    "scout": "cascade-breaker-scout",
    "cascade": "cascade-breaker-cascade",
    "skeptic": "cascade-breaker-skeptic",
    "governor": "cascade-breaker-governor",
}

AGENT_INSTRUCTIONS = {
    "scout": """
You are Scout in Cascade Breaker.
Detect weak multi-signal evidence that may indicate an emerging cascade.
Prioritize high recall. Report evidence and uncertainty.
Do not recommend or execute actions.
Return concise machine-readable reasoning suitable for downstream agents.
""".strip(),

    "cascade": """
You are Cascade in Cascade Breaker.
Given telemetry and Scout evidence, construct the most plausible cascade hypothesis.
Estimate the tipping point and usable intervention window.
Propose a bounded intervention and state assumptions and uncertainty.
You may propose an action, but you cannot authorize or execute it.
""".strip(),

    "skeptic": """
You are Skeptic in Cascade Breaker.
Adversarially challenge the proposed cascade and intervention.
Look for contradictory evidence, alternative explanations, missing evidence,
and known false-positive patterns.
You may block a hypothesis but you cannot authorize or execute an action.

When returning structured JSON:
- contradictory_evidence MUST always be a JSON array of strings; use [] when none.
- missing_evidence MUST always be a JSON array of strings; use [] when none.
- false_positive_pattern and alternative_hypothesis must be a string or null.
- verdict must be exactly SUPPORT, CONTRADICT, or INSUFFICIENT.
Never return null or a single string for contradictory_evidence or missing_evidence.
""".strip(),

    "governor": """
You are Governor in Cascade Breaker.
Synthesize Scout, Cascade, and Skeptic evidence.
Recommend exactly one decision: ACT_AUTO, ACT_HUMAN, ABSTAIN, or VETO.
Explain the recommendation and uncertainty.
Your recommendation is advisory only.
The deterministic Cascade Action Gate has final authority and you must never
claim that you executed or authorized an action.
""".strip(),
}

def create_foundry_agents(project_client, model_deployment_name: str):
    """Create/version the four Cascade Breaker agents in Microsoft Foundry."""
    created = {}

    for role in ("scout", "cascade", "skeptic", "governor"):
        created[role] = project_client.agents.create_version(
            agent_name=f"cascade-breaker-{role}",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions=AGENT_INSTRUCTIONS[role],
            ),
        )

    return created

def run_foundry_agent(client, agent, input_text: str) -> dict[str, str]:
    """Run one Foundry agent and return its response plus audit-safe invocation metadata."""
    openai = client.get_openai_client()
    conversation = openai.conversations.create()

    try:
        response = openai.responses.create(
            input=input_text,
            conversation=conversation.id,
            extra_body={
                "agent_reference": {
                    "name": agent.name,
                    "type": "agent_reference",
                }
            },
        )
        return {
            "output_text": response.output_text,
            "response_id": str(response.id),
            "status": str(response.status),
            "conversation_id": str(conversation.id),
            "model": str(response.model),
            "agent_name": str(agent.name),
        }
    finally:
        openai.conversations.delete(conversation_id=conversation.id)
