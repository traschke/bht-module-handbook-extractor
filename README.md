# CompEx

Extract text from modulehandbooks. Currently only handles descriptions of competencies and requirements, but can easily be extended for other puposes!
(only tested with modulehandbooks of Department VI of Beuth University of Applied Sciences Berlin)

## How does it work?
The algorithm searches each page for specific keywords, to identify areas which contain relevant data. It dynamically creates bounding-boxes based on these keywords on each page of the pdf, where relevant data is assumed. As module handbooks at Beuth University are usually formatted as tables, for each desired data field, there is always a descriptor/keyword, e.g. "Modulnummer" or "Lernziele/Kompetenzen". To correctly calculate the bounding box, it uses the next row of the column as terminator.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 3.7 
* [pipenv](https://github.com/pypa/pipenv)
* (optional) [pyenv](https://github.com/pyenv/pyenv) to automatically install required Pythons
  * If pyenv is not installed, Python 3.7 is required, otherwise pyenv will install it

### Installing

Setup a python virtual environment and download all dependencies

```console
$ pipenv install
```

### Running
Enter the virtual environment
```console
$ pipenv shell
```

Show help
```console
$ python -m pdfextract -h
```

#### Extraction

Extract descriptions of competencies and requirements to console
```console
$ python -m pdfextract example.pdf
```

You can add an output directory with the `-o` parameter. For each module a folder will be created, with a `competencies.txt` and `requirements.txt` file, which hold the corresponding data.
```console
$ python -m pdfextract -o ./out example.pdf
```

## Running the tests

Unfortunately, there are no tests at the moment. :(

## Built With

* [Python 3.7](https://docs.python.org/3.7/)
* [pipenv](https://pipenv.pypa.io/en/latest/) - Python Development Workflow for Humans
* [pdfquery](https://github.com/jcushman/pdfquery) - A fast and friendly PDF scraping library

## Authors

* **Timo Raschke** - *Initial work* - [traschke](https://github.com/traschke)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
