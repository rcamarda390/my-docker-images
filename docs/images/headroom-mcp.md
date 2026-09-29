# Headroom / AWS Bedrock image

[Back to repository README](../../README.md) · [Image source](../../images/headroom-mcp/)

A significant project area is:

```text
images/headroom-mcp/
```

This image supports the Headroom → LiteLLM → AWS Bedrock path used in the work environment.

Verified runtime chain:

```text
Cline
  ↓
Bifrost
  ↓
Headroom
  ↓
LiteLLM
  ↓
AWS Bedrock GovCloud
```

The Headroom image has required Bedrock-specific dependencies in addition to the base proxy dependencies.

A prior build used:

```text
uv sync --frozen --extra proxy --no-dev --no-editable
```

The Bedrock-capable build needs the Bedrock dependency extra as well:

```text
uv sync --frozen --extra proxy --extra bedrock --no-dev --no-editable
```

The Bedrock extra supplies the AWS SDK dependencies required by the Headroom/LiteLLM backend rather than installing them manually with `pip`.

AWS credentials should continue to come from the host/runtime IAM environment.

### Offline-oriented environment settings

For an air-gap-oriented Headroom image, previous project work identified these settings as useful:

```text
LITELLM_LOCAL_MODEL_COST_MAP=True
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
HEADROOM_UPDATE_CHECK=off
```

Do **not** blindly set:

```text
HEADROOM_OFFLINE=1
```

when the container still needs to communicate with AWS Bedrock.

### Permanent patches

Compatibility fixes discovered through live-container testing should be folded back into:

```text
images/headroom-mcp/
```

rather than left only in the running container.

One area investigated was Headroom/LiteLLM OpenAI-compatible request handling, including SSL verification and translation between OpenAI-compatible token parameters and the Bedrock-facing implementation.

The repository already contains:

```text
patch-headroom-bedrock-openai.py
```

for image-build-time compatibility handling.
