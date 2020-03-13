import argparse
import pprint
import pdfextract.extract as extractor

def parse_args():
    parser = argparse.ArgumentParser(description="Extracts competencies and requirements from a module handbook.")
    parser.add_argument('pdf_file', metavar='pdf_file', type=str, nargs=1, help='the module handbook to be extracted')
    parser.add_argument('-o', metavar='output_directory', type=str, help='directory to write the extracted data to')

    return parser.parse_args()

def main():
    args = parse_args()

    pdf = extractor.load_pdf(args.pdf_file[0])
    results = extractor.extract_competencies(pdf)
    if args.o is not None:
        extractor.write_to_conll_directory_structure(results, args.o)
    else:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(results)

if __name__ == "__main__":
    main()
