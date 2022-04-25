# Core entity-reference development

Reading: 5 minutes, Last update: 10 March 2022

---

The following proposal has been initially prepared for the **IUST Compiler** and **IUST Advanced Compiler** courses in _Fall 2021_ and _Winter/Spring 2022_.


**Note 1:** Before reading this proposal ensure that you have read and understood the [OpenUnderstand white-paper](../index.md).

Students must form groups of up to *four* persons. Each group develops analysis passes to find a subset of references kinds listed in [Table 2](../reference_kinds.md) along with their corresponding entities. The exact list of reference kind will be assigned to each group subsequently. The entity kinds in [Table 1](../entity_kinds.md) and references kinds in [Table 2](../reference_kinds.md) _may_ update during the semester for bug fixing purposes.

**Note 2:** Each pair of references kinds must be implemented as a standalone Python module (single .py file) in the `openuderstand.analysis_passes` package. Consider the existing modules in the packages as examples.

**Note 3:** Each python module should follow [PEP -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/) and document well.

**Note 4:** Each group is asked to review the code of at least one other group in the classroom. Your final project score is computed considering the score given by referees to each member of the team.


**Note 5:** Before developing your codes ensure that you have pulled the latest version of the OpenUnderstand repository.
For final presentation, your code must pass all unit tests and have no conflicts with other modules. Unit tests are under development, and we will inform you as they are released.


Keep in touch!

---

