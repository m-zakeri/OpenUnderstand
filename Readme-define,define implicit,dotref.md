First using the site soft 98 32-bit file download it and start installing it? and after installing the crack file inside the installation place of the program.





[![1png.png](https://i.postimg.cc/L59wpcks/1png.png)](https://postimg.cc/MMLd0rFk)






Then we start using the tool and enter the program environment:

[![2.png](https://i.postimg.cc/mr4SJQyL/2.png)](https://postimg.cc/YvXgmLPZ)

In the application environment we need to create a project and specify the code environment by using the button specified in the image to specify the file for the code.

[![2.png](https://i.postimg.cc/pTpkJPBz/2.png)](https://postimg.cc/TLvrRMF3)

The steps for selecting the code environment are outlined as follows:

[![3.png](https://i.postimg.cc/k5kRL9mx/3.png)](https://postimg.cc/SXfKzBjs)

[![4.png](https://i.postimg.cc/qRNV6VhZ/4.png)](https://postimg.cc/k6PhLHyx)

[![5.png](https://i.postimg.cc/Gmfj3WRp/5.png)](https://postimg.cc/tsh62mY0)

[![6.png](https://i.postimg.cc/dtrBQH1R/6.png)](https://postimg.cc/D8fsBc1m)

[![7.png](https://i.postimg.cc/j5nfg2n6/7.png)](https://postimg.cc/BLsttqgt)



The code file is placed on the left side of the program. You can view the contents of the code file by selecting the file

[![8.png](https://i.postimg.cc/C1mF8T43/8.png)](https://postimg.cc/XGBSMPmL)



You can also see that the code is defined. In these graphic analysis images you can see the code

[![9.png](https://i.postimg.cc/L6dHZTk6/9.png)](https://postimg.cc/4n5CDpFr)

[![11.png](https://i.postimg.cc/xTLC17zP/11.png)](https://postimg.cc/GHhrMXzB)

[![2.png](https://i.postimg.cc/pTpkJPBz/2.png)](https://postimg.cc/TLvrRMF3)


Here are the images related to define entities that have been shown how they relate to other entities:

[![13.png](https://i.postimg.cc/Ls46v3sK/13.png)](https://postimg.cc/sM8rgSSw)



def process_file(file_address):
p = Project()
lap = ListenersAndParsers()
tree, parse_tree, file_ent =
lap.parser(file_address=file_address, p=p)
if tree is None and parse_tree is None and file_ent is None:
return
entity_generator = lap.entity_gen(file_address=file_address,
parse_tree=parse_tree)
listeners = [
lap.create_listener,
lap.type_listener,
lap.define_listener,
lap.declare_listener,
lap.override_listener,
lap.callby_listener,
lap.couple_listener,
lap.useby_listener,
lap.setby_listener,
lap.dotref_listener,
lap.throws_listener,
lap.extend_coupled_listener,
]
lap.modify_listener(
entity_generator=entity_generator,
parse_tree=parse_tree,
file_address=file_address,
p=p,
)
for listener in listeners:
listener(file_address=file_address, p=p,
file_ent=file_ent, tree=tree)




In this phase, we use the understand tool to analyze and compare code manually and with tools.
If we want to analyze this code ourselves، we can draw this table:

def process_file
import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
public class PasswordValidatorMain {
 public static void main(String[] args) {
 String input = "Your password input here"; 
 PasswordValidatorLexer lexer = new PasswordValidatorLexer(CharStreams.fromString(input));
 CommonTokenStream tokens = new CommonTokenStream(lexer);
 PasswordValidatorParser parser = new PasswordValidatorParser(tokens);
 ParseTree tree = parser.password();
 boolean isValid = tree.getText().equals(input);
 System.out.println(isValid);
 }
}

Number of Output:1
Number of input:1
Number of Objects:4
Number of Classes:5
Number of Variables:2


[![14.png](https://i.postimg.cc/HxbVJsZB/14.png)](https://postimg.cc/gXkYQdPZ)

Number of outputs:1
Number of inputs:2
Number of Objects:4
Numbers of Classes:5
Number of Variables:6

The following code can also be used as a command.

def get_all_variables(self, static=False): 
db = und.open(self.udb_path) _ 
candidates = [] 
if static: 
query = _db.ents("Static Variable") 
blacklist = () 
else: 
query = _db.ents("Variable") 
blacklist = ('static',) 
for ent in query: 
kind_name = ent.kindname().lower() 
if any(word in kind_name for word in blacklist): 
continue 
parent = ent.parent() 
if parent is None: 
continue 
if not parent.kind().check("class") or parent.kind().check("anonymous"): 
continue 
source_package = None 
long_name = ent.longname().split(".") 
if len(long_name) >= 3: 
source_package = '.'.join(long_name[:-2]) 
source_class, field_name = long_name[-2:] 
elif len(long_name) == 2: 
source_class, field_name = long_name 
else: 
continue 
 
db.close() _ 
return candidates


public class PasswordValidatorMain {
public static void main(String[] args) {
String input = "Your password input here";
PasswordValidatorLexer lexer = new
PasswordValidatorLexer(CharStreams.fromString(input));
CommonTokenStream tokens = new CommonTokenStream(lexer);
PasswordValidatorParser parser = new PasswordValidatorParser(tokens);
ParseTree tree = parser.password();
boolean isValid = tree.getText().equals(input);
System.out.println(isValid);
}
}

[![Results-of-understand.png](https://i.postimg.cc/W3qfgxg9/Results-of-understand.png)](https://postimg.cc/S2qrpTZ8)

[![Results-of-analyse.png](https://i.postimg.cc/7hM9N46N/Results-of-analyse.png)](https://postimg.cc/dZ3GqzG7)



Real Results

Number of outputs:1

Number of inputs:1

Number of objects:4

Number of classes:4

Number of Variables:2

The number of classes 1 is introduced. The reason is that it only chose the name of the current cals، but 
It should also count the names of the carriages in the code.

For example:

It must also specify the PasswordValidatorParser class in its calculations.

To solve this problem, the code can be changed in such a way that the understand tool has the ability to better recognize it.

You can change the code in this way:

public class PasswordValidatorMain {
public static void main(String[] args) {
String input = "Your password input here";
PasswordValidatorLexer lexer = new
PasswordValidatorLexer(CharStreams.fromString(input));
CommonTokenStream tokens = new CommonTokenStream(lexer);
PasswordValidatorParser parser = new PasswordValidatorParser(tokens);
ParseTree tree = parser.password();
boolean isValid = tree.getText().equals(input);
System.out.println(isValid);
}
private class PasswordValidatorLexer{
}
private class CommonTokenStream {
}
private class PasswordValidatorParser {
}

As a result، by making these changes، i.e. creating separate classes for each class that is used inside its code name can be 
Caused these classes to be identified by understand.

18 lines
1 file
4 classes 
1 function

[![final-graphs.png](https://i.postimg.cc/DzLxz1TD/final-graphs.png)](https://postimg.cc/qtBsbhgX)