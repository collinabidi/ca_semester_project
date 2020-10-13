# open text_file
readInput = open(r"C:\Users\HP\Desktop\CA\CA_project\input.txt","r")
f = readInput.readlines()
print(f)

row = 0  # start counting at 0 because the first one is a header
for line in f:
    # splits each line in tabs to pull out values from table
    v = line.strip().split('\t')  # outputs each line in text file

    # create dictionary to access data
    if len(v) > 1:  # checking if line has data in it--- the \t split looks for
        # table values
        data = v[1::]  # organizes data
        nrg = data[0]  # number of registers
        cie = data[1]  # cycles in ex.
        cim = data[2]  # cycles in memory

        # create dictionary for each reservation station
        if row == 1:
            intA = {}  # create empty dictionary called interger adder
            for number in ["nrg", "cie", "cim"]:
                intA[number] = eval(number)

            print(intA)

        elif row == 2:
            FPA = {}  # create empty dictionary floating point adder
            for number in ["nrg", "cie", "cim"]:
                FPA[number] = eval(number)
            print(FPA)

        elif row == 3:
            FPM = {}  # Floating point multiplier
            for number in ["nrg", "cie", "cim"]:
                FPM[number] = eval(number)

            print(FPM)
        row +=1  # read next line in table
