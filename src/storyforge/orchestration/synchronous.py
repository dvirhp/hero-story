"""Engine-owned synchronous ports. Backend supplies durable authority, never a worker.

No implementation here stores input, authorizes a paid call, or selects credentials.
"""
from collections.abc import Callable
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from threading import Lock
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import ConfigDict, Field
from storyforge.config import AppSettings
from storyforge.domain.base import Contract, Label, NonNegativeInt, PositiveInt
from storyforge.domain.generation import AttemptRecord, UsageSummary
from storyforge.domain.output_validation import OutputValidationIssue
from storyforge.domain.story_v2 import NormalizedBriefV2
from storyforge.llm.configuration import ModelCapabilities
from storyforge.llm.protocol import LLMRequest
from storyforge.orchestration.budget import BudgetLimits, FakePricing, ModelPricing
from storyforge.quality.rules import QualityRules
from storyforge.validation.page_policy import PagePolicy


class PortContract(Contract):
    model_config = ConfigDict(revalidate_instances="always", hide_input_in_errors=True)


def canonical_digest(value: object) -> str:
    """Non-content config/schema digest; NOT a substitute for keyed child-input HMAC."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def cost_nanos(value: float) -> int:
    return int((Decimal(str(value)) * Decimal(1_000_000_000)).to_integral_value(rounding=ROUND_CEILING))


class FrozenEngineManifestV1(PortContract):
    schema_version: Literal["sync-engine-manifest-v1"] = "sync-engine-manifest-v1"
    engine_build: Literal["sync-engine-v1"] = "sync-engine-v1"
    contract_version: Literal["2"] = "2"
    normalization_version: Literal["normalize-v2-frozen-v1"] = "normalize-v2-frozen-v1"
    profile_version: Label
    planner_prompt_version: Label
    writer_prompt_version: Label
    plan_schema_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    story_schema_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    token_bound_algorithm: Label
    settings: AppSettings
    limits: BudgetLimits
    rules: QualityRules
    page_policy: PagePolicy
    planner_pricing: FakePricing | ModelPricing
    writer_pricing: FakePricing | ModelPricing
    planner_capabilities: ModelCapabilities | None
    writer_capabilities: ModelCapabilities | None

    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class AttemptProposal(PortContract):
    operation_id: UUID
    request_id: Label
    attempt_id: UUID
    authorization_nonce: UUID
    attempt_number: Annotated[int, Field(ge=1, le=3)]
    stage: Literal["planner", "writer"]
    provider: Label
    manifest_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    schema_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    request: LLMRequest = Field(repr=False, exclude=True)
    input_token_bound: PositiveInt
    maximum_output_tokens: PositiveInt
    reserved_tokens: PositiveInt
    reserved_cost_nanos: NonNegativeInt
    mandatory_future_slots: NonNegativeInt
    mandatory_future_tokens: NonNegativeInt
    mandatory_future_cost_nanos: NonNegativeInt
    execution_expires_at: datetime


class AuthorizationDecision(PortContract):
    operation_id: UUID
    request_id: Label
    attempt_id: UUID
    attempt_number: Annotated[int, Field(ge=1, le=3)]
    stage: Literal["planner", "writer"]
    manifest_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    payload_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    expires_at: datetime
    disposition: Literal["NEW", "REPLAY"]


@dataclass(frozen=True, repr=False)
class SendAuthorization:
    """Local non-serializable one-use receipt. NEW must originate in committed backend CAS.

    Distinct forged NEW receipts cannot be prevented by an engine; durable uniqueness
    is the mandatory backend hook's responsibility, across processes and HTTP retries.
    """
    decision: AuthorizationDecision
    _used: bool = field(default=False, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False, compare=False)

    def consume(self) -> bool:
        with self._lock:
            if self._used or self.decision.disposition != "NEW":
                return False
            object.__setattr__(self, "_used", True)
            return True


class AttemptOutcome(PortContract):
    operation_id: UUID
    request_id: Label
    attempt_id: UUID
    attempt_number: Annotated[int, Field(ge=1, le=3)]
    state: Literal["RECORDED", "UNKNOWN"]
    record: AttemptRecord
    # Explicit internal hook data; provider result JSON continues excluding these details.
    validation_issues: Annotated[tuple[OutputValidationIssue, ...], Field(max_length=8)] = ()
    validation_issues_truncated: bool = False


class SynchronousExecutionHooks(Protocol):
    async def authorize_attempt(self, proposal: AttemptProposal) -> SendAuthorization: ...
    async def record_outcome(self, outcome: AttemptOutcome) -> None: ...


class FrozenExecutionInvalid(ValueError):
    def __init__(self): super().__init__("FROZEN_EXECUTION_INVALID")


class ExecutionBoundaryStopped(Exception):
    def __init__(self, reason: Literal["AUTHORIZATION_UNCERTAIN", "OUTCOME_UNCERTAIN", "STORAGE_UNAVAILABLE", "CANCELLED"],
                 operation_id: UUID, request_id: str, attempt_id: UUID | None, safe_usage: UsageSummary):
        self.reason, self.operation_id, self.request_id = reason, operation_id, request_id
        self.attempt_id, self.safe_usage = attempt_id, safe_usage
        super().__init__(reason)


@dataclass(repr=False)
class FrozenExecution:
    brief: NormalizedBriefV2
    operation_id: UUID
    request_id: str
    manifest: FrozenEngineManifestV1
    execution_expires_at: datetime
    hooks: SynchronousExecutionHooks
    cancelled: Callable[[], bool]
    utc_clock: Callable[[], datetime]
    current_attempt: UUID | None = None
    acknowledged_slots: int = 0

    def stop(self, reason, run):
        return ExecutionBoundaryStopped(reason, self.operation_id, self.request_id, self.current_attempt, run.usage())

    def remaining(self) -> float:
        now = self.utc_clock()
        if now.utcoffset() is None:
            raise FrozenExecutionInvalid()
        return max(0.0, (self.execution_expires_at - now.astimezone(timezone.utc)).total_seconds())

    def check_cancelled(self, run):
        if self.cancelled():
            raise self.stop("CANCELLED", run)

    async def authorize(self, proposal, run):
        self.current_attempt = proposal.attempt_id
        try:
            grant = await self.hooks.authorize_attempt(proposal)
            if not isinstance(grant, SendAuthorization): raise ValueError()
            d = AuthorizationDecision.model_validate_json(grant.decision.model_dump_json())
            if (d.operation_id, d.request_id, d.attempt_id, d.attempt_number, d.stage, d.manifest_digest) != (
                    proposal.operation_id, proposal.request_id, proposal.attempt_id,
                    proposal.attempt_number, proposal.stage, proposal.manifest_digest): raise ValueError()
            if d.expires_at.utcoffset() is None or d.expires_at > self.execution_expires_at: raise ValueError()
            self.check_cancelled(run)
            if self.remaining() <= 0 or d.expires_at <= self.utc_clock() or not grant.consume(): raise ValueError()
        except ExecutionBoundaryStopped:
            raise
        except asyncio.CancelledError:
            raise self.stop("CANCELLED", run) from None
        except Exception:
            raise self.stop("AUTHORIZATION_UNCERTAIN", run) from None

    async def record(self, run, *, unknown=False):
        record = run.attempts[-1]
        diag = record.provider_diagnostic
        outcome = AttemptOutcome(operation_id=self.operation_id, request_id=self.request_id,
            attempt_id=self.current_attempt, attempt_number=record.attempt_number,
            state="UNKNOWN" if unknown else "RECORDED", record=record,
            validation_issues=diag.validation_issues if diag else (),
            validation_issues_truncated=diag.validation_issues_truncated if diag else False)
        try:
            await self.hooks.record_outcome(outcome)
        except asyncio.CancelledError:
            raise self.stop("CANCELLED", run) from None
        except Exception:
            raise self.stop("STORAGE_UNAVAILABLE", run) from None
        self.acknowledged_slots = record.attempt_number
        if unknown:
            raise self.stop("OUTCOME_UNCERTAIN", run)
        self.check_cancelled(run)
