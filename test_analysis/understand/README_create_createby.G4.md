# openunderstand

## Overview
 
The objective of my project is to implement a software to mimic the functionality of Create& Createby queries available in SciTools Understand software analysis toolbox. I have utilized ANTLRv4 and SQLite database to store the outcomes. For further information regarding Understand, database schemas, and terminology, you can refer to this [link](https://m-zakeri.github.io/OpenUnderstand/).

## `What changes did I make?`
- I added new conditions to the Create and Createby file (fix the Create_Createby_g9.py) to be closer to the output of understand using Hierarchy and small test examples  like caclculator_app with checking them through the JavaParserLabeled.g4 file.  

## output

these are my output in Windows and Linux:
- these show us line and longname 
- before changes in windows:
![00](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/00.png?raw=true)

- after changes in windows:
![01](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/01.png?raw=true)
 
- before changes in linux:
![02](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/photo_5917882626973221723_x.jpg?raw=true)

- the numbers show the line of the code that create ref appears and end of the output tells that Which line is seen only in openunderstand and which only in understand

- after (linux):
![03](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/photo_5917882626973221722_x.jpg?raw=true)


- and these are kind and content in windows :

![04](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/02.png?raw=true)
![05](https://github.com/zahrahabibolah/OpenUnderstand/blob/dev/test_analysis/03.png?raw=true)
## read the output
- First line numbers indicate all "create" references in openundrestand and undrestand
- The output structure shows:
1. first line, It shows the name of the file we are in
2. Shows the line in which Create appears
3. It shows the long name of the Create reference

- for example understand_counter: 205 => it shows us understand has diagnosed 205 ent in  'Create' refs in JSON file 
- openund_counter: 196 => it shows us openunderstand has diagnosed 196  ent  in 'Create' refs in JSON file 
- File: C:\Users\black\OpenUnderstand\benchmark\JSON\src\main\java\org\json\JSONStringer.java => this shows us which file we are in
- openund: {64: 'StringWriter'} => in openunderstand we have 'create' ref in line 64 in specified file above and its has 'StringWriter' as it long name 
- understand: {64: 'java.io.StringWriter'} => in understand we have 'create' ref in line 64 in specified file above and its has 'java.io.StringWriter' as it long name 


## Result

- With these changes, in addition to bringing the numbers openunderstand and understand closer together,also bring them closer in terms of the lines,long name,name,scope etc.