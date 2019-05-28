__author__ = "schelle"

import unittest
import logging
import sys

sys.path = ["../"] + sys.path
import wflow.wflow_bmi as bmi
import time
import os

"""
Simple test for wflow bmi framework
"""


class MyTest(unittest.TestCase):
    def testbmifuncs(self):

        bmiobj = bmi.wflowbmi_csdms()
        bmiobj.initialize("wflow_sceleton/wflow_sceleton.ini", loglevel=logging.ERROR)

        print("-------------- Grid origin: ")
        gorigin = bmiobj.get_grid_origin("Altitude")
        # print(gorigin)
        self.assertAlmostEqual(
            sum([45.875934703275561, 5.2088299822062254]), sum(gorigin), places=4
        )

        print("-------------- Grid shape: ")
        print((bmiobj.get_grid_shape("Altitude")))
        self.assertAlmostEqual(
            sum([169, 187]), sum(bmiobj.get_grid_shape("Altitude")), places=4
        )

        print("-------------- Grid spacing: ")
        print((bmiobj.get_grid_spacing("Altitude")))
        self.assertAlmostEqual(
            sum([0.036666665, 0.036666665]),
            sum(bmiobj.get_grid_spacing("Altitude")),
            places=4,
        )

        print("-------------- Grid X: ")
        print((bmiobj.get_grid_x("Altitude")))
        self.assertAlmostEqual(
            5.22716331, bmiobj.get_grid_x("Altitude")[0, 0], places=4
        )

        print("-------------- Grid Y: ")
        print((bmiobj.get_grid_y("Altitude")))
        self.assertAlmostEqual(
            45.89426804, bmiobj.get_grid_y("Altitude")[0, 0], places=4
        )

        print("-------------- Grid Z: ")
        print((bmiobj.get_grid_z("Altitude")))
        self.assertAlmostEqual(
            218.44944763, bmiobj.get_grid_z("Altitude")[0, 0], places=4
        )

        print("-------------- Name: ")
        print((bmiobj.get_component_name()))
        self.assertEqual("wflow_sceleton", bmiobj.get_component_name())

        print("-------------- Input var names: ")
        print((bmiobj.get_input_var_names()))

        print("-------------- UNit of var TEMP: ")
        print((bmiobj.get_var_units("TEMP")))

        print("-------------- UNit of var P: ")
        print((bmiobj.get_var_units("P")))

        print("-------------- Output var names: ")
        print((bmiobj.get_output_var_names()))

        print("-------------- Time units: ")
        print((bmiobj.get_time_units()))

        print("-------------- Time step: ")
        print((bmiobj.get_time_step()))

        print("-------------- Start time: ")
        print((bmiobj.get_start_time()))

        print("-------------- Current time: ")
        print((bmiobj.get_current_time()))
        a = bmiobj.get_current_time()
        # print(time.localtime(bmiobj.get_current_time()))

        os.environ["TZ"] = "Europe/London"

        print("-------------- Current time (set to london): ")
        print((bmiobj.get_current_time()))
        b = bmiobj.get_current_time()

        self.assertAlmostEqual(a, b)

        print ("-------------- update: ")
        bmiobj.update()

        print("-------------- Current time after update: ")
        print((bmiobj.get_current_time()))
        print((time.localtime(bmiobj.get_current_time())))

        print("-------------- Start time: ")
        print((bmiobj.get_start_time()))
        print((time.localtime(bmiobj.get_start_time())))

        print("-------------- End time: ")
        print((bmiobj.get_end_time()))
        print((time.localtime(bmiobj.get_end_time())))

        print("-------------- Grid type: ")
        print((bmiobj.get_grid_type("Altitude")))

        print("-------------- Var type: ")
        print((bmiobj.get_var_type("Altitude")))

        print("-------------- Var rank: ")
        print((bmiobj.get_var_rank("Altitude")))

        print("-------------- Var size: ")
        print((bmiobj.get_var_size("Altitude")))

        print("-------------- Var nbytes: ")
        print((bmiobj.get_var_nbytes("Altitude")))

        print("-------------- Getvalue: ")
        print((bmiobj.get_value("Altitude")))

        print("-------------- Getvalue: ")
        print((bmiobj.get_value("timestepsecs")))

        print ("-------------- get_attribute_names: ")
        names = bmiobj.get_attribute_names()
        print(names)

        print("-------------- get_attribute_value: ")
        print(names[0])
        print((bmiobj.get_attribute_value(names[0])))

        print("-------------- set_attribute_value: ")
        print(names[0])
        bmiobj.set_attribute_value(names[0], "SET By TEST")
        print((bmiobj.get_attribute_value(names[0])))
        self.assertEqual("SET By TEST", bmiobj.get_attribute_value(names[0]))

        print ("-------------- set_start_time: ")
        bmiobj.set_start_time(0)
        print((bmiobj.get_attribute_value("run:starttime")))

        print ("-------------- save the state:")
        bmiobj.save_state(".")
        self.assertTrue(os.path.exists("TSoil.map"))
        os.remove("TSoil.map")

        bmiobj.finalize()

    def testbmirun(self):
        bmiobj = bmi.wflowbmi_csdms()
        bmiobj.initialize("wflow_sceleton/wflow_sceleton.ini", loglevel=logging.DEBUG)
        bmiobj.set_attribute_value("run:runlengthdetermination", "intervals")
        print((bmiobj.get_var_type("IF")))
        et = bmiobj.get_end_time()
        st = bmiobj.get_start_time()
        ts = 86400
        # Do timesteps and chak

        bmiobj.update_until(et)
        bmiobj.get_current_time()
        bmiobj.finalize()
        print(et - bmiobj.get_current_time())
        self.assertEqual(et, bmiobj.get_current_time())

    def testbmirun_l(self):
        print("Run with update(-1)")
        bmiobj = bmi.wflowbmi_light()
        bmiobj.initialize("wflow_sceleton/wflow_sceleton.ini", loglevel=logging.ERROR)
        print(bmiobj.get_current_time())
        et = bmiobj.get_end_time()
        st = bmiobj.get_start_time()
        print(bmiobj.get_current_time())
        bmiobj.update(et - st)
        print(bmiobj.get_current_time())
        bmiobj.finalize()
        print(bmiobj.get_current_time())
        print(et)
        print(st)
        self.assertEqual(et, bmiobj.get_current_time())

    def testbmirun_space_in_name(self):
        print("Run with update(-1)")
        bmiobj = bmi.wflowbmi_light()
        bmiobj.initialize("wflow_sceleton/wflow_sceleton.ini", loglevel=logging.ERROR)
        et = bmiobj.get_end_time()
        st = bmiobj.get_start_time()
        bmiobj.update(et - st)
        bmiobj.finalize()
        self.assertEqual(et, bmiobj.get_current_time())

    def testbmirunnetcdf(self):
        bmiobj = bmi.wflowbmi_csdms()
        bmiobj.initialize_config("wflow_sbm/wflow_sbm_nc.ini", loglevel=logging.ERROR)
        bmiobj.set_start_time(1399597200)
        bmiobj.set_end_time(1399597200 + (4 * 3600))

        st = bmiobj.get_start_time()
        ett = bmiobj.get_end_time()
        ts = bmiobj.get_time_step()

        bmiobj.initialize_model()
        tt = bmiobj.get_value("timestepsecs")
        curtime = st
        cnt = 0
        lastcurtime = bmiobj.get_current_time()
        while curtime < ett:
            avar = bmiobj.get_value("PET")
            bmiobj.set_value("PET", avar + 10.0)
            cnt = cnt + 1
            bmiobj.update_until(curtime + ts)
            print((curtime + ts) / ts)
            curtime = bmiobj.get_current_time()
            print(bmiobj.get_current_time() - lastcurtime)
            lastcurtime = bmiobj.get_current_time()

        bmiobj.finalize()
        self.assertEqual(ett, bmiobj.get_current_time())


if __name__ == "__main__":
    unittest.main()
