# Main driver and heartbeat code
from RAT import RegisterAliasTable
from cdb import CommonDataBus
from functional_units import *
from memory import *
from reading_input import input_parser
from time_table import TimingTable


# STAND ALONE SYSTEM PRINT & I/O FUNCTIONS
# These two just print for the moment but they let us pipe to a file etc
def sys_print(cycle, out_file=None):
    return

def sys_msg(message):
    print(message)
    return

class Processor:
    def __init__(self, config_file, verbose=False):

        # Parse input from the configuration file
        initr = input_parser(config_file)

        # Initialize components
        self.cycle_count = 0
        self.verbose = verbose
        self.tracker = TimingTable(self.cycle_count)
        self.instr_buf = InstructionBuffer(config_file)
        self.reg_alias_tbl = RegisterAliasTable(register_qty=16)
        self.reorder_buf = ROB(int(initr.ROBe), 16, 16) # Number of INT ARF and FP ARF currently hardcoded
        self.reorder_buf.register_arfs(initr.ARFI, initr.ARFF)

        # Register all functional units
        # TODO: Multiple FUs
        self.func_units = [LoadStoreQueue(256, initr.LSU["nrg"], initr.LSU["cim"], initr.LSU["cie"], self.reorder_buf, initr.CBDe, wl=1, config=initr.memory),
                           FPAdder(int(initr.FPA["nrg"]), int(initr.FPA["cie"]), int(initr.FPA["nfu"]), self.reorder_buf),
                           FPMultiplier(int(initr.FPM["nrg"]), int(initr.FPM["cie"]), int(initr.FPM["nfu"]), self.reorder_buf),
                           IntegerAdder(int(initr.intA["nrg"]), int(initr.intA["cie"]), int(initr.intA["nfu"]), self.reorder_buf) ]

        # Initialize BTB
        # TODO: Pass a list of all IntAdders, FPAdders, FPMultipliers
        self.brnch_trnsl_buf = BTB(self.reorder_buf, self.reg_alias_tbl,
                                   [self.func_units[3]], [self.func_units[1]],
                                   [self.func_units[2]])

        # Specify which units subscribe to the CDB
        cdb_subs = [self.brnch_trnsl_buf, self.reorder_buf]
        for opr in self.func_units:
            cdb_subs.append(opr)

        # Initialize the CDB
        self.CDB = CommonDataBus(self.func_units, cdb_subs)

        if verbose:
            sys_msg("[PROC] Processor fully init'd")

        # finish references to all components still needing it.
        # ==========REGISTER ALIAS TABLE============
        self.reg_alias_tbl.instr_queue = self.instr_buf
        self.reg_alias_tbl.rob = self.reorder_buf
        self.reg_alias_tbl.func_units["LSQ"] = self.func_units[0]
        self.reg_alias_tbl.func_units["FPA"] = self.func_units[1]
        self.reg_alias_tbl.func_units["FPM"] = self.func_units[2]
        self.reg_alias_tbl.func_units["INT"] = self.func_units[3]
        self.reg_alias_tbl.func_units["BTB"] = self.brnch_trnsl_buf

        # ========== REORDER BUFFER =============
        self.reorder_buf.RAT = self.reg_alias_tbl
        self.reorder_buf.LSQ = self.func_units[0]

    def run_code(self, bp=False):
        # run the heartbeat loop
        if self.verbose:
            sys_msg(self.instr_buf)

        while(1):
            # TIME TABLE PREP
            self.cycle_count += 1
            self.tracker.current_cyc = self.cycle_count

            # FETCH/DECODE/ISSUE
            self.reg_alias_tbl.tick(self.tracker)
            self.brnch_trnsl_buf.tick(self.tracker)

            # EXECUTE
            for unit in self.func_units:
                unit.tick(self.tracker)
                print(unit)

            # WRITE BACK
            self.CDB.tick(self.tracker)

            # COMMIT
            committed_instruction = self.reorder_buf.tick(self.tracker)
            print(self.reorder_buf)

            # Print tracker status
            print(self.tracker)

            #print system state
            sys_print(0)

            if bp is True:
                print("===============================================================================================================================")
                print("Cycle {} complete *************************************************************************************************************".format(self.cycle_count))
                print("===============================================================================================================================")
                input("Break Pointing... Press Enter to step\n\n")



if __name__ == "__main__":
    # decode command line args
    my_processor = Processor("test_files/test3b.txt", verbose=True)
    my_processor.run_code(bp=True)
