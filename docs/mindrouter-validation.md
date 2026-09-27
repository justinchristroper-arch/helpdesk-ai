# MindRouter live validation — 2026-09-28

Exactly two external synthesis requests were made through the backend chat endpoint with bundled synthetic HelpDesk AI facts. FastEmbed and pgvector supplied evidence first. Both returned HTTP 200 from MindRouter using requested model `deepseek/deepseek-flash`; the response reported model `deepseek-flash`. Both responses reached the configured 300 output token limit but did not pass the strict fact-ID response validation. The application therefore returned its deterministic, source-backed answer. The reason the model output failed validation was not captured; the 300-token limit is a plausible cause, not a proven one. The provider-generated answer path is still unverified in a live run. No further live requests were made.

After these calls, the system prompt was shortened and complete, validated JSON is accepted even when the provider reports a length stop. These changes passed mocked tests but were not retested against MindRouter because the request was for exactly two real validations.

## Test 1 — two sources

Question: “My MFA is broken while I'm working remotely. What should I do?”

- MindRouter called: yes; external calls after this test: **1**.
- HTTP: **200 success**; synthesis state: `invalid_response`, so deterministic fallback was used.
- Requested model: `deepseek/deepseek-flash`; returned model: `deepseek-flash`; answer stored with local FastEmbed model `BAAI/bge-small-en-v1.5` because fallback produced it.
- Provider usage: **331 input tokens, 300 output tokens**.
- Citations: `[1]` mfa-reset-guide, “MFA stops working”; `[2]` remote-work-checklist, “Before remote work”. Both map to active PostgreSQL document chunks, and each cited fact occurs in its chunk.

Answer:

> Based on the current IT knowledge base:
>
> MFA stops working
> 1. Check that your phone has network access and automatic time enabled. [1]
> 2. If your authenticator is unavailable or your phone is lost, contact IT support and request an MFA reset. [1]
> 3. Support verifies identity through the registered employee recovery process before resetting enrollment. [1]
> 4. Do not approve unexpected sign-in prompts. [1]
>
> Before remote work
> 1. Use an approved managed laptop, install pending company updates, confirm MFA access, and test the VPN when internal services require it. [2]
> 2. Keep the service desk contact details accessible. [2]
> 3. Store work files only in approved company storage. [2]

## Test 2 — complex paraphrase

Question: “The laptop assigned to me has stopped working safely while I am traveling; how should I report the damage and arrange help from IT?”

- MindRouter called: yes; external calls after this test: **2 total**.
- HTTP: **200 success**; synthesis state: `invalid_response`, so deterministic fallback was used.
- Requested model: `deepseek/deepseek-flash`; returned model: `deepseek-flash`; answer stored with local FastEmbed model `BAAI/bge-small-en-v1.5` because fallback produced it.
- Provider usage: **256 input tokens, 300 output tokens**.
- Citation: `[1]` laptop-damage-procedure, “Immediate action”. It maps to an active PostgreSQL chunk, and every cited fact occurs in that chunk.

Answer:

> Here's the documented guidance:
>
> Immediate action
> 1. Stop using a damaged company laptop. [1]
> 2. For liquid spills or visible electrical damage, disconnect power if safe and do not switch the device back on. [1]
> 3. Report the incident to IT support with the asset tag, description, and photos if safe to obtain. [1]
> 4. Do not attempt repairs yourself. [1]

## Evidence and limits

The validator counted calls to the configured MindRouter chat-completions endpoint in the API process and observed **two total**. It checked each stored citation against the current `MessageSource`, `Chunk` and `Document` rows, including matching chunk IDs, document IDs, excerpts and quoted fact text. Usage came from the provider response. The key was not printed, sent to the browser, or copied into the image. The fact-ID selector's successful live behavior, hosted behavior and quality on unseen queries remain unverified.

[MindRouter chat API](https://mindrouter.io/en/docs/chat) documents the OpenAI-compatible endpoint and JSON response format; [model catalog](https://mindrouter.io/en/docs/models) lists the requested DeepSeek Flash model.
