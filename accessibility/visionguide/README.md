# OmniSense | AI Accessibility Agent

🌍 **OmniSense** is an AI-powered accessibility companion designed to empower users with visual or hearing impairments.

## Project Structure

```text
omnisense/
├── agents/             # Specialized AI agents (Vision, Audio, Base)
├── orchestrator/       # Agent Runtime for multimodal coordination
├── api/                # FastAPI backend
├── mobile/             # Glassmorphic mobile frontend
├── infra/              # Docker and Cloud Run deployment scripts
├── prompts/            # Externalized AI personality/instructions
├── scripts/            # Utility and test scripts
└── tests/              # Unit and integration tests
```

## Getting Started

1.  **Install Dependencies**: `pip install -r requirements.txt`
2.  **Configure API Key**: Add `GEMINI_API_KEY=your_key` to `.env`.
3.  **Run Locally**: `uvicorn api.main:app --reload`
4.  **Audio Feature**: Tap **Listen** on the mobile UI to analyze environmental sounds.

## Deployment

Run `bash infra/cloudrun_deploy.sh` to deploy directly to Google Cloud.
