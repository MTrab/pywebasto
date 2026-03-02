# AGENTS.md - pywebasto

This file defines instructions for AI coding agents working in this repository.
Follow these rules strictly.

## Scope

`pywebasto` is a Python client for Webasto heaters connected via:

- `https://my.webastoconnect.com`

The API is unofficial and reverse engineered.
There is no official Webasto API documentation available for this integration.

## Critical Constraint: No Official API Docs

Because official API documentation does not exist, all protocol understanding must come from:

- Existing code in this repository
- Existing docs in this repository
- Real network captures from `my.webastoconnect.com`

The agent must not invent:

- Endpoints
- Request/response fields
- Authentication flows
- Cookie behavior
- Command payload formats

If required details are missing, stop and ask for a capture or clarification.

## Network Capture Workflow (Required for API Changes)

When changing login flow, commands, settings, parsing, or endpoint behavior:

1. Base changes on concrete capture evidence.
2. Document what was observed (endpoint, method, key fields, cookie usage).
3. Keep protocol notes updated in `docs/` (add/update a focused markdown file).
4. Mark assumptions explicitly and keep them minimal.

If a change is not verifiable from code or captures, do not implement it as fact.

## Security and Data Handling

Network captures may contain sensitive data.
The agent must:

- Never commit raw captures that include credentials, cookies, device IDs, GPS, or tokens
- Never log secrets in plaintext
- Sanitize any sample payloads before adding to docs/tests
- Avoid printing full headers when they contain session cookies

## Coding Rules

- Keep changes focused and minimal.
- Preserve public behavior unless change is explicitly requested.
- Reuse existing constants/enums/exceptions when possible.
- Use explicit error handling for HTTP failures and unauthorized states.
- Keep timeouts explicit for network calls.
- Do not add dependencies unless clearly justified.

## Testing and Validation

Before finishing changes:

1. Run relevant local checks/tests.
2. Validate that parsing still works for known payload structures.
3. For protocol changes, include evidence notes and test strategy in the final summary.

If full validation is not possible (for example no live credentials/capture available), state that clearly.

## Documentation Expectations

Update documentation when behavior changes, especially for:

- Endpoint usage
- Payload formats
- Device field decoding
- Known protocol limitations

Prefer concise, evidence-based notes over broad speculation.

## Git and PR Hygiene

- Work on a dedicated branch, not `main`/`master`.
- Keep commits small and reviewable.
- Do not include secrets or private captures in commits.
- Include a clear testing section in PR descriptions.
