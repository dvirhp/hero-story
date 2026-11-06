"""Text-free diagnostics survive engine recovery, but never enter public JSON."""

import json
from typing import Literal

import httpx
import pytest
from pydantic import ValidationError, model_validator

from storyforge.api.app import create_app
from storyforge.api.dependencies import Resources
from storyforge.domain.base import Contract
from storyforge.domain.diagnostics import ProviderDiagnostic
from storyforge.domain.output_validation import OutputValidationIssue
from storyforge.domain.story_v2 import StoryV2
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.orchestration.engine import StoryEngine
from storyforge.validation.output_diagnostics import validation_diagnostic, export_validation_diagnostics
from test_roy_final_forms import book, SETTINGS, LIMITS

PRIVATE = "private-child-name-prompt-key-url-response"


def test_error_projection_omits_input_message_context_and_arbitrary_keys():
    class Schema(Contract):
        pages: tuple[int, ...]
        choice: Literal[PRIVATE]
    try:
        Schema.model_validate_json(json.dumps({"pages": [PRIVATE], "choice": "wrong", PRIVATE: PRIVATE}))
    except ValidationError as error:
        diagnostic = validation_diagnostic(error)
    else:
        pytest.fail("Invalid witness unexpectedly passed")
    issues = [i.model_dump(mode="json") for i in diagnostic.validation_issues]
    assert issues[0]["path"] == ["pages", 0] and issues[0]["rule"] == "int_type"
    assert any(i["rule"] == "literal_error" for i in issues)
    assert any(i["path"] == ["unknown"] and i["rule"] == "extra_forbidden" for i in issues)
    assert PRIVATE not in json.dumps(issues)
    assert all(set(i) == {"code", "path", "rule", "observed_count", "minimum_count", "maximum_count"} for i in issues)


def test_arbitrary_validator_exception_context_is_not_copied():
    class Schema(Contract):
        title: str
        @model_validator(mode="after")
        def reject(self):
            raise ValueError(PRIVATE)
    with pytest.raises(ValidationError) as caught:
        Schema(title=PRIVATE)
    diagnostic = validation_diagnostic(caught.value)
    assert diagnostic.validation_issues[0].rule == "value_error"
    assert PRIVATE not in str(diagnostic.validation_issues)


def test_issue_list_is_bounded_and_extra_field_names_are_redacted():
    class Schema(Contract):
        title: str
    with pytest.raises(ValidationError) as caught:
        Schema.model_validate_json(json.dumps({f"{PRIVATE}-{i}": PRIVATE for i in range(40)}))
    diagnostic = validation_diagnostic(caught.value)
    assert len(diagnostic.validation_issues) == 8 and diagnostic.validation_issues_truncated
    assert PRIVATE not in str(diagnostic.validation_issues)


def test_diagnostics_have_no_production_json_or_serialization_schema_fields():
    issue = OutputValidationIssue(code="page_word_count", path=("pages", 22), observed_count=11,
                                   minimum_count=12, maximum_count=24)
    diagnostic = ProviderDiagnostic(category="invalid_output", validation_issues=(issue,))
    assert diagnostic.model_dump(mode="json") == {"category": "invalid_output", "upstream_http_status": None}
    assert set(ProviderDiagnostic.model_json_schema(mode="serialization")["properties"]) == {
        "category", "upstream_http_status"}
    forged = issue.model_copy(update={"path": (PRIVATE,)})
    with pytest.raises(ValidationError):
        ProviderDiagnostic(category="invalid_output", validation_issues=(forged,))




@pytest.mark.parametrize("mutation,code", [
    ("short", "page_count_mismatch"), ("declared", "declared_page_count"),
    ("order", "page_order"), ("duplicate", "duplicate_page_id"), ("direction", "direction_mismatch"),
    ("density", "page_word_count"), ("targets", "target_sequence_mismatch"),
    ("title", "title_mismatch"), ("units", "sentence_unit_count"), ("profile", "profile_mismatch"),
])
def test_schema_and_context_constraints_have_stable_safe_codes(run_async, profiles, book, mutation, code):
    req, _, plan, raw = book
    if mutation == "short":
        raw["pages"].pop(); raw["page_count"] -= 1
    elif mutation == "declared": raw["page_count"] -= 1
    elif mutation == "order": raw["pages"][0]["page_number"] = 99
    elif mutation == "duplicate": raw["pages"][1]["page_id"] = raw["pages"][0]["page_id"]
    elif mutation == "direction": raw["direction"] = "ltr"
    elif mutation == "density": raw["pages"][0]["sentence_units"] = [PRIVATE, "אור"]
    elif mutation == "targets": raw["pages"][0]["target_id"] = PRIVATE
    elif mutation == "title": raw["title"] = PRIVATE
    elif mutation == "units": raw["pages"][0]["sentence_units"] = [" ".join(raw["pages"][0]["sentence_units"])]
    else: raw["profile_version"] = PRIVATE
    bad = FakeStep(response_json=json.dumps(raw))
    provider = FakeProvider((plan, bad, bad))
    result = run_async(StoryEngine(provider, profiles, settings=SETTINGS, limits=LIMITS, contract_version="2").generate(req))
    assert result.status == "failure" and len(provider.calls) == 3 and not hasattr(result, "story")
    exported = export_validation_diagnostics(result.usage.attempts)
    assert len(exported) == 2 and exported[0]["validation_issues"][0]["code"] == code
    assert PRIVATE not in json.dumps(exported) + result.model_dump_json()


def test_json_parser_failure_is_distinguished_and_ledger_keeps_it(run_async, profiles, book):
    req, _, plan, _ = book
    bad = FakeStep(response_json='{"pages": ')
    result = run_async(StoryEngine(FakeProvider((plan, bad, bad)), profiles, settings=SETTINGS,
                                  limits=LIMITS, contract_version="2").generate(req))
    exported = export_validation_diagnostics(result.usage.attempts)
    assert exported[0]["validation_issues"][0]["rule"] == "json_invalid"
    assert "validation_issues" not in result.model_dump_json()


@pytest.mark.parametrize("path", ["/v1/stories/generate", "/v2/stories/generate"])
def test_http_errors_and_openapi_retain_existing_production_shape(run_async, profiles, path):
    provider = FakeProvider((FakeStep(response_json="{}"),) * 2)
    app = create_app(resources=Resources(profiles=profiles, provider=provider))
    payload = dict(language="en", display_name="private-child", age_months=0, theme="Night")
    if path.startswith("/v2"):
        payload.update(schema_version="2", page_count=1)
    async def perform():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await client.post(path, json=payload), await client.get("/openapi.json")
    response, schema = run_async(perform())
    assert response.status_code == 503 and response.json()["error"]["code"] == "BUDGET_EXCEEDED"
    assert "validation_issues" not in response.text + schema.text
    assert PRIVATE not in response.text and "private-child" not in response.text
    assert all(set(a["provider_diagnostic"]) == {"category", "upstream_http_status"}
               for a in response.json()["usage"]["attempts"])
