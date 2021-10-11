# Reference kinds

The total number of Java references kinds is 34×2=68. Table 2 lists the OpenUnderstand Java reference kinds, the kind names, and the kind examples for use with the Python API.



_Table 2. Java references kinds details_


 |     Reference kind full name                                                                                                                                           |     Description                                                                                                                                                                                                                                                                                                                                                                                  |     Example code snippet                                                                                                                                                      |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     Java Call/Callby                                                                                                                                                   |     Indicates an invocation of a method.                                                                                                                                                                                                                                                                                                                                                         |  [Call and Callby](#call-and-callby)    |
|     Java Call/Callby Nondynamic                                                                                                                                        |     Indicates a non-dynamic invocation of a method.                                                                                                                                                                                                                                                                                                                                              | [Java Call Nondynamic and Callby Nondynamic](#java-call-nondynamic-and callby-nondynamic)      |
|     Java Cast/Castby                                                                                                                                                   |     Indicates a type is used to cast an instance to a different type.                                                                                                                                                                                                                                                                                                                            |  [Java Cast and Castby](#java-cast-and-castby)   |
|     Java Contain/Containin                                                                                                                                             |     Indicates a class is in a package.                                                                                                                                                                                                                                                                                                                                                           |  [Java Contain and Containin](#java-contain-and-containin)                                                                                       |
|           Java Couple/Coupleby                                                                                                                                         |     Indicates a coupling link as counted in   the OO coupling metrics. A link is created from a class to any external class   (a class that is not in the extends/implements hierarchy) that is referenced.                                                                                                                                                                                      |  [Java Couple and Coupleby](#java-couple-and-coupleby)                                                                                         |
|     Java Extend Couple/Coupleby     Java Extend Couple/Coupleby External     Java Extend Couple/Coupleby Implicit     Java Extend Couple/Coupleby Implicit External    |     Indicates one class or interface   extends another. This extends     relation is used when the extended   class is in a file that is part of the project. If the extended class was   found in a classpath .jar file, the relation is Java Extend Couple External.   If the Indicates class implicitly extends the java.lang.Object class, the   relation is Java Extend Couple Implicit.    |  [Java Extend Couple and Extendby Coupleby ](#java-extend-couple-and-extendby-coupleby)                                                                              |
|     Java Implement Couple/Coupleby                                                                                                                                     |     Indicates a class implements an   interface.                                                                                                                                                                                                                                                                                                                                                 |   [Java Implement Couple and Implementby Coupleby ](#java-implement-couple-and-implementby-coupleby)                                                  |
|     Java Create/Createby                                                                                                                                               |     Indicates that an instance of a class is created (“new” operator)   in a scope.                                                                                                                                                                                                                                                                                                              |   [Java Create and Createby](#java-create-and-createby)                                                                                   |
|     Java Declare/Declarein                                                                                                                                             |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |      [Java Declare and Declarein](#java-declare-and-declarein)                                                                                                                                                                     |
|     Java Define/Definein                                                                                                                                               |     Indicates that an entity is defined in a scope.                                                                                                                                                                                                                                                                                                                                              |   [Java Define and Definein](#java-define-and-definein)                                                                                                          |
|     Java Define/Definein Implicit                                                                                                                                      |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Define and Definein Implicit](#java-define-and-definein)                                                                           |
|     Java DotRef/DotRefby                                                                                                                                               |     Indicates that an entity name was used to the left of a “.” in a     qualified name.                                                                                                                                                                                                                                                                                                         |   [Java DotRef and DotRefby](#java-dotref-and-dotrefby)  |
|     Java Export/Exportby                                                                                                                                               |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Export and Exportby](#java-export-and-exportby)                                                                                                                                                                     |
|     Java Import/Importby     Java Import/Importby Demand                                                                                                               |     Java Import indicates a file imports an individual class. For     example, the some_file.java file might contain:     import pack1.some_class;     Java Import Demand indicates a file has an on-demand import statement   for a package or class. For example, the some_file.java file might contain:     import pack1.*;                                                                   | [Java Import and Importby](#java-import-and-importby)                                                                                                              |
|     Java Modify/Modifyby                                                                                                                                               |     Indicates that a variable’s value is modified or both read and   set, as with the increment (++), decrement (--), and assignment/operator combinations   (*=, /=, ...).                                                                                                                                                                                                                      |  [Java Modify and Modifyby](#java-modify-and-modifyby)                                                                                                     |
|     Java ModuleUse/ModuleUseby                                                                                                                                         |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java ModuleUse and ModuleUseby](#java-moduleuse-and-moduleuseby)                                                                                                                                                                     |
|     Java Override/Overrideby                                                                                                                                           |     Indicates that a method overrides a method from a parent class.                                                                                                                                                                                                                                                                                                                              |  [Java Override and Overrideby](#java-override-and-overrideby)                               |
|     Java Provide/Provideby                                                                                                                                             |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Provide and Provideby](#java-provide-and-provideby)                                                                                                                                                                     |
|     Java Require/Requireby                                                                                                                                             |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Require and Requireby](#java-require-and-requireby)                                                                                                                                                                    |
|     Java Set/Setby                                                                                                                                                     |     Java Set indicates that a variable is set by a separate   statement.                                                                                                                                                                                                                                                                                                                         |  [Java Set and Setby](#java-set-and-setby)                                                                                                          |
|     Java Set/Setby Init                                                                                                                                                |     Java Set Init indicates that a variable is initialized in its   declaration.                                                                                                                                                                                                                                                                                                                 |  [Java Set Init and Setby Init](#java-set-and-setby)                                                                                                                  |
|     Java Set/Setby Partial                                                                                                                                             |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Set Partial and Setby Partial](#java-set-and-setby)                                                                                                                                                                     |
|     Java Typed/Typedby                                                                                                                                                 |     Indicates the type of a variable or parameter.                                                                                                                                                                                                                                                                                                                                               |  [Java Typed and Typedby](#java-typed-and-typedby)                                                                                             |
|     Java Use/Useby                                                                                                                                                     |     Indicates that a variable is used or read.                                                                                                                                                                                                                                                                                                                                                   |  [Java Use and Useby](#java-use-and-useby)                               |
|     Java Use/Useby Partial                                                                                                                                             |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Use Partial and Useby Partial](#java-use-and-useby)                                                                                                                                                                   |
|     Java Use/Useby Ptr                                                                                                                                                 |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Use Ptr and Useby Ptr](#java-use-and-useby)                                                                                                                                                                     |
|     Java Use/Useby Return                                                                                                                                              |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |      [Java Use Return and Useby Return](#java-use-and-useby)                                                                                                                                                                     |
|     Java Open/Openby                                                                                                                                                   |     Todo:                                                                                                                                                                                                                                                                                                                                                                                        |     [Java Open and Openby](#java-open-and-openby)                                                                                                                                                                     |
|     Java Throw/Throwby                                                                                                                                                 |     Indicates that a method throws an exception.                                                                                                                                                                                                                                                                                                                                                 |  [Java Throw and Throwby](#java-throw-and-throwby)                                                                                           |
|     Java End                                                                                                                                                           |     Indicates the end   of a class, interface, or method.                                                                                                                                                                                                                                                                                                                                        |   [Java End and Endby](#java-end-and-endby)                                                                                                                      |


## Reference kind examples
This section describes the example in Table 2 with more details.


### Call and Callby
Indicates an invocation of a method.

```java
class class1 {
 void meth1() {
  ...
 }
}
class class2 {
 class1 some_obj;
 void meth2() {
  some_obj.meth1();
 }
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Call                  |     `meth2`                             |     `meth1`                        |
|     Java Callby                |     `meth1`                             |     `meth2`                        |


### Java Call Nondynamic and Callby Nondynamic
Indicates a non-dynamic invocation of a method.

```java
class class1 {
 void meth1() {
  ...
 }
}
class class2 extends class1 {
 class1 some_obj;
 void meth1() {
  super.meth1();
 }
}

```

|     Reference kind   string     |     Entity   performing references    |     Entity being   referenced    |
|---------------------------------|---------------------------------------|----------------------------------|
|     Java Call   Nondynamic      |     `class2.meth1`                      |     `class1.meth1`                 |
|     Java Callby   Nondynamic    |     `class1.meth1`                      |     `class2.meth1`                 |


### Java Cast and Castby
Indicates a type is used to cast an instance to a different type.

```java
class c1 {
 ...
}
class c2 extends c1 {
 ...
}
class c3 {
 c2 b = new c2();
 c1 a = (c1) b;
}

```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Cast                  |     `c3`                                |     `c1`                           |
|     Java Castby                |     `c1`                                |     `c3`                           |


### Java Contain and Containin
Indicates a class is in a package.

```java
package some_pack;

class some_class {
 ...
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Contain               |     `some_pack`                         |     `some_class`                   |
|     Java   Containin           |     `some_class`                        |     `some_pack`                    |


### Java Couple and Coupleby
Indicates a coupling link as counted in the OO coupling metrics. A link is created from a class to any external class (a class that is not in the extends/implements hierarchy) that is referenced.

```java
public class c1 {
 ...
}

public class c2 {
 cl obj;
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Couple                |     `c2`                                |     `c1`                           |
|     Java Coupleby              |     `c1`                                |     `c2`                           |


### Java Extend Couple and Extendby Coupleby
Indicates one class or interface extends another. This extends relation is used when the extended class is in a file that is part of the project. If the extended class was found in a classpath .jar file, the relation is Java Extend Couple External. If the Indicates class implicitly extends the java.lang.Object class, the relation is Java Extend Couple Implicit.

- [ ] **Todo:** add a short definition with and an example code and corresponding table for Java Extend Couple Implicit External and Java Extendby Coupleby Implicit External reference kind.
 

```java
// Example 1:
class class1 {
 ...
}
class class2 extends class1 {
 ...
}
// Example 2:
class some_class extends java.io.Writer {
 ...
}
// Example 3:
class some_class {
 ...
}
// Example 4:
//Todo
```

|     Reference kind   string                       |     Entity   performing references    |     Entity being   referenced    |
|---------------------------------------------------|---------------------------------------|----------------------------------|
|     Java Extend   Couple                          |     Ex 1: `class2`                      |     Ex 1: `class2`                 |
|     Java Extendby   Coupleby                      |     Ex 1: `class1`                      |     Ex 1: `class1`                 |
|     Java Extend   Couple External                 |     Ex 2: `some_class`                  |     Ex 2: `java.io.Writer`         |
|     Java Extendby   Coupleby External             |     Ex 2: `java.io.Writer`              |     Ex 2: `some_class`             |
|     Java Extend   Couple Implicit                 |     Ex 3: `some_class`                  |     Ex 3: `java.lang.Object`       |
|     Java Extendby   Coupleby Implicit             |     Ex 3: `java.lang.Object`            |     Ex 3: `some_class`             |
|     Java Extend   Couple Implicit External        |     Todo                              |     Todo                         |
|     Java Extendby   Coupleby Implicit External    |     Todo                              |     Todo                         |


### Java Implement Couple and Implementby Coupleby
Indicates a class implements an interface.

```java
interface some_interface {
 ...
}

class some_class implements some_interface {
 ...
}
```

|     Reference kind   string        |     Entity   performing references    |     Entity being   referenced    |
|------------------------------------|---------------------------------------|----------------------------------|
|     Java   Implement Couple        |     `some_class`                        |     `some_interface`               |
|     Java   Implementby Coupleby    |     `some_interface`                    |     `some_class`                   |


### Java Create and Createby
Indicates that an instance of a class is created (`new` operator) in a scope.

```java
class c1 {
 ...
}

class c2 {
 c1 a = new c1();
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Create                |     `c2`                                |     `c1`                           |
|     Java Createby              |     `c1`                                |     `c2`                           |


### Java Declare and Declarein
- [ ]  **Todo:** add a short definition with and an example code and corresponding table for this reference kind


### Java Define and Definein
Indicates that an entity is defined in a scope.

```java
//Example Define
class some_class {
 int some_var = 5;
}

//Example Define implicit
//Todo
```

- [ ] **Todo:** add a short definition with and an example code and corresponding table for Define Implicit and Definein Implicit reference kind.



|     Reference kind   string     |     Entity   performing references    |     Entity being   referenced    |
|---------------------------------|---------------------------------------|----------------------------------|
|     Java Define                 |     `some_class`                        |     `some_var`                     |
|     Java Definein               |     `some_var`                         |     `some_class`                   |
|     Java Define Implicit        |     Todo:                             |     Todo:                        |
|     Java Definein   Implicit    |     Todo:                             |     Todo:                        |


### Java DotRef and DotRefby

Indicates that an entity name was used to the left of a `“.”` in a qualified name.

```java
package some_pack;
class class1 {
 static int covid;
}

class class2 {
 void some_meth() {
  some_pack.class1.covid = 2021;
 }
}
```


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java DotRef                |     `some_meth`                         |     `some_pack`                    |
|     Java DotRefby              |     `some_pack`                         |     `some_meth`                    |


### Java Export and Exportby

- [ ] **Todo:** add a short definition with and an example code and corresponding table for this reference kind.


### Java Import and Importby

Java Import indicates a file imports an individual class. For example, the `some_file.java` file might contain:

```java
import pack1.some_class;
```

Java Import Demand indicates a file has an _on-demand_ import statement for a package or class. For example, the `some_file.java` file might contain:

```java
import pack1.*;
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Import                |     `some_file`                         |     `pack1.some_class`             |
|     Java Importby              |     `pack1.some_class`                  |     `some_file`                    |
|     Java Import   Demand       |     `some_file`                         |     `pack1`                        |
|     Java Importby   Demand     |     `pack1`                             |     `some_file`                    |


### Java Modify and Modifyby

Indicates that a variable’s value is modified or both read and set, as with the increment (`++`), decrement (`--`), and assignment/operator combinations (`*=`, `/=`, ...).

```java
class some_class {
 void some_meth() {
  int i = 5;
  i++;
 }
}
```


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Modify                |     `some_meth`                         |     `i`                            |
|     Java Modifyby              |     `i`                                 |     `some_meth`                    |


### Java ModuleUse and ModuleUseby

- [ ] **Todo:** add a short definition with and an example code and corresponding table for this reference kind.



### Java Override and Overrideby

Indicates that a method overrides a method from a parent class.

```java
class A {
 int some_meth() {
 ...
 }
}

class B extends A{
 int some_meth() {
 ...
 }
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Override              |     `B.some_meth`                       |     `A.some_meth`                  |
|     Java   Overrideby          |     `A.some_meth`                       |     `B.some_meth`                  |


### Java Provide and Provideby
- [ ] **Todo:** add a short definition with and an example code and corresponding table for this reference kind.



### Java Require and Requireby
- [ ] **Todo:** add a short definition with and an example code and corresponding table for this reference kind.



### Java Set and Setby

Java Set indicates that a variable is set by a separate statement.

```java
void some_meth() {
 int i;
 i = 5;
}
```

Java Set Init indicates that a variable is initialized in its declaration.

```java
void some_meth() {
 int i = 5;
}
```

- [ ] **Todo:** add a short definition with and an example code and corresponding table for Set Partial and Setby Partial reference kinds.


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Set                   |     `some_meth`                         |     `i`                            |
|     Java Setby                 |     `i`                                 |     `some_meth`                    |
|     Java Set Init              |     `some_meth`                         |     `i`                            |
|     Java Setby   Init          |     `i`                                 |     `some_meth`                    |
|     Set Partial                |     Todo:                             |     Todo:                        |
|     Setby Partial              |     Todo:                             |     Todo:                        |


### Java Typed and Typedby

Indicates the type of a variable or parameter.

```java
class class1 {
 ...
}

class class2 {
 class1 some_obj;
}
```

|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Typed                 |     `some_obj`                          |     `class1`                       |
|     Java Typedby               |     `class1`                            |     `some_obj`                    |



### Java Use and Useby

Indicates that a variable is used or read.


```java
class some_class {
 int some_var;
 void some_meth() {
  int local_var = some_var; // read of some_var
 }
}
```

- [ ] **Todo:** add a short definition with and an example code and corresponding table for Use Partial and Useby Partial reference kinds.
- [ ] **Todo:** add a short definition with and an example code and corresponding table for Use Ptr and Useby Ptr reference kinds.
- [ ] **Todo:** add a short definition with and an example code and corresponding table for Use Return and Useby Return reference kinds.


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Use                   |     `some_meth`                         |     `some_var`                     |
|     Java Useby                 |     `some_var`                          |     `some_meth`                    |
|     Java Use   Partial         |     Todo:                             |     Todo:                        |
|     Java Useby   Partial       |     Todo:                             |     Todo:                        |
|     Java Use Ptr               |     Todo:                             |     Todo:                        |
|     Java Useby   Partial       |     Todo:                             |     Todo:                        |
|     Java Use Return            |     Todo:                             |     Todo:                        |
|     Java Useby Return          |     Todo:                             |     Todo:                        |


###  Java Open and Openby
- [ ] **Todo:** add a short definition with and an example code and corresponding table for this reference kind.




### Java Throw and Throwby

Indicates that a method throws an exception.

```java
void some_meth() throws java.io.IOException {
 ...
}
```


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java Throw                   |     `some_meth`                         |     `java_io.IOException`          |
|     Java Throwby                 |     `java_io.IOException`               |     `some_meth`                   |





### Java End and Endby
Indicates the end of a class, interface, or method.

- [ ] **Todo:** Requires a better example (I cannot understand this kind in understand!)


|     Reference kind   string    |     Entity   performing references    |     Entity being   referenced    |
|--------------------------------|---------------------------------------|----------------------------------|
|     Java End                   |     `some_class`                        |     `some_class`                   |
|     Java Endby                 |     `some_class`                        |     `some_class`                   |



## References
[1] SciTools, “Understand,” 2020. https://www.scitools.com/ (accessed Sep. 11, 2020).