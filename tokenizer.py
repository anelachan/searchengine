from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords as sw
from nltk.stem.porter import PorterStemmer
from nltk.stem.lancaster import LancasterStemmer
from nltk.stem import SnowballStemmer
from nltk import WordNetLemmatizer


def tokens(document, lowercase=True, tokenize='no_digits', 
           stopwords=False, stemming=None, lemmatize=False):
    """Tokenize a raw string based on passed tokenization options."""
    raw_doc = unicode(document, errors='ignore')

    # adjust case
    if lowercase:
        raw_doc = raw_doc.lower()

    # tokenize according to specifications
    if tokenize == 'symbols':
        tokenizer = RegexpTokenizer(r'[\'\w\-]+')
    if tokenize == 'no_symbols':
        tokenizer = RegexpTokenizer(r'\w+')
    if tokenize == 'no_digits':
        tokenizer = RegexpTokenizer(r'[A-Za-z]+')
    tokens = tokenizer.tokenize(raw_doc)

    if not stopwords:
        stop = sw.words('english')
        tokens = [word for word in tokens if word not in stop]

    if stemming and lemmatize:
        print ('Error: can only choose one of stemming or lemmatize. '
               'Choosing stemming')
        lemmatize = False

    if stemming:
        if stemming == 'porter':
            stemmer = PorterStemmer()
        if stemming == 'lancaster':
            stemmer = LancasterStemmer()
        if stemming == 'snowball':
            stemmer = SnowballStemmer('english')
        tokens = [stemmer.stem(word) for word in tokens]

    if lemmatize:
        wnl = WordNetLemmatizer()
        tokens = [wnl.lemmatize(word) for word in tokens]

    return tokens
