"""
Tests for IEC 61511 simplified SIL assessment via risk graph method.
Covers: assess_sil() with all SIL levels, edge cases, PFD/RRF ranges,
and all input parameter combinations.
"""

import pytest
from metering_designer.safety.sil import assess_sil


# ---------------------------------------------------------------------------
# 1. SIL level achievement tests
# ---------------------------------------------------------------------------

def test_sil_1_achieved():
    """
    A scenario yielding SIL 1 (score between 5 and 8 inclusive).
    serious(2) * rare(1) * possible(1) * high(3) = 6 → SIL 1
    """
    result = assess_sil(
        consequence="serious",
        occupancy="rare",
        avoidance="possible",
        demand_rate="high",
    )
    assert result["sil_rating"] == "SIL 1"
    assert result["raw_score"] == 6
    assert "10^-2" in result["pfd_range"]
    assert "10^-1" in result["pfd_range"]


def test_sil_2_achieved():
    """
    A scenario yielding SIL 2 (score between 9 and 16 inclusive).
    major(3) * frequent(2) * possible(1) * medium(2) = 12 → SIL 2
    """
    result = assess_sil(
        consequence="major",
        occupancy="frequent",
        avoidance="possible",
        demand_rate="medium",
    )
    assert result["sil_rating"] == "SIL 2"
    assert result["raw_score"] == 12
    assert "10^-3" in result["pfd_range"]
    assert "10^-2" in result["pfd_range"]


def test_sil_3_achieved():
    """
    A scenario yielding SIL 3 (score between 17 and 32 inclusive).
    catastrophic(4) * frequent(2) * possible(1) * high(3) = 24 → SIL 3
    """
    result = assess_sil(
        consequence="catastrophic",
        occupancy="frequent",
        avoidance="possible",
        demand_rate="high",
    )
    assert result["sil_rating"] == "SIL 3"
    assert result["raw_score"] == 24
    assert "10^-4" in result["pfd_range"]
    assert "10^-3" in result["pfd_range"]


def test_sil_no_sil():
    """
    A scenario yielding "No SIL" (score ≤ 4).
    minor(1) * rare(1) * possible(1) * low(1) = 1 → No SIL
    """
    result = assess_sil(
        consequence="minor",
        occupancy="rare",
        avoidance="possible",
        demand_rate="low",
    )
    assert "No SIL" in result["sil_rating"]
    assert result["raw_score"] == 1
    assert result["risk_reduction_factor"] == "< 10"


def test_sil_catastrophic():
    """
    Catastrophic + continuous + impossible + high → highest SIL.
    4 * 3 * 3 * 3 = 108 → "SIL 3 with redundancy"
    """
    result = assess_sil(
        consequence="catastrophic",
        occupancy="continuous",
        avoidance="impossible",
        demand_rate="high",
    )
    assert "SIL 3 with redundancy" in result["sil_rating"]
    assert result["raw_score"] == 108
    assert result["pfd_range"] == "< 10^-4"
    assert result["risk_reduction_factor"] == "> 10000"


