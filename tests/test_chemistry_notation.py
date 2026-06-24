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


def test_reaction_notation_supports_metastable_star_species():
    text = "Metastable pooling channel: Ar*+Ar*→Ar+Ar⁺+e ."

    match = REACTION_RE.search(text)
    assert match is not None
    reaction = " ".join(match.group(1).split())
    normalized, reactants, products = normalize_reaction(reaction)

    assert normalized == "Ar* + Ar* -> Ar + Ar⁺ + e"
    assert reactants == ["Ar*", "Ar*"]
    assert products == ["Ar", "Ar⁺", "e"]


def test_reaction_notation_supports_radical_dot_species():
    text = "Dissociation channel: e+H₂O→OH·+H·+e ."

    match = REACTION_RE.search(text)
    assert match is not None
    reaction = " ".join(match.group(1).split())
    normalized, reactants, products = normalize_reaction(reaction)

    assert normalized == "e + H₂O -> OH· + H· + e"
    assert reactants == ["e", "H₂O"]
    assert products == ["OH·", "H·", "e"]


def test_reaction_notation_supports_modifier_letter_state_labels():
    text = "Nitrogen metastable channel: e+N₂(A³Σᵤ⁺)→N₂+e ."

    match = REACTION_RE.search(text)
    assert match is not None
    reaction = " ".join(match.group(1).split())
    normalized, reactants, products = normalize_reaction(reaction)

    assert normalized == "e + N₂(A³Σᵤ⁺) -> N₂ + e"
    assert reactants == ["e", "N₂(A³Σᵤ⁺)"]
    assert products == ["N₂", "e"]
