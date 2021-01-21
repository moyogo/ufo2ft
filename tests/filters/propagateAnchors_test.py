import pytest
from fontTools.misc.loggingTools import CapturingLogHandler

import ufo2ft.filters
from ufo2ft.constants import OPENTYPE_CATEGORIES_KEY
from ufo2ft.filters.propagateAnchors import PropagateAnchorsFilter, logger

EXPECTED_MODIFIED = {
    "a-cyr",
    "amacron",
    "adieresis",
    "adieresismacron",
    "amacronbelow",
    "amacrondieresis",
    "a_a",
    "dieresis",
    "emacron",
    "macroncomb.alt",
    "ohorn",
}


@pytest.fixture(
    params=[
        {
            "glyphs": [
                {"name": "space", "width": 500},
                {
                    "name": "a",
                    "unicodes": [0x0061],
                    "width": 350,
                    "outline": [
                        ("moveTo", ((0, 0),)),
                        ("lineTo", ((300, 0),)),
                        ("lineTo", ((300, 300),)),
                        ("lineTo", ((0, 300),)),
                        ("closePath", ()),
                    ],
                    "anchors": [(175, 300, "top"), (175, 0, "bottom")],
                },
                {
                    "name": "dieresiscomb",
                    "unicodes": [0x0308],
                    "width": 0,
                    "outline": [
                        ("moveTo", ((-120, 320),)),
                        ("lineTo", ((-60, 320),)),
                        ("lineTo", ((-60, 360),)),
                        ("lineTo", ((-120, 360),)),
                        ("closePath", ()),
                        ("moveTo", ((120, 320),)),
                        ("lineTo", ((60, 320),)),
                        ("lineTo", ((60, 360),)),
                        ("lineTo", ((120, 360),)),
                        ("closePath", ()),
                    ],
                    "anchors": [(0, 300, "_top"), (0, 480, "top")],
                },
                {
                    "name": "dieresis",
                    "unicodes": [0x00A8],
                    "width": 300,
                    "outline": [
                        ("addComponent", ("dieresiscomb", (1, 0, 0, 1, 150, 0)))
                    ],
                },
                {
                    "name": "macroncomb",
                    "width": 0,
                    "outline": [
                        ("moveTo", ((-120, 330),)),
                        ("lineTo", ((120, 330),)),
                        ("lineTo", ((120, 350),)),
                        ("lineTo", ((-120, 350),)),
                        ("closePath", ()),
                    ],
                    "anchors": [(0, 300, "_top"), (0, 480, "top")],
                },
                {
                    "name": "a-cyr",
                    "unicodes": [0x0430],
                    "width": 350,
                    "outline": [("addComponent", ("a", (1, 0, 0, 1, 0, 0)))],
                },
                {
                    "name": "amacron",
                    "unicodes": [0x0101],
                    "width": 350,
                    "outline": [
                        ("addComponent", ("a", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("macroncomb", (1, 0, 0, 1, 175, 0))),
                    ],
                    "anchors": [(175, 481, "top")],
                },
                {
                    "name": "adieresis",
                    "unicodes": [0x00E4],
                    "width": 350,
                    "outline": [
                        ("addComponent", ("a", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("dieresiscomb", (1, 0, 0, 1, 175, 0))),
                    ],
                },
                {
                    "name": "amacrondieresis",
                    "width": 350,
                    "outline": [
                        ("addComponent", ("amacron", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("dieresiscomb", (1, 0, 0, 1, 175, 180))),
                    ],
                },
                {
                    "name": "adieresismacron",
                    "width": 350,
                    "outline": [
                        ("addComponent", ("a", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("dieresiscomb", (1, 0, 0, 1, 175, 0))),
                        ("addComponent", ("macroncomb", (1, 0, 0, 1, 175, 180))),
                    ],
                },
                {
                    "name": "a_a",
                    "width": 700,
                    "outline": [
                        ("addComponent", ("a", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("a", (1, 0, 0, 1, 350, 0))),
                    ],
                    "category": "ligature",
                },
                {
                    "name": "emacron",
                    "unicodes": [0x0113],
                    "width": 350,
                    "outline": [
                        ("addComponent", ("e", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("macroncomb", (1, 0, 0, 1, 175, 0))),
                    ],
                },
                {
                    "name": "macroncomb.alt",
                    "width": 0,
                    "outline": [
                        ("addComponent", ("macroncomb", (1, 0, 0, 1, 0, -30))),
                    ],
                    "anchors": [(0, 340, "_top")],
                },
                {
                    "name": "o",
                    "unicodes": [0x006F],
                    "width": 350,
                    "outline": [
                        ("moveTo", ((20, 0),)),
                        ("lineTo", ((330, 0),)),
                        ("lineTo", ((330, 330),)),
                        ("lineTo", ((20, 330),)),
                        ("closePath", ()),
                        ("moveTo", ((40, 20),)),
                        ("lineTo", ((310, 0),)),
                        ("lineTo", ((310, 310),)),
                        ("lineTo", ((40, 310),)),
                        ("closePath", ()),
                    ],
                    "anchors": [(175, 340, "top"), (175, 0, "bottom")],
                },
                {
                    "name": "ohorn",
                    "unicodes": [0x01A1],
                    "width": 350,
                    "outline": [
                        ("moveTo", ((310, 310),)),
                        ("lineTo", ((345, 310),)),
                        ("lineTo", ((345, 345),)),
                        ("lineTo", ((345, 345),)),
                        ("closePath", ()),
                        ("addComponent", ("o", (1, 0, 0, 1, 0, 0))),
                    ],
                    "anchors": [(345, 340, "topright")],
                },
                {
                    "name": "macronbelowcomb",
                    "unicodes": [0x0331],
                    "width": 0,
                    "outline": [
                        ("addComponent", ("macroncomb", (1, 0, 0, 1, 0, -430))),
                    ],
                    "anchors": [(0, 0, "_bottom"), (0, -180, "bottom")],
                },
                {
                    "name": "amacronbelow",
                    "width": 350,
                    "outline": [
                        ("addComponent", ("a", (1, 0, 0, 1, 0, 0))),
                        ("addComponent", ("macronbelowcomb", (1, 0, 0, 1, 175, 0))),
                    ],
                },
                {
                    "name": "circumflexcomb",
                    "unicodes": [0x0302],
                    "width": 0,
                    "outline": [
                        ("moveTo", ((-120, 330),)),
                        ("lineTo", ((-100, 330),)),
                        ("lineTo", ((0, 400),)),
                        ("lineTo", ((100, 330),)),
                        ("lineTo", ((120, 330),)),
                        ("lineTo", ((0, 430),)),
                        ("closePath", ()),
                    ],
                    "anchors": [(0, 300, "_top"), (0, 480, "top")],
                },
                {
                    "name": "caroncomb",
                    "unicodes": [0x0304],
                    "width": 0,
                    "outline": [
                        ("addComponent", ("circumflexcomb", (1, 0, 0, -1, 0, 760))),
                    ],
                    "anchors": [(0, 0, "_bottom"), (0, -280, "bottom")],
                },
                {
                    "name": "caronbelowcomb",
                    "unicodes": [0x032C],
                    "width": 0,
                    "outline": [
                        ("addComponent", ("circumflexcomb", (-1, 0, 0, -1, 0, 280))),
                    ],
                    "anchors": [(0, 0, "_bottom"), (0, -280, "bottom")],
                },
            ]
        }
    ]
)
def font(request, FontClass):
    font = FontClass()
    for param in request.param["glyphs"]:
        glyph = font.newGlyph(param["name"])
        glyph.unicodes = param.get("unicodes", [])
        glyph.width = param.get("width", 0)
        pen = glyph.getPen()
        for operator, operands in param.get("outline", []):
            getattr(pen, operator)(*operands)
        for x, y, name in param.get("anchors", []):
            glyph.appendAnchor(dict(x=x, y=y, name=name))
        category = param.get("category")
        if category:
            if not font.lib.get(OPENTYPE_CATEGORIES_KEY):
                font.lib[OPENTYPE_CATEGORIES_KEY] = dict()
            font.lib[OPENTYPE_CATEGORIES_KEY][glyph.name] = category
    return font


class PropagateAnchorsFilterTest:
    def test_empty_glyph(self, font):
        philter = PropagateAnchorsFilter(include={"space"})
        assert not philter(font)

    def test_contour_glyph(self, font):
        philter = PropagateAnchorsFilter(include={"a"})
        assert not philter(font)

    def test_single_component_glyph(self, font):
        philter = PropagateAnchorsFilter(include={"a-cyr"})
        assert philter(font) == {"a-cyr"}
        assert [(a.name, a.x, a.y) for a in font["a-cyr"].anchors] == [
            ("bottom", 175, 0),
            ("top", 175, 300),
        ]

    def test_single_component_mark_glyph(self, font):
        name = "dieresis"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("top", 150, 480),
        ]

    def test_two_component_glyph(self, font):
        name = "adieresis"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("bottom", 175, 0),
            ("top", 175, 480),
        ]

    def test_one_anchor_two_component_glyph(self, font):
        name = "amacron"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("top", 175, 481),
            ("bottom", 175, 0),
        ]

    def test_three_component_glyph(self, font):
        name = "adieresismacron"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("bottom", 175, 0),
            ("top", 175, 660),
        ]

    def test_nested_component_glyph(self, font):
        name = "amacrondieresis"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("bottom", 175, 0),
            ("top", 175, 660),
        ]

    def test_similar_anchor_name(self, font):
        name = "ohorn"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("topright", 345, 340),
            ("bottom", 175, 0),
            ("top", 175, 340),
        ]

    def test_ligature_glyph(self, font):
        name = "a_a"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("bottom_1", 175, 0),
            ("bottom_2", 525, 0),
            ("top_1", 175, 300),
            ("top_2", 525, 300),
        ]

    def test_mark_glyph(self, font):
        name = "macroncomb.alt"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("_top", 0, 340),
            ("top", 0, 450),
        ]

    def test_top_bottom_mark_single_component(self, font):
        name = "macronbelowcomb"
        philter = PropagateAnchorsFilter(include={name})
        assert not philter(font)

        name = "amacronbelow"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert [(a.name, a.x, a.y) for a in font[name].anchors] == [
            ("bottom", 175, -180),
            ("top", 175, 300),
        ]

    def test_transformed_top_bottom_mark_component(self, font):
        name = "caroncomb"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) is None

        name = "caronbelowcomb"
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) is None

    def test_whole_font(self, font):
        philter = PropagateAnchorsFilter()
        modified = philter(font)
        assert modified == EXPECTED_MODIFIED

    def test_whole_font_custom_attachments(self, font):
        philter = PropagateAnchorsFilter(
            attachments=[
                {"base": ["top"], "mark": ["_top"]},
                {"base": ["bottom"], "mark": ["_bottom"]},
            ]
        )
        modified = philter(font)
        assert modified == EXPECTED_MODIFIED

    def test_fail_during_anchor_propagation(self, font):
        name = "emacron"
        with CapturingLogHandler(logger, level="WARNING") as captor:
            philter = PropagateAnchorsFilter(include={name})
            philter(font)
        captor.assertRegex(
            "Anchors not propagated for inexistent component e " "in glyph emacron"
        )

    def test_logger(self, font):
        with CapturingLogHandler(logger, level="INFO") as captor:
            philter = PropagateAnchorsFilter()
            philter(font)
        captor.assertRegex(
            "Glyphs with propagated anchors: %i" % len(EXPECTED_MODIFIED)
        )


