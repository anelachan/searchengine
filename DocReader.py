from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem.lancaster import LancasterStemmer
from nltk.stem import SnowballStemmer
from nltk import WordNetLemmatizer

default_options = {
	'lowercase' : True,
	'tokenize' 	: 'no_digits', # 'symbols' or 'no_symbols'
	'stopwords' : False, 
	'stemming' 	: None, # 'porter', 'lancaster','snowball', 'none'
	'lemmatize' : False
}

class DocReader(object):
	# document is raw text, options are diff. strategies
	def __init__(self,document,options=default_options):
		self.options = default_options
		self.raw_doc = unicode(document,errors='ignore')
		# reset options if given
		for key in options.keys():
			self.options[key] = options[key]

		# adjust case
		if self.options['lowercase']:
				self.raw_doc = self.raw_doc.lower()

		# tokenize according to specifications
		if self.options['tokenize'] == 'symbols':
			tokenizer = RegexpTokenizer(r'[\'\w\-]+')
		if self.options['tokenize'] == 'no_symbols':
			tokenizer = RegexpTokenizer(r'\w+')
		if self.options['tokenize'] == 'no_digits':
			tokenizer = RegexpTokenizer(r'[A-Za-z]+')
		self.tokens = tokenizer.tokenize(self.raw_doc)

		if not self.options['stopwords']:
			stop = stopwords.words('english')
			self.tokens = [word for word in self.tokens if word not in stop]

		if self.options['stemming'] and self.options['lemmatize']:
			print 'Error: can only choose one of stemming or lemmatize. Choosing stemming'
			self.options['lemmatize'] = False

		# stemming?
		if self.options['stemming']:
			if self.options['stemming'] == 'porter':
				stemmer = PorterStemmer()
			if self.options['stemming'] == 'lancaster':
				stemmer = LancasterStemmer()
			if self.options['stemming'] == 'snowball':
				stemmer = SnowballStemmer('english')
			self.tokens = [stemmer.stem(word) for word in self.tokens]

		# lemmatizing?
		if self.options['lemmatize']:
			wnl = WordNetLemmatizer()
			self.tokens = [wnl.lemmatize(word) for word in self.tokens]



	def words(self):
		return self.tokens