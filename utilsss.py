import csv
import itertools
import numpy as np
import nltk
import time
import sys
import operator
import io
import array
from datetime import datetime
from gru_theano import GRUTheano
from nltk.tokenize import sent_tokenize, word_tokenize,RegexpTokenizer
from nltk.corpus import wordnet as wn
import csv
import pandas as pd
import csv
import nltk
import numpy as np
import theano as theano
import theano.tensor as T


SENTENCE_START_TOKEN = "sent_start"
SENTENCE_END_TOKEN = "sent_end"
UNKNOWN_TOKEN = "UNKNOWN_TOKEN"



f=open("Sentence.txt","r")
x= f.read()
print()
row_of_sentences=sent_tokenize(x);

for i in range (len(row_of_sentences)):
    tok=word_tokenize(row_of_sentences[i])  #list type
    tok.insert(0,"sent_start")
    tok.append("sent_end")
    row_of_sentences[i]=tok;
    #print(tok)
    
df=pd.read_csv("final.csv",names=['Words'])  
df=df['Words']
#df.loc[0]='sent_start'
voc=df.values.tolist()


#vecx=[]
#vecy=[]
index_to_word=dict()
word_to_index=dict()

for i in row_of_sentences:
    vecx=[]
    for j in i[:-1]:
        #print (j)
        if(j in voc):
            x=voc.index(j)
            vecx.append(x)
            index_to_word[x]=j
            word_to_index[j]=x
        else:
            x=len(voc)
            df.loc[len]=j
            df.to_csv("final.csv")
            voc=df.values.tolist()
            vecx.append(x)
            index_to_word[x]=j
            word_to_index[j]=x


x=voc.index("sent_end")
index_to_word[x]="sent_end"
word_to_index["sent_end"]=x 

def train_with_sgd(model, X_train, y_train, learning_rate=0.001, nepoch=20, decay=0.9,
    callback_every=10000, callback=None):
    num_examples_seen = 0
    for epoch in range(nepoch):
        # For each training example...
        for i in np.random.permutation(len(y_train)):
            # One SGD step
            model.sgd_step(X_train[i], y_train[i], learning_rate, decay)
            num_examples_seen += 1
            # Optionally do callback
            if (callback and callback_every and num_examples_seen % callback_every == 0):
                callback(model, num_examples_seen)            
    return model

def save_model_parameters_theano(model, outfile):
    np.savez(outfile,
        E=model.E.get_value(),
        U=model.U.get_value(),
        W=model.W.get_value(),
        V=model.V.get_value(),
        b=model.b.get_value(),
        c=model.c.get_value())
    print("Saved model parameters to %s." % outfile)

def load_model_parameters_theano(path, modelClass=GRUTheano):
    npzfile = np.load(path)
    E, U, W, V, b, c = npzfile["E"], npzfile["U"], npzfile["W"], npzfile["V"], npzfile["b"], npzfile["c"]
    hidden_dim, word_dim = E.shape[0], E.shape[1]
    print("Building model model from %s with hidden_dim=%d word_dim=%d" % (path, hidden_dim, word_dim))
    sys.stdout.flush()
    model = modelClass(word_dim, hidden_dim=hidden_dim)
    model.E.set_value(E)
    model.U.set_value(U)
    model.W.set_value(W)
    model.V.set_value(V)
    model.b.set_value(b)
    model.c.set_value(c)
    return model 

def gradient_check_theano(model, x, y, h=0.001, error_threshold=0.01):
    # Overwrite the bptt attribute. We need to backpropagate all the way to get the correct gradient
    model.bptt_truncate = 1000
    # Calculate the gradients using backprop
    bptt_gradients = model.bptt(x, y)
    # List of all parameters we want to chec.
    model_parameters = ['E', 'U', 'W', 'b', 'V', 'c']
    # Gradient check for each parameter
    for pidx, pname in enumerate(model_parameters):
        # Get the actual parameter value from the mode, e.g. model.W
        parameter_T = operator.attrgetter(pname)(model)
        parameter = parameter_T.get_value()
        print("Performing gradient check for parameter %s with size %d." % (pname, np.prod(parameter.shape)))
        # Iterate over each element of the parameter matrix, e.g. (0,0), (0,1), ...
        it = np.nditer(parameter, flags=['multi_index'], op_flags=['readwrite'])
        while not it.finished:
            ix = it.multi_index
            # Save the original value so we can reset it later
            original_value = parameter[ix]
            # Estimate the gradient using (f(x+h) - f(x-h))/(2*h)
            parameter[ix] = original_value + h
            parameter_T.set_value(parameter)
            gradplus = model.calculate_total_loss([x],[y])
            parameter[ix] = original_value - h
            parameter_T.set_value(parameter)
            gradminus = model.calculate_total_loss([x],[y])
            estimated_gradient = (gradplus - gradminus)/(2*h)
            parameter[ix] = original_value
            parameter_T.set_value(parameter)
            # The gradient for this parameter calculated using backpropagation
            backprop_gradient = bptt_gradients[pidx][ix]
            # calculate The relative error: (|x - y|/(|x| + |y|))
            relative_error = np.abs(backprop_gradient - estimated_gradient)/(np.abs(backprop_gradient) + np.abs(estimated_gradient))
            # If the error is to large fail the gradient check
            if relative_error > error_threshold:
                print("Gradient Check ERROR: parameter=%s ix=%s" % (pname, ix))
                print("+h Loss: %f" % gradplus)
                print("-h Loss: %f" % gradminus)
                print("Estimated_gradient: %f" % estimated_gradient)
                print("Backpropagation gradient: %f" % backprop_gradient)
                print("Relative Error: %f" % relative_error)
                return 
            it.iternext()
        print("Gradient check for parameter %s passed." % (pname))
              


'''def print_sentence(s, index_to_word):
    sentence_str = [index_to_word[x] for x in s[1:-1]]
    print(" ".join(sentence_str))
    sys.stdout.flush()
'''
def generate_sentence(model,word):
        x=1
        #print("hello")
        # We start the sentence with the given start word
        new_sentence = [voc.index(word)]
        sent=word
        #print(sent)
        while (not new_sentence[-1] ==voc.index("sent_end") and (not x>5)):
            x+=1;
            next_word_probs=model.predict(new_sentence)[-1]
            samples = np.random.multinomial(1, next_word_probs)
            sampled_word = np.argmax(samples)
            new_sentence.append(sampled_word)
            if(not (voc[sampled_word]=="sent_start")):
                sent=sent+" "+voc[sampled_word]
        # Seomtimes we get stuck if the sentence becomes too long, e.g. "........" :(
        # And: We don't want sentences with UNKNOWN_TOKEN's
        
        # sentence_str = [index_to_word[x] for x in new_sentence[1:-1]]
        print("Generated text")
        print(sent)
        print()
