# Description

`spacy2iob.py` produces a corpus with NER labels in IOB2 format. The source can be raw text (it relies on [spaCy](https://spacy.io/) to obtain the labels) or a gold standard in XML. It is designed to work with [this XML Schema](https://galabra.linguarum.net/corpus/schemadoc/), though it can be adapted to some extent by means of a config file.

It may also produce a version of the *gold standard corpus* (in XML) labelled with [spaCy](https://spacy.io/), so the output can be used to evaluate spaCy models.

# Installation

## Dependencies

In order to use `spacy2iob.py`, you have to install these python modules: spaCy, BeautifulSoup and lxml.

```bash
pip install spacy
pip install bs4
pip install lxml
```

or

```bash
pip install -r requirements.txt
```

Along with the modules, you may want to download a [spaCy pretrained model](https://spacy.io/usage/models).

Example:

```bash
python3 -m spacy download pt_core_news_sm
```

# Usage

It takes one or more XML or text files as input, and produces IOB2 files with the same name and extension `.iob`.

1. **Raw text labelling**

```bash
python spacy2iob.py -m es_core_news_lg -f text corpus/*.txt
```

This generates an IOB2 version of the text files in `corpus`, using the spaCy pretrained model `es_core_news_lg`. The resulting files are stored in `corpus` with the same name and extension `.iob`.

2. **XML with a gold standard**

```bash
python spacy2iob.py -s golden corpus_000.xml
```

It produces an IOB2 version of `corpus_000.xml` and saves it as `corpus_000.iob`. NER labels are obtained from the XML tags and spaCy is merely used for tokenization.

3. **XML with labelling from spaCy**

It is also possible to generate an IOB2 version of the XML files labelled with spaCy.

```bash
python spacy2iob.py -s spacy corpus/*.xml
```

This may be useful for evaluating a spaCy model against the gold standard IOB2 version obtained in section 2.

XML files must tipically validate against [this XML Schema](https://galabra.linguarum.net/corpus/schemadoc/), but it can be configured to use a different set of tags (see below).

With `--help` or `-h`, a helping message about usage is displayed.

```txt
$ python3 spacy2iob.py -h
usage: spacy2iob.py [-h] [-s {spacy,golden}] [-f {text,xml}]
                    [-m {es_core_news_lg}] [-c CONFIG] [-d] [-v]
                    input files [input files ...]

Script to convert a corpus (in XML or raw text) into IOB.

positional arguments:
  input files           Corpus files

optional arguments:
  -h, --help            show this help message and exit
  -s {spacy,golden}, --source {spacy,golden}
                        Source of the entity tags ("golden" = XML file with
                        the gold standard) (default: spacy)
  -f {text,xml}, --format {text,xml}
                        Format of the input file with the corpus (XML or raw
                        text) (default: xml)
  -m MODEL, --model MODEL
                        spaCy model (only with --source="spacy") (default:
                        None)
  -c CONFIG, --config CONFIG
                        Config file (default: None)
  -d, --dump-config     Dump a config file with default options (default:
                        False)
  -v, --version         show program's version number and exit
```

# Configuration

Default options may be overridden by using a config file in JSON. You can obtain a config file containing the default options by calling the script with `--dump-config`.

```json
{
    "general": {
        "iob_separator": "\t"
    },
    "golden": {
        "tags": [
            "a",
            "q"
        ],
        "attributes": {},
        "entity_tag": "entity",
        "entity_attr": "type",
        "mapping": {
            "org": "ORG",
            "location": "LOC",
            "misc": "MISC",
            "person": "PER",
            "webpage": "MISC",
            "title": "MISC",
            "email": "MISC"
        }
    },
    "spacy": {
        "model": "en_core_web_sm",
        "split_sentences": false,
        "mapping": {
            "PER": "PER",
            "LOC": "LOC",
            "GPE": "LOC",
            "ORG": "ORG",
            "MISC": "MISC",
            "PRODUCT": "MISC",
            "PERSON": "PER"
        }
    }
}
```

Options:

- section `general`

    - `iob_separator` (string): field delimiter between the token and the IOB2 label.

- section `golden`: configuration regarding the processing of the gold standard in XML.

    - `tags` (array): list of tags in the XML containing the textual data we want to label. Tags other than these won't be processed. If the list is empty, every tag in the XML file will be taken as input.
    - `attributes` (object): attributes in `tags` that will be used for filtering. Only tags (in the list specified as `tags`) with these attributes (all of them) will be processed. If empty, no filter will be applied and every tag in the list will be included.
    - `entity_tag`: XML tag storing information about entities.
    - `entity_attr`: attribute containing the entity type.
    - `mapping`: mapping between the XML entity types and IOB2 final labels.

- section `spacy`: configuration regarding the processing of the corpus with spaCy.

    - `model` (string): spaCy's pretrained model to be used. It may be overridden by the command line option `--model`.
    - `split_sentences` (boolean): if it is set to `false`, sentence boundaries are not marked and the tokens are arranged one after the other. Otherwise, an extra newline character will be added between sentences. 
    - `mapping` (object): mapping between spaCy and IOB2 labels.

# Examples

## XML gold standard

Sample XML file:

```xml
<?xml version="1.0" encoding="utf-8" standalone="no" ?>
<corpus xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="transcription.xsd">
<metadata>
    <participant>
        <speaker id="162">
            <age value="3"/>
            <gender value="M"/>
            <origin value="ES"/>
        </speaker>
    </participant>
</metadata>
<data>
<text>
  <ent enttype="person">Alejandro</ent> está viajando de <ent enttype="location">Bogotá</ent> a <ent enttype="location">Los Ángeles</ent>, en <ent enttype="location">California</ent>. Allí asistirá al congreso de la <ent enttype="org">Association for Computational Linguistics</ent>.
</text>
</data>
</corpus>
```

A configuration file for processing the sample file included above could be:

```json
{
    "general": {
        "iob_separator": " "
    },
    "golden": {
        "tags": ["text"],
        "entity_tag": "ent",
        "entity_attr": "enttype",
        "mapping": {
            "org": "ORG",
            "location": "LOC",
            "misc": "MISC",
            "person": "PER"
        }
    }
}
```

It process XML contents included in tag `text` and uses a blank space as IOB field separator.

**Usage**

- IOB2 format with labels from the XML gold standard.

```python spacy2iob.py -c config.json -s golden sample.xml```

Results:

```
Alejandro B_PER
está O
viajando O
de O
Bogotá B_LOC
a O
Los B_LOC
Ángeles I_LOC
, O
en O
California B_LOC
. O

Allí O
asistirá O
al O
congreso O
de O
la O
Association B_ORG
for I_ORG
Computational I_ORG
Linguistics I_ORG
. O
```

- IOB2 format with labels from spaCy.

`python spacy2iob.py -c config.json sample.xml`


## Raw text

Sample text file

```
Paulo está a viajar de Lisboa para São Francisco, na Califórnia. Aí participará na conferência da Association for Computational Linguistics.
```

**Usage**

```python spacy2iob.py -m pt_core_news_lg -f text sample.txt```

This command will process the sample text file using the default options (we override the model to be used with `-m`).

Results:

```
Paulo	B_PER
está	O
a	O
viajar	O
de	O
Lisboa	B_LOC
para	O
São	B_LOC
Francisco	I_LOC
,	O
na	O
Califórnia	B_LOC
.	O
Aí	O
participará	O
na	O
conferência	O
da	O
Association	B_ORG
for	I_ORG
Computational	I_ORG
Linguistics	I_ORG
.	O
```
