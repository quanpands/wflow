#!/usr/bin/python

"""
Definition of the wflow_mswat model.
-------------------------------------


Usage:
wflow_mswat  -C case -R Runid -c inifile -T last timestep [-S Firststimestep]

    -C: set the name  of the case (directory) to run
    
    -R: set the name runId within the current case
    
    -c name of the config file (in the case directory)
    
$Author:  $
$Id:  $
$Rev: 898 $
"""

import os
import os.path
import getopt

from wflow.wf_DynamicFramework import *
from wflow.wflow_adapt import *


def usage(*args):
    sys.stdout = sys.stderr
    for msg in args:
        print(msg)
    print(__doc__)
    sys.exit(0)


class WflowModel(DynamicModel):
    """
  The user defined model class. This is your work!
  """

    def __init__(self, cloneMap, Dir, RunDir, configfile):
        """
      *Required*

      The init function **must** contain what is shown below. Other functionality
      may be added by you if needed.

      """
        DynamicModel.__init__(self)
        setclone(Dir + "/staticmaps/" + cloneMap)
        self.runId = RunDir
        self.caseName = Dir
        self.Dir = Dir
        self.configfile = configfile

    def parameters(self):
        """
      List all the parameters (both static and forcing here). Use the wf_updateparameters()
      function to update them in the initial section (static) and the dynamic section for
      dynamic parameters and forcing date.

      Possible parameter types are:

      + staticmap: Read at startup from map
      + statictbl: Read at startup from tbl, fallback to map (need Landuse, Soil and TopoId (subcatch) maps!
      + timeseries: read map for each timestep
      + monthlyclim: read a map corresponding to the current month (12 maps in total)
      + dailyclim: read a map corresponding to the current day of the year
      + hourlyclim: read a map corresponding to the current hour of the day (24 in total)


      :return: List of modelparameters
      """
        modelparameters = []

        # Static map model parameters
        modelparameters.append(
            self.ParamType(
                name="Altitude",
                stack="staticmaps/wflow_dem.map",
                type="staticmap",
                default=0.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="LandUse",
                stack="staticmaps/wflow_landuse.map",
                type="staticmap",
                default=1,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="Soil",
                stack="staticmaps/wflow_soil.map",
                type="staticmap",
                default=1,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="TopoId",
                stack="staticmaps/wflow_subcatch.map",
                type="staticmap",
                default=1,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="TopoLdd",
                stack="staticmaps/wflow_ldd.map",
                type="staticmap",
                default=1,
                verbose=False,
                lookupmaps=[],
            )
        )

        # These should be linked to soil type
        modelparameters.append(
            self.ParamType(
                name="percent_clay",
                stack="intbl/percent_clay.tbl",
                type="statictbl",
                default=0.1,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="percent_silt",
                stack="intbl/percent_silt.tbl",
                type="statictbl",
                default=0.1,
                verbose=False,
                lookupmaps=[],
            )
        )
        # Impervious area fraction == Pathfrac from wfow_sbm
        modelparameters.append(
            self.ParamType(
                name="PathFrac",
                stack="intbl/PathFrac.tbl",
                type="statictbl",
                default=0.1,
                verbose=False,
                lookupmaps=[],
            )
        )
        #      modelparameters.append(self.ParamType(name="idplt",stack="intbl/idplt.tbl",type="statictbl",default=0.1, verbose=False,lookupmaps=[]))
        # These should be linked to LAI and/or land use
        modelparameters.append(
            self.ParamType(
                name="canopy_height",
                stack="intbl/canopy_height.tbl",
                type="statictbl",
                default=0.1,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="LAI",
                stack="intbl/LAI.tbl",
                type="statictbl",
                default=3.0,
                verbose=False,
                lookupmaps=[],
            )
        )

        # Sediment delivery ratio
        modelparameters.append(
            self.ParamType(
                name="dratio",
                stack="intbl/dratio.tbl",
                type="statictbl",
                default=1.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="rill_mult",
                stack="intbl/rill_mult.tbl",
                type="statictbl",
                default=1.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="usle_k",
                stack="intbl/usle_k.tbl",
                type="statictbl",
                default=1.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="c_factor",
                stack="intbl/c_factor.tbl",
                type="statictbl",
                default=1.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="eros_expo",
                stack="intbl/eros_expo.tbl",
                type="statictbl",
                default=1.5,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="eros_spl",
                stack="intbl/eros_spl.tbl",
                type="statictbl",
                default=2,
                verbose=False,
                lookupmaps=[],
            )
        )
        #      modelparameters.append(self.ParamType(name="idplt_cvm", stack="intbl/idplt_cvm.tbl", type="statictbl", default=1.0, verbose=False,lookupmaps=[]))
        #      modelparameters.append(self.ParamType(name="soil_cov", stack="intbl/soil_cov.tbl", type="statictbl", default=1.0, verbose=False,lookupmaps=[]))

        # Climatology
        modelparameters.append(
            self.ParamType(
                name="LAI",
                stack="inmaps/climatology/LAI",
                type="monthlyclim",
                default=0.9,
                verbose=False,
                lookupmaps=[],
            )
        )

        modelparameters.append(
            self.ParamType(
                name="CanopyGapFraction",
                stack="intbl/CanopyGapFraction.tbl",
                type="statictbl",
                default=0.1,
                verbose=False,
                lookupmaps=[],
            )
        )

        # Meteo and other forcing
        modelparameters.append(
            self.ParamType(
                name="Precipitation",
                stack="inmaps/P",
                type="timeseries",
                default=0.0,
                verbose=True,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="RunDepth",
                stack=self.runId + "/outmaps/exs",
                type="timeseries",
                default=1.0,
                verbose=True,
                lookupmaps=[],
            )
        )

        return modelparameters

    def stateVariables(self):
        """
      *Required*

      Returns a list of state variables that are essential to the model.
      This list is essential for the resume and suspend functions to work.

      This function is specific for each model and **must** be present. This is
      where you specify the state variables of you model. If your model is stateless
      this function must return and empty array (states = [])

      In the simple example here the TSoil variable is a state
      for the model.

      :var TSoil: Temperature of the soil [oC]
      """
        states = []

        return states

    def supplyCurrentTime(self):
        """
      *Optional*

      Supplies the current time in seconds after the start of the run
      This function is optional. If it is not set the framework assumes
      the model runs with daily timesteps.

      Output:

          - time in seconds since the start of the model run

      """

        return self.currentTimeStep() * int(
            configget(self.config, "model", "timestepsecs", "86400")
        )

    def suspend(self):
        """
      *Required*
      
      Suspends the model to disk. All variables needed to restart the model
      are saved to disk as pcraster maps. Use resume() to re-read them
      
      This function is required. 
      
    """

        self.logger.info("Saving initial conditions...")
        #: It is advised to use the wf_suspend() function
        #: here which will suspend the variables that are given by stateVariables
        #: function.
        self.wf_suspend(self.Dir + "/outstate/")

    def initial(self):

        """
    *Required*
    
    Initial part of the model, executed only once. It reads all static model
    information (parameters) and sets-up the variables used in modelling.
    
    This function is required. The contents is free. However, in order to
    easily connect to other models it is advised to adhere to the directory
    structure used in the other models.
    
    """
        #: pcraster option to calculate with units or cells. Not really an issue
        #: in this model but always good to keep in mind.
        setglobaloption("unittrue")

        # time and space specs
        self.timestepsecs = int(configget(self.config, "run", "timestepsecs", "86400"))
        sizeinmetres = int(configget(self.config, "layout", "sizeinmetres", "0"))
        self.basetimestep = 86400
        # Reads all parameter from disk
        self.wf_updateparameters()
        self.ZeroMap = 0.0 * self.Altitude
        self.SedStore = self.ZeroMap

        # Calculate cell area
        self.xl, self.yl, self.reallength = pcrut.detRealCellLength(
            self.ZeroMap, sizeinmetres
        )
        self.hru_km = (self.reallength / 1000.0) ** 2

        # Calulate slope taking into account that x,y may be in lat,lon
        self.Slope = slope(self.Altitude)
        self.Slope = max(0.00001, self.Slope * celllength() / self.reallength)

        # Calculate detachability of the soil (k)
        self.percent_sand = 100 - (self.percent_clay + self.percent_silt)
        self.erod_k = ifthenelse(
            pcrand(
                self.percent_clay >= 40.0,
                pcrand(self.percent_sand >= 20.0, self.percent_sand <= 45.0),
            ),
            2.0,
            ifthenelse(
                pcrand(
                    self.percent_clay >= 27.0,
                    pcrand(self.percent_sand >= 20.0, self.percent_sand <= 45.0),
                ),
                1.7,
                ifthenelse(
                    pcrand(self.percent_silt <= 40.0, self.percent_sand <= 20.0),
                    2.0,
                    ifthenelse(
                        pcrand(self.percent_silt > 40.0, self.percent_clay >= 40.0),
                        1.6,
                        ifthenelse(
                            pcrand(
                                self.percent_clay >= 35.0, self.percent_sand >= 45.0
                            ),
                            1.9,
                            ifthenelse(
                                pcrand(
                                    self.percent_clay >= 27.0, self.percent_sand < 20.0
                                ),
                                1.6,
                                ifthenelse(
                                    pcrand(
                                        self.percent_clay <= 10.0,
                                        self.percent_silt >= 80.0,
                                    ),
                                    1.2,
                                    ifthenelse(
                                        self.percent_silt >= 50,
                                        1.5,
                                        ifthenelse(
                                            pcrand(
                                                self.percent_clay >= 7.0,
                                                pcrand(
                                                    self.percent_sand <= 52.0,
                                                    self.percent_silt >= 28.0,
                                                ),
                                            ),
                                            2.0,
                                            ifthenelse(
                                                self.percent_clay >= 20.0,
                                                2.1,
                                                ifthenelse(
                                                    self.percent_clay
                                                    >= self.percent_sand - 70.0,
                                                    2.6,
                                                    ifthenelse(
                                                        self.percent_clay
                                                        >= (2.0 * self.percent_sand)
                                                        - 170.0,
                                                        3,
                                                        scalar(1.9),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        # over write parameters with maps from ini-file if provided
        # This is not needed as you can specify a map with a name and put in in the staticmaps anayway!!!!
        usle_k_map = str(configget(self.config, "model", "usle_k", "NotProvided"))
        c_factor_map = str(configget(self.config, "model", "usle_c", "NotProvided"))
        if not c_factor_map == "NotProvided":
            self.c_factor = readmap(os.path.join(self.Dir, c_factor_map))
        if not usle_k_map == "NotProvided":
            self.usle_k = readmap(os.path.join(self.Dir, usle_k_map))
        self.logger.info("Starting Dynamic run...")
        self.thestep = 0

    def resume(self):
        """ 
    *Required*

    This function is required. Read initial state maps (they are output of a 
    previous call to suspend()). The implementation shown here is the most basic
    setup needed.
    
    """
        self.logger.info("Reading initial conditions...")
        #: It is advised to use the wf_resume() function
        #: here which pick up the variable save by a call to wf_suspend()
        try:
            self.wf_resume(self.Dir + "/instate/")
        except:
            self.logger.warning("Cannot load initial states, setting to default")
            for s in self.stateVariables():
                exec("self." + s + " = cover(1.0)")

    def default_summarymaps(self):
        """
      *Optional*

      Return a default list of variables to report as summary maps in the outsum dir.
      The ini file has more options, including average and sum
      """
        return ["self.Altitude"]

    def dynamic(self):
        """
    *Required*

    This is where all the time dependent functions are executed. Time dependent
    output should also be saved here.
    """

        self.logger.debug(
            "Step: "
            + str(int(self.thestep + self._d_firstTimeStep))
            + "/"
            + str(int(self._d_nrTimeSteps))
        )
        self.thestep = self.thestep + 1

        self.wf_updateparameters()  # Read forcing and dynamic variables

        # calculate rainfall intensity
        rintnsty = self.Precipitation / self.timestepsecs
        rain_d50 = 0.188 * rintnsty ** 0.182

        """Weird assumption for now, should be a lookuptabel of LAI and landuse type...
       Original formulation of Jeong. Depreciated as one is basically calling canopy gap fraction
       self.canopy_cover = min(1.0,self.LAI)

       in stead we take it from the CanopyGapFraction
       maybe better incorporate exactly the same definition for CanopyGapFraction as WFlow_sbm? """
        self.canopy_cover = min(1.0, 1 - self.CanopyGapFraction)

        """ Rainfall kinetic energy generated by direct throughfall (J/m^2/mm)
    JS: IN SWAT CODE (ovr_sed.f):
    !! Rainfall kinetic energy generated by direct throughfall (J/m^2/mm)
	    ke_direct = 8.95 + 8.44 * log10(rintnsty)
    """
        ke_direct = max(11.87 + 8.73 * log10(max(0.0001, rintnsty)), 0.0)
        pheff = 0.5 * self.canopy_height
        ke_leaf = max((15.8 * pheff ** 0.5) - 5.87, 0.0)

        """ Depth of rainfall """
        # This should be taken from direct precipitation
        # DT true, take it from SBM?
        rdepth_tot = max(self.Precipitation / (self.timestepsecs), 0.0)
        # This should be taken from troughfall
        # DT true, take it from SBM?
        rdepth_leaf = max(rdepth_tot * self.canopy_cover, 0.0)
        rdepth_direct = max(rdepth_tot - rdepth_leaf, 0.0)

        """ total kinetic energy by rainfall (J/m^2) """
        ke_total = 0.001 * (rdepth_direct * ke_direct + rdepth_leaf * ke_leaf)

        """ total soil detachment by raindrop impact (ton/cell) """
        self.RunDepthMM = self.RunDepth  # *1000.
        self.sedspl = (
            self.erod_k * ke_total * exp(-self.eros_spl * self.RunDepthMM) * self.hru_km
        )

        """ Impervious area of HRU """
        # JS PAthFrac (Fimp) is already impervious fraction so this (sedspl) is the pervious?
        # So we multiply sedspl with pervious area fraction
        # DT Yes we do, it is erosion from pervious area. Splash erosion from impervious area (I think they call it 'wash') is not included.
        self.sedspl = self.sedspl * (1.0 - self.PathFrac)

        """ maximum water depth that allows splash erosion """
        self.sedspl = ifthenelse(
            pcror(self.RunDepthMM >= 3.0 * rain_d50, self.RunDepthMM <= 1.0e-6),
            0.0,
            self.sedspl,
        )

        """ Overland flow erosion """
        """ cover and management factor used in usle equation (ysed.f) """
        # DT I think we better forget this for now and directly supply the USLE C
        # c = exp((-.2231 - self.idplt_cvm) * exp(-.00115 * self.soil_cov + self.idplt_cvm))

        """ calculate shear stress (N/m2) """
        self.bed_shear = 9807 * self.RunDepth / 1000.0 * self.Slope

        """ sediment yield by overland flow (kg/hour/m2) """
        self.sedov = (
            11.02
            * self.rill_mult
            * self.usle_k
            * self.c_factor
            * self.bed_shear ** self.eros_expo
        )

        """ sediment yield by overland flow (ton/cell) """
        # DT 1E6/1E3/60 = 16.667
        self.sedov = 16.667 * self.sedov * self.hru_km * self.timestepsecs / 60.0

        """ Impervious area of HRU """
        # DT, again it is only erosion from pervious area
        self.sedov = self.sedov * (1.0 - self.PathFrac)

        """ Report sediment yield """
        self.hhsedy = self.dratio * (self.sedspl + self.sedov)
        self.hhsedy = cover(
            ifthenelse(self.hhsedy < 1.0e-10, 0, self.hhsedy), scalar(0.0)
        )
        # We could use accucapacityflux and link the capacity to runoff of speed
        self.SedRunoff = accuflux(self.TopoLdd, self.hhsedy)
        # limit downstream flow by surface runoff erosion rate

        # self.SedStore = self.SedStore + self.hhsedy
        # self.SedRunoff = accucapacityflux(self.TopoLdd, self.SedStore,self.sedov *20.0)
        # self.SedStore = accucapacitystate(self.TopoLdd, self.SedStore,self.sedov * 20.0 )


# The main function is used to run the program from the command line


def main(argv=None):
    """
    *Optional but needed it you want to run the model from the command line*
    
    Perform command line execution of the model. This example uses the getopt
    module to parse the command line options.
    
    The user can set the caseName, the runDir, the timestep and the configfile.
    """
    global multpars
    caseName = "default"
    runId = "run_default"
    configfile = "wflow_mswat.ini"
    _lastTimeStep = 10
    _firstTimeStep = 1
    timestepsecs = 86400
    wflow_cloneMap = "wflow_dem.map"

    # This allows us to use the model both on the command line and to call
    # the model usinge main function from another python script.

    if argv is None:
        argv = sys.argv[1:]
        if len(argv) == 0:
            usage()
            return

    opts, args = getopt.getopt(argv, "C:S:T:c:s:R:")

    for o, a in opts:
        if o == "-C":
            caseName = a
        if o == "-R":
            runId = a
        if o == "-c":
            configfile = a
        if o == "-s":
            timestepsecs = int(a)
        if o == "-T":
            _lastTimeStep = int(a)
        if o == "-S":
            _firstTimeStep = int(a)

    if len(opts) <= 1:
        usage()

    myModel = WflowModel(wflow_cloneMap, caseName, runId, configfile)
    dynModelFw = wf_DynamicFramework(
        myModel, _lastTimeStep, firstTimestep=_firstTimeStep
    )
    dynModelFw.createRunId(NoOverWrite=False, level=logging.DEBUG)
    dynModelFw._runInitial()
    dynModelFw._runResume()
    dynModelFw._runDynamic(_firstTimeStep, _lastTimeStep)
    dynModelFw._runSuspend()
    dynModelFw._wf_shutdown()


if __name__ == "__main__":
    main()
