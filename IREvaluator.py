import re
from SearchEngine import SearchEngine
from SearchEngine import pd

class IREvaluator(object):
  
  def __init__(self,search_engine,relevant_file,topic_file,k):

    self.s = search_engine
    self.k = k

    topics = open(topic_file).read()
    queries = re.findall(r'<num> Number: (\d+)\n\n<title> ([\"\w+\s+\d+\??]+)\s\s<desc>',topics)
    self.query_dict = dict([(query[0].rstrip(),query[1]) for query in queries])
    self.query_dict_inv = dict([(v,k) for (k,v) in self.query_dict.items()])

    # find the blog id's of any missing documents
    missing = pd.DataFrame(self.s.blank_docs,columns=['num'])
    missing = pd.merge(missing,self.s.blog_ids,how='inner',left_on='num',right_index=True)

    # QRELS format:
    # 851 0 BLOG06-20060201-000-0021156117 0
    self.relevant = {} # query_id: [list,of,relevant,docs]
    for line in open(relevant_file):
      data = line.split()
      query_id = data[0]
      blog_id = data[2]

      # only look at blog id's that we actually have documents for!
      if not blog_id in set(missing['id']):
        if query_id not in self.relevant:
          self.relevant[query_id] = []
        if int(data[3]) > 0:
          if blog_id in set(self.s.blog_ids['id']):
            self.relevant[query_id].append(blog_id)

    self.retrieved = {}
    self.metrics = {} # query_id: { metric_name: score }
    self.df = None
    self.averages = None

    self.evaluate()


  def evaluate(self):
    self.query_many() # query_id: [list,of,retrieved,docs]
    self.calc_metrics()
    self.df = pd.DataFrame(self.metrics).T
    self.averages = self.df.mean()

  def query_many(self):
    for query_id in self.query_dict.keys():
      results = self.s.query(self.query_dict[query_id],self.k)
      self.retrieved[query_id] = list(results['id'])
      # to deal w/ the fact that some relevant docs may not be not returned
      # due to the terms being missing from the query...
      query_results = self.retrieved[query_id]
      num_results = len(query_results)
      if num_results < self.k:
        # take a random sample of other collection files and return them
        other_ids = set(self.s.blog_ids['id']) - set(self.missing['id']) - set(query_results)
        self.retrieved[query_id] += random.sample(other_ids,self.k - num_results)

  def calc_metrics(self):
    for query_id in self.retrieved.keys():
      if self.relevant[query_id]: # REMOVE THIS LATER
        self.metrics[query_id] = {}
        inner_dict = self.metrics[query_id]
        precision = self.calc_precision(query_id,self.k)
        recall = self.calc_recall(query_id)
        inner_dict['precision'] = precision
        inner_dict['recall'] = recall
        inner_dict['p@5'] = self.calc_precision(query_id,5)
        inner_dict['r-prec'] = self.calc_precision(query_id,len(self.relevant[query_id]))
        inner_dict['RR'] = self.calc_RR(query_id)
        inner_dict['AP'] = self.calc_AP(query_id)
        inner_dict['F1'] = self.calc_fscore(precision,recall,1)
        inner_dict['F.2'] = self.calc_fscore(precision,recall,0.2)

  def pr_curve(self,max_range):
    precision = []
    recall = []
    for k in range(1,max_range+1):
      self.k = k
      self.evaluate()

      precision.append(self.averages['precision'])
      recall.append(self.averages['recall'])
    pr = pd.DataFrame([precision,recall]).T 
    pr.columns=['precision','recall']
    return pr
            
  def calc_precision(self,query_id,d):
    # precision = (intersection of retrieved and relevant at depth d)/ d
    # retrieved_list will be sliced to precision @ d for re-usability
    return (float(len(list(set(self.retrieved[query_id][:d])
      & set(self.relevant[query_id]))))/float(d))         

  def calc_recall(self,query_id):
    # recall = intersection of retrieved and relevant / number relevant
    return (float(len(list(set(self.retrieved[query_id]) 
      & set(self.relevant[query_id]))))/ float(len(self.relevant[query_id])))

  def calc_AP(self,query_id):
    # avg precision at each correct match retrieved
    retrieved = self.retrieved[query_id]
    precisions = []
    for doc in retrieved:
      if doc in self.relevant[query_id]:
        precisions.append(self.calc_precision(query_id,retrieved.index(doc) +1))
    return float(sum(precisions))/ float(len(self.relevant[query_id]))

  def calc_RR(self,query_id):
    # reciprocal rank = reciprocal of rank of first correct answer
    retrieved = self.retrieved[query_id]
    for doc in retrieved:
      if doc in self.relevant[query_id]: # find rank of first correct answer
        return 1.0/float(retrieved.index(doc) + 1)
    return None

  def calc_fscore(self,precision,recall,beta):
    if precision == 0 or recall == 0:
      return None
    else:
      return (((1.0+beta**2) * (precision * recall)) /
        ((beta**2)*precision + recall))

  # tool for inspecting results
  def query_read(self,query_str):
    results = self.s.query(query_str,self.k)
    for blog_id in results['id']:
      print blog_id
      try:
        query_id = self.query_dict_inv[query_str]
        if blog_id in self.relevant[query_id]:
          print 'RELEVANT'
      except KeyError:
        pass
      f = open(self.s.options['corpus_dir'] + blog_id +'.txt')
      print f.read()
      f.close()

  def check_rel(self,query_str,blog_id):
    try:
      query_id = self.query_dict_inv[query_str]
      if blog_id in self.relevant[query_id]:
        print 'RELEVANT'
      else:
        print 'NOT RELEVANT'
    except KeyError:
      print 'Error: Query not found.'

  def compare(self,orig_query_str,new_query_str):
    results = self.s.query(new_query_str,self.k)
    try:
      query_id = self.query_dict_inv[orig_query_str]
      print 'Old Precision: ' + str(self.df['precision'].loc[query_id])
      print 'New Precision: ' + str(float(len(list(set(results['id'])
        & set(self.relevant[query_id]))))/float(self.k))
      print 'Old P@5: ' + str(self.df['p@5'].loc[query_id])
      print 'New P@5: ' + str(float(len(list(set(results['id'][:5])
            & set(self.relevant[query_id]))))/float(5))
    except KeyError:
      print 'Error: Original query not found.'
