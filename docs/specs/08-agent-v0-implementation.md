# Agent v0 Implementation Notes

## Purpose

Agent v0 implements the first deterministic agent loop for Echo Hollow. It does not call an LLM yet. The goal is to make the architecture compatible with modern agent patterns before model integration.

## Patterns Borrowed

### ReAct

The loop follows an observe -> retrieve -> act -> observe shape. The implementation stores concise public summaries of each step rather than hidden chain-of-thought.

Reference: https://arxiv.org/abs/2210.03629

### LangGraph

The world state remains explicit and durable. Short-term working context is assembled for a decision, while long-term game state stays in world memory, relationships, rumors, and event facts.

Reference: https://docs.langchain.com/oss/javascript/langgraph/overview

### OpenAI Agents SDK

The agent produces tool proposals. Application code owns tool execution, validation, state, and guardrails.

Reference: https://developers.openai.com/api/docs/guides/agents

### AutoGen / Multi-Agent Frameworks

The design keeps agents as isolated actors with explicit context transfer. Future NPC-to-NPC delegation can reuse the same tool proposal and validator boundary.

Reference: https://microsoft.github.io/autogen/stable//user-guide/agentchat-user-guide/tutorial/agents.html

## Current Loop

```text
triggering event
-> memory write
-> context packet assembly
-> deterministic AgentLoop decision
-> tool proposal
-> validator result
-> world mutation / event log
-> snapshot and WebSocket diff
```

## Context Packet

`AgentContext` contains:

- actor id
- objective
- triggering memory
- retrieved memories
- relationship state
- active world facts
- allowed tools
- public observations

This is the future prompt boundary. When an LLM is added, it should receive this structured context instead of raw world state.

## Tool Boundary

The current allowed tools are:

- `talk_to`
- `share_memory`
- `gossip`
- `investigate`

Every tool proposal must go through validator checks. The model or deterministic policy can propose tools, but only the world simulation applies accepted mutations.

## Why This Matters

The important achievement is not that Mira can lower trust in Tomo. The important achievement is that the chain is inspectable:

```text
player claim -> Mira memory -> retrieved context -> tool proposal -> validator -> relationship change -> event log
```

That gives the project a stable agent spine before adding LLM dialogue or richer planning.
