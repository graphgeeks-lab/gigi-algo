"""Every typed object Gigi passes between modules or writes to disk.

One file until it passed 400 lines, which is the rule; then four, by concern:

    people.py     who created it, and who built the entry
    spec.py       what the registry claims about a method
    data.py       what we know about the data it runs on
    execution.py  what happened when it ran

Nothing here imports another Gigi module except its siblings, so it stays cheap
to import. `from gigi.models import X` keeps working for every name.
"""

from __future__ import annotations

from gigi.models.data import *  # noqa: F401,F403
from gigi.models.execution import *  # noqa: F401,F403
from gigi.models.people import *  # noqa: F401,F403
from gigi.models.spec import *  # noqa: F401,F403

__all__ = [
    'AiContext',
    'BackendSupport',
    'ChoicePoint',
    'Comparison',
    'ComparisonSpec',
    'Complexity',
    'Credits',
    'DetectSpec',
    'Difference',
    'Divergence',
    'DivergenceCategory',
    'DivergenceCheck',
    'DomainMeaning',
    'DomainSpec',
    'EdgeColumns',
    'Family',
    'Formula',
    'GraphInputSpec',
    'DatasetKind',
    'DatasetMetadata',
    'GraphMetadata',
    'GraphProfile',
    'VectorMetadata',
    'VectorProfile',
    'INVERSE_RELATIONS',
    'InlineGraph',
    'InputKind',
    'InputSpec',
    'Intent',
    'Invariant',
    'InvariantResult',
    'KnownAnswer',
    'Maths',
    'Maturity',
    'MethodKind',
    'MethodSpec',
    'ScoreResult',
    'PartitionResult',
    'NormalizedResult',
    'OriginalAuthor',
    'OriginalWork',
    'OutputKind',
    'OutputSpec',
    'ParameterInterpretation',
    'ParameterSpec',
    'Person',
    'Precursor',
    'ProblemSpec',
    'Provenance',
    'RelationKind',
    'Relationship',
    'RequirementFlag',
    'Role',
    'RunResult',
    'RunStatus',
    'SemanticInterpretation',
    'Severity',
    'UseCaseSpec',
    'VectorInputSpec',
    'VerificationReport',
    'VerificationSettings',
]
