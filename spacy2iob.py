import argparse
import json
import os
import re
import sys
import spacy
from bs4 import BeautifulSoup as bs


__version = '0.1.0'

fallback_cfg = {
    "general": {
        "iob_separator": "\t",
    },
    "golden": {
        "tags": ["a", "q"],
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
        "split_sentences": False,
        "mapping": {
            "PER": "PER",
            "LOC": "LOC",
            "GPE": "LOC",
            "ORG": "ORG",
            "MISC": "MISC",
            "PRODUCT": "MISC",
            "PERSON": "PER"
        }
    },
}


class Config:
    def __init__(self, conffile=None):
        if conffile is not None:
            self._settings = self._parse_config(conffile)
        else:
            self._settings = {}

    def _parse_config(self, conffile):
        if not os.path.exists(conffile):
            raise FileNotFoundError(
                "Config file {!r} doesn't exist.".format(conffile))

        with open(conffile) as f:
            return json.load(f)

    def get_property(self, section, property_name):
        fallback = fallback_cfg[section][property_name]

        if section in self._settings:
            return self._settings[section].get(property_name, fallback)

        return fallback

    @staticmethod
    def dump():
        return json.dumps(fallback_cfg, indent=4)


class Spacy:
    def __init__(self, separator="\t", mapping={}, model=None, segment=False):
        self._sep = separator
        self._mapping = mapping
        self._segment = segment

        try:
            self.nlp = spacy.load(model)
        except Exception as err:
            print(f'Unable to load spaCy model:\n{err}', file=sys.stderr)
            sys.exit(1)

    def __call__(self, text):
        return self.nlp(text)

    def tokenizer(self, text):
        return list(self.nlp(
            text,
            disable=[
                "ner", "tok2vec", "tagger", "parser",
                "attribute_ruler", "lemmatizer"])
            )

    def token_to_iob(self, token):
        iob = token.ent_iob_
        enttype = self._mapping.get(token.ent_type_, token.ent_type_)
        iob_tag = iob if iob == 'O' else f'{iob}-{enttype}'

        return f'{token.text}{self._sep}{iob_tag}'

    def span_to_iob(self, doc):
        tokens = []
        for sentence in doc.sents:
            for token in sentence:
                tokens.append(self.token_to_iob(token))
            if self._segment:
                tokens[-1] = tokens[-1] + '\n'
        return tokens

    @staticmethod
    def get_installed_models():
        return spacy.util.get_installed_models() or ["No models available"]


class _DumpConfigAction(argparse.Action):
    def __init__(self,
                 option_strings,
                 dest,
                 default=argparse.SUPPRESS,
                 help=None):
        super(_DumpConfigAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, True)
        print(Config.dump())
        parser.exit()


def parse_args():
    description = "Script to convert a corpus (in XML or raw text) into IOB."

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '-s',
        '--source',
        required=False,
        default='spacy',
        type=str,
        choices=['spacy', 'golden'],
        help='Source of the entity tags ("golden" = XML file with the gold standard)',  # noqa
    )
    parser.add_argument(
        '-f',
        '--format',
        required=False,
        default='xml',
        choices=['text', 'xml'],
        help='Format of the input file with the corpus (XML or raw text)'
    )
    parser.add_argument(
        '-m',
        '--model',
        required=False,
        choices=Spacy.get_installed_models(),
        help='spaCy model (only with --source="spacy")'
    )
    parser.add_argument(
        '-c',
        '--config',
        type=str,
        required=False,
        help='Config file'
    )
    parser.add_argument(
        '-d',
        '--dump-config',
        dest='dump',
        default=False,
        action=_DumpConfigAction,
        help='Dump a config file with default options',
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'%(prog)s {__version}'
    )
    parser.add_argument(
        'file',
        metavar='input files',
        type=str,
        nargs='+',
        help='Corpus files'
    )
    return parser.parse_args()


