"""Synthetic FakeProvider execution and mocked durable hooks; no database/live calls."""
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from uuid import UUID, uuid4
import pytest
from storyforge.domain.generation import GenerationError
from storyforge.domain.diagnostics import ProviderDiagnostic
from storyforge.llm.protocol import ProviderFailure
from storyforge.llm.fake import FakeProvider, FakeStep
from storyforge.llm.fixtures_v2 import fixture_steps_v2
from storyforge.orchestration.engine import StoryEngine
from storyforge.orchestration.synchronous import (
    AuthorizationDecision, SendAuthorization, ExecutionBoundaryStopped, FrozenExecutionInvalid,
    canonical_digest, cost_nanos,
)
from test_v2_execution import SETTINGS, LIMITS, request, brief

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
OPERATION = UUID("11111111-1111-4111-8111-111111111111")


class Journal:
    """TEST-ONLY committed-hook simulation, not production durable uniqueness."""
    def __init__(self):
        self.proposals, self.outcomes, self.events = [], [], []
        self.slots = set()
        self.lock = asyncio.Lock()
    async def authorize_attempt(self, p):
        async with self.lock:
            disposition = "REPLAY" if (p.operation_id, p.attempt_number) in self.slots else "NEW"
            self.slots.add((p.operation_id, p.attempt_number))
            self.proposals.append(p)
            self.events.append(("authorize", p.attempt_number))
            semantic = p.request.model_dump(mode="json", exclude={"remaining_seconds"})
            digest = hmac.new(b"synthetic-test-only-key" * 2,
                json.dumps(semantic, sort_keys=True).encode(), hashlib.sha256).hexdigest()
            return SendAuthorization(AuthorizationDecision(operation_id=p.operation_id,
                request_id=p.request_id, attempt_id=p.attempt_id, attempt_number=p.attempt_number,
                stage=p.stage, manifest_digest=p.manifest_digest, payload_digest=digest,
                expires_at=p.execution_expires_at, disposition=disposition))
    async def record_outcome(self, o):
        self.outcomes.append(o)
        self.events.append(("outcome", o.attempt_number))


def make(profiles, req=None, steps=None, **kwargs):
    b = brief(req or request(pages=2))
    provider = FakeProvider(steps if steps is not None else fixture_steps_v2(b))
    e = StoryEngine(provider, profiles, settings=SETTINGS, limits=LIMITS, contract_version="2",
        utc_clock=lambda: NOW, **kwargs)
    return e, provider, b


def execute(e, b, journal, **kwargs):
    return e.generate_frozen(b, operation_id=kwargs.pop("operation_id", OPERATION),
        request_id="issued-request", manifest=kwargs.pop("manifest", e.freeze_manifest()),
        execution_expires_at=kwargs.pop("execution_expires_at", NOW + timedelta(seconds=80)),
        hooks=journal, cancelled=kwargs.pop("cancelled", lambda: False), **kwargs)


@pytest.mark.parametrize("language,pages", [("en", 2), ("he", 27)])
def test_acceptance_frozen_identity_hooks_before_send(profiles, run_async, language, pages):
    e, provider, b = make(profiles, request(language=language, age=36, pages=pages))
    journal = Journal()
    original = provider.generate
    async def checked(req, schema):
        assert journal.events[-1][0] == "authorize"
        journal.events.append(("send", len(provider.calls) + 1))
        return await original(req, schema)
    provider.generate = checked
    # Normalizer must not be invoked, including for a changed current profile resolver.
    object.__setattr__(e.contracts, "normalize", lambda _: pytest.fail("re-normalized frozen brief"))
    result = run_async(execute(e, b, journal))
    assert result.status == "success" and result.request_id == "issued-request"
    assert result.resolved_constraints == b.constraints
    assert result.quality.check_version == "quality-v2+book-v2-1"
    assert [p.page_number for p in result.story.pages] == list(range(1, pages + 1))
    assert journal.events == [("authorize", 1), ("send", 1), ("outcome", 1),
                              ("authorize", 2), ("send", 2), ("outcome", 2)]
    assert all(p.operation_id == OPERATION and p.request_id == "issued-request" for p in journal.proposals)
    assert all("request" not in p.model_dump() for p in journal.proposals)
    assert all(b.request.display_name not in repr(p) for p in journal.proposals)
    assert [p.mandatory_future_slots for p in journal.proposals] == [1, 0]
    assert journal.proposals[1].request.prompt_version == "writer-v2-3"


