__author__ = "schelle"

import datetime
import os
import unittest

import numpy as np
import wflow.wflow_hbv as wf

"""

Run wflow_hbv for 30 steps and checks if the outcome is approx that of the reference run

"""


class MyTest(unittest.TestCase):
    def testapirun(self):
        startTime = 1
        stopTime = 30
        currentTime = 1

        # set runid, clonemap and casename. Also define the ini file
        runId = "unittest"
        configfile = "wflow_hbv.ini"
        wflow_cloneMap = "wflow_catchment.map"
        caseName = "wflow_hbv"
        starttime = starttime = datetime.datetime(1990, 1, 1)

        myModel = wf.WflowModel(wflow_cloneMap, caseName, runId, configfile)
        # initialise the framework
        dynModelFw = wf.wf_DynamicFramework(
            myModel, stopTime, firstTimestep=startTime, datetimestart=starttime
        )
        print(dynModelFw.DT)

        # Load model config from files and check directory structure
        dynModelFw.createRunId(NoOverWrite=False, level=wf.logging.DEBUG)
        # Run the initial part of the model (reads parameters and sets initial values)
        dynModelFw._runInitial()  # Runs initial part

        dynModelFw._runResume()  # gets the state variables
        sump = 0.0
        for ts in range(startTime, stopTime + 1):
            if ts < 10:
                dynModelFw.wf_setValues("P", 0.0)
            elif ts <= 15:
                dynModelFw.wf_setValues("P", 10.0)
            else:
                dynModelFw.wf_setValues("P", 0.0)

            dynModelFw.wf_setValues("PET", 2.0)
            dynModelFw.wf_setValues("TEMP", 10.0)
            dynModelFw._runDynamic(ts, ts)  # runs for all timesteps
        dynModelFw._runSuspend()  # saves the state variables
        dynModelFw._wf_shutdown()

        # nore read the csv results acn check of they match the first run
        # Sum should be approx c 4.569673676
        my_data = np.genfromtxt(
            os.path.join(caseName, runId, "watbal.csv"), delimiter=","
        )

        print("Checking  water budget ....")
        self.assertAlmostEqual(0.0011471913849163684, my_data[:, 2].sum(), places=4)

        my_data = np.genfromtxt(os.path.join(caseName, runId, "run.csv"), delimiter=",")
        print("Checking  discharge ....")
        self.assertAlmostEqual(1086.9438420613608, my_data[:, 2].mean(), places=4)


if __name__ == "__main__":
    unittest.main()
