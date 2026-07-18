# DECISION: FPT structured-output mode for the ragas judge (consumed by T05)

Date: 2026-07-18
FPT_CHAT_MODEL: `GLM-5.2` (a reasoning model — see `backend/app/config.py:22` for the known "thinking eats content" failure mode)
Versions: ragas 0.4.3, mlflow 3.14.0, instructor (bundled by ragas 0.4.3), langchain-openai (bundled), openai 1.59.6

## Probe matrix

| Probe | Mode | generate(ProbeAnswer) | Faithfulness score | Thinking disabled? | Notes |
|-------|------|------------------------|---------------------|---------------------|-------|
| A | `llm_factory` default | **fail** — `pydantic_core.ValidationError: Invalid JSON: EOF while parsing a value ... input_value=''` | not reached | no | Classic GLM-reasoning symptom: content field came back empty because the model spent its output budget "thinking" instead of answering. |
| A2 | `llm_factory` + `extra_body={"chat_template_kwargs":{"enable_thinking": False}}` | **pass** — `ProbeAnswer(verdict='yes', reasons=[...], confidence=0.95)` | **1.0** | yes | Both layers pass cleanly, twice (spike run 1 and the final clean re-run gave the same shape of result). |
| B | `llm_factory` + `mode=instructor.Mode.MD_JSON` | **fail** — `TypeError: instructor.process_response.handle_response_model() got multiple values for keyword argument 'mode'` | not reached | n/a | This looks like a ragas 0.4.3 / instructor incompatibility: `llm_factory` already threads a `mode` kwarg into instructor's `create()` internally, so passing `mode=` explicitly collides. Not usable as written; not needed since A2 passed. |
| C | `LangchainLLMWrapper(ChatOpenAI(...))` (legacy) | n/a (layer 1 skipped — wrapper only used via metrics) | **1.0** | no (not attempted — A2 already passed) | Confirmed as a working fallback if A2 ever regresses, but not the chosen path (ragas 0.4.x deprecation-wraps this class). |

## Decision

**Chosen mode: A2 — modern `ragas.llms.llm_factory(model, client=..., extra_body={"chat_template_kwargs": {"enable_thinking": False}})`.**

Plain `llm_factory` (probe A) fails outright on this FPT model because `GLM-5.2` is a reasoning model that returns empty `content` when it "thinks" instead of answering directly — the exact failure mode `llm_client._thinking_extra` already works around for the app's own chat/embed calls (`backend/app/services/llm_client.py:68-72`). Passing the same `extra_body` disable-thinking payload through to `llm_factory`'s `**kwargs` (which flow straight into the underlying `client.chat.completions.create(...)` call, confirmed by reading `ragas/llms/base.py`) fixes it completely: both the raw `generate()` structured-output call and a real `Faithfulness` metric score succeed, reproducibly, with score 1.0 on an obviously-faithful sample. This keeps T05 on ragas's supported, non-deprecated API (`llm_factory`) rather than falling back to `LangchainLLMWrapper`, which ragas 0.4.x explicitly deprecates. Probe B's failure is a ragas/instructor bug unrelated to FPT and moot since A2 already works.

**No escalation needed** — proceed to T05.

## Evidence transcript

Verbatim output from the final clean run (`cd backend && PYTHONPATH=. python eval/spikes/spike_fpt_structured_output.py`, exit code 0):

```
FPT_CHAT_MODEL='GLM-5.2'  FPT_BASE_URL='https://mkp-api.fptcloud.com'

============================================================
PROBE A: llm_factory default
============================================================
[layer 1] FAILED: 1 validation error for ProbeAnswer
  Invalid JSON: EOF while parsing a value at line 1 column 0 [type=json_invalid, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.10/v/json_invalid

============================================================
PROBE A2: llm_factory + disable-thinking (GLM variant)
============================================================
[layer 1] generate() -> ProbeAnswer(verdict='yes', reasons=['Phí thường niên là một loại phí liên quan trực tiếp đến việc duy trì và sử dụng thẻ tín dụng.', "Câu văn đề cập đến 'Phí thường niên của thẻ', đây là một khoản phí đặc trưng và phổ biến nhất của thẻ tín dụng do các ngân hàng phát hành thu hàng năm."], confidence=0.95)
[layer 2] Faithfulness score -> 1.0

>>> PROBE A2 PASSED BOTH LAYERS — stopping ladder.
```

Earlier exploratory run (before A2 was added to the script) also exercised probes B and C for completeness — kept here as evidence B is genuinely broken and C genuinely works, in case A2 ever needs to be revisited:

```
PROBE B: llm_factory MD_JSON
[layer 1] FAILED: instructor.process_response.handle_response_model() got multiple values for keyword argument 'mode'

PROBE C: LangchainLLMWrapper (legacy)
[layer 1] skipped (wrapper only used via metrics)
[layer 2] Faithfulness score -> 1.0
>>> PROBE C PASSED (layer 2) — stopping ladder.
```

## Implications for T05

The judge factory in `llm_client.py` must construct the ragas judge as:

```python
from ragas.llms import llm_factory as ragas_llm_factory

judge_llm = ragas_llm_factory(
    settings.eval_judge_model or settings.fpt_chat_model,
    client=make_openai_client(),  # new public factory in llm_client.py, mirrors _client()
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
```

- **`extra_body={"chat_template_kwargs": {"enable_thinking": False}}` is required**, not optional — this is the one load-bearing fact from this spike. Bake it into the factory unconditionally (it is harmless for non-GLM models that don't recognize the param — `llm_client._is_unsupported_param_error` already has fallback precedent for this in the app's own chat path, but the spike did not need a fallback here since the target model is GLM).
- Do **not** pass `mode=instructor.Mode.MD_JSON` to `llm_factory` — it currently crashes with a `TypeError` on ragas 0.4.3.
- Do **not** use `LangchainLLMWrapper`/legacy path for the default judge — it works but is deprecated on 0.4.x; keep it only as a documented emergency fallback in comments, not code, unless A2 regresses on a future ragas/instructor version bump.
- Embeddings: not probed here (per task's Out of scope — `llm_client.embed` already proves the FPT embeddings endpoint works); T05 wires `ragas.embeddings.OpenAIEmbeddings(client=..., model=...)` using the same client.
