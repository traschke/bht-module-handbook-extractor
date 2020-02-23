#!/usr/bin/env python

import os
import pprint
import sys
import re
import argparse
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional

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

    pdf = PDFQuery(file, parse_tree_cacher=FileCache(cache_dir))
    pdf.load()
    return pdf

def get_page_count(pdf: PDFQuery) -> int:
    return resolve1(pdf.doc.catalog['Pages'])['Count']

def get_selector_for_element_text(pdf: PDFQuery, page: int, descriptors: Tuple[str], underlaying_descriptors: Tuple[str], value_deviations: (Point, Point), desc: Optional[str] = None):
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
    for descriptor in descriptors:
        descriptor_element = pdf.pq('LTPage[page_index="%s"] LTTextLineHorizontal:contains("%s")' % (page, descriptor))
        if len(descriptor_element) >= 1:
            break

    if len(descriptor_element) < 1:
        raise ValueError("Descriptor \"%s\" not found on page %s" % (descriptor, page + 1))

    for underlaying_descriptor in underlaying_descriptors:
        underlaying_descriptor_element = pdf.pq('LTPage[page_index="%s"] LTTextLineHorizontal:contains("%s")' % (page, underlaying_descriptor))
        if len(underlaying_descriptor_element) >= 1:
            break

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
    if desc is None:
        desc = descriptor.lower()
    # print("Page %s: bbox for %s: %s, %s" % (page + 1, desc, value_coords[0], value_coords[1]))
    return (desc, 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (value_coords[0].x, value_coords[0].y, value_coords[1].x, value_coords[1].y), lambda match: match.text().strip())

def extract_competencies(pdf: PDFQuery) -> List[Dict]:
    page_count = get_page_count(pdf)
    results: List[Dict] = []

    for i in range(page_count - 1):
        # Limit the extraction to the current page and only extract text
        selectors = [
            ('with_parent','LTPage[page_index="%s"]' % (i)),
            ('with_formatter', 'text'),
        ]

        # Try to find a "Modulnummer" on that page. If there is none, then it's not a module-description page.
        try:
            selectors.append(get_selector_for_element_text(pdf, i, ("Modulnummer",), ("Titel",), (Point(120, 0), Point(490, 1)), "id"))
        except ValueError as err:
            eprint("No \"Modulnummer\" found on page %s, skipping..." % (i + 1))
            continue

        # Find the module title
        try:
            selectors.append(get_selector_for_element_text(pdf, i, ("Titel",), ("Leistungspunkte", "Credits"), (Point(120,0), Point(490,1)), "name"))
        except ValueError as err:
            eprint("Error parsing \"Titel\": %s" % (err))

        # Find the module competencies
        try:
            selectors.append(get_selector_for_element_text(pdf, i, ("Lernziele / Kompetenzen","Lernziele/Kompetenzen"), ("Voraussetzungen",), (Point(120, 0), Point(490, 1)), "competencies"))
        except ValueError as err:
            eprint("Error parsing \"Lernziele / Kompetenzen\": %s" % (err))

        # Find the module requirements
        try:
            selectors.append(get_selector_for_element_text(pdf, i, ("Voraussetzungen",), ("Niveaustufe",), (Point(120, 0), Point(490, 1)), "requirements"))
        except ValueError as err:
            eprint("Error parsing \"Voraussetzungen\": %s" % (err))

        # Do the extraction
        page_results: Dict = pdf.extract(selectors)

        # Add the pagenumber for convenience reasons
        page_results['page'] = i + 1

        # Split the extracted sentences
        page_results['competencies'] = split_sentences(page_results['competencies'])
        page_results['requirements'] = split_sentences(page_results['requirements'])

        results.append(page_results)

    return results

def write_to_conll_directory_structure(results: List[Dict], path: str):
    folder_structure = Path(path)
    for result in results:
        # Remove any forbidden character from the filename
        try:
            escaped_name = re.sub(r"[^\w\-_\.]", "_", result["name"])
        except:
            escaped_name = "unknown"
        module_folder = folder_structure / ("%s-%s" % (result["id"], escaped_name))

        # Write competencies and requirements to specific files
        write_sentences_to_file(result["competencies"], module_folder / ("%s-competencies.txt" % (result["id"])))
        write_sentences_to_file(result["requirements"], module_folder / ("%s-requirements.txt" % (result["id"])))

def split_sentences(text: str) -> List[str]:
    # Split sentences at . ! or ?, but not if its preceeded by a number or an abbrevation like z.B. oder etc.
    split_pattern: str = r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<![0-9]\.)(?<=\.|\?|\!)\s"
    sentences = re.split(split_pattern, text)
    sentences = [sentence.strip() for sentence in sentences]

    # remove weird looking hyphenated words like "Fer- tigkeit"
    sentences = [re.sub(r"(?<!\s)(- )", "", sentence) for sentence in sentences]

    return sentences

def write_sentences_to_file(sentences: List[str], file: str):
    filePath: Path = Path(file)
    folder: Path = filePath.parent
    if not os.path.exists(folder):
            os.makedirs(folder)
    f = open(filePath, "w")
    f.writelines(sentence + '\n' for sentence in sentences)
    f.close()

def parse_args():
    parser = argparse.ArgumentParser(description="Extracts competencies and requirements from a module handbook.")
    parser.add_argument('pdf_file', metavar='pdf_file', type=str, nargs=1, help='the module handbook to be extracted')
    parser.add_argument('-o', metavar='output_directory', type=str, help='directory to write the extracted data to')

    return parser.parse_args()

def main():
    args = parse_args()

    pdf = load_pdf(args.pdf_file[0])
    results = extract_competencies(pdf)
    if args.o is not None:
        write_to_conll_directory_structure(results, args.o)
    else:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(results)

if __name__ == "__main__":
    main()
