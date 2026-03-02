# AGENTS.md - pywebasto

This file defines instructions for AI coding agents working in this repository.
Follow these rules strictly.

## Scope

`pywebasto` is a Python client for Webasto heaters connected via:

- `https://my.webastoconnect.com`

The API is unofficial and reverse engineered.
There is no official Webasto API documentation available for this integration.

## No-Assumption Rule (Facts Only)

If required technical details are missing, the agent MUST:

- Locate the information inside the repository (docs, source, CI config, comments), or
- Explicitly request clarification before implementing a dependent solution

The agent must NOT:

- Invent API endpoints
- Invent protocol structures
- Guess authentication flows
- Introduce undocumented environment variables

If there is uncertainty, stop and request clarification.

## Critical Constraint: No Official API Docs

Because official API documentation does not exist, all protocol understanding must come from:

- Existing code in this repository
- Existing docs in this repository
- Real network captures from `my.webastoconnect.com`

Use the No-Assumption Rule for all unknown protocol details.

## Network Capture Workflow (Required for API Changes)

When changing login flow, commands, settings, parsing, or endpoint behavior:

1. Base changes on concrete capture evidence.
2. Document what was observed (endpoint, method, key fields, cookie usage).
3. Keep protocol notes updated in `docs/` (add/update a focused markdown file).
4. Mark assumptions explicitly and keep them minimal.

If a change is not verifiable from code or captures, do not implement it as fact.

## Security Constraints

The agent must NOT:

- Introduce telemetry without explicit approval
- Send user data to third-party services
- Add undocumented network endpoints
- Disable encryption for convenience
- Commit raw captures that include credentials, cookies, device IDs, GPS, or tokens
- Log secrets in plaintext
- Add unsanitized payload samples to docs/tests
- Print full headers when they contain session cookies

All cloud endpoints must be documented in `docs/`.

## Code Standards

- Follow existing project formatting and naming conventions.
- Do not introduce large refactors in the same change as functional modifications unless explicitly requested.
- Keep commits small and focused.
- Avoid introducing new dependencies unless justified.
- Use `ruff` as formatter/linter in this repository.

## Coding Rules

- Keep changes focused and minimal.
- Preserve public behavior unless change is explicitly requested.
- Reuse existing constants/enums/exceptions when possible.
- Use explicit error handling for HTTP failures and unauthorized states.
- Keep timeouts explicit for network calls.

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

## Git Workflow

Branch naming convention:

```
feature/<name>
fix/<name>
refactor/<name>
chore/<name>
```

Each PR must include:

- A clear description of changes
- Test strategy (automated or manual)
- Known limitations
- Any required configuration changes
- If the PR resolves an issue, include the text `Fixes #<issue-id>`

The agent must NOT merge a PR without explicit permission.

The agent must NOT use administrative merge overrides (for example `gh pr merge --admin`).

Before merging any PR, the agent MUST wait until all required CI/status checks are green/passing.

When a branch is merged it must also be deleted both local and remote, and changes merged to `master` must be pulled.

## When in Doubt

The agent must stop and request clarification regarding:

- Authentication flow
- API contract details
- CI expectations
- Required vs optional features

## Definition of Done

A change is considered complete when:

- All relevant tests pass locally and in CI
- New behavior is covered by tests (where feasible)
- Documentation is updated if configuration or API changes
- No secrets are committed
- Linting and formatting checks pass
- The implementation adheres strictly to the No-Assumption Rule
