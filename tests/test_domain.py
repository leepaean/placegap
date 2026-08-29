from core.models import Confidence, Dimension, Evidence, Finding, Hypothesis, Place, Reliability, VerificationStatus


def test_evidence_to_finding_to_hypothesis_chain():
    place = Place(
        name="Example Cultural Place",
        diagnostic_scope="Test whether observed evidence supports a value-formation hypothesis.",
    )

    evidence = Evidence(
        place_id=place.id,
        title="Official visitor statistics",
        source_type="official",
        excerpt="The site received 80,000 visitors during the holiday period.",
        reliability=Reliability.HIGH,
    )

    finding = Finding(
        place_id=place.id,
        statement="The site received 80,000 visitors during the reported holiday period.",
        dimension=Dimension.VISIBILITY,
        evidence_ids=[evidence.id],
        verification_status=VerificationStatus.ACCEPTED,
    )

    hypothesis = Hypothesis(
        place_id=place.id,
        statement="Low visitor awareness may not be the primary bottleneck during major holiday periods.",
        supporting_evidence_ids=[evidence.id],
        alternative_explanations=[
            "Holiday traffic may not represent normal-period awareness.",
            "Visitors may arrive for adjacent attractions rather than this place itself.",
        ],
        confidence=Confidence.MEDIUM,
        confidence_reason="Supported by one high-reliability source, but temporal representativeness is limited.",
    )

    assert finding.evidence_ids == [evidence.id]
    assert hypothesis.confidence == Confidence.MEDIUM
    assert len(hypothesis.alternative_explanations) == 2
