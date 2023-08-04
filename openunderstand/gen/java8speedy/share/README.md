after install antlr4 version 4.9.1 c++ runtime use below command to create libMyGrammar.so
***************************************
g++ -shared -o libMyGrammar.so *.cpp -I /usr/local/include/antlr4-runtime/ -L /usr/local/lib/ -lantlr4-runtime -fPIC
***********************************
g++ -O3 -Wall -shared -std=c++11 -fPIC -I /home/y/Desktop/iust/OpenUnderstand/openunderstand/gen/java8speedy/antlr4-runtime/include/ -L /home/y/Desktop/iust/OpenUnderstand/openunderstand/gen/java8speedy/antlr4-runtime/lib/ $(python3 -m pybind11 --includes) sa_javalabeled_cpp_parser.cpp -o cpp_parser'python3-config --extension-suffix'

*************************
g++ -O3 -Wall -shared -std=c++11 -fPIC -I /home/y/Desktop/iust/OpenUnderstand/openunderstand/gen/java8speedy/antlr4-runtime/include/  $(python3 -m pybind11 --includes) sa_javalabeled_cpp_parser.cpp -o sa_kavalabeled_cpp_parser$(python3-config --extension-suffix)

