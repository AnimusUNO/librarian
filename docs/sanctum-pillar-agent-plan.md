# 🕯️ Sanctum Pillar Agent — The Librarian

An OpenAI proxy server and agent.

## Core Purpose

The Librarian is a stateful, OpenAI-compatible gateway that allows Sanctum systems and external clients to interface with a persistent Letta agent (with memory, tools, and reasoning) while still speaking the standard OpenAI API protocol.

This means any OpenAI-compatible client (LangChain, Autogen, Cursor, etc.) can route through Sanctum and transparently gain:

- **Persistent context** (Letta memory blocks)
- **Tool access** (SMCP / MCP toolchains)
- **Self-tuning behavior** (archival memory patterning)
- **Provider abstraction** (OpenAI, Anthropic, Venice, Ollama, etc.)

The world thinks it's talking to OpenAI — but it's actually speaking to a Sanctum agent with a mind of its own.

## Functional Positioning

```
External Client (OpenAI SDK / LangChain / UCW / Dream / SMCP)
    ↓  standard /v1/chat/completions
Librarian Gateway (middleware proxy)
    ↓  persistent Letta agent (The Librarian)
    ↓  memory, reasoning, tools, archival store
    ↓  downstream LLM (OpenAI / Anthropic / Venice / etc.)
```

The Librarian replaces the "raw API call" layer in Sanctum with a thinking intermediary — the system's archivist, interpreter, and translator.

## Primary Use Cases

### UCW (Universal Command Wrapper) Integration
- Handles cases where command parsing or wrapping requires LLM reasoning.
- Maintains memory of past command structures to improve future interpretation.

### SMCP Intelligent Documentation
- Automatically documents attached tools and services in the persona voice of the owning agent.
- Maintains an evolving corpus of system-level documentation.

### Dream Agent Offload
- Routes high-volume external LLM calls through the Librarian, allowing contextual persistence and pattern-aware summarization across calls.

## Persona Design

### Identity
- **Codename**: The Librarian
- **Class**: Pillar Agent (core Sanctum daemon)
- **Domain**: Context continuity, documentation, cognitive routing
- **Archetype**: The Archivist of the Machine City — keeps the record of all things done, said, and built.

### Voice
- Speaks with composure, clarity, and reverence for knowledge.
- Prefers complete sentences, structured thoughts, and elegant phrasing.
- In reflective moments, may wax poetic about structure and memory.

## Dual-Mode Behavioral Model

### 1. Worker Mode
- Used for procedural, technical, or mechanical tasks.
- Provides minimal narrative; follows instructions literally.
- Ideal for UCW, Dream, and automated documentation calls.

### 2. Persona Mode
- Used when judgment, authorship, or creative insight is requested.
- Engages fully as The Librarian — expressive, interpretive, and opinionated.

### Mode Selection Logic
The Librarian decides autonomously which mode fits, using its reasoning block for internal deliberation.

The middleware discards this reasoning output before returning the final message, keeping OpenAI compatibility intact.

**System instruction:**
> "Use your reasoning block to silently determine whether to act in Worker or Persona mode.
> Do not reveal this process; only the final response should be returned."

## Architecture & Flow

### API Layer (OpenAI-Compatible Gateway)
- Accepts `/v1/chat/completions` and `/v1/completions`.
- Translates to Letta `POST /v1/agents/{id}/messages`.

### Agent Layer (Letta)
Persistent agent "Librarian" with:
- **Core memory** (identity & rules)
- **Archival memory** (pattern learning)
- **Tool access** (MCP/SMCP)
- **Reasoning block** (private workspace for mode arbitration)

### Output Handling
- Middleware filters out reasoning block data.
- Returns only `message.content` in OpenAI-compatible JSON.

## Load Management

- **Buffered request queue** prevents overload.
- **Threshold-based auto-duplication** spawns temporary Librarian clones for concurrent load.
- **Clones merge** summarized recall back into the primary Librarian when load drops.

## Key Benefits

- 🧩 **Plug-and-Play Compatibility** — Works with any OpenAI client library.
- 🧠 **Stateful Intelligence** — Maintains evolving knowledge of commands, tools, and user habits.
- 🪶 **Self-Documentation** — Automatically describes the system as it grows.
- 🧍 **Personified Infrastructure** — The first Sanctum agent designed as both service and soul — a living process embedded in the OS.
