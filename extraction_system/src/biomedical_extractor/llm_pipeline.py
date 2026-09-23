"""Compose the existing NER contract with the controlled LLM RE contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .entity_extraction import (
    DEFAULT_ENTITY_MODEL,
    Entity,
    EntityExtractor,
    GLiNERBioMedExtractor,
)
from .entity_assembly import _assemble_document_entities, assemble_document_entities
from .graph import GraphResult, build_graph_result
from .hunflair2 import HUNFLAIR2_MODEL_IDENTIFIER, HunFlair2BioMedExtractor
from .identity_resolution import (
    ExplicitIdentityVerifier,
    find_unresolved_explicit_identity_candidates,
    validate_explicit_identity_result,
)
from .llm_identity_resolution import LLMExplicitIdentityVerifier
from .llm_relation_extraction import LLMRelationExtractor, OpenAIConfig
from .paper_roles import (
    PaperRoleExtractor,
    PaperRoleTarget,
    apply_paper_roles,
)
from .relation_extraction import (
    Relation,
    RelationExtractionResult,
    RelationExtractor,
    validate_relations,
)


@dataclass(frozen=True)
class ComposedExtractionResult:
    """Normalized entity-plus-grounded-relation output for the LLM path."""

    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entities", tuple(self.entities))
        object.__setattr__(self, "relations", tuple(self.relations))

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return a JSON-serializable composed extraction result."""

        return {
            "entities": [entity.to_dict() for entity in self.entities],
            "relations": [relation.to_dict() for relation in self.relations],
        }


