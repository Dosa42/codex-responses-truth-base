# Multi-agent Reference

Multi-agent is documented separately from ordinary Responses execution and is beta in the pinned documentation snapshot.

Important transport distinction from the official guide:

- OpenAI SDK beta Responses examples pass `responses_multi_agent=v1` through the SDK `betas` argument.
- Raw HTTP and WebSocket clients pass `OpenAI-Beta: responses_multi_agent=v1` in request/connection headers.
- Hosted collaboration actions emitted as `multi_agent_call` are handled by OpenAI and must not be executed by the consuming application.
- Developer-defined `function_call` items still require the consuming application to execute the function and submit matching `function_call_output` items.

Authority: `upstream/docs/multi-agent.md` plus the pinned OpenAPI schema.
