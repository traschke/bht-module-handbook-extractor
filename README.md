# Module Handbook Extractor for module handbooks of Beuth University of Applied Sciences Berlin

## Application areas
This tool can be used to extract competencies and requirements from module handbooks of Beuth University, which are usually only distributed in pdf-format.

## How does it work?
The algorithm searches each page for specific keywords, to identify areas which contain relevant data. It dynamically creates bounding-boxes based on these keywords on each page of the pdf, where relevant data is assumed. As module handbooks at Beuth are usually formatted as tables, for each desired data field, there is always a descriptor/keyword, e.g. "Modulnummer" or "Lernziele/Kompetenzen". To correctly calculate the bounding box, it uses the next row of the column as terminator.

## How to use?
### Install
#### Prerequisites
* Python 3.7
* [pipenv](https://github.com/pypa/pipenv)
* [pyenv](https://github.com/pyenv/pyenv) (optional, to install required python runtime)

#### Install dependencies
```
$ pipenv install
```


### Run
```
$ pipenv shell
$ ./extract.py -h
usage: extract.py [-h] [-o output_directory] pdf_file

Extracts competencies and requirements from a module handbook.

positional arguments:
  pdf_file             the module handbook to be extracted

optional arguments:
  -h, --help           show this help message and exit
  -o output_directory  directory to write the extracted data to
```
If no output directory is specified, the output is printed to `stdout`.
