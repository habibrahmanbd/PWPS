import signal
import sys
import json
import jsonrpclib
#import makesets
import makesets 
import pickle
from random import randint
from train_local_elm import get_k_eqs
from train_local_elm import read_parse
from train_local_elm import read_sets
#sys.path.insert(0, 'libsvm/python')
#from svmutil import *
from random import sample
import elm
import numpy as np
multi=None
elmk = None
tr_result = None
data = None
def compute(p,op,e,target,problem,story,order): # Returns the val of probability for the operator 'op'
    vec = makesets.vector(p,e,problem,story,target)
    
    file_to_work = open('data/tm.data', 'w')
    file_to_work.write(repr(0))
    for i in range(len(vec)):
        file_to_work.write(" "+repr(vec[i]))
    file_to_work.write(" \n")
    file_to_work.write(repr(0))
    for i in range(len(vec)):
        file_to_work.write(" "+repr(vec[i]))
    file_to_work.write(" \n")
    file_to_work.close()
    
    test_data = elm.read('data/tm.data')
    #print len(test_data)
    #tr_result = elmk.train(test_data)
    te_result = elmk.test(test_data)
    te_result.predicted_targets = np.round(te_result.predicted_targets)
    val = te_result.predicted_targets[0]
    #print te_result.predicted_targets
    op_val=[]
    c = makesets.combine(p[1],e[1],op)
    return (val,c,op_val)


class StanfordNLP:
    def __init__(self, port_number=8080):
        self.server = jsonrpclib.Server("http://localhost:%d" % port_number)

    def parse(self, text):
        return json.loads(self.server.parse(text))

nlp = StanfordNLP()

def cleannum(n):
    n = ''.join([x for x in n if x.isdigit() or x=='.' or x=='x' or x=='x*'])
    return n

def kill(signum, frame):
    raise Exception("end of time")

def training(a,b,problem,story,target,j,order,score,constraints):
    #this function take the trips and creates positive and negative training instances from them
    
    if j == 0:
        j=-1
    vec = [j,order,score,constraints]
    vec.extend(makesets.eqvector(a,b,problem,story,target))

    return vec


def make_eq(q,a,equations):
    tdata = []
    wps = q #open(q).readlines() #List of the Problem Text
    answs = a #open(a).readlines() # List of the Answers of the problem

    for k in range(len(wps)):
        print(k,equations[k])
        answers = get_k_eqs(equations[k],g=True) # Positive / Negative, Expr, and OBJ_SCORE
        #simpleanswers = [x for x in answers if x[1].split(" ")[-2] == '=']
        #if simpleanswers:
        #    answers = simpleanswers
        good = list(set([x for x in answers if x[0]==1])) # Positive Expresions
        bad = list(set([x for x in answers if x[0]==0]))[:len(good)] # Negative Expresions
        '''
        if len(bad)>len(good):
            bad = sample(bad,len(good))
        '''
        answers = good+bad
        if answers == []: continue
        answers = list(set(answers)) # Gets the distincts


        #First preprocessing, tokenize slightly
        problem = wps[k]#.lower()
        problem = problem.strip().split(" ")
        for i,x in enumerate(problem):
            if len(x)==0:continue
            if x[-1] in [',','.','?']:
                problem[i] = x[:-1]+" "+x[-1]
        problem = ' '.join(problem)
        problem = " " + problem + " "
        print(problem)

        #make story
        #story = nlp.parse(problem)
        story = read_parse(int(equations[k]))
        #sets = makesets.makesets(story['sentences'])
        sets = read_sets(int(equations[k]))
        i = 0

        xidx = [i for i,x in enumerate(sets) if x[1].num=='x']
        if not xidx:
            print("NO X WHY");continue

        #TODO look for 2 xes
        xidx = xidx[0]


        numlist = [(cleannum(v.num),v) for k,v in sets] #takes original Number or variables
        numlist = [x for x in numlist if x[0]!='']
        allnumbs = {str(i):v for i,v in numlist}
        objs = {i:(0,v) for i,v in numlist}
        #print(numlist)
        consts = [x for x in answers[0][1].split(" ") if x not in ['(',')','+','-','/','*','=',]]
        #print(consts)
        present = [x for x in consts if x in objs]
        if present!=consts: print(present,consts);print("missing thing");continue

        scores = []
        #print(answers)

        for j,eq,cons in answers: #j is Good or Bad , Eq is the Expr ...
            consts = [x for x in eq.split(" ") if x not in ['(',')','+','-','/','*','=',]]
            order = int(consts==[x[0] for x in numlist])
            #if order == 0:continue
            trips = []
            print(j,eq)
            l,r = [x.strip().split(' ') for x in eq.split('=')] #Divides the Expersion by left and Right
            consts = " ".join([x for x in answers[0][1].split(" ") if x not in ['(',')','+','-','/','*',]])
            consts = consts.split(" = ")
            
            target = 'x'
            target = (target,objs[target])

            #find innermost parens?
            sides = []
            thisscore = []
            for i,compound in enumerate([l,r]):
                while len(compound)>1:
                    if "(" in compound:
                        rpidx = (len(compound) - 1) - compound[::-1].index('(')
                        lpidx = rpidx+compound[rpidx:].index(")")
                        subeq = compound[rpidx+1:lpidx]
                        substr = "("+''.join(subeq)+")"
                        compound = compound[:rpidx]+[substr]+compound[lpidx+1:]
                    else:
                        subeq = compound[0:3]
                        substr = "("+''.join(subeq)+")"
                        compound = [substr]+compound[3:]
                    p,op,e = subeq
                    p = objs[p]
                    e = objs[e]
                    op = op.strip()
                    pute = compute(p,op,e,target,problem,story,order)
                    objs[substr]=pute
                    if pute == -1:
                        exit()
                    score,c,vals = pute
                    thisscore.append(score)
                sides.append(objs[compound[0]])
            p = sides[0]; e = sides[1]
            #thisscore.append(compute(p,'=',e,target,problem,story,order,sp)[0])
            score = 1
            for s in thisscore: score *= s
            #scores.append((score,j,eq))
            tdata.append(training(sides[0],sides[1],problem,story,target,j,order,score,cons))

    f = open("data/"+sys.argv[1][-1]+".global.data",'w') 
    for v in tdata:
        f.write(str(v[0])+" ")
        for i,j in enumerate(v[1:]):
            f.write(str(j)+" ")
        f.write("\n")




def parse_inp(inp):
    q=[] # List of The problem Texts
    a=[] # List of the Answers of the Problems
    e=[] # List of the Problem Numbers Actually, But used for equations
    with open(inp) as f:
        f = f.readlines()
        i=0
        while i<len(f):
            q.append(f[i])
            i+=1
            e.append(f[i])
            i+=1
            a.append(f[i])
            i+=1
    return (q,a,e)



if __name__=="__main__":
    #q, a = sys.argv[1:3]
    elmk = elm.ELMKernel()
    data = elm.read(sys.argv[2])
    
    tr_result = elmk.train(data)
    #te_result = elmk.test(data)
    #print te_result.predicted_targets
    inp = sys.argv[1] #train'$1'
    
    #multi = svm_load_model(sys.argv[2])
    makesets.FOLD = sys.argv[1][-1]
    q,a,e = parse_inp(inp)
    make_eq(q,a,e)