def test_CantarellAnchorPropagation(FontClass, datadir):
    ufo_path = datadir.join("CantarellAnchorPropagation.ufo")
    ufo = FontClass(ufo_path)
    pre_filters, _ = ufo2ft.filters.loadFilters(ufo)

    philter = pre_filters[0]
    philter(ufo)

    anchors_combined = {
        (a.name, a.x, a.y) for a in ufo["circumflexcomb_tildecomb"].anchors
    }
    assert anchors_combined == {
        ("_top", 213.0, 482.0),
        ("top", 214.0, 730.0),
    }

    anchors_o = {(a.name, a.x, a.y) for a in ufo["ocircumflextilde"].anchors}
    assert anchors_o == {("bottom", 283.0, 0.0), ("top", 284.0, 730.0)}

    anchors_bottom_in_top = {(a.name, a.x, a.y) for a in ufo["shadda_kasra-ar"].anchors}
    assert anchors_bottom_in_top == {
        ("_top", 56, 674),
        ("top", 0, 1044),
    }


def test_CantarellAnchorPropagation_openTypeCategories(FontClass, datadir):
    ufo_path = datadir.join("CantarellAnchorPropagation.ufo")
    ufo = FontClass(ufo_path)
    ufo.lib["public.openTypeCategories"] = {
        "circumflexcomb.loclVIET": "mark",
        "circumflexcomb_tildecomb": "mark",
        "o": "base",
        "ocircumflextilde": "base",
        "tildecomb.loclVIET": "mark",
    }
    pre_filters, _ = ufo2ft.filters.loadFilters(ufo)

    philter = pre_filters[0]
    philter(ufo)

    anchors_combined = {
        (a.name, a.x, a.y) for a in ufo["circumflexcomb_tildecomb"].anchors
    }
    assert anchors_combined == {
        ("_top", 213.0, 482.0),
        ("top", 214.0, 730.0),
    }

    anchors_o = {(a.name, a.x, a.y) for a in ufo["ocircumflextilde"].anchors}
    assert anchors_o == {("bottom", 283.0, 0.0), ("top", 284.0, 730.0)}


