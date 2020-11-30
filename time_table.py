"""
  Timing Table for viewing instruction progression throughout the program
  - Timing Table hooks into the tick function through a common .update() interface
  - Class manages and tracks instructions throughout their time in the processor
  - Class manages loops by tracking transitions for each instruction
"""


class TimingTable:
    def __init__(self, initial_clock):
        self.tracked_instructions = []    #every cycle we've ever seen.
        self.current_cyc = initial_clock  #processor updates this timely.

    def update(self, tag, data):
        """ Update needs the tag ("issue" || "execute" || "memory" || "wrtback" || "commit")
            and the data (Instruction || {"pc":INT})
        """
        print("Tracker received data: {}".format(data))
        if tag == "issue":
            # if instruction is being issued, its new - so save it straight away
            #  'data' should be the
            self.tracked_instructions.append({"instr":data, "state":"issue", \
                                             "issue":self.current_cyc, \
                                             "execute":"--", "memory":"--", \
                                             "wrtback":"--", "commit":"--"})
        elif tag == "branch-resolve":
            # not needed currently
            print("branch correctly predicted.")
        elif tag == "branch-rewind":
            # not needed currently
            print("branch not correctly predicted, remove some tracked instructions")
        else:
            # find the 1st instance of the instruction w/ both right PC and matching
            #  stage transition (We expect these to be dictionaries with a "pc" entry)
            for line in self.tracked_instructions:
                if line["instr"].pc == data["pc"]:
                    if self.__verify_tx__(line["instr"].op, line["state"], tag):
                        line["state"] = tag
                        line[tag] = self.current_cyc
                        return
            print("Odd... not tracking this instruction:{} {}".format(tag, data))


    def __str__(self):
        output_str = "Issue | Exe | Memory | WB | Commit | Instruction\n"
        output_str +="-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
        for i in self.tracked_instructions:
            output_str += str(i["issue"]) +"\t"+ str(i["execute"]) +"\t"+ \
                          str(i["memory"]) + "\t" + str(i["wrtback"]) + "\t" + \
                          str(str(i["commit"]) + "\t" + "{}\n".format(i["instr"]))
        output_str +="\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
        return output_str


    def file_str(self):
        output_str = "Iss | Exe | Mem | WB | Cmit | Instruction\n"
        output_str +="-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
        for i in self.tracked_instructions:
            output_str += " "+ str(i["issue"]) +" | "+ str(i["execute"]) +" | "+ \
                          str(i["memory"]) + " | " + str(i["wrtback"]) + " | " + \
                          str(str(i["commit"]) + " | " + "{}\n".format(i["instr"]))
        output_str +="\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n"
        return output_str



    def __verify_tx__(self, op, state_c, state_n):
        # looks at tx's for each instruction & decides if this is correct tx in pipeline
        tx_order = None
        if op =="Sd":
            tx_order = ["issue", "execute", "commit", "memory"]
        elif op == "Ld":
            tx_order = ["issue", "execute", "memory", "wrtback", "commit"]
        else:
            tx_order = ["issue", "execute", "wrtback", "commit"]

        idex_state_c = tx_order.index(state_c)
        idex_state_n = tx_order.index(state_n)

        # if the new and current indexes are directly next to each other in the
        #   transition order, then the transition is correct, otherwise it couldn't
        #   be this instruction
        return (idex_state_n - idex_state_c) == 1
