#!/usr/bin/env python

import os
import sys
import re
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional

from pdfquery import PDFQuery
from pdfquery.cache import FileCache
from pdfminer.pdfinterp import resolve1

class Point(object):
    """Represents a two-dimensional point."""

    def __init__(self, x: float = 0, y: float = 0):
        """Creates a new instance.

        Parameters
        ----------
        x : float, optional
            The x value of the point, by default 0
        y : float, optional
            The y value of the point, by default 0
        """
        self.data: [float, float] = [x, y]

    def __str__(self) -> str:
        return "point(%s,%s)" % (self.x, self.y)

    def __getitem__(self, item) -> float:
        return self.data[item]

    def __setitem__(self, idx: int, value: float):
        self.data[idx] = value

    @property
    def x(self) -> float:
        """Get the x value of the point.

        Returns
        -------
        float
            The x value of the point
        """
        return self.data[0]

    @property
    def y(self) -> float:
        """Get the y value of the point

        Returns
        -------
        float
            The y value of the point
        """
        return self.data[1]

def eprint(*args, **kwargs):
    """Prints text to stderr
    """
    print(*args, file=sys.stderr, **kwargs)

def load_pdf(file: str, cache_dir: str = "./.cache/") -> PDFQuery:
    """Loads and parses a PDF file with pdfquery.

    Parameters
    ----------
    file : str
        Path to a PDF file
    cache_dir : str, optional
        folder to store cache in, by default "./.cache/"

    Returns
    -------
    PDFQuery
        A PDFQuery object with the parsed PDF
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    pdf = PDFQuery(file, parse_tree_cacher=FileCache(cache_dir))
    pdf.load()
    return pdf

def get_page_count(pdf: PDFQuery) -> int:
    """Get the total page count of a PDF.

    Parameters
    ----------
    pdf : PDFQuery
        The PDF

    Returns
    -------
    int
        Total page count
    """

    return resolve1(pdf.doc.catalog['Pages'])['Count']

def get_selector_for_element_text(pdf: PDFQuery, page: int, descriptors: Tuple[str], underlying_descriptors: Tuple[str], value_deviations: (Point, Point), desc: Optional[str] = None):
    """Extracts a text value from the given handbook based on descriptors

    The operation is based on a descriptor of the value to extract and an underlying descriptor used
    to calculate the bounding box of the value of interest on the page.
    You can use value_derivations to adjust the calculated bounding box.
    ┌───────────────────────┬──────────────────────────┐
    │ descriptor            │ This is the text we want │
    ├───────────────────────┼──────────────────────────┤
    │ underlying_descriptor │ uninteresting text       │
    └───────────────────────┴──────────────────────────┘

    Parameters
    ----------
    pdf : PDFQuery
        The PDF
    page : int
        The page to use
    descriptors : Tuple[str]
        A tuple of descriptors to search for on the page
    underlaying_descriptors : Tuple[str]
        A tuple of descriptors that follow the descriptors to search for on the page
    value_deviations : (Point, Point)
        A tuple with the length of 2 with derivation from initial calculation for start and ending of bbox (e.g. first column of table is smaller/bigger)
    desc : Optional[str], optional
        A description of the data you try to extract, by default None, uses found descriptor as default

    Returns
    -------
    Tuple
        A tuple with the descriptor and generated selector

    Raises
    ------
    ValueError
        If a the descriptor is not found on the page
    ValueError
        If a the underlying descriptor is not found on the page
    """

    for descriptor in descriptors:
        descriptor_element = pdf.pq('LTPage[page_index="%s"] LTTextLineHorizontal:contains("%s")' % (page, descriptor))
        if len(descriptor_element) >= 1:
            break

    if len(descriptor_element) < 1:
        raise ValueError("Descriptor \"%s\" not found on page %s" % (descriptor, page + 1))

    for underlaying_descriptor in underlying_descriptors:
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

    return (desc, 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (value_coords[0].x, value_coords[0].y, value_coords[1].x, value_coords[1].y), lambda match: match.text().strip())

def extract_competencies(pdf: PDFQuery) -> List[Dict]:
    """Extracts Lernziele/Kompetenzen and Voraussetzungen from BHT modulehandbooks.

    Parameters
    ----------
    pdf : PDFQuery
        The PDF

    Returns
    -------
    List[Dict]
        List of extracted values as Dict
    """

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

        # Trim extrated text
        page_results['id'] = page_results['id'].strip()
        page_results['name'] = page_results['name'].strip()

        # Split the extracted sentences (which also does a trim to each sentence)
        page_results['competencies'] = split_sentences(page_results['competencies'])
        page_results['requirements'] = split_sentences(page_results['requirements'])

        results.append(page_results)

    return results

def escape_filename(input: str) -> str:
    """Remove forbidden chars from a string.

    Parameters
    ----------
    input : str
        A string

    Returns
    -------
    str
        Cleaned string
    """

    output = re.sub(r"[^\w\-_\.]", "_", input)
    return output

def write_to_conll_directory_structure(results: List[Dict], path: str):
    """Writes extracted data to files.

    Parameters
    ----------
    results : List[Dict]
        The results of extract_competencies
    path : str
        A path/folder where to store the data
    """

    folder_structure = Path(path)
    for result in results:
        # Remove any forbidden character from the filename
        try:
            escaped_name = escape_filename(result["name"])
        except:
            escaped_name = "unknown"
        escaped_id = escape_filename(result["id"])
        module_folder = folder_structure / ("%s-%s" % (escaped_id, escaped_name))

        # Write competencies and requirements to specific files
        write_sentences_to_file(result["competencies"], module_folder / ("%s-competencies.txt" % (escaped_id)))
        write_sentences_to_file(result["requirements"], module_folder / ("%s-requirements.txt" % (escaped_id)))

def split_sentences(text: str) -> List[str]:
    """Splits sentences.

    Parameters
    ----------
    text : str
        A string with multiple sentences

    Returns
    -------
    List[str]
        A List of sentences
    """
    # Split sentences at . ! or ?, but not if its preceeded by a number or an abbrevation like z.B. oder etc.
    split_pattern: str = r"(?<!\w\.\w.)(?<!etc\.|bzw\.|usw\.|uvm\.)(?<![A-Z][a-z]\.)(?<![0-9]\.)(?<=\.|\?|\!)\s"
    sentences = re.split(split_pattern, text)
    sentences = [sentence.strip() for sentence in sentences]

    # remove weird looking hyphenated words like "Fer- tigkeit"
    sentences = [re.sub(r"(?<!\s)(- )", "", sentence) for sentence in sentences]
    sentences = [sentence.strip() for sentence in sentences]

    return sentences

def write_sentences_to_file(sentences: List[str], file: str):
    """Writes a list of sentences to a files. One sentence per line.

    Parameters
    ----------
    sentences : List[str]
        A List of sentences
    file : str
        Path of a file to store the sentences to
    """

    filePath: Path = Path(file)
    folder: Path = filePath.parent
    if not os.path.exists(folder):
            os.makedirs(folder)
    f = open(filePath, "w")
    f.writelines(sentence + '\n' for sentence in sentences)
    f.close()
