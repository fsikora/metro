###### PARAMETERS
RERlinesInput=True
tourWithRER=False                   #RERlinesInput should be true then...
tourCyclic=False
allowSameStationTwice=True
allowRetakeTheLine=True
startingPoint=None                  #use Gambetta if you want the shortest Cyclic tour (if tourCyclic is True) #use None if no startingPoint given
tokyo=False
multipleSolution=False
allowFootPath=True
threadsNb=2 #used by CPlex

#########################

import networkx as nx
import cplex
import math

#CPlex Object
C = cplex.Cplex()
C.parameters.threads.set(threadsNb)


def draw(G):
    import matplotlib.pyplot as plt
    col={}
    #https://stackoverflow.com/questions/25639169/networkx-change-color-width-according-to-edge-attributes-inconsistent-result
    col['1']="y"
    col['2']="b"
    col['3']="brown"
    col['4']="red"
    col['5']="orange"
    col['6']="g"
    col['7']="pink"
    col['8']="purple"
    col['9']="green"
    col['10']="yellow"
    col['11']="brown"
    col['12']="green"
    col['13']="blue"
    col['14']="purple"
    col["3b"]="b"
    col["7b"]="g"
    
    edgec=[]
    ed=[]
    for e in G.edges(data=True):
        if not e[2]['line'].startswith('P'):
            
            edgec.append(col[e[2]['line']])
            ed.append(e)
    nx.draw(G,pos=nx.spring_layout(G),with_labels=True,edgelist=ed,node_color="w", edge_color=edgec, edge_vmin=1, edge_vmax=16)

    plt.show()
    import sys
    sys.exit()

def parseParis(fileName):
    f = open(fileName, 'r')
    G = nx.MultiDiGraph()
    prev = None
    
    for l in f:
        l = l.strip()
        if l.startswith("##"):
            prev = None
            continue
        d = l.split(':')
        line = d[0].split('-')[0]
        stat = d[1]
        if stat.startswith('P') and not allowFootPath:
            continue
        if prev != None:
            G.add_edge(prev, stat, line=line, weight=1)
        prev = stat
    f.close()
    
    #draw(G)
    
    #path from s to t, we can go from s to any, and from any to t
    nodes=set(G.nodes())
    #for n in G.nodes():
    for n in nodes:
        if startingPoint is None:      
            G.add_edge('s',n,line=0,weight=0)
        if not tourCyclic:
            G.add_edge(n,'t',line=0,weight=0)
        
    return G
    
def parseTokyo():
    f = open('tokyoAll.csv', 'r')
    
    G = nx.MultiDiGraph()
    prev = None
    line = None
    lines = set()
    
    for l in f:
        l = l.strip()
        l2 = l.split(',')
        stat = l2[0]
        stat = stat.lower()
        if line is None or l2[1] != line:
            line = l2[1]
            if not line.startswith("P"):
                lines.add(line)
            prev = None
        
        if prev is not None:
            G.add_edge(prev, stat, line=line, weight=1)
            G.add_edge(stat, prev, line=line, weight=1)
        prev = stat
            
        
    #path from s to t, we can go from s to any, and from any to t
    for n in G.nodes():
        if startingPoint is None:      
            G.add_edge('s',n,line=0,weight=0)
        if not tourCyclic:
            G.add_edge(n,'t',line=0,weight=0)
        
    f.close()
    return (G,lines)


def removeDegOne(G):
    b = False
    toRemove = set()
    for n in G.nodes():
        p = set(G.predecessors(n))
        s = set(G.successors(n))
        if 's' in p:
            p.remove('s')
        if 't' in s:
            s.remove('t')
        if len(p) == 1 and p == s:
            #G.remove_node(n)
            toRemove.add(n)
            b = True
    if b:
        G.remove_nodes_from(toRemove)
    return b
    
def preprocess(G):
    #n=299, e=1288 -> n=188, e=844
    #remove degree 1+1 to the same
    #remove while there is (removing could create others)
    while removeDegOne(G):
        pass

if tokyo:
    (G,lines) = parseTokyo()
else:
    if RERlinesInput:
        #G = parseParis("stationsWithRERNoAccent.data")
        G = parseParis("stationsWithRERNoAccentNewL14.data")
    else:
        #G = parseParis("stationsWithoutRERNoAccent.data")
        G = parseParis("stationsWithoutRERNoAccentNewL14.data")
        


preprocess(G)