def test_manifest_mismatch_and_forged_brief_zero_calls(profiles, run_async):
    e, provider, b = make(profiles)
    changed = e.freeze_manifest().model_copy(update={"writer_prompt_version": "unsupported"})
    for candidate, manifest in [(b, changed), (b.model_copy(update={"request": {}}), e.freeze_manifest())]:
        with pytest.raises(FrozenExecutionInvalid): run_async(execute(e, candidate, Journal(), manifest=manifest))
    assert not provider.calls


def test_schema_repair_waits_for_recorded_outcome_and_keeps_details(profiles, run_async):
    _, _, b = make(profiles)
    e, provider, _ = make(profiles, steps=(FakeStep(response_json="{}"),) + fixture_steps_v2(b))
    journal = Journal()
    result = run_async(execute(e, b, journal))
    assert result.status == "success" and len(provider.calls) == 3
    assert journal.events == [("authorize", 1), ("outcome", 1), ("authorize", 2),
                              ("outcome", 2), ("authorize", 3), ("outcome", 3)]
    assert journal.outcomes[0].validation_issues
    assert "validation_issues" not in result.model_dump_json()


def test_known_rejection_never_contains_story(profiles, run_async):
    error = GenerationError(code="PROVIDER_REFUSED", stage="planner", retryable=False, message="synthetic")
    e, provider, b = make(profiles, steps=(FakeStep(error=error),))
    journal = Journal()
    result = run_async(execute(e, b, journal))
    assert result.status == "failure" and result.error.code == "PROVIDER_REFUSED"
    assert result.stop_reason == "provider_failure"
    assert "story" not in result.model_dump() and len(provider.calls) == 1
    assert len(journal.outcomes) == 1 and journal.outcomes[0].state == "RECORDED"


@pytest.mark.parametrize("failure", ["authorize", "record", "replay", "expired", "mismatch"])
def test_hook_uncertainty_never_resends(profiles, run_async, failure):
    class Broken(Journal):
        async def authorize_attempt(self, p):
            if failure == "authorize": raise RuntimeError("private-api-key-canary")
            grant = await super().authorize_attempt(p)
            if failure in {"replay", "expired", "mismatch"}:
                changes = {"disposition": "REPLAY"} if failure == "replay" else (
                    {"expires_at": NOW} if failure == "expired" else {"operation_id": uuid4()})
                return SendAuthorization(grant.decision.model_copy(update=changes))
            return grant
        async def record_outcome(self, o):
            if failure == "record": raise RuntimeError("private-api-key-canary")
            await super().record_outcome(o)
    e, provider, b = make(profiles)
    with pytest.raises(ExecutionBoundaryStopped) as error:
        run_async(execute(e, b, Broken()))
    assert error.value.reason == ("STORAGE_UNAVAILABLE" if failure == "record" else "AUTHORIZATION_UNCERTAIN")
    assert len(provider.calls) == (1 if failure == "record" else 0)
    assert "private-api-key-canary" not in str(error.value)


@pytest.mark.parametrize("kind", ["timeout", "connection", "adapter-timeout"])
def test_unknown_send_retains_reservations_and_no_retry(profiles, run_async, kind):
    e, provider, b = make(profiles)
    if kind == "adapter-timeout":
        provider = FakeProvider((FakeStep(error=GenerationError(code="DEADLINE_EXCEEDED",
            stage="planner", retryable=True, message="synthetic")),))
        e.provider = provider
    else:
        async def broken(req, schema):
            if kind == "timeout": raise TimeoutError("private")
            raise ConnectionError("private")
        provider.generate = broken
    journal = Journal()
    with pytest.raises(ExecutionBoundaryStopped, match="^OUTCOME_UNCERTAIN$") as error:
        run_async(execute(e, b, journal))
    assert len(journal.proposals) == len(journal.outcomes) == 1
    assert journal.outcomes[0].state == "UNKNOWN"
    assert error.value.safe_usage.has_unknown_usage
    assert error.value.operation_id == OPERATION and error.value.attempt_id is not None


