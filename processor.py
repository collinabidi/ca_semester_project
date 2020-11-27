# Main driver and heartbeat code
import sys
from RAT import RegisterAliasTable
from cdb import CommonDataBus
from functional_units import *
from memory import *
from reading_input import input_parser
from time_table import TimingTable



class Processor:
    def __init__(self, config_file, verbose=False, pipe_cd=10):

        # Parse input from the configuration file
        self.output_trgt = config_file
        initr = input_parser(config_file)

        # meta data
        self.cycle_count = 0
        self.end_cycle = 0
        self.pipe_cd = pipe_cd
        self.verbose = verbose

        # Initialize components
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

        if verbose:
            print("[PROC] Processor fully init'd")


    def run_code(self, bp=False):
        # run the heartbeat loop
        if self.verbose:
            print(self.instr_buf)

        while(self.__continue__(self.pipe_cd)):
            # TIME TABLE PREP
            self.cycle_count += 1
            self.tracker.current_cyc = self.cycle_count

            # FETCH/DECODE/ISSUE
            self.reg_alias_tbl.tick(self.tracker)
            self.brnch_trnsl_buf.tick(self.tracker)
            # EXECUTE
            for unit in self.func_units:
                unit.tick(self.tracker)
                #if verbose:
            print(self.func_units[3])
            if self.verbose:
                print(self.func_units[0])
            # WRITE BACK
            self.CDB.tick(self.tracker)
            print(self.CDB)
            # COMMIT
            committed_instruction = self.reorder_buf.tick(self.tracker)
            if self.verbose:
                print(self.reorder_buf)

            # Print tracker status
            if self.verbose:
                print(self.tracker)

            if bp is True:
                print("===============================================================================================================================")
                print("Cycle {} complete *************************************************************************************************************".format(self.cycle_count))
                print("===============================================================================================================================")
                input("Break Pointing... Press Enter to step\n\n")

        if self.verbose:
            print("Exiting...")
        output_str = self.tracker.file_str()
        output_str += "\n\n===Register Values===\n"
        output_str += str(self.reorder_buf.int_arf)+"\n"+str(self.reorder_buf.fp_arf)
        output_str += str(self.reg_alias_tbl.func_units["LSQ"].mem_unit)
        file_nm = self.output_trgt.split(".")

        with open((file_nm[0]+"_output.txt"), "w") as out_file:
            out_file.write("Processor Execution Output:\n")
            out_file.write(output_str)
            out_file.close()


    def __continue__(self, flush_cycs):
        trigger = self.reorder_buf.rob_empty and self.instr_buf.out_of_bounds_hit
        flush = False
        if self.end_cycle == 0 and trigger:
            self.end_cycle = self.cycle_count
        else:
            flush = self.cycle_count >= (self.end_cycle + flush_cycs)
        #print("[CONTINUE] rob:" + str(self.reorder_buf.rob_empty) + " i_buf:"+str(self.instr_buf.out_of_bounds_hit)+ " end:"+str(self.end_cycle)+ "cyc:"+str(self.cycle_count) + " flush:"+ str(flush))
        return not (trigger and flush)



if __name__ == "__main__":
    # decode command line args
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print("Usage: python processor.py --input <filename> [--bp] [--clr=#]")
        print("--input <filename> is required, --bp/--clr are optional")
        print("--bp enables cycle breakpointing")
        print("--clr=# sets the amount of flush time ")
    else:
        debug = False
        pipe_cd = 10
        if len(sys.argv) > 3:
            for i in range(3,len(sys.argv)):
                if sys.argv[i] == "--bp":
                    debug = True
                elif "--clr" in sys.argv[i]:
                    clr_vals = sys.argv[i].split("=")
                    pipe_cd = int(clr_vals[1])

        #init and run
        my_processor = Processor(sys.argv[2], verbose=debug, pipe_cd=pipe_cd)
        my_processor.run_code(bp=debug)
