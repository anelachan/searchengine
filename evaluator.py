import re
import random

import pandas as pd


class Evaluator(object):
    """Class to evalute a search engine against gold standard relevant docs."""

    def __init__(self, search_engine,
                 relevant_file='qrels.february',
                 topic_file='06.topics.851-900.txt', num_docs=10):
        """Initialize w/ search engine to evaluate."""
        self.search_engine = search_engine
        self.num_docs = num_docs

        topics = open(topic_file).read()
        queries = re.findall(r'<num> Number: (\d+)\n\n<title> '
                             '([\"\w+\s+\d+\??]+)\s\s<desc>', topics)
        print queries
        self.query_dict = dict([(query[0].rstrip(), query[1])
                                for query in queries])
        self.query_dict_inv = dict([(val, key) for (key, val)
                                    in self.query_dict.items()])

        # find the blog id's of any missing documents
        missing = pd.DataFrame(self.search_engine.blank_docs, columns=['num'])
        missing = missing.merge(self.search_engine.blog_ids,
                                left_on='num',
                                right_index=True)

        # QRELS format:
        # 851 0 BLOG06-20060201-000-0021156117 0
        # query_id: [list,of,relevant,docs]
        self.relevant = {}
        for line in open(relevant_file):
            data = line.split()
            query_id = data[0]
            blog_id = data[2]

            # only look at blog id's that we actually have documents for!
            if blog_id not in set(missing['id']):
                if query_id not in self.relevant:
                    self.relevant[query_id] = []
                if int(data[3]) > 0:
                    if blog_id in set(self.search_engine.blog_ids['id']):
                        self.relevant[query_id].append(blog_id)

        # query_id: [list,of,retrieved,docs]
        self.retrieved = {}
        self.metrics = {}
        self.results = None
        self.averages = None
        self.missing = missing

        self.query_many()
        self.calc_metrics()
        self.results = pd.DataFrame(self.metrics).T
        self.averages = self.results.mean()

    def query_many(self):
        for query_id in self.query_dict.keys():
            results = self.search_engine.query(self.query_dict[query_id],
                                               self.num_docs)
            self.retrieved[query_id] = list(results['id'])
            # some relevant docs may not be not returned
            # due to the terms being missing from the query
            query_results = self.retrieved[query_id]
            num_results = len(query_results)
            if num_results < self.num_docs:
                # return a random sample of other collection files
                other_ids = (set(self.search_engine.blog_ids['id']) -
                             set(self.missing['id']) - set(query_results))
                self.retrieved[query_id] += random.sample(
                    other_ids, self.num_docs - num_results)

    def calc_metrics(self):
        for query_id in self.retrieved.keys():
            if self.relevant[query_id]:
                self.metrics[query_id] = {}
                inner_dict = self.metrics[query_id]
                precision = self.calc_precision(query_id, self.num_docs)
                recall = self.calc_recall(query_id)
                inner_dict['precision'] = precision
                inner_dict['recall'] = recall
                inner_dict['p@5'] = self.calc_precision(query_id, 5)
                inner_dict['r-prec'] = self.calc_precision(query_id, len(
                    self.relevant[query_id]))
                inner_dict['RR'] = self.calc_rr(query_id)
                inner_dict['AP'] = self.calc_ap(query_id)
                inner_dict['F1'] = self.calc_fscore(precision, recall, 1)
                inner_dict['F.2'] = self.calc_fscore(precision, recall, 0.2)

    def pr_curve(self, max_range):
        precision = []
        recall = []
        for k in range(1, max_range + 1):
            self.num_docs = k
            self.evaluate()

            precision.append(self.averages['precision'])
            recall.append(self.averages['recall'])
        pr = pd.DataFrame([precision, recall]).T
        pr.columns = ['precision', 'recall']
        return pr

    def calc_precision(self, query_id, d):
        """Get precision at depth d of one query."""
        # precision = (intersection of retrieved and relevant at depth d)/ d
        # retrieved_list will be sliced to precision @ d for re-usability

        return (float(len(list(set(self.retrieved[query_id][:d]) &
                set(self.relevant[query_id])))) / float(d))

    def calc_recall(self, query_id):
        """Get recall on one query."""
        # intersection of retrieved and relevant / number relevant
        num_relevant = len(self.relevant[query_id])
        return (float(len(list(set(self.retrieved[query_id]) &
                set(self.relevant[query_id])))) / float(num_relevant))

    def calc_ap(self, query_id):
        """Get the avg precision at each correct match retrieved."""
        retrieved = self.retrieved[query_id]
        precisions = []
        for doc in retrieved:
            if doc in self.relevant[query_id]:
                precisions.append(self.calc_precision(query_id,
                                  retrieved.index(doc) + 1))
        return float(sum(precisions)) / float(len(self.relevant[query_id]))

    def calc_rr(self, query_id):
        """Get reciprocal rank, the reciprocal of rank of first relevant."""
        retrieved = self.retrieved[query_id]
        for doc in retrieved:
            # find rank of first correct answer
            if doc in self.relevant[query_id]:
                return 1.0 / float(retrieved.index(doc) + 1)
        return None

    def calc_fscore(self, precision, recall, beta):
        """Get f-score."""
        if precision == 0 or recall == 0:
            return None
        else:
            return (((1.0 + beta**2) * (precision * recall)) /
                    ((beta**2) * precision + recall))

    def query_read(self, query_str):
        """Inspect results."""
        results = self.search_engine.query(query_str, self.num_docs)
        for blog_id in results['id']:
            print blog_id
            try:
                query_id = self.query_dict_inv[query_str]
                if blog_id in self.relevant[query_id]:
                    print 'RELEVANT'
            except KeyError:
                pass
            f = open('{}{}.txt'.format(self.search_engine.corpus_dir, blog_id))
            print f.read()
            f.close()

    def check_rel(self, query_str, blog_id):
        """Look at relevance of passed query to particular blog."""
        try:
            query_id = self.query_dict_inv[query_str]
            if blog_id in self.relevant[query_id]:
                print 'RELEVANT'
            else:
                print 'NOT RELEVANT'
        except KeyError:
            print 'Error: Query not found.'

    def compare(self, orig_query_str, new_query_str):
        """Compare the results of one query to a new query."""
        results = self.search_engine.query(new_query_str, self.num_docs)
        try:
            query_id = self.query_dict_inv[orig_query_str]
            print 'Old Precision: {}'.format(
                self.results['precision'].loc[query_id])
            print 'New Precision: {}'.format(len(
                set(results['id']) & set(self.relevant[query_id])) /
                float(self.num_docs))
            print 'Old P@5: {}'.format(self.results['p@5'].loc[query_id])
            print 'New P@5: {}'.format(
                len(set(results['id'][:5]) &
                    set(self.relevant[query_id])) / 5.0)
        except KeyError:
            print 'Error: Original query not found.'
