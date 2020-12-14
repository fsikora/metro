## The shortest way to visit all metro lines in a city

Code used in the paper [The shortest way to visit all metro lines in a city](https://arxiv.org/abs/1709.05948)

* Finds the shortest path or cycle using at least once every line of a metro network. 
* Can try different parameters (allowing to re-use multiple times the same station, the line, to be cycle or not, to compute all the solutions or not etc)
* Data of Paris and Tokyo.

### Requirements

* Python3
* Networkx
* CPlex