if not tokyo:
    if tourWithRER:
        lines = set(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', "7b", "3b", "A", "B", "C", "D", "E"])
    else:
        lines = set(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', "7b", "3b"])

if not tourCyclic:
    lines.add(0)

changingLines=[]

x='x'
y='v'
f='f'
c='c'

def var5(s1,s2,s3,l1,l2):
    return c+str(s1)+"_"+str(s2)+"_"+str(s3)+"_"+str(l1)+"_"+str(l2)

def var(l,a,b=None,c=None):
    if b and c:
        return l+str(a)+"_"+str(b)+"_"+str(c)
    elif b:
        return l+str(a)+"_"+str(b)
    else :
        return l+str(a)
        
#shortest
C.objective.set_sense(C.objective.sense.minimize)

#min number of used edges
for e in G.edges(data=True):
    #need to have multiple variables for u and v if there is different lines using it...
    #+1 as coef except for footpath (with epsilon weight to avoid taking them for free)!
    if e[2]['line']!=0 and e[2]['line'].startswith("P"):
        weight=0.001
    else:
        weight=1
    C.variables.add(obj=[weight], names=[var(x,e[0],e[1],e[2]['line'])], types=C.variables.type.binary)
    
    #Flow variables, not in the objective
    C.variables.add(names=[var(f,e[0],e[1],e[2]['line'])], types=C.variables.type.integer)
    
    #to minimize the number of line changes... (to comment)
    #for each edge, look at the successor and add a variable whose weight will depend on the line change
    #or, we want to avoid this, just add the variables but not in the objective
    if not allowRetakeTheLine:
        for e2 in G.out_edges(e[1], data=True):
            if e[2]['line'] == e2[2]['line']:
                weight=0
            else:
                #weight=100
                weight=0
            v = var5(e[0],e[1],e2[1],e[2]['line'],e2[2]['line'])
            C.variables.add(obj=[weight], names=[v], types=C.variables.type.binary)
            changingLines.append((e[0],e[1],e2[1],e[2]['line'],e2[2]['line']))  #adding the 4-tuple to reuse after
   
    
    
#just to know if a station is used or not
for v in G.nodes():
   C.variables.add(names=[var(y,v)], types=C.variables.type.integer)
    
    
#look for a path from s to t
for i in G.nodes():
    ind = []
    val = []
    for j in G.successors(i):
        for ed,edv in G.get_edge_data(i,j).items():
            ind.append(var(x,i,j,edv['line']))
            val.append(1)
    for j in G.predecessors(i):
        for ed,edv in G.get_edge_data(j,i).items():
            ind.append(var(x,j,i,edv['line']))
            val.append(-1)
    right = 0
    if not tourCyclic and (i == startingPoint or (startingPoint is None and i == 's')):
        right  = 1
    if not tourCyclic and i == 't':
        right = -1
    sp = cplex.SparsePair(ind = ind, val = val)
    C.linear_constraints.add(lin_expr=[sp], senses = "E", rhs=[right], range_values = [0])      #E : equals
#sum of out must be equal to sum of out

#if a node is selected, at least one arc must be
for v in G.nodes():
   ind = []
   val = []
   ind.append(var(y,v))
   val.append(1)
   for j in G.successors(v):
        for ed,edv in G.get_edge_data(v,j).items():
            ind.append(var(x,v,j,edv['line']))
            val.append(-1)
   for j in G.predecessors(v):
       for ed,edv in G.get_edge_data(j,v).items():
            ind.append(var(x,j,v,edv['line']))
            val.append(-1)
   sp = cplex.SparsePair(ind = ind, val = val)
   C.linear_constraints.add(lin_expr=[sp], senses = "G", rhs=[0], range_values = [0])  


   #do not take more than once a station: must be used 2 times max
   if not allowSameStationTwice:
    C.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=[var(y,v)], val=[1])], senses = "L", rhs=[2], range_values = [0])  


if not allowRetakeTheLine:
    #constraints to set up correctly the binary variable saying there is a change of line
    for e in G.edges(data=True):
        for e2 in G.out_edges(e[1], data=True):
            ind=[]
            val=[]
            
            ind.append(var(x,e[0],e[1],e[2]['line']))
            val.append(1)
            ind.append(var(x,e2[0],e2[1],e2[2]['line']))    #e[1] must be equal to e2[0]
            val.append(1)
            ind.append(var5(e[0],e[1],e2[1],e[2]['line'],e2[2]['line']))
            val.append(-1)
            
            sp = cplex.SparsePair(ind = ind, val = val)
            C.linear_constraints.add(lin_expr=[sp], senses = "L", rhs=[1], range_values = [0])  

    #we want to avoid more than 2 change line for a given line (in and out)
    for line in lines:
        if line is not 0 and not line.startswith("P"):
            ind=[]
            val=[]
            for (s1,s2,s3,l1,l2) in changingLines:
                if l1 != l2 and (l1 == line or l2 == line):
                    ind.append(var5(s1,s2,s3,l1,l2))
                    val.append(1)
            sp = cplex.SparsePair(ind = ind, val = val)
            C.linear_constraints.add(lin_expr=[sp], senses = "E", rhs=[2], range_values = [0])
        
