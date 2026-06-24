from app.services.chemistry import REACTION_RE, normalize_reaction


def test_reaction_notation_supports_greek_excited_state_species():
    text = "Measured process: e+O₂(a¹Δg)→O⁻+O ."

    match = REACTION_RE.search(text)
    assert match is not None
    reaction = " ".join(match.group(1).split())
    normalized, reactants, products = normalize_reaction(reaction)

    assert normalized == "e + O₂(a¹Δg) -> O⁻ + O"
    assert reactants == ["e", "O₂(a¹Δg)"]
    assert products == ["O⁻", "O"]
