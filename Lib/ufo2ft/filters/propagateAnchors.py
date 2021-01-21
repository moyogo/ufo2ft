# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re
from collections import defaultdict
from functools import partial
from types import SimpleNamespace

from fontTools.misc.transform import Transform

from ufo2ft.constants import OPENTYPE_CATEGORIES_KEY
from ufo2ft.filters import BaseFilter
from ufo2ft.util import unicodeInCategories

logger = logging.getLogger(__name__)


VERTICAL_OPPOSITES = {
    "top": "bottom",
    "topleft": "bottomleft",
    "topright": "bottomright",
    "bottom": "top",
    "bottomleft": "topleft",
    "bottomright": "topright",
}
HORIZONTAL_OPPOSITES = {
    "bottomleft": "bottomright",
    "bottomright": "bottomleft",
    "topleft": "topright",
    "topright": "topleft",
}


class Attachment:
    def __init__(self, base=None, mark=None):
        if base:
            self.base = base
        else:
            self.base = []

        if mark:
            self.mark = mark
        else:
            self.mark = []

    def __str__(self):
        return "Attachments(base=[%s], mark=[%s]" % (
            ", ".join(f'"{b}"' for b in self.base),
            ", ".join(f'"{m}"' for m in self.mark),
        )


class PropagateAnchorsFilter(BaseFilter):
    """
    Filter that propagates anchors from glyphs to composite glyphs using them as
    components. Some anchors are not copied depending on whether the composite
    glyph is a base (normal) glyph, a mark glyph or a ligature glyph.
    """

    _kwargs = dict(
        vertical_opposites=VERTICAL_OPPOSITES,
        horizontal_opposites=HORIZONTAL_OPPOSITES,
        attachments=None,
        markRE="^_",
    )
    unicodeMarkCategories = frozenset(
        {
            "Mn",  # Nonspacing_Mark
            "Me",  # Enclosing_Mark
            # Mc Spacing_Mark shouldn't be OpenType marks
        }
    )

    def set_context(self, font, glyphSet):
        ctx = super().set_context(font, glyphSet)
        ctx.processed = set()
        ctx.attachments = self._collect_attachments()
        return ctx

    def __call__(self, font, glyphSet=None):
        if super().__call__(font, glyphSet):
            modified = self.context.modified
            if modified:
                logger.info("Glyphs with propagated anchors: %i" % len(modified))
            return modified

    def filter(self, glyph):
        if not glyph.components:
            return False
        before = len(glyph.anchors)
        after = len(self._propagate_glyph_anchors(glyph))
        return after > before

    def get_glyph_category(self, glyph):
        font = self.context.font
        category = font.lib.get(OPENTYPE_CATEGORIES_KEY, {}).get(glyph.name)
        glyphSet = self.context.glyphSet

        # Use openTypeCategories if possible
        if category:
            return category

        # Try Unicode category
        unicodeIsMark = partial(
            unicodeInCategories, categories=self.unicodeMarkCategories
        )
        if glyph.unicode:
            # Guess category from Unicode value
            uv = glyph.unicode
            if unicodeIsMark(uv):
                return "mark"
            else:
                return "base"

        # Consider it a mark if it has mark anchors
        for anchor in glyph.anchors:
            attachment = self.get_anchor_attachment(anchor.name)
            if not attachment:
                continue
            elif anchor.name in attachment.mark:
                return "mark"

        # Look at components to guess category
        if glyph.components:
            component_categories = dict()
            for i, component in enumerate(glyph.components):
                if component.baseGlyph in glyphSet:
                    baseGlyph = glyphSet[component.baseGlyph]
                    baseCategory = self.get_glyph_category(baseGlyph)
                    if baseCategory:
                        component_categories[(component.baseGlyph, i)] = baseCategory

            # If all components are marks, assume it's mark
            if all(v == "mark" for v in component_categories.values()):
                return "mark"

    def _collect_attachments(self):
        # Use the options attachments if defined
        if self.options.attachments:
            return {Attachment(a["base"], a["mark"]) for a in self.options.attachments}

        # Collect anchor names to build an attachment mapping
        # <Attachment base=["top", "top_1", "top_2"], mark="["_top"]>
        anchor_names = set()
        for glyph in self.context.font:
            for anchor in glyph.anchors:
                anchor_names.add(anchor.name)

        attachments_dict = defaultdict(Attachment)
        # attachments_dict = {
        #     "top": {
        #         <Attachment base={"top", "top_1", "top_2", ..}, mark={"_top"}>,
        #         ...
        #     }
        # }
        for anchor_name in anchor_names:
            # "_top"
            m = self._mark_anchor_name(anchor_name)
            if m:
                key = anchor_name.replace(m.group(0), "", 1)
                if anchor_name not in attachments_dict[key].mark:
                    attachments_dict[key].mark.append(anchor_name)
            # "top_1" or "top_viet"
            elif anchor_name.find("_") > 0:
                key = anchor_name.rsplit("_", 1)[0]
                if anchor_name not in attachments_dict[key].base:
                    attachments_dict[key].base.append(anchor_name)
            # "top"
            else:
                key = anchor_name
                if anchor_name not in attachments_dict[key].base:
                    attachments_dict[key].base.append(anchor_name)
        return set(at for at in attachments_dict.values() if at.base and at.mark)

    def get_anchor_attachment(self, name):
        # find attachment with name
        for attachment in self.context.attachments:
            if name in attachment.base or name in attachment.mark:
                return attachment

    def _mark_anchor_name(self, anchorName):
        return re.match(self.options.markRE, anchorName)

    def _prune_attached_anchors(self, propagated_anchors, mode=None):
        # Remove anchors that are probably attached, i.e. remove pairs
        # of anchors that have matching anchor_attachment, except the furthest
        # pair when mode="mark".
        # For each mark anchor, find closest base anchor and remove the pair
        # Also remove all base anchors with the same anchor_attachment and
        # the same component as the closest base anchor.
        matched_anchors = dict()
        for pa1 in list(propagated_anchors):
            if pa1.anchor.name not in pa1.attachment.mark:
                continue
            elif not pa1.component_is_mark:
                continue

            matched = matched_distance = None

            for pa2 in list(propagated_anchors):
                if pa1 == pa2:
                    continue
                elif pa1.attachment != pa2.attachment:
                    continue
                elif pa2.anchor.name not in pa1.attachment.base:
                    continue
                elif pa1.component == pa2.component:
                    continue

                if not matched:
                    matched = pa2
                    matched_distance = _distance(
                        (pa1.anchor.x, pa1.anchor.y),
                        (pa2.anchor.x, pa2.anchor.y),
                    )
                else:
                    distance = _distance(
                        (pa1.anchor.x, pa1.anchor.y),
                        (pa2.anchor.x, pa2.anchor.y),
                    )
                    if distance < matched_distance:
                        matched = pa2
                        matched_distance = distance

            if matched:
                matched_anchors.setdefault(pa1.anchor.name, []).append(
                    (matched_distance, pa1, matched)
                )

        # Remove the mark anchor pa1, the matched base anchor pa2,
        # (except the further pair when mode="mark"),
        # and also all the base anchor pa with the same component
        # as pa2.component.
        # For example if _top of comp2 has a matched top in comp1,
        # also remove top_viet in comp1.
        for matches in matched_anchors.values():
            num = len(matches) - 1
            for i, (_dist, pa1, pa2) in enumerate(sorted(matches, key=lambda t: t[0])):
                if mode == "mark" and i == num:
                    break
                propagated_anchors.remove(pa1)
                propagated_anchors.remove(pa2)
                for pa in list(propagated_anchors):
                    if (
                        pa.component == pa2.component
                        and pa.anchor.name in pa2.attachment.base
                    ):
                        propagated_anchors.remove(pa)

    def _prune_opposite_mark_anchors(self, glyph, propagated_anchors):
        glyph_anchor_names = {a.name for a in glyph.anchors}
        # Prune anchors if opposites present in glyph
        for pa in list(propagated_anchors):
            opposites = set()
            for name in pa.attachment.base:
                if name in self.options.vertical_opposites:
                    opposites.add(self.options.vertical_opposites[name])
                if name in self.options.horizontal_opposites:
                    opposites.add(self.options.horizontal_opposites[name])
            if opposites.intersection(glyph_anchor_names):
                propagated_anchors.remove(pa)

    def _rename_composite_ligature_anchors(self, glyph, propagated_anchors):
        anchor_names = set(pa.anchor.name for pa in propagated_anchors)
        counters = defaultdict(int)
        for pa in list(propagated_anchors):
            if pa.anchor.name in anchor_names:
                counters[pa.anchor.name] += 1
                i = counters[pa.anchor.name]
                pa.anchor.name = "%s_%d" % (pa.anchor.name, i)

    def _prune_mark_anchors(self, propagated_anchors):
        for pa in list(propagated_anchors):
            if pa.anchor.name in pa.attachment.mark:
                propagated_anchors.remove(pa)

    def _collect_components_anchors(self, glyph):
        glyphSet = self.context.glyphSet
        propagated_anchors = []

        # First pass to progate anchors to components recursively
        # and store their transformed anchors to be imported.
        for component in glyph.components:
            try:
                component_glyph = glyphSet[component.baseGlyph]
            except KeyError:
                logger.warning(
                    "Anchors not propagated for inexistent component {} "
                    "in glyph {}".format(component.baseGlyph, glyph.name)
                )
                continue

            component_anchors = self._propagate_glyph_anchors(component_glyph)

            component_is_mark = any(
                self._mark_anchor_name(a.name) for a in component_glyph.anchors
            )

            t = Transform(*component.transformation)
            # copy anchors so only transform anchors onces
            for a in component_anchors:
                # ufoLib2
                # if not hasattr(anchor, "name"):
                #     anchor = SimpleNamespace(
                #         name=anchor[0], x=anchor[0][0], y=anchor[0][1]
                #     )
                # else:
                #     anchor = SimpleNamespace(
                #         name=anchor.name, x=anchor.x, y=anchor.y
                #     )
                anchor = SimpleNamespace(name=a.name, x=a.x, y=a.y)

                # Rename anchor in flipped components
                # Note: 180deg rotation means horizontal and vertical flipping.
                # Horizontally
                if t[0] < 0 and anchor.name in self.options.horizontal_opposites:
                    anchor.name = self.options.horizontal_opposites[anchor.name]

                # Vertically
                if t[3] < 0 and anchor.name in self.options.vertical_opposites:
                    self.options.vertical_opposites[anchor.name]

                # Transform anchors with component's transform
                if t != (1, 0, 0, 1, 0, 0):
                    (anchor.x, anchor.y) = t.transformPoint((anchor.x, anchor.y))

                propagated_anchors.append(
                    SimpleNamespace(
                        component=component,
                        component_is_mark=component_is_mark,
                        anchor=anchor,
                        attachment=self.get_anchor_attachment(anchor.name),
                    )
                )
        return propagated_anchors

    def _propagate_glyph_anchors(self, glyph):
        processed = self.context.processed

        # This glyph has already been process and it’s anchors are up to date
        if glyph.name in processed:
            return glyph.anchors
        processed.add(glyph.name)

        # This glyph has no components, no anchors will be updated
        if not glyph.components:
            return glyph.anchors

        # This is an unprocessed composite glyph
        # collect all component anchors as propagated anchors
        # to be pruned or added
        propagated_anchors = self._collect_components_anchors(glyph)

        # Get glyph category
        glyph_category = self.get_glyph_category(glyph)

        glyph_anchor_names = {a.name for a in glyph.anchors}
        for pa in list(propagated_anchors):
            # Prune anchors with undefined attachments:
            if pa.attachment is None:
                propagated_anchors.remove(pa)
            # Prune anchors that are already in glyph
            elif pa.anchor.name in glyph_anchor_names:
                propagated_anchors.remove(pa)

        # Prune unwanted anchors based on glyph category
        if glyph_category == "base":
            # Drop attached anchors and mark anchors
            self._prune_attached_anchors(propagated_anchors)
            self._prune_mark_anchors(propagated_anchors)

        elif glyph_category == "mark":
            self._prune_opposite_mark_anchors(glyph, propagated_anchors)
            self._prune_attached_anchors(propagated_anchors, "mark")

        elif glyph_category == "ligature":
            self._prune_attached_anchors(propagated_anchors)
            self._prune_mark_anchors(propagated_anchors)
            self._rename_composite_ligature_anchors(glyph, propagated_anchors)

        else:
            self._prune_attached_anchors(propagated_anchors)

        for pa in sorted(
            propagated_anchors,
            key=lambda pa: (pa.anchor.name, pa.anchor.x, pa.anchor.y),
        ):
            name, x, y = pa.anchor.name, pa.anchor.x, pa.anchor.y
            try:
                glyph.appendAnchor({"name": name, "x": x, "y": y})
            except TypeError:  # pragma: no cover
                # fontParts API
                glyph.appendAnchor(name, (x, y))

        return glyph.anchors


def _distance(pos1, pos2):
    x1, y1 = pos1
    x2, y2 = pos2
    return (x1 - x2) ** 2 + (y1 - y2) ** 2
