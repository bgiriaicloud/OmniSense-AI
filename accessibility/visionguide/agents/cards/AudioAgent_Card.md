# AudioAgent Card

Real-time analysis of environmental sounds to enhance safety and situational context.

## Overview
The `AudioAgent` processes environmental audio snippets to identify important sound events and provide safety guidance, acting as an additional layer of awareness beyond visual input.

## Capabilities
- **Sound Event Identification**: Detects and identifies critical sounds such as sirens, alarms, approaching vehicles, or shouting.
- **Urgency Assessment**: Categorizes sound events into safety levels (e.g., "Caution", "Danger", "Safe") to prioritize feedback.
- **Guidance Generation**: Provides actionable advice based on sounds (e.g., "I hear a siren, please move to the sidewalk").
- **Senior Mode Integration**: In Senior Mode, it offers intellectual observations or friendly small talk about the acoustic environment.

## Operating Constraints
- **Signal-to-Noise Ratio**: In extremely noisy environments (e.g., heavy construction), specific sound events may be harder to distinguish.
- **Audio Duration**: Analysis is performed on 4-second audio samples. Events occurring outside these windows may be missed.
- **Distance**: The accuracy of identifying sound sources depends on their distance and the microphone's sensitivity.

## Model
Uses `gemini-flash-latest` for efficient processing of audio data and natural language generation.