class LLMExtractionPipeline:
    """Compose NER, explicit local identity resolution, and grounded relations."""

    def __init__(
        self,
        entity_extractor: EntityExtractor,
        relation_extractor: RelationExtractor,
        paper_role_extractor: PaperRoleExtractor | None = None,
        identity_verifier: ExplicitIdentityVerifier | None = None,
    ) -> None:
        """Bind independently replaceable extraction and enrichment seams."""

        self.entity_extractor = entity_extractor
        self.relation_extractor = relation_extractor
        self.paper_role_extractor = paper_role_extractor
        self.identity_verifier = identity_verifier

    @classmethod
    def from_pretrained(
        cls,
        *,
        entity_model: str = DEFAULT_ENTITY_MODEL,
        entity_labels: Sequence[str] | None = None,
        entity_threshold: float = 0.5,
        device: str | None = None,
        llm_config: OpenAIConfig | None = None,
        entity_backend: str = "hunflair2",
        hunflair2_model: str = HUNFLAIR2_MODEL_IDENTIFIER,
        hunflair2_runtime_python: Path | str | None = None,
        hunflair2_runtime_script: Path | str | None = None,
        hunflair2_runtime_cache: Path | str = Path(".cache/hunflair2"),
        hunflair2_offline: bool = False,
        paper_role_extractor: PaperRoleExtractor | None = None,
        identity_verifier: ExplicitIdentityVerifier | None = None,
    ) -> LLMExtractionPipeline:
        """Load the selected NER backend and shared OpenAI relation/identity harnesses."""

        if entity_backend == "gliner":
            entity_extractor = GLiNERBioMedExtractor.from_pretrained(
                model_name=entity_model,
                labels=entity_labels,
                threshold=entity_threshold,
                device=device,
            )
        elif entity_backend == "hunflair2":
            if entity_labels is not None:
                raise ValueError(
                    "HunFlair2 uses its official labels; entity_labels are only "
                    "supported by the GLiNER backend"
                )
            entity_extractor = HunFlair2BioMedExtractor.from_pretrained(
                model_identifier=hunflair2_model,
                runtime_python=hunflair2_runtime_python,
                runtime_script=hunflair2_runtime_script,
                runtime_cache=hunflair2_runtime_cache,
                device=device,
                offline=hunflair2_offline,
            )
        else:
            raise ValueError(
                f"Unsupported entity backend {entity_backend!r}; expected "
                "'gliner' or 'hunflair2'"
            )
        relation_extractor = LLMRelationExtractor.from_openai(llm_config)
        verifier = (
            identity_verifier
            if identity_verifier is not None
            else LLMExplicitIdentityVerifier.from_openai(llm_config)
        )
        return cls(
            entity_extractor,
            relation_extractor,
            paper_role_extractor,
            verifier,
        )

    @classmethod
    def from_hunflair2(
        cls,
        *,
        model_identifier: str = HUNFLAIR2_MODEL_IDENTIFIER,
        runtime_python: Path | str | None = None,
        runtime_script: Path | str | None = None,
        runtime_cache: Path | str = Path(".cache/hunflair2"),
        device: str | None = None,
        offline: bool = False,
        llm_config: OpenAIConfig | None = None,
        paper_role_extractor: PaperRoleExtractor | None = None,
        identity_verifier: ExplicitIdentityVerifier | None = None,
    ) -> "LLMExtractionPipeline":
        """Load pretrained HunFlair2 and the existing grounded RE harness."""

        return cls.from_pretrained(
            entity_backend="hunflair2",
            hunflair2_model=model_identifier,
            hunflair2_runtime_python=runtime_python,
            hunflair2_runtime_script=runtime_script,
            hunflair2_runtime_cache=runtime_cache,
            hunflair2_offline=offline,
            device=device,
            llm_config=llm_config,
            paper_role_extractor=paper_role_extractor,
            identity_verifier=identity_verifier,
        )

    from_openai = from_pretrained

    def extract(self, text: str) -> ComposedExtractionResult:
        """Extract normalized entities and evidence-grounded relations."""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return ComposedExtractionResult(entities=(), relations=())

        entities = tuple(self.entity_extractor.extract_entities(text))
        relation_result = self.extract_relations(text, entities)
        return ComposedExtractionResult(
            entities=entities,
            relations=relation_result.relations,
        )

    def extract_entities(self, text: str) -> tuple[Entity, ...]:
        """Run only the configured entity extractor for this composed path."""

        return tuple(self.entity_extractor.extract_entities(text))

    def extract_relations(
        self, text: str, entities: Sequence[Entity]
    ) -> RelationExtractionResult:
        """Run RE on supplied entities and recheck the stable output boundary."""

        result = self.relation_extractor.extract_relations(text, entities)
        if not isinstance(result, RelationExtractionResult):
            raise TypeError(
                "Relation extractor must return RelationExtractionResult, "
                f"not {type(result).__name__}"
            )
        # A custom implementation must honor the same local contract as the LLM
        # harness; this recheck prevents invalid values from escaping composition.
        return validate_relations(text, entities, result.relations)

    def extract_graph(
        self,
        text: str,
        *,
        document_id: str = "input",
        paper_title: str = "",
        paper_role_extractor: PaperRoleExtractor | None = None,
    ) -> GraphResult:
        """Extract, assemble, and serialize-ready graph data for one document.

        Deterministic and eligible verified identities are finalized before
        relation extraction, graph construction, unconnected-node detection,
        and paper-role enrichment. Mentions passed to the relation extractor
        remain unchanged.
        """

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            return build_graph_result(document_id, assemble_document_entities((), text), ())

        entities = tuple(self.entity_extractor.extract_entities(text))
        assembly = assemble_document_entities(entities, text)
        verifier = self.identity_verifier
        if verifier is not None:
            candidates = find_unresolved_explicit_identity_candidates(
                entities, text, assembly
            )
            if candidates:
                verification = verifier.verify_explicit_identities(text, candidates)
                verified_pairs = validate_explicit_identity_result(
                    text, candidates, verification
                )
                if verified_pairs:
                    assembly = _assemble_document_entities(
                        entities,
                        text,
                        verified_identity_pairs=verified_pairs,
                    )
        relation_result = self.extract_relations(text, entities)
        graph = build_graph_result(document_id, assembly, relation_result)

        role_extractor = (
            paper_role_extractor
            if paper_role_extractor is not None
            else self.paper_role_extractor
        )
        if role_extractor is None or not graph.unconnected_nodes:
            return graph

        targets = tuple(
            PaperRoleTarget(
                node_id=node.id,
                label=node.label,
                type=node.type,
                mentions=node.mentions,
            )
            for node in graph.unconnected_nodes
        )
        roles = role_extractor.extract_roles(paper_title, text, targets)
        return apply_paper_roles(graph, text, roles)


BiomedicalLLMExtractor = LLMExtractionPipeline
