import os
import gc
import random

import nltk
from nltk.corpus import stopwords as sw
import numpy as np
import pandas as pd

from tokenizer import tokens


class SearchEngine(object):

    def __init__(self, sample=True, docs=200, normalize=False,
                 biwords=False, english_only=False, corpus_dir='corpus/',

                 lowercase=True, tokenize='no_digits', stopwords=True,
                 stemming=None, lemmatize=False):

        # set shared options
        if biwords:
            stopwords = False

        self.tokenization = {
            'lowercase': lowercase,
            'tokenize': tokenize,
            'stopwords': stopwords,
            'stemming': stemming,
            'lemmatize': lemmatize
        }
        self.biwords = biwords
        self.normalize = normalize
        self.corpus_dir = corpus_dir

        # load collection
        files = [os.path.join(root, name)
                 for root, dirs, files in os.walk(
                 corpus_dir, topdown=True) for name in files]

        collection = list()
        blog_ids = list()

        if sample:
            files = random.sample(files, docs)

        for filename in files:
            f = open(filename)
            collection.append(f.read())
            blog_ids.append(filename.split('/')[1].split('.')[0])
            f.close()

        # lookup of blog id's
        self.blog_ids = pd.DataFrame(blog_ids,
                                     index=range(1, len(blog_ids) + 1),
                                     columns=['id'])

        # build data structure
        self.postings = {}
        self.weights = {}
        self.doc_lengths = {}
        self.normalized = {}
        self.blank_docs = list()

        # for cheap language detection
        stop = sw.words('english')

        id_num = 1
        for doc in collection:
            # skip empty docs!
            if doc:
                words = tokens(doc, **self.tokenization)
                fd = dict(nltk.FreqDist(words))

                if english_only:

                    top_words = list()
                    if stopwords:
                        top_words = sorted(fd.keys(), key=fd.get)[-3:]

                    # if want to check english but NOT keep stopwords:
                    # i.e. if using bigrams
                    elif not stopwords:
                        # reset parse options - pretend we will keep stopwords
                        stopwords = True
                        words_with_stop = tokens(doc, **self.tokenization)
                        # need to RECALCULATE the FD
                        fd_with_stop = dict(nltk.FreqDist(words_with_stop))
                        top_words = sorted(fd.keys(),
                                           key=fd_with_stop.get)[-3:]

                    filtered = [word for word in top_words if word in stop]
                    if len(filtered) < 2:
                        words = None

                if words:
                    self.add_to_postings(fd, id_num)

                if words and biwords:
                    # store common bi-word phrases
                    bigram_fd = dict(nltk.FreqDist(nltk.bigrams(words)))
                    top_3_bigrams = sorted(
                        bigram_fd.keys(), key=bigram_fd.get)[-3:]
                    top_fd = dict([(k, v) for (k, v) in bigram_fd.items()
                                   if k in top_3_bigrams and v > 1])
                    self.add_to_postings(top_fd, id_num)

            # deal with any blank docs
            else:
                    self.blank_docs.append(id_num)
            id_num += 1

        if not sample:
            docs = 15948 - len(self.blank_docs)

        # calc TF-IDF weights
        self.calc_weights_l(self.postings.keys(), docs)
        if normalize:
            self.normalize_l()
        else:
            self.normalized = self.weights

    def query(self, raw_string, k=10):

        query_list = tokens(raw_string, **self.tokenization)
        if self.biwords:
            try:
                query_list += list(nltk.bigrams(query_list))
            except ValueError:
                pass

        df = pd.DataFrame()
        for word in query_list:
            try:
                zipped = zip(*self.normalized[word])
                new_df = pd.DataFrame(list(zipped[1]),
                                      index=list(zipped[0]),
                                      columns=[word])
                df = df.join(new_df, how='outer')
            except KeyError:
                # just ignore words not found
                continue
        score = df.sum(axis=1)
        result_df = pd.DataFrame(score[:k]).join(self.blog_ids)
        result_df.columns = ['relevance', 'id']
        return result_df.sort_values('relevance', ascending=False)

    def tf(self, num):
        if num == 0:
            return 0
        else:
            return 1 + np.log(num)

    def add_to_postings(self, fd, id_num):
        for word in fd.keys():
            if word not in self.postings:
                self.postings[word] = []
            self.postings[word].append((id_num, fd[word]))

    def calc_weights_l(self, word_list, docs):
        for word in word_list:
            # not actual frequency, just DOCUMENT frequency
            doc_count = len(self.postings[word])
            self.weights[word] = []
            for (doc, freq) in self.postings[word]:
                tfidf = self.tf(freq) * np.log(docs / float(doc_count))
                self.weights[word].append((doc, tfidf))
                # add to doc length record
                if doc not in self.doc_lengths:
                    self.doc_lengths[doc] = []
                self.doc_lengths[doc].append(tfidf)
        del self.postings
        gc.collect()

    def normalize_l(self):
        for doc in self.doc_lengths.keys():
            self.doc_lengths[doc] = np.linalg.norm(self.doc_lengths[doc])

        for word in self.weights.keys():
            self.normalized[word] = []
            for pair in self.weights[word]:
                new = (pair[0], pair[1] / self.doc_lengths[pair[0]])
                self.normalized[word].append(new)

    def pivot(self, slope, pivot_factor):
        # results from PivotFinder
        # DO NOT try to instantiate PivotFinder from within this class
        if self.normalize is False:
            raise Exception('Error, can only pivot whe nonrmalized.')
        pivoted = {}
        for word in self.weights.keys():
            pivoted[word] = []
            for pair in self.weights[word]:
                doc_num = pair[0]
                new_weight = pair[1] / (((1.0 - slope) * pivot_factor) + (
                    slope * self.doc_lengths[doc_num]))
                new = (doc_num, new_weight)
                pivoted[word].append(new)
        del self.normalized
        gc.collect()
        self.normalized = pivoted
