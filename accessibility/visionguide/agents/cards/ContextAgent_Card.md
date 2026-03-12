# ContextAgent Card

Intelligent memory service maintaining environmental and historical awareness for the OmniSense system.

## Overview
The `ContextAgent` acts as the "brain" of OmniSense, tracking the history of visual and auditory observations to provide persistent hazard tracking and contextual continuity.

## Capabilities
- **Environmental Memory**: Maintains a sliding window of recent observations to provide continuity between requests.
- **Persistent Hazard Tracking**: Identifies recurring hazards (e.g., "The car you saw previously is still behind you").
- **A2A Coordination**: Provides context to the `VisionAgent` and `AudioAgent` to refine their individual analyses.
- **Safety Prioritization**: Flags persistent themes to elevate the urgency level of current guidance.

## Operating Constraints
- **Memory Window**: Currently tracks a maximum of 5 recent observations. Historical context beyond this window is not maintained.
- **Pattern Matching**: Primarily identifies persistence based on simple keyword matching (e.g., 'car', 'bus') in hazard reports.
- **In-Memory only**: Context is maintained in-memory for the duration of the server session; it is not currently persisted across restarts.

## Model
Driven by rule-based logic and ADK-powered A2A (Agent-to-Agent) coordination.