def find_entities(entities, doc):
    def sequence_in(entity, target, idx):
        seq = [token.text for token in nlp.tokenizer(entity)]
        for i in range(len(target[idx:]) - len(seq) + 1):
            if seq == target[i+idx:i+idx+len(seq)]:
                return(i+idx, i+idx+len(seq))
        raise Exception(f"Entity {seq} not found in: {target}")

    tokens = [token.text for token in doc]

    for ent in entities:
        entity, enttype, ent_idx = ent
        coords = sequence_in(entity, tokens, ent_idx)

        for idx, i in enumerate(range(coords[0], coords[1])):
            tokens[i] = "{}{}{}-{}".format(
                tokens[i],
                IOB_separator,
                "B" if idx == 0 else "I", enttype
            )

    for i in range(len(tokens)):
        if not re.search(r'{}[BI]-'.format(IOB_separator), tokens[i]):
            tokens[i] = "{}{}{}".format(tokens[i], IOB_separator, "O")
        if doc[i].is_sent_end and segment:
            tokens[i] = tokens[i] + '\n'

    return tokens


def get_entity_indexes(turn):
    indexes = []
    turn_copy = bs(re.sub(r'\s+', ' ', str(turn)), 'lxml-xml')

    entities = turn_copy.find_all(entity_tag)
    for e in entities:
        entity_tokens = [t.text for t in nlp.tokenizer(e.text)]
        e.string = re.sub(
            r'^{}'.format(entity_tokens[0]),
            entity_tokens[0] + 'PART-ENTITY',
            e.text
        )

    tokens = [
        t.text for t in nlp(re.sub(r'\s+', ' ', turn_copy.text.strip()))
    ]
    for i, token in enumerate(tokens):
        if token.endswith('PART-ENTITY'):
            indexes.append(i)
        elif re.match(r'PART-ENTITY', token):
            indexes.append(i - 1)

    return indexes


def get_iob_tokens_from_xml(corpusfile):
    iob_tokens = []
    data = bs(corpusfile, 'lxml-xml')

    for turn in data.find_all(xmltags, attrs=attrs):
        entities = []

        if turn.text is '':
            continue
        offsets = get_entity_indexes(turn)
        for i, entity in enumerate(turn.find_all(entity_tag)):
            if args.source == 'golden':
                try:
                    entities.append(
                        (
                            entity.text,
                            mapping.get(
                                entity[entity_attr],
                                entity[entity_attr]
                            ),
                            offsets[i]
                        )
                    )
                except KeyError as err:
                    print(
                        f"Key {err} not found in tag {entity_tag}: {entity}",
                        file=sys.stderr
                    )
                    sys.exit(2)
            else:
                entity.unwrap()

        doc = nlp(re.sub(r'\s+', ' ', turn.text.strip()))
        if args.source == 'golden':
            iob_tokens.extend(find_entities(entities, doc))
        else:
            iob_tokens.extend(nlp.span_to_iob(doc))

    return iob_tokens


def get_iob_tokens_from_text(corpusfile):
    iob_tokens = []
    for line in corpusfile:
        doc = nlp(line.strip())
        iob_tokens.extend(nlp.span_to_iob(doc))
    return iob_tokens


args = parse_args()
cfg = Config(args.config)
if args.dump:
    cfg.dump()
    sys.exit(0)

xmltags = cfg.get_property('golden', 'tags')
attrs = cfg.get_property('golden', 'attributes')
entity_tag = cfg.get_property('golden', 'entity_tag')
entity_attr = cfg.get_property('golden', 'entity_attr')

mapping = cfg.get_property(args.source, 'mapping')
IOB_separator = cfg.get_property('general', 'iob_separator')
segment = cfg.get_property('spacy', 'split_sentences')

nlp = Spacy(
    separator=IOB_separator,
    mapping=mapping,
    model=args.model or cfg.get_property('spacy', 'model'),
    segment=segment,
)

for ifile in args.file:
    ofile = ".".join([os.path.splitext(ifile)[0], "iob"])
    try:
        fout = open(ofile, "w")
    except Exception as e:
        print(f"Unable to write: {e}")
        sys.exit(1)

    iob_tokens = []
    with open(ifile) as corpusfile:
        print(f"Processing {ifile}", file=sys.stderr)

        if args.format == 'text':
            iob_tokens = get_iob_tokens_from_text(corpusfile)
        elif args.format == 'xml':
            iob_tokens = get_iob_tokens_from_xml(corpusfile)

    print('\n'.join(iob_tokens).strip(), file=fout)
    fout.close()
