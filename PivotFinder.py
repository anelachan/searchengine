from scipy.stats import linregress
from numpy.linalg import solve
import pandas as pd
import re
import sys

# insert qrels and topics files here
QRELS = 'qrels.february'
TOPICS = '06.topics.851-900.txt'

class PivotFinder(object):

	def __init__(self,search_engine,k,num_bins):

		if not search_engine.options['normalize']:
			print 'Error: PivotFinder can only work with normalized weights.'
			sys.exit()

		retrieved = dict([(blog_id,0) for blog_id in search_engine.blog_ids['id']])
		relevant = dict([(blog_id,0) for blog_id in search_engine.blog_ids['id']])

		# build dict of document: # retrieved
		topics = open(TOPICS).read()
		queries = re.findall(r'<num> Number: (\d+)\n\n<title> ([\"\w+\s+\d+\??]+)\s\s<desc>',topics)
		queries = dict([(query[0].rstrip(),query[1]) for query in queries])
		for query_id in queries.keys():
		  results = search_engine.query(queries[query_id],k)
		  for blog_id in results['id']:
		  	retrieved[blog_id] += 1

		# build dict of document: # of relevant
		for line in open(QRELS):
			try:
			  data = line.split()
			  blog_id = data[2]
			  if int(data[3]) > 0:
			  	relevant[blog_id] += 1
			except KeyError: # doc not found!
				pass

		# turn the document lengths into bins, and calculate medians of those bins
		zipped_lengths = zip(*search_engine.doc_lengths.items())
		length_df = pd.DataFrame(list(zipped_lengths[1]),index = list(zipped_lengths[0]),columns=['length'])
		length_df['length_binned'] = pd.qcut(length_df['length'],num_bins)
		grouped = length_df.groupby(['length_binned'])
		medians = grouped.median()
		length_df = pd.merge(length_df,medians,how='left',left_on='length_binned',right_index=True)
		length_df.columns = ['actual_length','length_binned','median_bin_length']

		# build df from retrieved documents joining w/ integer blog index
		zipped_retrieved = zip(*retrieved.items())
		retrieved_df = pd.DataFrame(list(zipped_retrieved[1]),index = list(zipped_retrieved[0]),columns=['retrieved'])
		retrieved_df =  pd.merge(search_engine.blog_ids,retrieved_df,left_on='id',right_index=True)

		# build df from relevant documents joining w/ integer blog index
		zipped_relevant = zip(*relevant.items())
		relevant_df = pd.DataFrame(list(zipped_relevant[1]),index = list(zipped_relevant[0]),columns=['relevant'])
		relevant_df =  pd.merge(search_engine.blog_ids,relevant_df,left_on='id',right_index=True)

		# merge these into one table - bins and retrieved/relevant
		merged = pd.merge(length_df,relevant_df,left_index=True,right_index=True)
		merged = pd.merge(merged,retrieved_df,left_index=True,right_index=True)
		merged = merged[['median_bin_length','retrieved','relevant']]

		# group by median to get proportions/probabilities
		pivot = merged.pivot_table(index=['median_bin_length'])
		# fit to lines
		rel_s,rel_i,ret_r,ret_p,ret_se = linregress(pivot.index,pivot['relevant'])
		self.slope = rel_s
		ret_s,ret_i,ret_r2,ret_p2,ret_se2 = \
			linregress(pivot.index[1:],pivot[pivot.index != pivot.index[0]]['retrieved'])
		# note: i arbitrarily removed the outlier

		# solve system of linear equations to get pivot point
		solved = solve([[ret_s,-1],[rel_s,-1]],[-ret_i,-rel_i])
		self.pivot_factor = solved[0]
		self.pivot_data = pivot
