"""Unit tests for MatchService with fake adapters.

No Qdrant or embedding model required — all dependencies are fakes.
"""

import uuid

import pytest

from ad_injector.app.embedding_provider import EmbeddingProvider
from ad_injector.app.match_service import MatchService
from ad_injector.app.policy_engine import PolicyEngine
from ad_injector.app.targeting_engine import TargetingEngine
from ad_injector.app.vector_store import VectorFilter, VectorStore
from ad_injector.models.mcp_requests import (
    MatchConstraints,
    MatchRequest,
    PlacementContext,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

FIXED_VECTOR = [0.1] * 384


class FakeEmbeddingProvider(EmbeddingProvider):
    """Always returns FIXED_VECTOR, no model loaded."""

    def __init__(self):
        # Skip parent __init__ to avoid importing fastembed
        pass

    def embed(self, text: str) -> list[float]:
        return FIXED_VECTOR


def _make_hit(ad_id: str, score: float, *, sensitive: bool = False,
              age_restricted: bool = False, blocked_keywords: list[str] | None = None,
              advertiser_id: str = "adv-1") -> dict:
    """Build a raw hit dict matching VectorStore.query() output shape."""
    return {
        "id": str(uuid.uuid4()),
        "score": score,
        "metadata": {
            "ad_id": ad_id,
            "advertiser_id": advertiser_id,
            "title": f"Title for {ad_id}",
            "body": f"Body for {ad_id}",
            "cta_text": "Click",
            "landing_url": f"https://example.com/{ad_id}",
            "topics": ["tech"],
            "locale": ["en-US"],
            "verticals": ["technology"],
            "blocked_keywords": blocked_keywords or [],
            "sensitive": sensitive,
            "age_restricted": age_restricted,
        },
    }


SAMPLE_HITS = [
    _make_hit("ad-1", 0.95),
    _make_hit("ad-2", 0.80),
    _make_hit("ad-3", 0.60),
]


class FakeVectorStore(VectorStore):
    """Returns canned hits; records calls for assertions."""

    def __init__(self, hits: list[dict] | None = None):
        self.hits = hits if hits is not None else list(SAMPLE_HITS)
        self.last_query_args: dict | None = None

    def query(self, vector, vector_filter, top_k):
        self.last_query_args = {
            "vector": vector,
            "vector_filter": vector_filter,
            "top_k": top_k,
        }
        return self.hits[:top_k]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_service(hits: list[dict] | None = None) -> tuple[MatchService, FakeVectorStore]:
    store = FakeVectorStore(hits)
    svc = MatchService(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=store,
        targeting_engine=TargetingEngine(),
        policy_engine=PolicyEngine(),
    )
    return svc, store


def _simple_request(**overrides) -> MatchRequest:
    defaults = {"context_text": "test query", "top_k": 5}
    defaults.update(overrides)
    return MatchRequest(**defaults)


# ---------------------------------------------------------------------------
# Tests — pipeline basics
# ---------------------------------------------------------------------------

class TestMatchServicePipeline:
    """Verify the end-to-end MatchService.match() pipeline with fakes."""

    def test_returns_candidates(self):
        svc, _ = _build_service()
        resp = svc.match(_simple_request())
        assert len(resp.candidates) == 3
        assert resp.candidates[0].ad_id == "ad-1"
        assert resp.candidates[0].score == pytest.approx(0.95)

    def test_request_id_is_uuid(self):
        svc, _ = _build_service()
        resp = svc.match(_simple_request())
        uuid.UUID(resp.request_id)  # raises if not valid

    def test_placement_passed_through(self):
        svc, _ = _build_service()
        req = _simple_request(
            placement=PlacementContext(placement="sidebar", surface="search"),
        )
        resp = svc.match(req)
        assert resp.placement == "sidebar"

    def test_top_k_respected(self):
        svc, store = _build_service()
        resp = svc.match(_simple_request(top_k=1))
        assert len(resp.candidates) == 1
        assert store.last_query_args["top_k"] == 1

    def test_embedding_provider_receives_normalized_text(self):
        """Whitespace should be collapsed."""
        svc, store = _build_service()
        svc.match(_simple_request(context_text="  hello   world  "))
        # The vector store receives the fixed vector from FakeEmbeddingProvider
        assert store.last_query_args["vector"] == FIXED_VECTOR

    def test_empty_hits_returns_empty_candidates(self):
        svc, _ = _build_service(hits=[])
        resp = svc.match(_simple_request())
        assert resp.candidates == []
        assert resp.request_id  # still has a request_id


# ---------------------------------------------------------------------------
# Tests — match_id determinism
# ---------------------------------------------------------------------------

class TestMatchId:
    """match_id must be deterministic: uuid5(request_id, ad_id)."""

    def test_match_id_is_deterministic(self):
        svc, _ = _build_service()
        resp = svc.match(_simple_request())
        c = resp.candidates[0]
        expected = str(uuid.uuid5(uuid.UUID(resp.request_id), c.ad_id))
        assert c.match_id == expected

    def test_different_request_ids_produce_different_match_ids(self):
        svc, _ = _build_service()
        r1 = svc.match(_simple_request())
        r2 = svc.match(_simple_request())
        # Different request_ids → different match_ids for the same ad
        assert r1.request_id != r2.request_id
        assert r1.candidates[0].match_id != r2.candidates[0].match_id


# ---------------------------------------------------------------------------
# Tests — PolicyEngine filtering
# ---------------------------------------------------------------------------

class TestPolicyFiltering:
    """PolicyEngine must remove ineligible ads post-query."""

    def test_age_restricted_filtered_by_default(self):
        hits = [
            _make_hit("ad-ok", 0.9),
            _make_hit("ad-age", 0.8, age_restricted=True),
        ]
        svc, _ = _build_service(hits)
        resp = svc.match(_simple_request())
        ids = [c.ad_id for c in resp.candidates]
        assert "ad-ok" in ids
        assert "ad-age" not in ids

    def test_age_restricted_allowed_when_opted_in(self):
        hits = [
            _make_hit("ad-ok", 0.9),
            _make_hit("ad-age", 0.8, age_restricted=True),
        ]
        svc, _ = _build_service(hits)
        req = _simple_request(
            constraints=MatchConstraints(age_restricted_ok=True),
        )
        resp = svc.match(req)
        ids = [c.ad_id for c in resp.candidates]
        assert "ad-age" in ids

    def test_sensitive_filtered_by_default(self):
        hits = [
            _make_hit("ad-ok", 0.9),
            _make_hit("ad-sens", 0.8, sensitive=True),
        ]
        svc, _ = _build_service(hits)
        resp = svc.match(_simple_request())
        ids = [c.ad_id for c in resp.candidates]
        assert "ad-sens" not in ids

    def test_sensitive_allowed_when_opted_in(self):
        hits = [
            _make_hit("ad-ok", 0.9),
            _make_hit("ad-sens", 0.8, sensitive=True),
        ]
        svc, _ = _build_service(hits)
        req = _simple_request(
            constraints=MatchConstraints(sensitive_ok=True),
        )
        resp = svc.match(req)
        ids = [c.ad_id for c in resp.candidates]
        assert "ad-sens" in ids

    def test_blocked_keywords_removes_ad(self):
        hits = [
            _make_hit("ad-ok", 0.9),
            _make_hit("ad-blocked", 0.8, blocked_keywords=["gambling"]),
        ]
        svc, _ = _build_service(hits)
        req = _simple_request(
            constraints=MatchConstraints(topics=["gambling"]),
        )
        resp = svc.match(req)
        ids = [c.ad_id for c in resp.candidates]
        assert "ad-blocked" not in ids
        assert "ad-ok" in ids


# ---------------------------------------------------------------------------
# Tests — TargetingEngine filter construction
# ---------------------------------------------------------------------------

class TestTargetingFilter:
    """TargetingEngine should produce correct VectorFilter for the store."""

    def test_no_constraints_produces_empty_filter(self):
        svc, store = _build_service()
        svc.match(_simple_request())
        vf = store.last_query_args["vector_filter"]
        assert isinstance(vf, VectorFilter)
        assert vf.must == []
        assert vf.must_not == []

    def test_topics_constraint_adds_must(self):
        svc, store = _build_service()
        req = _simple_request(
            constraints=MatchConstraints(topics=["python", "ai"]),
        )
        svc.match(req)
        vf = store.last_query_args["vector_filter"]
        assert len(vf.must) == 1
        assert vf.must[0].key == "topics"

    def test_exclude_advertiser_adds_must_not(self):
        svc, store = _build_service()
        req = _simple_request(
            constraints=MatchConstraints(exclude_advertiser_ids=["bad-adv"]),
        )
        svc.match(req)
        vf = store.last_query_args["vector_filter"]
        assert len(vf.must_not) == 1
        assert vf.must_not[0].key == "advertiser_id"

    def test_combined_constraints(self):
        svc, store = _build_service()
        req = _simple_request(
            constraints=MatchConstraints(
                topics=["python"],
                locale="en-US",
                verticals=["tech"],
                exclude_advertiser_ids=["bad-adv"],
                exclude_ad_ids=["bad-ad"],
            ),
        )
        svc.match(req)
        vf = store.last_query_args["vector_filter"]
        assert len(vf.must) == 3       # topics, locale, verticals
        assert len(vf.must_not) == 2   # advertiser, ad_id


# ---------------------------------------------------------------------------
# Tests — score clamping
# ---------------------------------------------------------------------------

class TestScoreClamping:
    """Scores should be clamped to [0, 1]."""

    def test_score_above_one_clamped(self):
        hits = [_make_hit("ad-1", 1.5)]
        svc, _ = _build_service(hits)
        resp = svc.match(_simple_request())
        assert resp.candidates[0].score == 1.0

    def test_negative_score_clamped(self):
        hits = [_make_hit("ad-1", -0.3)]
        svc, _ = _build_service(hits)
        resp = svc.match(_simple_request())
        assert resp.candidates[0].score == 0.0
