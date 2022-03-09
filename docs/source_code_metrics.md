# Source code metrics

Source code metrics are essential components in the software measurement process. They are extracted from the source code of the software, and their values allow us to reach conclusions about the quality attributes measured by the metrics.

OpenUnderstand supports the following source code metrics for the Java programming language.


_Table 3. OpenUnderstand source code metrics for Java_




| API name                      	| Friendly name                                              	| Description                                                                               	|
|-------------------------------	|------------------------------------------------------------	|-------------------------------------------------------------------------------------------	|
| AvgCyclomatic                 	| Average   Cyclomatic Complexity                            	| Average   cyclomatic complexity for all nested functions or methods.                      	|
| AvgCyclomaticModified         	| Average   Modified Cyclomatic Complexity                   	| Average   modified cyclomatic complexity for all nested functions or methods.             	|
| AvgCyclomaticStrict           	| Average   Strict Cyclomatic Complexity                     	| Average   strict cyclomatic complexity for all nested functions or methods.               	|
| AvgEssential                  	| Average   Essential Cyclomatic Complexity                  	| Average   Essential complexity for all nested functions or methods.                       	|
| AvgLine                       	| Average   Number of Lines                                  	| Average   number of lines for all nested functions or methods.                            	|
| AvgLineBlank                  	| Average   Number of Blank Lines                            	| Average   number of blank for all nested functions or methods.                            	|
| AvgLineCode                   	| Average   Number of Lines of Code                          	| Average   number of lines containing source code for all nested functions or methods.     	|
| AvgLineComment                	| Average   Number of Lines with Comments                    	| Average   number of lines containing comment for all nested functions or methods.         	|
| CountClassBase                	| Base   Classes                                             	| Number   of immediate base classes. [aka IFANIN]                                          	|
| CountClassCoupled             	| Coupling   Between Objects                                 	| Number   of other classes coupled to. [aka CBO (coupling between object classes)]         	|
| CountClassDerived             	| Number   of Children                                       	| Number   of immediate subclasses. [aka NOC (number of children)]                          	|
| CountDeclClass                	| Classes                                                    	| Number   of classes.                                                                      	|
| CountDeclClassMethod          	| Class   Methods                                            	| Number   of class methods.                                                                	|
| CountDeclClassVariable        	| Class   Variables                                          	| Number   of class variables.                                                              	|
| CountDeclExecutableUnit       	| Executable   Unit                                          	| Number   of program units with executable code.                                           	|
| CountDeclFile                 	| Number   of Files                                          	| Number   of files.                                                                        	|
| CountDeclFunction             	| Function                                                   	| Number   of functions.                                                                    	|
| CountDeclInstanceMethod       	| Instance   Methods                                         	| Number   of instance methods. [aka NIM]                                                   	|
| CountDeclInstanceVariable     	| Instance   Variables                                       	| Number   of instance variables. [aka NIV]                                                 	|
| CountDeclMethod               	| Local   Methods                                            	| Number   of local methods.                                                                	|
| CountDeclMethodAll            	| Methods                                                    	| Number   of methods, including inherited ones. [aka RFC (response for class)]             	|
| CountDeclMethodDefault        	| Local   Default Visibility Methods                         	| Number   of local default methods.                                                        	|
| CountDeclMethodPrivate        	| Private   Methods                                          	| Number   of local private methods. [aka NPM]                                              	|
| CountDeclMethodProtected      	| Protected   Methods                                        	| Number   of local protected methods.                                                      	|
| CountDeclMethodPublic         	| Public   Methods                                           	| Number   of local public methods. [aka NPRM]                                              	|
| CountInput                    	| Inputs                                                     	| Number   of calling subprograms plus global variables read. [aka FANIN]                   	|
| CountLine                     	| Physical   Lines                                           	| Number   of all lines. [aka NL]                                                           	|
| CountLineBlank                	| Blank   Lines of Code                                      	| Number   of blank lines. [aka BLOC]                                                       	|
| CountLineCode                 	| Source   Lines of Code                                     	| Number   of lines containing source code. [aka LOC]                                       	|
| CountLineCodeDecl             	| Declarative   Lines of Code                                	| Number   of lines containing declarative source code.                                     	|
| CountLineCodeExe              	| Executable   Lines of Code                                 	| Number   of lines containing executable source code.                                      	|
| CountLineComment              	| Lines   with Comments                                      	| Number   of lines containing comment. [aka CLOC]                                          	|
| CountOutput                   	| Outputs                                                    	| Number   of called subprograms plus global variables set. [aka FANOUT]                    	|
| CountPath                     	| Paths                                                      	| Number   of possible paths, not counting abnormal exits or gotos. [aka NPATH]             	|
| CountPathLog                  	| Paths   Log(x)                                             	| Log10,   truncated to an integer value, of the metric CountPath                           	|
| CountSemicolon                	| Semicolons                                                 	| Number   of semicolons.                                                                   	|
| CountStmt                     	| Statements                                                 	| Number   of statements.                                                                   	|
| CountStmtDecl                 	| Declarative   Statements                                   	| Number   of declarative statements.                                                       	|
| CountStmtExe                  	| Executable   Statements                                    	| Number   of executable statements.                                                        	|
| Cyclomatic                    	| Cyclomatic   Complexity                                    	| Cyclomatic   complexity.                                                                  	|
| CyclomaticModified            	| Modified   Cyclomatic Complexity                           	| Modified   cyclomatic complexity.                                                         	|
| CyclomaticStrict              	| Strict   Cyclomatic Complexity                             	| Strict   cyclomatic complexity.                                                           	|
| Essential                     	| Essential   Complexity                                     	| Essential   complexity. [aka Ev(G)]                                                       	|
| Knots                         	| Knots                                                      	| Measure   of overlapping jumps.                                                           	|
| MaxCyclomatic                 	| Max   Cyclomatic Complexity                                	| Maximum   cyclomatic complexity of all nested functions or methods.                       	|
| MaxCyclomaticModified         	| Max   Modified Cyclomatic Complexity                       	| Maximum   modified cyclomatic complexity of nested functions or methods.                  	|
| MaxCyclomaticStrict           	| Max   Strict Cyclomatic Complexity                         	| Maximum   strict cyclomatic complexity of nested functions or methods.                    	|
| MaxEssential                  	| Max   Essential Complexity                                 	| Maximum   essential complexity of all nested functions or methods.                        	|
| MaxEssentialKnots             	| Max   Knots                                                	| Maximum   Knots after structured programming constructs have been removed.                	|
| MaxInheritanceTree            	| Depth   of Inheritance Tree                                	| Maximum   depth of class in inheritance tree. [aka DIT]                                   	|
| MaxNesting                    	| Nesting                                                    	| Maximum   nesting level of control constructs.                                            	|
| MinEssentialKnots             	| Minimum   Knots                                            	| Minimum   Knots after structured programming constructs have been removed.                	|
| PercentLackOfCohesion         	| Lack   of Cohesion in Methods                              	| 100%   minus the average cohesion for package entities. [aka LCOM, LOCM]                  	|
| PercentLackOfCohesionModified 	| Modified   Lack of Cohesion in Methods                     	| 100%   minus the average cohesion for class data members, modified for accessor   methods 	|
| RatioCommentToCode            	| Comment   to Code Ratio                                    	| Ratio   of comment lines to code lines.                                                   	|
| SumCyclomatic                 	| Sum   Cyclomatic Complexity                                	| Sum   of cyclomatic complexity of all nested functions or methods. [aka WMC]              	|
| SumCyclomaticModified         	| Sum   Modified Cyclomatic Complexity                       	| Sum   of modified cyclomatic complexity of all nested functions or methods.               	|
| SumCyclomaticStrict           	| Sum   Strict Cyclomatic Complexity                         	| Sum   of strict cyclomatic complexity of all nested functions or methods.                 	|
| SumEssential                  	| Sum Essential Complexity                                   	| Sum of essential complexity of all nested functions   or methods.                         	|
| NAMM                          	| Number   of Accessor (Getter) and Mutator (Setter) Methods 	|                                                                                           	|
| NOID                          	| Number of Identifiers                                      	|                                                                                           	|
| NOKW                          	| Number of Keywords                                         	|                                                                                           	|
| HCPL                          	| Halstead   Calculated Program Length                       	|                                                                                           	|
| HDIF                          	| Halstead   Difficulty                                      	|                                                                                           	|
| HEFF                          	|  	Halstead Effort                                           	|                                                                                           	|
| HNDB                          	| Halstead   Number of Delivered Bugs                        	|                                                                                           	|
| HPL                           	| Halstead   Program Length                                  	|                                                                                           	|
| HPV                           	|  	Halstead Program Vocabulary                               	|                                                                                           	|
| HTRP                          	| Halstead   Time Required to Program                        	|                                                                                           	|
| HVOL                          	| Halstead   Volume                                          	|                                                                                           	|
| NOABSCLASS                    	| Number of   Abstract Class                                 	|                                                                                           	|
| NOINTERFACE                   	| NOINTERFACE                                                	|                                                                                           	|


