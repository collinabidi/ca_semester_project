## Computer Architecture Project for Fall 2020: Tomasulo's Algorithm

Collin Abidi, Clara Ferreira, Brendan Luksik

A Pythonic implementation of Tomasulo's algorithm for Computer Architecture.
System Requirements: Python 3.8.5 (any version of Python 3 should work though)
Downloading
Navigate to https://github.com/collinabidi/ca_semester_project
Clone the repository with
git clone https://github.com/collinabidi/ca_semester_project
Main File Usage
The main file to be used is called processor.py . You can feed an input file by calling

python3 processor.py --input input.txt --bp --verbose   
input.txt is your input text file.
--bp  Makes processor components verbose and breakpoints after every cycle (optional)
--verbose  Enables verbose printing during execution
Input / Output
Test cases can be run from the input specification given in the instructions, but Please note: Instructions must begin after line 11 in any input text file.
Output is piped to the same directory as the input is sourced from as <input_filename>_output.txt
