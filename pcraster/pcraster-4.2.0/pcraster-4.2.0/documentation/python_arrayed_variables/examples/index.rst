.. _examples:

Examples
********

Initialising arrays and assigning values in the script
------------------------------------------------------

The first example demonstrates a simple dynamic script with the usage of index variables, assigning values and looping over over the array indices:

.. literalinclude::  ../../../data/demo/python_arrayed_variables/simpleLoops.py

In the initial section we create an index type, called Plants with two types of array-index, namely TG and SG. After that, two variables, QMax and Cvr are initialised and individual values are assigned. For two other variables, dH and dH_1, array-indeces are initialised with an default value of 0.

In the dynamic section we loop over the array-indices and execute some simple operations.

Using parameter files for variable initialisation
-------------------------------------------------

The second example simplifies the initialisation of variables by external files:

.. literalinclude:: ../../../data/demo/python_arrayed_variables/parameterFile.py
..   :linenos:

The functionality of the example above equals the one of the first example. Here, the variables QMax and Cvr are initialised from a parameter file 'plant.tbl'.


Parameter files
~~~~~~~~~~~~~~~

The structure of the parameter files must be the same as used for oldcalc. Therefore, the second example uses a parameter file like:

.. literalinclude:: ../../../data/demo/python_arrayed_variables/plant.tbl
