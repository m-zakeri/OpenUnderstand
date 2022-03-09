# Source code metrics

Source code metrics are essential components in the software measurement process. They are extracted from the source code of the software, and their values allow us to reach conclusions about the quality attributes measured by the metrics.

OpenUnderstand supports the following source code metrics for the Java programming language.


_Table 3. OpenUnderstand source code metrics for Java_

| API name                      | Friendly name                            | Description                                                                                                            |
| :---------------------------- |:-----------------------------------------|:-----------------------------------------------------------------------------------------------------------------------|
| AvgCyclomatic                 | Average Cyclomatic Complexity            | Average  cyclomatic complexity for all nested functions or methods.                                                    |
| AvgCyclomaticModified         | Average Modified Cyclomatic Complexity   | Average modified cyclomatic complexity for all nested functions or methods.                                            |
| AvgCyclomaticStrict           | Average  Strict Cyclomatic Complexity    | Average strict cyclomatic complexity for all nested functions or methods.               |
| AvgEssential                  | Average                                  
  Essential Cyclomatic Complexity | Average                                  
  Essential complexity for all nested functions or methods.                       |
| AvgLine                       | Average                                  
  Number of Lines                 | Average                                  
  number of lines for all nested functions or methods.                            |
| AvgLineBlank                  | Average                                  
  Number of Blank Lines           | Average                                  
  number of blank for all nested functions or methods.                            |
| AvgLineCode                   | Average                                  
  Number of Lines of Code         | Average                                  
  number of lines containing source code for all nested functions or methods.     |
| AvgLineComment                | Average                                  
  Number of Lines with Comments   | Average                                  
  number of lines containing comment for all nested functions or methods.         |
| CountClassBase                | Base                                     
  Classes                            | Number                                   
  of immediate base classes. (a.k.a. IFANIN)                                          |
| CountClassCoupled             | Coupling                                 
  Between Objects                | Number                                   
  of other classes coupled to. (a.k.a. CBO  or coupling between object classes)         |
| CountClassDerived             | Number                                   
  of Children                      | Number                                   
  of immediate subclasses. (a.k.a. NOC or number of children)                          |
| CountDeclClass                | Classes                                  | Number                                                                                                                 
  of classes.                                                                      |
| CountDeclClassMethod          | Class                                    
  Methods                           | Number                                   
  of class methods.                                                                |
| CountDeclClassVariable        | Class                                    
  Variables                         | Number                                   
  of class variables.                                                              |
| CountDeclExecutableUnit       | Executable                               
  Unit                         | Number                                   
  of program units with executable code.                                           |
| CountDeclFile                 | Number                                   
  of Files                         | Number                                   
  of files.                                                                        |
| CountDeclFunction             | Function                                 | Number                                                                                                                 
  of functions.                                                                    |
| CountDeclInstanceMethod       | Instance                                 
  Methods                        | Number                                   
  of instance methods. (a.k.a. NIM)                                                   |
| CountDeclInstanceVariable     | Instance                                 
  Variables                      | Number                                   
  of instance variables. (a.k.a. NIV)                                                 |
| CountDeclMethod               | Local                                    
  Methods                           | Number                                   
  of local methods.                                                                |
| CountDeclMethodAll            | Methods                                  | Number                                                                                                                 
  of methods, including inherited ones. (a.k.a. RFC or response for class)             |
| CountDeclMethodDefault        | Local                                    
  Default Visibility Methods        | Number                                   
  of local default methods.                                                        |
| CountDeclMethodPrivate        | Private                                  
  Methods                         | Number                                   
  of local private methods. (a.k.a. NPM)                                              |
| CountDeclMethodProtected      | Protected                                
  Methods                       | Number                                   
  of local protected methods.                                                      |
| CountDeclMethodPublic         | Public                                   
  Methods                          | Number                                   
  of local public methods. (a.k.a. NPRM)                                              |
| CountInput                    | Inputs                                   | Number                                                                                                                 
  of calling subprograms plus global variables read. (a.k.a. FANIN)                   |
| CountLine                     | Physical                                 
  Lines                          | Number                                   
  of all lines. (a.k.a. NL)                                                           |
| CountLineBlank                | Blank                                    
  Lines of Code                     | Number                                   
  of blank lines. (a.k.a. BLOC)                                                       |
