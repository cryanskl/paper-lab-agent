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


def test_sections_from_tei_uses_grobid_labels_for_table_and_figure_titles():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <figure type="table">
            <label>Table 7</label>
            <figDesc>Electron impact reactions.</figDesc>
            <p>e + Ar -> e + e + Ar+</p>
          </figure>
          <figure>
            <label>Figure 3</label>
            <figDesc>Electron density profile.</figDesc>
          </figure>
          <table>
            <label>Table A1</label>
            <row><cell>Reaction</cell><cell>Rate</cell></row>
          </table>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Table 7",
            "content": "Electron impact reactions. e + Ar -> e + e + Ar+",
            "section_type": "table",
        },
        {
            "seq": 2,
            "title": "Figure 3",
            "content": "Electron density profile.",
            "section_type": "figure_caption",
        },
        {
            "seq": 3,
            "title": "Table A1",
            "content": "Reaction Rate",
            "section_type": "table",
        },
    ]


def test_sections_from_tei_preserves_table_notes_with_rows():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <table>
            <head>Table 2</head>
            <row><cell>Reaction</cell><cell>Rate</cell></row>
            <row><cell>e + Ar -> Ar+</cell><cell>1.0e-13 cm3/s</cell></row>
            <note>Rates are reported in the source paper without unit conversion.</note>
          </table>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Table 2",
            "content": (
                "Reaction Rate "
                "e + Ar -> Ar+ 1.0e-13 cm3/s "
                "Rates are reported in the source paper without unit conversion."
            ),
            "section_type": "table",
        }
    ]


def test_sections_from_tei_preserves_direct_body_and_div_notes():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <note>Global note: source data kept in original units.</note>
          <div>
            <head>Rate data</head>
            <p>Argon reaction rates are listed below.</p>
            <note>Footnote: values copied from the source table.</note>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Section 1",
            "content": "Global note: source data kept in original units.",
            "section_type": "body",
        },
        {
            "seq": 2,
            "title": "Rate data",
            "content": "Argon reaction rates are listed below. Footnote: values copied from the source table.",
            "section_type": "body",
        },
    ]


def test_sections_from_tei_preserves_direct_body_and_div_quote_blocks():
    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <quote>Quoted plasma kinetics note from the source.</quote>
          <div>
            <head>Cross-section sources</head>
            <p>The model cites the following source.</p>
            <cit>
              <quote>Electron impact cross sections are tabulated in LXCat.</quote>
              <bibl>LXCat Argon set</bibl>
            </cit>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Section 1",
            "content": "Quoted plasma kinetics note from the source.",
            "section_type": "body",
        },
        {
            "seq": 2,
            "title": "Cross-section sources",
            "content": (
                "The model cites the following source. "
                "Electron impact cross sections are tabulated in LXCat. LXCat Argon set"
            ),
            "section_type": "body",
        },
    ]
