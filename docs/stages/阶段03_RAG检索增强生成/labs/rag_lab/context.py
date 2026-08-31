"""Context assembly with explicit non-truncating budget decisions."""

from __future__ import annotations

from rag_lab.errors import problem
from rag_lab.ids import derived_id, sha256_text
from rag_lab.models import (
    ContextAssemblyCommand,
    ContextBundle,
    SelectedHit,
    StageResult,
    WarningRecord,
)
from rag_lab.snapshot import PipelineSnapshot


class BudgetedContextAssembler:
    """Select eligible hits in rank order without silently truncating chunks."""

    def __init__(self, snapshot: PipelineSnapshot) -> None:
        self._snapshot = snapshot

    def assemble(self, command: ContextAssemblyCommand) -> StageResult[ContextBundle]:
        """Build a deterministic context bundle and record every budget drop."""

        if command.token_budget < 1:
            budget_problem = problem(
                "CONTEXT_BUDGET_EXCEEDED",
                "context",
                "Context token budget is invalid",
                "The context profile requires a positive token budget.",
                422,
            )
            return StageResult(command.request_id, "failed", problem=budget_problem)
        selected: list[SelectedHit] = []
        rendered_parts: list[str] = []
        warnings: list[WarningRecord] = []
        token_count = 0
        for ranked_hit_id in command.ranked_hit_ids:
            hit = self._snapshot.ranked_hits.get(ranked_hit_id)
            if hit is None or hit.query_id != command.query_id:
                missing = problem(
                    "CONTRACT_VALIDATION_ERROR",
                    "context",
                    "Ranked hit reference does not exist",
                    "Context assembly requires immutable hits from the same query.",
                    400,
                    item_ref={"ranked_hit_id": ranked_hit_id},
                )
                return StageResult(command.request_id, "failed", problem=missing)
            if not hit.eligible_for_context:
                continue
            chunk = self._snapshot.chunks[hit.chunk_id]
            if token_count + chunk.token_count > command.token_budget:
                warnings.append(
                    WarningRecord(
                        "CHUNK_EXCEEDS_REMAINING_BUDGET",
                        "context",
                        "Chunk was skipped; context assembly never silently truncates evidence.",
                        item_ref=chunk.chunk_id,
                    )
                )
                continue
            render_order = len(selected) + 1
            selected.append(
                SelectedHit(
                    ranked_hit_id=hit.ranked_hit_id,
                    chunk_id=chunk.chunk_id,
                    render_order=render_order,
                    rendered_text_sha256=chunk.text_sha256,
                )
            )
            rendered_parts.append(f"[S{render_order}] {chunk.text}")
            token_count += chunk.token_count
        if not selected:
            warnings.append(
                WarningRecord(
                    "NO_ELIGIBLE_HITS",
                    "context",
                    "No ranked hit could enter the context under confidence and budget rules.",
                )
            )
        rendered_context = "\n\n".join(rendered_parts)
        hit_ids = tuple(item.ranked_hit_id for item in selected)
        bundle = ContextBundle(
            schema_version="1.0.0",
            context_bundle_id=derived_id(
                "ctx",
                command.query_id,
                *hit_ids,
                command.assembly_profile.identity,
                command.token_budget,
            ),
            query_id=command.query_id,
            assembly_profile=command.assembly_profile,
            token_budget=command.token_budget,
            token_count=token_count,
            selected_hits=tuple(selected),
            rendered_context=rendered_context,
            context_sha256=sha256_text(rendered_context),
            warnings=tuple(warnings),
        )
        return StageResult(command.request_id, "success", data=bundle, warnings=tuple(warnings))