| CountLineCode                 | Source                                   
  Lines of Code                    | Number                                   
  of lines containing source code. (a.k.a. LOC)                                       |
| CountLineCodeDecl             | Declarative                              
  Lines of Code               | Number                                   
  of lines containing declarative source code.                                     |
| CountLineCodeExe              | Executable                               
  Lines of Code                | Number                                   
  of lines containing executable source code.                                      |
| CountLineComment              | Lines                                    
  with Comments                     | Number                                   
  of lines containing comment. (a.k.a. CLOC)                                          |
| CountOutput                   | Outputs                                  | Number                                                                                                                 
  of called subprograms plus global variables set. (a.k.a. FANOUT)                    |
| CountPath                     | Paths                                    | Number                                                                                                                 
  of possible paths, not counting abnormal exits or gotos. (a.k.a. NPATH)             |
| CountPathLog                  | Paths                                    
  Log(x)                            | Log10,                                   
  truncated to an integer value, of the metric CountPath                           |
| CountSemicolon                | Semicolons                               | Number                                                                                                                 
  of semicolons.                                                                   |
| CountStmt                     | Statements                               | Number                                                                                                                 
  of statements.                                                                   |
| CountStmtDecl                 | Declarative                              
  Statements                  | Number                                   
  of declarative statements.                                                       |
| CountStmtExe                  | Executable                               
  Statements                   | Number                                   
  of executable statements.                                                        |
| Cyclomatic                    | Cyclomatic                               
  Complexity                   | Cyclomatic                               
  complexity.                                                                  |
| CyclomaticModified            | Modified                                 
  Cyclomatic Complexity          | Modified                                 
  cyclomatic complexity.                                                         |
| CyclomaticStrict              | Strict                                   
  Cyclomatic Complexity            | Strict                                   
  cyclomatic complexity.                                                           |
| Essential                     | Essential                                
  Complexity                    | Essential                                
  complexity. (a.k.a. Ev(G))                                                       |
| Knots                         | Knots                                    | Measure                                                                                                                
  of overlapping jumps.                                                           |
| MaxCyclomatic                 | Max                                      
  Cyclomatic Complexity               | Maximum                                  
  cyclomatic complexity of all nested functions or methods.                       |
| MaxCyclomaticModified         | Max                                      
  Modified Cyclomatic Complexity      | Maximum                                  
  modified cyclomatic complexity of nested functions or methods.                  |
| MaxCyclomaticStrict           | Max                                      
  Strict Cyclomatic Complexity        | Maximum                                  
  strict cyclomatic complexity of nested functions or methods.                    |
| MaxEssential                  | Max                                      
  Essential Complexity                | Maximum                                  
  essential complexity of all nested functions or methods.                        |
| MaxEssentialKnots             | Max                                      
  Knots                               | Maximum                                  
  Knots after structured programming constructs have been removed.                |
| MaxInheritanceTree            | Depth                                    
  of Inheritance Tree               | Maximum                                  
  depth of class in inheritance tree. (a.k.a. DIT)                                   |
| MaxNesting                    | Nesting                                  | Maximum                                                                                                                
  nesting level of control constructs.                                            |
| MinEssentialKnots             | Minimum                                  
  Knots                           | Minimum                                  
  Knots after structured programming constructs have been removed.                |
| PercentLackOfCohesion         | Lack                                     
  of Cohesion in Methods             | 100%                                     
  minus the average cohesion for package entities. (aka LCOM, LOCM)                  |
| PercentLackOfCohesionModified | Modified                                 
  Lack of Cohesion in Methods    | 100%                                     
  minus the average cohesion for class data members, modified for accessor
  methods |
| RatioCommentToCode            | Comment
  to Code Ratio                   | Ratio
  of comment lines to code lines.                                                   |
| SumCyclomatic                 | Sum
  Cyclomatic Complexity               | Sum
  of cyclomatic complexity of all nested functions or methods. (a.k.a. WMC)              |
| SumCyclomaticModified         | Sum
  Modified Cyclomatic Complexity      | Sum
  of modified cyclomatic complexity of all nested functions or methods.               |
| SumCyclomaticStrict           | Sum
  Strict Cyclomatic Complexity        | Sum
  of strict cyclomatic complexity of all nested functions or methods.                 |
| SumEssential                  |                                           | Sum of essential complexity of all nested functions
  or methods.                         |
  
