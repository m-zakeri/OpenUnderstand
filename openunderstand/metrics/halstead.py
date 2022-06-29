import argparse
import os.path
import sys
from javalang import tokenizer
from tabulate import tabulate
import math

operand_list=\
[
  "Literal",
  "Integer",
  "DecimalInteger",
  "OctalInteger",
  "BinaryInteger",
  "HexInteger",
  "FloatingPoint",
  "DecimalFloatingPoint",
  "HexFloatingPoint",
  "Boolean",
  "Character",
  "String",
  "Null",
  "Annotation",
  "Identifier"
]
br_operands=["for", "while", "if", "case"]

OPERANDS = set(operand_list)
branchOperators = set(br_operands)


def calculate_cyclomatic(operators):
    """_summary_

    Args:
        operators (dictionary operator:count): dictionary of operators and their count

    Returns:
        int: cyclomatic complexity
    """
    return sum([operators[cyc_operator]
                for cyc_operator in branchOperators if cyc_operator in operators], start=1)

def get_operators_operands_count(tokens):
    """_summary_

    Args:
        tokens (javalang tokens): source code tokens parsed by javalang

    Returns:
        tuple:
            - dictionary(operand: count): dictionary of operands in the tokens and their count
            - dictionary(operator: count): dictionary of operators in the tokens and their count
    """

    operands = {}
    operators = {}

    for token in tokens:
        value = token.value

        if token.__class__.__name__ in OPERANDS:
            operands[value] = operands.get(value, 0) + 1
        else:
            operators[value] = operators.get(value, 0) + 1

    return operators, operands



def get_operators_operands_count(tokens):
    """_summary_

    Args:
        tokens (javalang tokens): source code tokens parsed by javalang

    Returns:
        tuple:
            - dictionary(operand: count): dictionary of operands in the tokens and their count
            - dictionary(operator: count): dictionary of operators in the tokens and their count
    """

    operands = {}
    operators = {}

    for token in tokens:
        value = token.value

        if token.__class__.__name__ in OPERANDS:
            operands[value] = operands.get(value, 0) + 1
        else:
            operators[value] = operators.get(value, 0) + 1

    return operators, operands

def calculate_halstead(n1, N1, n2, N2):
    """_summary_

    Args:
        n1 (int): Number of Distinct Operators
        N1 (int): Number of Operators
        n2 (int): Number of Distinct Operands
        N2 (int): Number of Operands

    Returns:
        dictionary(label: value): halstead metrics
    """
    n = n1 + n2
    N = N1 + N2

    estimated_length = n1 * math.log2(n1) + n2 * math.log2(n2)
    purity_ratio = estimated_length / N
    volume = estimated_length * math.log2(n)

    difficulty = (n1 / 2) * (N2 / n2)
    effort = difficulty * volume
    time = effort / 18
    bugs = volume / 3000

    return {
        "Program vocabulary": n,
        "Program length": N,
        "Estimated length": estimated_length,
        "Purity ratio": purity_ratio,
        "Volume": volume,
        "Difficulty": difficulty,
        "Program effort": effort,
        "Time required to program": time,
        "Number of delivered bugs": bugs,
    }

def print_table(data, headers=[], title=None):
    """print dictionary as a two column table

    Args:
        data (dictionary): dictionary to print
        headers (list): table headers
        title (str): table title
    """
    if title:
        print("\n", title, "\n")
    print(tabulate(data.items(), headers=headers, tablefmt='fancy_grid'))


parser = argparse.ArgumentParser(
    description='outputs Halstead metrics and cyclomatic complexity for a given java file')
parser.add_argument('java_file', metavar='JAVA_FILE', type=str,
                    help='path to the java file')

args = parser.parse_args()

if not os.path.isfile(args.java_file):
    print('Invalid Java File')
    sys.exit()

with open(args.java_file, 'r', encoding='utf-8') as file:
    code = file.read()
    tokens = list(tokenizer.tokenize(code))

    operators, operands = get_operators_operands_count(tokens)

    print_table(
        {'Cyclomatic complexity': calculate_cyclomatic(operators)})

    n1 = len(operators)
    n2 = len(operands)
    N1 = sum(operators.values())
    N2 = sum(operands.values())

    print_table({"Number of Distinct Operators": n1,
                 "Number of Distinct Operands": n2,
                 "Number of Operators": N1,
                 "Number of Operands": N2,
                 **calculate_halstead(
                     n1, N1, n2, N2)}, ['Metric', 'Value'], 'Halstead Metrics:')

    print_table(operators, ['Operator', 'Count'], 'Operators:')

    print_table(operands, ['Operand', 'Count'], 'Operands:')


