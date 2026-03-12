# VisionAgent Card

Detailed analysis of the camera input to provide safety and situational awareness for the visually impaired.

## Overview
The `VisionAgent` is the primary sensory component of OmniSense. It processes image data from the user's camera to describe the environment, identify hazards, and assist with navigation.

## Capabilities
- **Scene Description**: Provides high-fidelity descriptions of the user's immediate surroundings.
- **Hazard Detection**: Identifies potential obstacles, barriers, or dangerous situations (e.g., "fast-moving car", "uneven pavement").
- **Navigation Assistance**: Suggests safe paths and identifies landmarks.
- **Multilingual Support**: Can provide feedback in English, French, Hindi, and Odia.
- **Senior Mode**: Adjusts descriptions to be more conversational, warm, and detailed.

## Operating Constraints
- **Lighting**: Performance depends on adequate environmental lighting. In low-light conditions, hazard detection accuracy may decrease.
- **Motion Blur**: Rapid camera movement may result in blurred images, affecting analysis quality.
- **Occlusion**: Objects or hazards occluded from the camera's view cannot be detected.

## Model
Uses `gemini-flash-latest` for low-latency, high-accuracy multimodal analysis.