# ---------------------------------------------------------------------------
# 2. PFD range verification (IEC 61511 target failure measures)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "consequence, occupancy, avoidance, demand, expected_sil, expected_pfd",
    [
        # SIL 1: 1e-2 to 1e-1  (scores 5-8)
        ("serious", "rare", "possible", "high", "SIL 1", "10^-2 to 10^-1"),              # 2*1*1*3=6 → SIL 1
        ("serious", "rare", "possible_limited", "medium", "SIL 1", "10^-2 to 10^-1"),    # 2*1*2*2=8 → SIL 1
        # SIL 2: 1e-3 to 1e-2  (scores 9-16)
        ("major", "frequent", "possible", "medium", "SIL 2", "10^-3 to 10^-2"),          # 3*2*1*2=12 → SIL 2
        ("serious", "frequent", "possible_limited", "medium", "SIL 2", "10^-3 to 10^-2"),# 2*2*2*2=16 → SIL 2
        # SIL 3: 1e-4 to 1e-3  (scores 17-32)
        ("catastrophic", "frequent", "possible_limited", "medium", "SIL 3", "10^-4 to 10^-3"),  # 4*2*2*2=32 → SIL 3
        ("major", "frequent", "impossible", "low", "SIL 3", "10^-4 to 10^-3"),           # 3*2*3*1=18 → SIL 3
        # No SIL: < 10^-1  (score ≤ 4)
        ("minor", "rare", "possible", "low", "No SIL required (a)", "< 10^-1"),          # 1*1*1*1=1 → No SIL
        # SIL 3 with redundancy: < 10^-4  (score > 32)
        ("catastrophic", "continuous", "impossible", "high", "SIL 3 with redundancy", "< 10^-4"),  # 4*3*3*3=108
    ],
)
def test_sil_pfd_range(consequence, occupancy, avoidance, demand, expected_sil, expected_pfd):
    """
    Verify that each SIL level returns the correct PFD range string
    per IEC 61511 target failure measures.
    """
    result = assess_sil(
        consequence=consequence,
        occupancy=occupancy,
        avoidance=avoidance,
        demand_rate=demand,
    )
    assert result["sil_rating"] == expected_sil
    assert result["pfd_range"] == expected_pfd


# ---------------------------------------------------------------------------
# 3. RRF range verification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "consequence, occupancy, avoidance, demand, expected_sil, expected_rrf",
    [
        # SIL 1: RRF 10 to 100  (scores 5-8)
        ("serious", "rare", "possible", "high", "SIL 1", "10 to 100"),            # 2*1*1*3=6 → SIL 1 ✓
        ("serious", "rare", "possible_limited", "medium", "SIL 1", "10 to 100"),  # 2*1*2*2=8 → SIL 1 ✓
        # SIL 2: RRF 100 to 1000
        ("major", "frequent", "possible", "medium", "SIL 2", "100 to 1000"),      # 3*2*1*2=12 → SIL 2 ✓
        # SIL 3: RRF 1000 to 10000
        ("catastrophic", "frequent", "possible_limited", "medium", "SIL 3", "1000 to 10000"),  # 4*2*2*2=32 → SIL 3 ✓
        # No SIL: RRF < 10
        ("minor", "rare", "possible", "low", "No SIL required (a)", "< 10"),       # 1*1*1*1=1 ✓
        # SIL 3+ redundancy: RRF > 10000
        ("catastrophic", "continuous", "impossible", "high", "SIL 3 with redundancy", "> 10000"),  # 108 ✓
    ],
)
def test_sil_rrf_range(consequence, occupancy, avoidance, demand, expected_sil, expected_rrf):
    """
    Verify the risk reduction factor (RRF) ranges for each SIL level.
    """
    result = assess_sil(
        consequence=consequence,
        occupancy=occupancy,
        avoidance=avoidance,
        demand_rate=demand,
    )
    assert result["sil_rating"] == expected_sil
    assert result["risk_reduction_factor"] == expected_rrf


# ---------------------------------------------------------------------------
# 4. Default parameter behavior
# ---------------------------------------------------------------------------

def test_assess_sil_defaults():
    """
    Default parameters should return a valid result with sensible defaults.
    Defaults: serious, rare, possible, low → 2*1*1*1 = 2 → No SIL
    """
    result = assess_sil()
    assert "sil_rating" in result
    assert "pfd_range" in result
    assert "risk_reduction_factor" in result
    assert "raw_score" in result
    assert "notes" in result
    assert result["raw_score"] == 2  # serious=2 * rare=1 * possible=1 * low=1
    assert "No SIL" in result["sil_rating"]


# ---------------------------------------------------------------------------
# 5. Boundary edge-case tests
# ---------------------------------------------------------------------------

def test_sil_boundary_score_4_no_sil():
    """
    Score exactly 4 → falls into <=4 bucket → "No SIL required (a)"
    serious(2) * frequent(2) * possible(1) * low(1) = 4
    """
    result = assess_sil("serious", "frequent", "possible", "low")
    assert result["raw_score"] == 4
    assert "No SIL" in result["sil_rating"]


