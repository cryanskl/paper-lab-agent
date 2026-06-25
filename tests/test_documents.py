from app.services.documents import sections_from_tei


def test_sections_from_tei_preserves_grobid_table_figure_caption_and_cells():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <front>
          <abstract><p>Electron impact reactions in argon plasma.</p></abstract>
        </front>
        <body>
          <div>
            <head>Results</head>
            <p>The body discusses plasma chemistry.</p>
            <figure type="table">
              <head>Table 1</head>
              <figDesc>Measured rate coefficients.</figDesc>
              <table>
                <row>
                  <cell>Reaction</cell>
                  <cell>Rate</cell>
                </row>
                <row>
                  <cell>e + Ar -> e + e + Ar+</cell>
                  <cell>original source value</cell>
                </row>
              </table>
            </figure>
            <figure type="figure">
              <head>Figure 1</head>
              <figDesc>Electron density profile.</figDesc>
            </figure>
          </div>
        </body>
        <back>
          <listBibl>
            <biblStruct><analytic><title>Reference paper</title></analytic></biblStruct>
          </listBibl>
        </back>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)
    by_type = {}
    for section in sections:
        by_type.setdefault(section["section_type"], []).append(section)

    assert by_type["abstract"][0]["content"] == "Electron impact reactions in argon plasma."
    assert by_type["body"][0]["title"] == "Results"
    assert "plasma chemistry" in by_type["body"][0]["content"]
    assert by_type["table"][0]["title"] == "Table 1"
    assert "Measured rate coefficients." in by_type["table"][0]["content"]
    assert "e + Ar -> e + e + Ar+ original source value" in by_type["table"][0]["content"]
    assert by_type["figure_caption"][0]["title"] == "Figure 1"
    assert by_type["figure_caption"][0]["content"] == "Electron density profile."
    assert by_type["reference"][0]["content"] == "Reference paper"


def test_sections_from_tei_reads_header_profile_abstract():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <profileDesc>
          <abstract>
            <p>Low temperature plasma kinetics from the TEI header.</p>
          </abstract>
        </profileDesc>
      </teiHeader>
      <text>
        <body>
          <div>
            <head>Introduction</head>
            <p>The body section remains available.</p>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)
    by_type = {}
    for section in sections:
        by_type.setdefault(section["section_type"], []).append(section)

    assert by_type["abstract"][0]["content"] == "Low temperature plasma kinetics from the TEI header."
    assert by_type["body"][0]["title"] == "Introduction"


def test_sections_from_tei_deduplicates_repeated_header_and_front_abstracts():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <profileDesc>
          <abstract>
            <p>Repeated plasma abstract.</p>
          </abstract>
        </profileDesc>
      </teiHeader>
      <text>
        <front>
          <abstract>
            <p>Repeated plasma abstract.</p>
          </abstract>
        </front>
        <body>
          <div>
            <head>Introduction</head>
            <p>The body section remains available.</p>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)
    abstracts = [section for section in sections if section["section_type"] == "abstract"]

    assert [abstract["content"] for abstract in abstracts] == ["Repeated plasma abstract."]