def test_duplicate_concurrent_runs_backend_single_slot_authority(profiles, run_async):
    async def run():
        e, provider, b = make(profiles)
        journal = Journal()
        result = await asyncio.gather(execute(e, b, journal), execute(e, b, journal), return_exceptions=True)
        assert sum(getattr(r, "status", None) == "success" for r in result) == 1
        assert sum(isinstance(r, ExecutionBoundaryStopped) for r in result) == 1
        assert len(provider.calls) == 2
    run_async(run())


def test_same_grant_cannot_be_consumed_twice(profiles, run_async):
    e, _, b = make(profiles)
    journal = Journal()
    run_async(execute(e, b, journal))
    # Grant consumption tested directly with an actual proposal.
    grant = run_async(Journal().authorize_attempt(journal.proposals[0]))
    assert grant.consume() is True and grant.consume() is False


@pytest.mark.parametrize("point", ["before", "authorize", "record", "provider", "retry_wait"])
def test_cancel_stops_future_sends(profiles, run_async, point):
    async def run():
        flag = [point == "before"]
        class Cancelling(Journal):
            async def authorize_attempt(self, p):
                result = await super().authorize_attempt(p)
                if point == "authorize": flag[0] = True
                return result
            async def record_outcome(self, o):
                await super().record_outcome(o)
                if point == "record": flag[0] = True
        e, provider, b = make(profiles)
        if point == "provider":
            async def cancel(req, schema): raise asyncio.CancelledError()
            provider.generate = cancel
        if point == "retry_wait":
            original = provider.generate
            async def transient(req, schema):
                return ProviderFailure(provider="fake", model=req.model, usage={"source": "unknown"}, latency_seconds=0.,
                    error=GenerationError(code="PROVIDER_UNAVAILABLE", stage="planner", retryable=True, message="safe"),
                    provider_diagnostic=ProviderDiagnostic(category="server_error", upstream_http_status=503))
            provider.generate = transient
            async def sleep(delay): flag[0] = True
            e.sleep = sleep
        journal = Cancelling()
        with pytest.raises(ExecutionBoundaryStopped, match="^CANCELLED$"):
            await execute(e, b, journal, cancelled=lambda: flag[0])
        assert len(journal.proposals) <= 1
    run_async(run())


def test_canonical_digest_and_nanounit_vectors():
    assert canonical_digest({"a": 1}) == "015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862"
    assert cost_nanos(0.0000000001) == 1
    assert cost_nanos(0.075) == 75000000
    assert cost_nanos(0.) == 0


@pytest.mark.parametrize("point", ["authorize", "provider", "record"])
def test_real_task_cancellation_does_not_spawn_recorder_or_next_send(profiles, run_async, point):
    async def run():
        entered = asyncio.Event()
        class Waiting(Journal):
            async def authorize_attempt(self, p):
                result = await super().authorize_attempt(p)
                if point == "authorize":
                    entered.set()
                    await asyncio.Event().wait()
                return result
            async def record_outcome(self, o):
                if point == "record":
                    entered.set()
                    await asyncio.Event().wait()
                await super().record_outcome(o)
        e, provider, b = make(profiles)
        if point == "provider":
            async def waiting(req, schema):
                entered.set()
                await asyncio.Event().wait()
            provider.generate = waiting
        journal = Waiting()
        task = asyncio.create_task(execute(e, b, journal))
        await asyncio.wait_for(entered.wait(), timeout=3)
        task.cancel()
        with pytest.raises(ExecutionBoundaryStopped) as stopped: await task
        assert stopped.value.reason == "CANCELLED" and len(journal.proposals) == 1
        assert len(stopped.value.safe_usage.attempts) == 1
    run_async(run())


