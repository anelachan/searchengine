# About

This software forms an information retrieval engine and was based on the task of finding web documents from the 2006 TREC blog track collection. Additional modules are included to evaluate the IR engine and to perform pivoted document length normalization (see Singhal et al. 1996).

The IR engine follows the vector space model and uses log TF*IDF weights.

## Corpus

The corpus is NOT included with this code, but the 2006 TREC blog track test collection can be acquired here: http://ir.dcs.gla.ac.uk/test_collections/blogs06info.html. However, the search engine should still work on any corpus where each document is stored in a single text file and all of these are stored in a directory called corpus/.

## Dependencies

Python 2.7.6

In addition to the standard library, the following must already be installed:
nltk (incl. the stopwords corpus)
numpy
scipy
pandas

## Usage

### SearchEngine

The main object for querying is SearchEngine. It should be called as follows:

```python
>>> s = SearchEngine(options, parse_options)
```

Querying is called with via the method query(query_string, num_of_results).

Example of instantiating and querying:

```python
# create an object for a sample of 1500 documents, with otherwise defaults
>>> s = SearchEngine({'docs':1500}) 

# get ranked list of 5 docs	
>>> s.query('cheney hunting',5)	 
              0                              id
1085  23.781539  BLOG06-20060217-020-0019557550
675   23.589061  BLOG06-20060214-022-0031627413
875   23.560228  BLOG06-20060216-035-0019518477
1421  22.525424  BLOG06-20060216-022-0021420409
748   21.452589  BLOG06-20060221-017-0005368642
```

##### Options

Search Engine comes with the following options but if not options are specified will best set to defaults. The options should be passed as a dictionary object with the following optional keys and values:

* 'corpus_dir' - The name of the directory where the corpus is stored, each as a single text file ending in .txt. Default is 'corpus/'.

* 'sample' - True or False. Whether to run on entire collection or not - if running on entire collection, choose False. Default is True.

* 'docs' - Integer. The number of docs to use in a sample. Will be ignored if 'sample' is False. Default is 200.

* 'normalize' - True or False. Whether to normalize the weights by document length or not. Default is False.

* 'biwords' - True or False. Whether to index biwords or not. Default is False.

* 'pivot' - True or False. If True, actual pivot parameters must be specified BY HAND as calculated SEPARATELY in PivotFinder. Default is False.

* 'pivot_factor' - Float. The pivot factor for pivoted document length normalization, calculated in PivotFinder (see below). Defaults to 37.48, the pivot calculated for the whole collection with plain vanilla options.

* 'slope' - Float. The slope of the P(relevant) line calculated in PivotFinder (see below). Defaults to .0016248, the slope calculated for the whole collection with plain vanilla options.

* 'english_only' - True or False. Whether or not to index only English documents as determined by stopwords-based language detection. Defaults to False.

### DocReader

Tokenization is managed through DocReader, which is automatically instantiated through SearchEngine. Tokenizing takes the format: doc = DocReader(raw_document,parse_options). The tokens can be retrieved through the words() method. The strings are all encoded as unicode. 

Example:

```python
# create an object with default options
>>> d = DocReader('Here is a raw string') 
>>> d.words()
[u'here', u'is', u'a', u'raw', u'string']
```

##### Options

You will not need to call DocReader to query or evaluate the search engine but the parse options can be passed as the second options object to SearchEngine. If not specified the parse options will become defaults. The parse options should be passed as a dictionary with the following optional keys and values:

* 'lowercase' - True or False. Whether to fold all words to lowercase. Default is True.

* 'tokenize' - 'no_digits', 'symbols' or 'no_symbols'. 'no_digits' has alphabetic characters only. 'symbols' includes apostrophes and hyphens as well as digits. 'no_symbols' includes alphabetic and digit word chapters but not apostrophes or hyphens. Default is 'no_digits'.

* 'stopwords' - True or False. Whether to INCLUDE stopwords - True means stopwords included, False means stopwords removed. Default is True.

* 'stemming' - None, 'porter', 'lancaster' or 'snowball'. Which stemmer to use, or no stemmer as None. Default is None.

* 'lemmatize' - True or False. Whether to lemmatize. Cannot be used in conjunction with stemming. Default is False.

### IREvaluator

The SearchEngine can be evaluated with IREvaluator. This is instantiated with IREvaluator(search_engine_object,QRELS_filename,query_filename,num_documents_k). Only text files in the format given for this project will parse correctly. Example:

```python
# create an IREvaluator object passing a search engine object, with k = 10
>>> s = SearchEngine()
>>> e = IREvaluator(s,'qrels.february','06.topics.851-900.txt',10)
```

The IREvaluator object has methods and attributes for easy inspection:

```python
# get the mean of metrics across the queries, a pandas object
>>> e.averages
AP           0.344866
F.2          0.515084
F1           0.453895
RR           0.771124
p@5          0.520833
precision    0.475000
r-prec       0.381769
recall       0.471608

# see individual query results, a pandas object
>>> e.df
           AP       F.2        F1   RR  p@5  precision    r-prec    recall
851  0.428571  0.303502  0.352941  1.0  0.6        0.3  0.428571  0.428571
852  0.500000  0.308300  0.461538  0.5  0.4        0.3  0.666667  1.000000
853  0.099405  0.445205  0.192308  1.0  0.8        0.5  0.119048  0.119048
854  0.400000  0.945455  0.571429  1.0  1.0        1.0  0.400000  0.400000
855  0.154464  0.390977  0.307692  1.0  0.4        0.4  0.250000  0.250000
...

# read a query manually and see if it was marked relevant (string must match that in the topic file exactly including random whitespace characters)

>>> e.query_read('cheney hunting')
BLOG06-20060217-020-0019557550
RELEVANT
JustOneMinute: Guns Don't Shoot People; Dick Cheney Shoots PeopleGuns Don't Shoot People; Dick Cheney Shoots People
The gang that couldn't shoot straight takes its act on the road, and the most dangerous man in Washington DC shows he is also the most dangerous man in South Texas :
...

# compare an old query with a different one

>>> e.compare('"letting india into the club?"','india nuclear power')
Old Precision: 0.0
New Precision: 0.4
Old P@5: 0.0
New P@5: 0.4

# get a pr curve for up to a specified # of documents

>>> e.pr_curve(10)
   precision    recall
0   0.583333  0.071967
1   0.562500  0.151687
2   0.562500  0.211425
3   0.552083  0.255722
4   0.520833  0.288804
5   0.517361  0.330253
6   0.497024  0.363176
7   0.492188  0.403322
8   0.488426  0.447407
9   0.475000  0.471608
```

### PivotFinder

This object can be used to calculate pivot factors. This must be done SEPARATELY based on a normalized SearchEngine object. It must be instantiated as PivotFinder(search_engine_object,number_to_retrieve,number_of_bins). Example:

```python
# after creating a normalized SearchEngine, instantiate a PivotFinder object requiring 100 docs to be retrieved, doc lengths go into 10 bins of equal length
>>> s = SearchEngine({'normalize':True})
>>> p = PivotFinder(s,100,10)

# get results (this is for tiny collection so numbers are off):
>>> p.slope
0.0014460603365386139
>>> p.pivot_factor
-47.047416916979387 
```

### A note on IR strategy testing

While this system should run end-to-end for querying, if you are going to test IR strategies, some of the data should be stored on disk, i.e. using the pickle module, to avoid redundant I/O and parsing. (Pickled files were removed for clarity.)