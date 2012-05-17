import itertools
import math
#import distance #libdistance library http://monkey.org/~jose/software/libdistance/
import affinegap
import lr
#import pegasos
from collections import defaultdict
from blocking import trainBlocking
from predicates import *


def identifyCandidates(data_d) :
  return [data_d.keys()]

def findDuplicates(candidates, data_d, data_model, threshold) :
  duplicateScores = []

  for candidates_set in candidates :
    for pair in itertools.combinations(candidates_set, 2):
      scorePair = {}
      score = data_model['bias'] 
      fields = data_model['fields']

      distances = calculateDistance(data_d[pair[0]], data_d[pair[1]], fields)
      for name in fields :
        score += distances[name] * fields[name]['weight']
      scorePair[pair] = score
      #print (pair, score)
      if score > threshold :
        #print (data_d[pair[0]],data_d[pair[1]])
        #print score
        duplicateScores.append(scorePair)
  
  return duplicateScores

def calculateDistance(instance_1, instance_2, fields) :
  distances_d = {}
  for name in fields :
    if fields[name]['type'] == 'String' :
      distanceFunc = affinegap.normalizedAffineGapDistance
    x = distanceFunc(instance_1[name],instance_2[name])
    distances_d[name] = x

  return distances_d

def createTrainingPairs(data_d, duplicates_s, n) :
  import random
  nonduplicates_s = set([])
  duplicates = []
  nonduplicates = []
  nPairs = 0
  while nPairs < n :
    random_pair = frozenset(random.sample(data_d, 2))
    training_pair = (data_d[tuple(random_pair)[0]],
                     data_d[tuple(random_pair)[1]])
    if random_pair in duplicates_s :
      duplicates.append(training_pair)
      nPairs += 1
    elif random_pair not in nonduplicates_s :
      nonduplicates.append(training_pair)
      nonduplicates_s.add(random_pair)
      nPairs += 1
      
  return(nonduplicates, duplicates)

def createTrainingData(training_pairs) :

  training_data = []

  for label, examples in enumerate(training_pairs) :
      for pair in examples :
          distances = calculateDistance(pair[0],
                                        pair[1],
                                        data_model['fields'])
          training_data.append((label, distances))

  return training_data

def trainModel(training_data, iterations, data_model) :
    trainer = lr.LogisticRegression()
    trainer.train(training_data, iterations)

    data_model['bias'] = trainer.bias
    for name in data_model['fields'] :
        data_model['fields'][name]['weight'] = trainer.weight[name]

    return(data_model)

def trainModelSVM(training_data, iterations, data_model) :

    labels, vectors = zip(*training_data)

    keys = data_model['fields'].keys()
    vectors = [[_[key] for key in keys] for _ in vectors]
    
    trainer = pegasos.PEGASOS()

    trainer.train((labels, vectors))

    data_model['bias'] = trainer.bias
    for i, name in enumerate(keys) :
        data_model['fields'][name]['weight'] = trainer.lw[i]

    return(data_model)


if __name__ == '__main__':
  from test_data import init
  numTrainingPairs = 16000
  numIterations = 50

  import time
  t0 = time.time()
  (data_d, duplicates_s, data_model) = init()
  candidates = identifyCandidates(data_d)
  #print "training data: "
  #print duplicates_s
  
  print "number of known duplicates: "
  print len(duplicates_s)

  training_pairs = createTrainingPairs(data_d, duplicates_s, numTrainingPairs)

  trainBlocking(training_pairs,
                (wholeFieldPredicate,
                 tokenFieldPredicate,
                 commonIntegerPredicate,
                 sameThreeCharStartPredicate,
                 sameFiveCharStartPredicate,
                 sameSevenCharStartPredicate,
                 nearIntegersPredicate,
                 commonFourGram,
                 commonSixGram),
                data_model, 1, 1)  
  
  training_data = createTrainingData(training_pairs)
  #print "training data from known duplicates: "
  #print training_data
  print "number of training items: "
  print len(training_data)

  data_model = trainModel(training_data, numIterations, data_model)
  
  print "finding duplicates ..."
  dupes = findDuplicates(candidates, data_d, data_model, -2)
  true_positives = 0
  false_positives = 0
  for dupe_pair in dupes :
    if set(dupe_pair.keys()[0]) in duplicates_s :
        true_positives += 1
    else :
        false_positives += 1

  print "precision"
  print (len(dupes) - false_positives)/float(len(dupes))

  print "recall"
  print true_positives/float(len(duplicates_s))
  print "ran in ", time.time() - t0, "seconds"

  print data_model

  

