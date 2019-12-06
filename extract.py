import os
import pprint
import sys

from pdfquery import PDFQuery
from pdfquery.cache import FileCache
from pdfminer.pdfinterp import resolve1

class Point(object):
    def __init__(self, x: float = 0, y: float = 0):
        self.data: [float, float] = [x, y]

    def __str__(self) -> str:
        return "point(%s,%s)" % (self.x, self.y)

    def __getitem__(self, item) -> float:
        return self.data[item]

    def __setitem__(self, idx: int, value: float):
        self.data[idx] = value

    @property
    def x(self) -> float:
        return self.data[0]

    @property
    def y(self) -> float:
        return self.data[1]

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def load_pdf(file: str, cache_dir: str = "./.cache/") -> PDFQuery:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    pdf = PDFQuery("./testdata/test.pdf", parse_tree_cacher=FileCache(cache_dir))
    pdf.load()
    return pdf

def get_page_count(pdf: PDFQuery) -> int:
    return resolve1(pdf.doc.catalog['Pages'])['Count']

def get_selector_for_element_text(pdf: PDFQuery, descriptor: str, underlaying_descriptor: str, value_deviations: (Point, Point), page: int):
    """Extracts a text value from the given handbook based on descriptors

    The operation is based on a descriptor of the value to extract and an underlaying descriptor used
    to calculate the bounding box of the value of interest on the page.
    You can use value_derivations to adjust the calculated bounding box.
    ┌────────────────────────┬──────────────────────────┐
    │ descriptor             │ This is the text we want │
    ├────────────────────────┼──────────────────────────┤
    │ underlaying_descriptor │ uninteresting text       │
    └────────────────────────┴──────────────────────────┘
    """

    descriptor_element = pdf.pq('LTPage[page_index="%s"] LTTextLineHorizontal:contains("%s")' % (page, descriptor))
    if len(descriptor_element) < 1:
        raise ValueError("Descriptor \"%s\" not found on page %s" % (descriptor, page + 1))

    underlaying_descriptor_element = pdf.pq('LTPage[page_index="%s"] LTTextLineHorizontal:contains("%s")' % (page, underlaying_descriptor))
    if len(underlaying_descriptor_element) < 1:
        raise ValueError("Underlaying descriptor \"%s\" not found on page %s" % (underlaying_descriptor, page + 1))

    value_coords = (
        Point(
            float(descriptor_element.attr('x0')) + value_deviations[0].x,
            float(underlaying_descriptor_element.attr('y1')) + value_deviations[0].y
        ),
        Point(
            float(descriptor_element.attr('x0')) + value_deviations[1].x,
            float(descriptor_element.attr('y1')) + value_deviations[1].y
        )
    )
    return (descriptor.lower(), 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (value_coords[0].x, value_coords[0].y, value_coords[1].x, value_coords[1].y), lambda match: match.text().strip())

def extract_competencies(pdf: PDFQuery):
    page_count = get_page_count(pdf)
    results = []

    for i in range(page_count - 1):
        # Limit the extraction to the current page and only extract text
        selectors = [
            ('with_parent','LTPage[page_index="%s"]' % (i)),
            ('with_formatter', 'text'),
        ]

        try:
            selectors.append(get_selector_for_element_text(pdf, "Modulnummer", "Titel", (Point(120, 0), Point(455, 1)), i))
        except ValueError as err:
            print("No \"Modulnummer\" found on page %s, skipping..." % (i + 1))
            continue

        try:
            selectors.append(get_selector_for_element_text(pdf, "Titel", "Leistungspunkte", (Point(120,0), Point(455,1)), i))
        except ValueError as err:
            eprint("Error parsing \"Titel\": %s" % (err))

        try:
            selectors.append(get_selector_for_element_text(pdf, "Lernziele / Kompetenzen", "Voraussetzungen", (Point(120, 0), Point(455, 1)), i))
        except ValueError as err:
            eprint("Error parsing \"Lernziele / Kompetenzen\": %s" % (err))

        try:
            selectors.append(get_selector_for_element_text(pdf, "Voraussetzungen", "Niveaustufe", (Point(120, 0), Point(455, 1)), i))
        except ValueError as err:
            eprint("Error parsing \"Voraussetzungen\": %s" % (err))

        page_results = pdf.extract(selectors)
        page_results['page'] = i + 1
        results.append(page_results)

    return results

def main():
    pdf = load_pdf("./testdata/test.pdf")
    results = extract_competencies(pdf)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(results)

if __name__ == "__main__":
    main()