def test_sil_boundary_score_5_sil1():
    """
    Score exactly 5 → first score >4 → "SIL 1"
    major(3) * rare(1) * possible_limited(2) * low(1) = 6 → SIL 1. Let's find exactly 5:
    With the given score weights it's hard to get exactly 5 (scores are integers 1-4, 1-3, 1-3, 1-3).
    Possible products: 1,2,3,4,6,8,9,12,16,18,24,27,32,36,48,54,64,72,81,96,108...
    There is no way to get 5. But the boundary test is still useful conceptually.
    The lowest SIL 1 score is 6.
    major(3) * rare(1) * possible_limited(2) * low(1) = 6 → SIL 1
    """
    result = assess_sil("major", "rare", "possible_limited", "low")
    assert result["raw_score"] == 6
    assert result["sil_rating"] == "SIL 1"


def test_sil_boundary_score_8_sil1():
    """
    Score exactly 8 → upper bound of SIL 1 bucket.
    serious(2) * rare(1) * possible_limited(2) * medium(2) = 8 → SIL 1
    """
    result = assess_sil("serious", "rare", "possible_limited", "medium")
    assert result["raw_score"] == 8
    assert result["sil_rating"] == "SIL 1"


def test_sil_boundary_score_9_sil2():
    """
    Score exactly 9 → first score >8 → lower bound of SIL 2.
    major(3) * rare(1) * impossible(3) * low(1) = 9 → SIL 2
    """
    result = assess_sil("major", "rare", "impossible", "low")
    assert result["raw_score"] == 9
    assert result["sil_rating"] == "SIL 2"


def test_sil_boundary_score_16_sil2():
    """
    Score exactly 16 → upper bound of SIL 2.
    catastrophic(4) * frequent(2) * possible(1) * low(1) = 8 → SIL 1. 
    Need a combo that gives 16: catastrophic(4)*frequent(2)*possible(1)*medium(2)=16 ✓
    """
    result = assess_sil("catastrophic", "frequent", "possible", "medium")
    assert result["raw_score"] == 16
    assert result["sil_rating"] == "SIL 2"


def test_sil_boundary_score_17_sil3():
    """
    Score = 17 → first score >16 → SIL 3.
    But can we get 17? Scores are all integer products from {1,2,3,4}×{1,2,3}×{1,2,3}×{1,2,3}.
    All products are multiples of the consequence factor. 17 is prime, can't be obtained.
    The next available after 16 is 18: major(3)*frequent(2)*impossible(3)*low(1)=18
    """
    result = assess_sil("major", "frequent", "impossible", "low")
    assert result["raw_score"] == 18
    assert result["sil_rating"] == "SIL 3"


def test_sil_boundary_score_32_sil3():
    """
    Score exactly 32 → upper bound of SIL 3.
    catastrophic(4)*frequent(2)*possible_limited(2)*medium(2)=32 ✓
    """
    result = assess_sil("catastrophic", "frequent", "possible_limited", "medium")
    assert result["raw_score"] == 32
    assert result["sil_rating"] == "SIL 3"


def test_sil_boundary_score_33_redundancy():
    """
    Score = 33 → >32 → "SIL 3 with redundancy"
    But 33 isn't achievable as product. 36 is: catastrophic(4)*continuous(3)*impossible(3)*low(1)=36
    """
    result = assess_sil("catastrophic", "continuous", "impossible", "low")
    assert result["raw_score"] == 36
    assert result["sil_rating"] == "SIL 3 with redundancy"


# ---------------------------------------------------------------------------
# 6. Invalid / unrecognised parameter values (graceful fallback)
# ---------------------------------------------------------------------------

def test_unrecognized_parameters_use_defaults():
    """
    Unrecognized string values should fall back to the default score mapping
    (uses .get(key, default) pattern: default=2 for consequence, 1 for others).
    """
    result = assess_sil(
        consequence="nonexistent",
        occupancy="bogus",
        avoidance="nonsense",
        demand_rate="garbage",
    )
    # consequence default=2 (serious), occupancy default=1 (rare), 
    # avoidance default=1 (possible), demand default=1 (low)
    # Score = 2*1*1*1 = 2 → No SIL
    assert result["raw_score"] == 2
    assert "No SIL" in result["sil_rating"]


