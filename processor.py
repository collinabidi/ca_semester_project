# Main driver and heartbeat code
from RAT import RegisterAliasTable
from cdb import CommonDataBus
from functional_units import *
from memory import *
from reading_input import input_parser


# STAND ALONE SYSTEM PRINT & I/O FUNCTIONS
# These two just print for the moment but they let us pipe to a file etc
def sys_print(cycle, out_file=None):
    return

def sys_msg(message):
    print(message)
    return



class Processor:
    def __init__(self, config_file, verbose=False):

        initr = input_parser(config_file)
        self.cycle_count = 0
        self.verbose = verbose
        # initialize all components here
        self.instr_buf = InstructionBuffer(config_file)
        self.reg_alias_tbl = RegisterAliasTable()
        self.reorder_buf = ROB(int(initr.ROBe), 16, 16) # HARD CODE? Are num registers param'd?

        self.func_units = [LoadStoreQueue(256, initr.LSU["nrg"], initr.LSU["cim"], self.reorder_buf, initr.CBDe, config=initr.memory),
                           FPAdder(int(initr.FPA["nrg"]), int(initr.FPA["cie"]), int(initr.FPA["nfu"]), self.reorder_buf),
                           FPMultiplier(int(initr.FPM["nrg"]), int(initr.FPM["cie"]), int(initr.FPM["nfu"]), self.reorder_buf),
                           IntegerAdder(int(initr.intA["nrg"]), int(initr.intA["cie"]), int(initr.intA["nfu"]), self.reorder_buf) ]

        self.brnch_trnsl_buf = BTB(self.reorder_buf, self.reg_alias_tbl,
                                   self.func_units[3], self.func_units[1],
                                   self.func_units[2])

        cdb_subs = [self.brnch_trnsl_buf, self.reorder_buf]
        for opr in self.func_units:
            cdb_subs.append(opr)

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
            # fetch/deocde/issue
            self.cycle_count += 1
            self.reg_alias_tbl.tick()
            self.brnch_trnsl_buf.tick()

            print(self.reg_alias_tbl)
            print(self.brnch_trnsl_buf)

            # issue instruction to proper reservation station


            # execute
            for unit in self.func_units:
                unit.tick()
                print(unit)


            # writeback
            self.CDB.tick()
            """ If the BTB mispredicted, the rewind can be triggered here internally
                cdb->btb.read_cdb()->btb.component_ref.rewind()
            """
            # commit
            self.reorder_buf.tick()

            #print system state
            sys_print(0)

            if bp is True:
                print("Cycle: " + str(self.cycle_count))
                input("Break Pointing... Press Enter to step")



if __name__ == "__main__":
    # decode command line args
    my_processor = Processor("test_files/test1a.txt", verbose=True)
    my_processor.run_code(bp=True)
