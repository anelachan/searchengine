import os
import gc
import random

import nltk
from nltk.corpus import stopwords
import numpy as np
import pandas as pd
from DocReader import DocReader

parse_options = {
	'lowercase' : True,
	'tokenize' 	: 'no_digits', # 'symbols','no_symbols','no_digits'
	'stopwords' : True, 
	'stemming' 	: None, # 'porter', 'lancaster','snowball', None
	'lemmatize' : False
}
default_options = {
	'sample'		: True,
	'docs'			: 200,
	'normalize'	: False,
	'pivot'			: False,
	'biwords'		: False,
	'slope' 		: 0.00162428, # must calculate separately and plug in
	'pivot_factor' : 37.48, # must calculate separately and plug in
	'english_only' : False,
	'corpus_dir' : 'corpus/'
}

class SearchEngine(object):

	def __init__(self,options=default_options, parse_options=parse_options):

		# SET OPTIONS---------------------------------------------------------

		self.options = default_options
		for key in options.keys():
			self.options[key] = options[key]

		self.parse_options = parse_options
		for key in parse_options.keys():
			self.parse_options[key] = parse_options[key]

		if self.options['biwords']:
			self.parse_options['stopwords'] = False

		if self.options['pivot']:
			self.options['normalize'] = True

		# FILE I/O - LOAD COLLECTION INTO MEMORY-------------------------------

		files = [os.path.join(root,name) \
			for root, dirs, files in os.walk(self.options['corpus_dir'],topdown=True) \
			for name in files]

		collection = list()
		blog_ids = list()

		if self.options['sample']:
			files = random.sample(files,self.options['docs'])	

		for filename in files:
			f = open(filename)
			collection.append(f.read())
			blog_ids.append(filename.split('/')[1].split('.')[0])
			f.close()
	
		self.blog_ids = pd.DataFrame(blog_ids,index=range(1,len(blog_ids)+1),columns=['id'])


		# BUILD DATA STRUCTURE------------------------------------------------

		self.postings = {}
		self.weights = {}
		self.doc_lengths = {}
		self.normalized = {}
		if self.options['pivot']:
			self.pivoted = {}
		self.blank_docs = list()

		# for cheap language detection
		stop = stopwords.words('english') # for avoiding English

		id_num = 1
		for doc in collection:

			if doc: # skip empty docs! 
				words = DocReader(doc,self.parse_options).words()
				fd = dict(nltk.FreqDist(words))

				if self.options['english_only']:

					top_words = list()
					if self.parse_options['stopwords']:
						top_words = sorted(fd.keys(), key=fd.get)[-3:]

					# if want to check english but NOT keeping stopwords: i.e. if using bigrams
					elif not self.parse_options['stopwords']:
						# reset parse options - pretend we will keep stopwords
						self.parse_options['stopwords'] = True
						words_with_stop = DocReader(doc,self.parse_options).words()
						# need to RECALCULATE the FD
						fd_with_stop = dict(nltk.FreqDist(words_with_stop))
						top_words = sorted(fd.keys(), key=fd_with_stop.get)[-3:]

					filtered = [word for word in top_words if word in stop]
					if len(filtered) < 2:
						words = None

				if words:
					self.add_to_postings(fd,id_num)

				if words and self.options['biwords']:
					# store common bi-word phrases
					bigram_fd = dict(nltk.FreqDist(nltk.bigrams(words)))
					top_3_bigrams = sorted(bigram_fd.keys(), key=bigram_fd.get)[-3:]
					top_fd = dict([(k,v) for (k,v) in bigram_fd.items() if k in top_3_bigrams and v > 1])
					self.add_to_postings(top_fd,id_num)

			# deal with any blank docs
			else:
					self.blank_docs.append(id_num)
			id_num += 1


		if not self.options['sample']:
			self.options['docs'] = 15948-len(self.blank_docs)

		# CALC. TF-IF WEIGHTS-------------------------------------------------

		self.calc_weights_l(self.postings.keys())
		if self.options['normalize']:
			self.normalize_l()
			if self.options['pivot']:
				self.pivot()
		else:
			self.normalized = self.weights

	def query(self,raw_string,k):
		query_list = DocReader(raw_string,self.parse_options).words()

		if self.options['pivot']:
			self.normalized = self.pivoted # dummy

		if self.options['biwords']:
			try:
				query_list += list(nltk.bigrams(query_list))
			except ValueError:
				pass

		df = pd.DataFrame()
		for word in query_list:
			try:
				zipped = zip(*self.normalized[word])
				new_df = pd.DataFrame(list(zipped[1]),index=list(zipped[0]),columns=[word])
				df = df.join(new_df,how='outer')
			except KeyError:
				continue # just ignore words not found
		score = df.sum(axis=1)
		score.sort(ascending=False)

		return pd.DataFrame(score[:k]).join(self.blog_ids)

	def tf(self,num):
		if num == 0:
			return 0
		else:
			return 1 + np.log(num)

	def add_to_postings(self,fd,id_num):
		for word in fd.keys():
			if word not in self.postings:
				self.postings[word] = []
			self.postings[word].append((id_num,fd[word]))

	def calc_weights_l(self,word_list):
		for word in word_list:
			doc_count = len(self.postings[word]) # not actual frequency, just DOCUMENT frequency
			self.weights[word] = []
			for (doc,freq) in self.postings[word]:
				TFIDF = self.tf(freq)*np.log(self.options['docs']/float(doc_count))
				self.weights[word].append((doc,TFIDF))
				# add to doc length record
				if doc not in self.doc_lengths:
					self.doc_lengths[doc] = []
				self.doc_lengths[doc].append(TFIDF)
		del self.postings
		gc.collect()

	def normalize_l(self):
		for doc in self.doc_lengths.keys():
			self.doc_lengths[doc] = np.linalg.norm(self.doc_lengths[doc])

		for word in self.weights.keys():
			self.normalized[word] = []
			for pair in self.weights[word]:
				new = (pair[0],pair[1]/self.doc_lengths[pair[0]])
				self.normalized[word].append(new)

	def pivot(self):
		# results from PivotFinder - DO NOT try to instantiate PivotFinder from here!
		slope = self.options['slope']
		pivot = self.options['pivot_factor']
		for word in self.weights.keys():
			self.pivoted[word] = []
			for pair in self.weights[word]:
				doc_num = pair[0]
				new_weight = pair[1] / (((1.0 - slope)*pivot) + (slope*self.doc_lengths[doc_num]))
				new = (doc_num,new_weight)
				self.pivoted[word].append(new)
		del self.normalized
		gc.collect()