def test_all_possible_avoidance_values():
    """
    'possible_limited' is a valid value (score 2) and should be handled.
    """
    result = assess_sil(
        consequence="serious",
        occupancy="frequent",
        avoidance="possible_limited",
        demand_rate="low",
    )
    # serious(2) * frequent(2) * possible_limited(2) * low(1) = 8 → SIL 1
    assert result["raw_score"] == 8
    assert result["sil_rating"] == "SIL 1"


# ---------------------------------------------------------------------------
# 7. Environment parameter (accepted but not scored)
# ---------------------------------------------------------------------------

def test_environment_parameter_accepted():
    """
    The environment parameter is accepted but does not alter the score.
    Verify both 'onshore' and 'offshore' work without error.
    """
    result_onshore = assess_sil(environment="onshore")
    result_offshore = assess_sil(environment="offshore")
    assert result_onshore["raw_score"] == result_offshore["raw_score"]
    assert result_onshore["sil_rating"] == result_offshore["sil_rating"]


# ---------------------------------------------------------------------------
# 8. All consequence levels coverage
# ---------------------------------------------------------------------------

def test_consequence_level_minor():
    """minor=1, everything else=1 → score=1 → No SIL"""
    result = assess_sil("minor", "rare", "possible", "low")
    assert result["raw_score"] == 1
    assert "No SIL" in result["sil_rating"]


def test_consequence_level_serious():
    """serious=2, all defaults → score=2 → No SIL"""
    result = assess_sil("serious", "rare", "possible", "low")
    assert result["raw_score"] == 2
    assert "No SIL" in result["sil_rating"]


def test_consequence_level_major():
    """major=3, all defaults → score=3 → No SIL"""
    result = assess_sil("major", "rare", "possible", "low")
    assert result["raw_score"] == 3
    assert "No SIL" in result["sil_rating"]


def test_consequence_level_catastrophic():
    """catastrophic=4, defaults → score=4 → No SIL (barely)"""
    result = assess_sil("catastrophic", "rare", "possible", "low")
    assert result["raw_score"] == 4
    assert "No SIL" in result["sil_rating"]


# ---------------------------------------------------------------------------
# 9. Pipeline gas metering realistic scenarios
# ---------------------------------------------------------------------------

def test_pipeline_gas_pressure_protection_sil2():
    """
    High-pressure gas pipeline over-pressure protection typically SIL 2.
    major consequence, frequent occupancy, possible avoidance, medium demand.
    3*2*1*2 = 12 → SIL 2.
    """
    result = assess_sil(
        consequence="major",
        occupancy="frequent",
        avoidance="possible",
        demand_rate="medium",
    )
    assert result["sil_rating"] == "SIL 2"
    assert result["raw_score"] == 12


def test_esd_valve_sil3():
    """
    Emergency shutdown valve in gas terminal could be SIL 3.
    catastrophic, continuous, possible, high → 4*3*1*3 = 36 → SIL 3 with redundancy
    """
    result = assess_sil(
        consequence="catastrophic",
        occupancy="continuous",
        avoidance="possible",
        demand_rate="high",
    )
    assert result["raw_score"] == 36
    assert "SIL 3" in result["sil_rating"]


def test_notes_field_present():
    """Every result must include the HAZOP validation note."""
    result = assess_sil()
    assert "IEC 61511" in result["notes"]
    assert "HAZOP" in result["notes"]


# ---------------------------------------------------------------------------
# 10. Return dictionary completeness
# ---------------------------------------------------------------------------

def test_return_dict_keys():
    """Verify all expected keys are present in the return dictionary."""
    result = assess_sil()
    expected_keys = {"sil_rating", "pfd_range", "risk_reduction_factor", "raw_score", "notes"}
    assert set(result.keys()) == expected_keys


def test_raw_score_is_int():
    """raw_score must always be an integer."""
    for cons in ["minor", "serious", "major", "catastrophic"]:
        result = assess_sil(consequence=cons)
        assert isinstance(result["raw_score"], int)
