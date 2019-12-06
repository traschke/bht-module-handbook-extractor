import os
import pprint

import pdfquery
from pdfquery.cache import FileCache
from pdfminer.pdfinterp import resolve1

def main():
    cache_dir = "./.cache/"

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    pdf = pdfquery.PDFQuery("./testdata/test.pdf", parse_tree_cacher=FileCache(cache_dir))
    pdf.load()

    page_count = resolve1(pdf.doc.catalog['Pages'])['Count']

    results = []

    for i in range(page_count - 1):
        # print(i)
        module_id = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Modulnummer")')

        # If a module id is found, we are on a module description page :D
        if len(module_id) >= 1:
            selectors = [
                ('with_parent','LTPage[page_index="' + str(i) + '"]'),
                ('with_formatter', 'text'),
            ]
            id_key_coords = {
                "x0": float(module_id.attr('x0')), "y0": float(module_id.attr('y0')),
                "x1": float(module_id.attr('x1')), "y1": float(module_id.attr('y1'))}
            id_value_coords = {
                "x0": id_key_coords['x0'] + 123, "y0": id_key_coords['y0'],
                "x1": id_key_coords['x0'] + 450, "y1": id_key_coords['y1']}

            selectors.append(('id', 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (id_value_coords['x0'], id_value_coords['y0'], id_value_coords['x1'], id_value_coords['y1']), lambda match: match.text().strip()))

            name = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Titel")')
            if len(name) >= 1:
                leistungspunkte = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Leistungspunkte")')

                if len(leistungspunkte) >= 1:
                    name_value_coords = {
                        "x0": float(name.attr('x0')) + 120, "y0": float(leistungspunkte.attr('y1')),
                        "x1": float(name.attr('x0')) + 455, "y1": float(name.attr('y1')) + 1
                    }
                    selectors.append(('name', 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (name_value_coords['x0'], name_value_coords['y0'], name_value_coords['x1'], name_value_coords['y1']), lambda match: match.text().strip()))

            competencies = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Lernziele / Kompetenzen")')
            if len(competencies) >= 1:
                requirements = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Voraussetzungen")')
                if len(requirements) >= 1:
                    competencies_value_coords = {
                        "x0": float(competencies.attr('x0')) + 120, "y0": float(requirements.attr('y1')),
                        "x1": float(competencies.attr('x0')) + 455, "y1": float(competencies.attr('y1')) + 1
                    }
                    selectors.append(('competencies', 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (competencies_value_coords['x0'], competencies_value_coords['y0'], competencies_value_coords['x1'], competencies_value_coords['y1']), lambda match: match.text().strip()))

                    niveau = pdf.pq('LTPage[page_index="' + str(i) + '"] LTTextLineHorizontal:contains("Niveaustufe")')
                    if len(niveau) >= 1:
                        requirements_value_coords = {
                            "x0": float(requirements.attr('x0')) + 120, "y0": float(niveau.attr('y1')),
                            "x1": float(requirements.attr('x0')) + 455, "y1": float(requirements.attr('y1')) + 1
                        }
                        selectors.append(('requirements', 'LTTextLineHorizontal:in_bbox("%s, %s, %s, %s")' % (requirements_value_coords['x0'], requirements_value_coords['y0'], requirements_value_coords['x1'], requirements_value_coords['y1']), lambda match: match.text().strip()))

            page_results = pdf.extract(selectors)
            page_results['page'] = i + 1
            results.append(page_results)

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(results)
    exit(0)

if __name__ == "__main__":
    main()