def test_expired_and_capacity_rejected_before_authorization(profiles, run_async):
    e, provider, b = make(profiles)
    journal = Journal()
    expired = run_async(execute(e, b, journal, execution_expires_at=NOW))
    assert expired.status == "failure" and expired.error.code == "DEADLINE_EXCEEDED"
    e.limits = e.limits.model_copy(update={"max_total_tokens": 1})
    rejected = run_async(execute(e, b, journal))
    assert rejected.status == "failure" and rejected.error.code == "BUDGET_EXCEEDED"
    assert not provider.calls and not journal.proposals


def test_quality_rejection_never_returns_draft(profiles, run_async):
    from storyforge.domain.generation import QualityReport, QualityIssue
    import storyforge.orchestration.engine as module
    e, provider, b = make(profiles)
    e.settings = e.settings.model_copy(update={"max_quality_rewrites": 0})
    original = module.assess_story
    def rejected(*args, **kwargs):
        return QualityReport(passed=False, check_version="quality-v2+book-v2-1", rubric_version="language-v1",
            issues=(QualityIssue(code="synthetic_gate_rejection", severity="terminal", guidance="Synthetic fixture"),))
    # Isolated gate injection tests the failure boundary, not new production quality criteria.
    try:
        module.assess_story = rejected
        result = run_async(execute(e, b, Journal()))
    finally:
        module.assess_story = original
    assert result.status == "failure" and result.error.code == "QUALITY_REJECTED"
    assert "story" not in result.model_dump() and len(provider.calls) == 2


def test_golden_manifest_result_and_unknown_usage_vectors(profiles):
    from pathlib import Path
    from storyforge.domain.generation import GenerationFailure, UsageSummary
    from storyforge.domain.generation_v2 import GenerationSuccessV2
    from storyforge.orchestration.synchronous import FrozenEngineManifestV1
    value = json.loads((Path(__file__).parent / "fixtures/synchronous_execution_v1.json").read_text(encoding="utf-8"))
    manifest = FrozenEngineManifestV1.model_validate_json(json.dumps(value["manifest"]))
    assert manifest.digest() == value["manifest_digest"] == make(profiles)[0].freeze_manifest().digest()
    accepted = GenerationSuccessV2.model_validate_json(json.dumps(value["accepted"]))
    rejected = GenerationFailure.model_validate_json(json.dumps(value["rejected"]))
    unknown = UsageSummary.model_validate_json(json.dumps(value["uncertain"]["safe_usage"]))
    assert accepted.quality.check_version == "quality-v2+book-v2-1"
    assert accepted.model_dump(mode="json") == value["accepted"]
    assert rejected.model_dump(mode="json") == value["rejected"]
    assert unknown.has_unknown_usage and unknown.has_unknown_cost


def test_unexpected_accounting_failure_cannot_be_known_terminal_success(profiles, run_async):
    e, provider, b = make(profiles)
    def broken(*args, **kwargs): raise ValueError("private-accounting-canary")
    e._complete_attempt = broken
    journal = Journal()
    with pytest.raises(ExecutionBoundaryStopped) as stopped:
        run_async(execute(e, b, journal))
    assert stopped.value.reason == "OUTCOME_UNCERTAIN"
    assert len(provider.calls) == 1 and not journal.outcomes
    assert "private-accounting-canary" not in str(stopped.value)


def test_configuration_drift_during_authorization_never_sends(profiles, run_async):
    e, provider, b = make(profiles)
    class Drifting(Journal):
        async def authorize_attempt(self, p):
            grant = await super().authorize_attempt(p)
            e.settings = e.settings.model_copy(update={"writer_output_tokens": e.settings.writer_output_tokens+1})
            return grant
    with pytest.raises(ExecutionBoundaryStopped) as stopped:
        run_async(execute(e, b, Drifting()))
    assert stopped.value.reason == "AUTHORIZATION_UNCERTAIN" and not provider.calls
