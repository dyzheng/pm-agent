from src.state import ProjectState, Phase
from src.phases.intake import run_intake


def test_intake_parses_neb_request():
    state = ProjectState(
        request="Develop an NEB calculation workflow for molecular reactions "
        "utilizing hybrid Machine Learning Potential acceleration with DFT verification"
    )
    result = run_intake(state)
    assert result.phase == Phase.AUDIT
    assert "domain" in result.parsed_intent
    assert "method" in result.parsed_intent
    assert "validation" in result.parsed_intent
    assert "keywords" in result.parsed_intent


def test_intake_parses_polarization_request():
    state = ProjectState(
        request="AI-driven computational workflow for polarization curves "
        "on Fe surfaces with DFT validation"
    )
    result = run_intake(state)
    assert result.phase == Phase.AUDIT
    assert "keywords" in result.parsed_intent
    assert len(result.parsed_intent["keywords"]) > 0


def test_intake_extracts_keywords():
    state = ProjectState(
        request="Add NEB workflow with MLP and CUDA support"
    )
    result = run_intake(state)
    keywords = result.parsed_intent["keywords"]
    assert any("neb" in k.lower() for k in keywords)