#to avoid disjoint CC, additional flow
n = 2*len(G.nodes())+4

#flow is non-negative only for visited edges
for e in G.edges(data=True):
    ind = []
    val = []
    
    ind.append(var(x,e[0],e[1],e[2]['line']))
    val.append(n)
    ind.append(var(f,e[0],e[1],e[2]['line']))
    val.append(-1)
    sp = cplex.SparsePair(ind = ind, val = val)
    C.linear_constraints.add(lin_expr=[sp], senses = "G", rhs=[0])

#all vertices except source loses some flow
for v in G.nodes():
    b = True
    if startingPoint is not None:
        b = v.startswith(startingPoint)
        
    if (startingPoint is None and v is not 's') or not b:
        ind = []
        val = []
        for e in G.in_edges(v, data=True):
            ind.append(var(f,e[0],e[1],e[2]['line']))
            val.append(1)
        for e in G.out_edges(v, data=True):
            ind.append(var(f,e[0], e[1], e[2]['line']))
            val.append(-1)
            
        ind.append(var(y,v))
        val.append(-1)
            
        sp = cplex.SparsePair(ind = ind, val = val)
        C.linear_constraints.add(lin_expr=[sp], senses = "G", rhs=[0])
   
#all lines must be used
for line in lines:
    ind = []
    val = []
    for e in G.edges(data=True):
        if e[2]["line"] == line:
            ind.append(var(x,e[0],e[1],line))
            val.append(1)
    sp = cplex.SparsePair(ind = ind, val = val)
    C.linear_constraints.add(lin_expr=[sp], senses = "G", rhs=[1])  #G: greater
    
    
def getEdge(G, var):
    elements = var[1:].split("_")
    return elements


def findIndex(l, startStation):
    i=0
    for el in l:    
        if el[0].startswith(startStation):
            return i
        i+=1
    return -1
    
#C.write("metro.lp")

if not multipleSolution:
    C.solve()

    for v in C.variables.get_names():
        print (v, " ", C.solution.get_values(v))

    print ("Solution value  = ", C.solution.get_objective_value())

    edges = []
    for v in C.variables.get_names():
        if C.solution.get_values(v) > 0.9 and C.solution.get_values(v) < 1.1 and v.startswith("x"):
            print (v, " ", C.solution.get_values(v))
            edges.append(getEdge(G,v))

    st = 1
    prev = startingPoint
    if startingPoint is None:
        prev = 's'
    while len(edges) > 0:
        i = findIndex(edges,prev)
        if i == -1:
            print ("Remains to be inserted:")
            print (edges)
            break
        print (st, ' ', edges[i])
        prev = edges[i][1]
        del(edges[i])
        st += 1
else:
    C.solve()
    
    curStr="SOLS:\n"
    bestObj = C.solution.get_objective_value()
    curStr += "best"+ str(bestObj)+"\n"
    bestObj = math.floor(bestObj)
    solcur = 0
    
    while True:

        edges = []
        for v in C.variables.get_names():
            if C.solution.get_values(v) > 0.9 and C.solution.get_values(v) < 1.1 and v.startswith("x"):
                edges.append(getEdge(G,v))

        st = 1
        prev = startingPoint
        if startingPoint is None:
            prev = 's'
        while len(edges) > 0:
            i = findIndex(edges,prev)
            if i == -1:
                curStr += "Remains to be inserted:\n"
                curStr += str(edges)+"\n"
                break
            curStr += str(st)+ ' '+ str(edges[i])+"\n"
            prev = edges[i][1]
            del(edges[i])
            st += 1
        
        
        #add the previous solution has not possible solution anymore
        ind = []
        val = []
        nb = 0
        for v in C.variables.get_names():
            if C.solution.get_values(v) > 0.9 and C.solution.get_values(v) < 1.1 and v.startswith("x"):
                nb +=1
                ind.append(v)
                val.append(1)
        sp = cplex.SparsePair(ind = ind, val = val)
        C.linear_constraints.add(lin_expr=[sp], senses = "L", rhs=[nb-1])
        
        #relaunch the solver
        C.solve()
        solcur+=1
        obj = C.solution.get_objective_value()
        curStr += "\n\nSolution: "+ str(solcur)+ "Value"+ str(obj) +"\n"
        
        print (curStr)
        
        #no alternative solution anymore
        #using floor to ignore footpaths
        if math.floor(obj) > bestObj:
            break
    
    print ("End:")
    print (curStr)
    
