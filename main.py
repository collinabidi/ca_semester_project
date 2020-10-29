import sys
import os
from functional_units import *

def make_instruction(input_list):
    """ Takes an input line split by spaces and returns an Instruction object
    Args:
        input_list (list): a formatted list of strings that contain instruction fields
    """
    return Instruction(input_list)


# This only runs if we call `python3 main.py` from the command line
if __name__ == "__main__":
    print("Executing main script")

    # Initialize intstruction buffer from input text file
    