def test_CantarellAnchorPropagation_reduced_filter(FontClass, datadir):
    ufo_path = datadir.join("CantarellAnchorPropagation.ufo")
    ufo = FontClass(ufo_path)
    ufo.lib["com.github.googlei18n.ufo2ft.filters"][0]["include"] = ["ocircumflextilde"]
    pre_filters, _ = ufo2ft.filters.loadFilters(ufo)

    philter = pre_filters[0]
    philter(ufo)

    anchors_combined = {
        (a.name, a.x, a.y) for a in ufo["circumflexcomb_tildecomb"].anchors
    }
    assert anchors_combined == {
        ("_top", 213.0, 482.0),
        ("top", 214.0, 730.0),
    }

    anchors_o = {(a.name, a.x, a.y) for a in ufo["ocircumflextilde"].anchors}
    assert anchors_o == {("bottom", 283.0, 0.0), ("top", 284.0, 730.0)}


def test_get_anchor_attachment(FontClass):
    ufo = FontClass()
    g = ufo.newGlyph("a")
    g.appendAnchor(dict(x=300, y=500, name="top"))
    g.appendAnchor(dict(x=300, y=0, name="bottom"))
    g = ufo.newGlyph("acutecomb")
    g.appendAnchor(dict(x=0, y=500, name="_top"))
    g = ufo.newGlyph("dotbelowcomb")
    g.appendAnchor(dict(x=0, y=0, name="_bottom"))
    g = ufo.newGlyph("circumflexcomb")
    g.appendAnchor(dict(x=0, y=560, name="top"))
    g.appendAnchor(dict(x=40, y=540, name="top_viet"))
    g.appendAnchor(dict(x=0, y=500, name="_top"))
    g = ufo.newGlyph("f_f")
    g.appendAnchor(dict(x=200, y=500, name="top_1"))
    g.appendAnchor(dict(x=600, y=500, name="top_2"))

    philter = PropagateAnchorsFilter()
    philter(ufo)
    attachment = philter.get_anchor_attachment("top")
    assert sorted(attachment.base) == ["top", "top_1", "top_2", "top_viet"]
    assert sorted(attachment.mark) == ["_top"]
    assert philter.get_anchor_attachment("_top") == philter.get_anchor_attachment("top")
    assert philter.get_anchor_attachment("top_1") == philter.get_anchor_attachment(
        "top"
    )
    assert philter.get_anchor_attachment("top_viet") == philter.get_anchor_attachment(
        "top"
    )
    attachment = philter.get_anchor_attachment("bottom")
    assert sorted(attachment.base) == ["bottom"]
    assert sorted(attachment.mark) == ["_bottom"]
    assert philter.get_anchor_attachment("_bottom") == philter.get_anchor_attachment(
        "bottom"
    )
