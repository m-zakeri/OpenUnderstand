# Core source code metrics development

Reading: 5 minutes, Last update: 10 March 2022

---

The following proposal has been initially prepared for the **IUST Compiler** and **IUST Advanced Compiler**  courses in _Winter/Spring 2022_.

**Note 1:** Before reading this proposal ensure that you have read and understood the [OpenUnderstand white-paper](../index.md).

The goal of this proposal is to implement an extended version of the [Sci-tools Understand APIs for computing source metrics](https://documentation.scitools.com/html/python/api/understand.Metric.html#understand.Metric). 
The following APIs are used to commute source code metrics at different abstraction levels:
* [understand.Db.metric](https://documentation.scitools.com/html/python/api/understand.Db.html)
* [understand.Ent.metric](https://documentation.scitools.com/html/python/api/understand.Ent.html)

Students must form groups of up to *four* persons. Each group develops analysis passes to compute the value of source code metrics listed in [Table 3](../source_code_metrics.md).The exact list of the metrics will be assigned to each group subsequently. The description of the source code metrics listed in [Table 3](../source_code_metrics.md) _may_ update during the semester.

The computation of source code metrics consists of two steps:

* First, developing the required APIs for querying the database created in [Phase 1](core_entity_reference_development.md) of the project. The APIs signature _must_ follow the [Sci-tools Understand Python API](https://documentation.scitools.com/html/python/index.html). 
* Second, querying the database using the developed API to find the appropriate entities and reference kinds involved in computing metrics according to the metric definitions. 


**Note 2:** The computation of each source code metric must be implemented as a standalone Python module (single .py file) in the `openuderstand.metrics` package. Consider the existing modules in the packages as examples. Please strongly use the created database in [Phase 1](core_entity_reference_development.md) to compute source code metrics.


**Note 3:** Each module should follow [PEP -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/) and document well.

**Note 4:** Each group is asked to review the code of at least one other group in the classroom. Your final project score is computed considering the score given by referees to each member of the team.


**Note 5:** Before developing your codes ensure that you have pulled the latest version of the OpenUnderstand repository.
For the final presentation, your code should work properly on the real-world software project existing in the [benchmark](../../benchmark) directory of the OpenUnderstand repository.

Keep in touch!

---
