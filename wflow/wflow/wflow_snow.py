#!/usr/bin/python

# Wflow is Free software, see below:
#
# Copyright (c) J. Schellekens/Deltares 2005-2011
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# TODO: remove dots in dynamic phase (default pcraster progress (how?)
# TODO: consistancy about what is in ini file and what is in environment
# TODO: formal test runs against SMHI model

# $Rev:: 542           $:  Revision of last commit
# $Author:: schelle    $:  Author of last commit
# $Date:: 2012-11-27 1#$:  Date of last commit
"""

Run the wflow_pack snow model


usage: 
wflow_snow [-h][-v level][-F runinfofile][-L logfile][-C casename][-R runId]
      [-c configfile][-T timesteps][-s seconds][-W][-E][-N][-U discharge]
      [-P parameter multiplication]

-X: save state at the end of the run over the initial conditions at the start    
-f: Force overwrite of existing results
-T: Set last timestep
-S: Set the start timestep (default = 1)
-s: Set the model timesteps in seconds (default 86400)
-I: re-initialize the initial model conditions with default
-i: Set input table directory (default is intbl)
-x: run for subcatchment only (e.g. -x 1)
-M: Switch on simple mass-wasting
-C: set the name  of the case (directory) to run
-R: set the name runId within the current case
-c: name of wflow the configuration file (default: Casename/wflow_hbv.ini). 
-h: print usage information
-P: set parameter multiply dictionary (e.g: -P {'self.FirstZoneDepth' : 1.2}
    to increase self.FirstZoneDepth by 20%, multiply with 1.2)
-p: set input parameter (dynamic, e.g. precip) multiply dictionary 
    (e.g: -p {'Precipitation' : 1.2} to increase Precipitation 
    by 20%, multiply with 1.2)    
    
"""

import getopt
import os.path

import pcraster.framework
from wflow.wf_DynamicFramework import *

wflow = "wflow_pack: "
wflowVersion = (
    "$Revision: 542 $  $Date: 2012-11-27 19:00:43 +0100 (Tue, 27 Nov 2012) $"
)  #: revision of the model


updateCols = []  #: columns used in updating


multpars = (
    {}
)  #: Dictionary with parameters and multipliers (static) (used in calibration)
multdynapars = (
    {}
)  #: Dictionary with parameters and multipliers (dynamic) (used in calibration)


def usage(*args):
    """
    Print usage information
    
    @param *args: command line arguments given
    
    """
    sys.stdout = sys.stderr
    for msg in args:
        print(msg)
    print(__doc__)
    sys.exit(0)


class WflowModel(pcraster.framework.DynamicModel):
    def __init__(self, cloneMap, Dir, RunDir, configfile):
        pcraster.framework.DynamicModel.__init__(self)
        pcr.setclone(Dir + "/staticmaps/" + cloneMap)
        self.runId = RunDir
        self.caseName = Dir
        self.Dir = Dir
        self.configfile = configfile

    def readmap(self, name, default, style=1):
        """
      Reads a pcraster map
      
      @param name: name of the map to read
      @param default: default value in case the maps is not found
      
      @return: pcraster map
      """
        return self._readmapNew(name, default, style)

    def supplyVariableNamesAndRoles(self):
        """
      Returns a list of variables as a
      List of list with the following structure::
          [[ name, role, unit]
          [ name, role, unit]
          ...   
          ]
          role: 0 = input (to the model)
                1 = is output (from the model)
                2 = input/output (state information)
          unit: 0 = mm/timestep
                1 = m^3/sec
                2 = m
                3 = degree Celcius
                4 = mm
                
      @return: list of variables
      """

        varlist = [
            ["FreeWater", 2, 4],
            ["DrySnow", 2, 4],
            ["Melt", 1, 4],
            ["P", 0, 0],
            ["T", 0, 3],
        ]

        return varlist

    # The following are made to better connect to deltashell/openmi
    def supplyCurrentTime(self):
        """
      gets the current time in seconds after the start of the run
      
      @return: time in seconds since the start of the model run
      """
        return self.currentTimeStep() * modelEnv["timestepsecs"]

    def readtblDefault(self, pathtotbl, landuse, subcatch, soil, default):
        """
    First check if a prepared  maps of the same name is present
    in the staticmaps directory. next try to
    read a tbl file to match a landuse, catchment and soil map. Returns 
    the default value if the tbl file is not found.
    
    @param pathtotbl: full path to table file
    @param landuse: landuse map
    @param subcatch: subcatchment map
    @param soil: soil map
    @param default: default value
    @return: map constructed from tbl file or map with default value
    """

        mapname = (
            os.path.dirname(pathtotbl)
            + "/../staticmaps/"
            + os.path.splitext(os.path.basename(pathtotbl))[0]
            + ".map"
        )
        if os.path.exists(mapname):
            self.logger.info("reading map parameter file: " + mapname)
            rest = pcr.cover(pcr.readmap(mapname), default)
        else:
            if os.path.isfile(pathtotbl):
                rest = pcr.cover(
                    pcr.lookupscalar(pathtotbl, landuse, subcatch, soil), default
                )
                self.logger.info("Creating map from table: " + pathtotbl)
            else:
                self.logger.warning(
                    "tbl file not found ("
                    + pathtotbl
                    + ") returning default value: "
                    + str(default)
                )
                rest = pcr.scalar(default)

        return rest

    def suspend(self):
        """
      Suspens the model to disk. All variables needed to restart the model
      are save to disk as pcraster maps. Use resume() to re-read them
    """

        self.logger.info("Saving initial conditions...")
        self.wf_suspend(self.SaveDir + "/outstate/")

        if self.OverWriteInit:
            self.logger.info("Saving initial conditions over start conditions...")
            self.wf_suspend(self.SaveDir + "/instate/")

        pcr.report(self.sumprecip, self.SaveDir + "/outsum/sumprecip.map")
        pcr.report(self.sumtemp, self.SaveDir + "/outsum/sumtemp.map")

    def initial(self):

        """
    Initial part of the model, executed only once. Is read all static model
    information (parameters) and sets-up the variables used in modelling.
    
    """
        global statistics

        pcr.setglobaloption("unittrue")

        self.thestep = pcr.scalar(0)
        self.setQuiet(True)
        self.precipTss = (
            "../intss/P.tss"
        )  #: name of the tss file with precipitation data ("../intss/P.tss")
        self.tempTss = (
            "../intss/T.tss"
        )  #: name of the tss file with temperature  data ("../intss/T.tss")

        self.logger.info("running for " + str(self.nrTimeSteps()) + " timesteps")
        self.setQuiet(True)

        # Set and get defaults from ConfigFile here ###################################
        self.scalarInput = int(configget(self.config, "model", "ScalarInput", "0"))
        self.Tslice = int(configget(self.config, "model", "Tslice", "1"))
        self.interpolMethod = configget(
            self.config, "model", "InterpolationMethod", "inv"
        )
        self.reinit = int(configget(self.config, "run", "reinit", "0"))
        self.OverWriteInit = int(configget(self.config, "model", "OverWriteInit", "0"))
        self.MassWasting = int(configget(self.config, "model", "MassWasting", "0"))
        self.sCatch = int(configget(self.config, "model", "sCatch", "0"))
        self.intbl = configget(self.config, "model", "intbl", "intbl")
        self.timestepsecs = int(
            configget(self.config, "model", "timestepsecs", "86400")
        )
        self.P_style = int(configget(self.config, "model", "P_style", "1"))
        self.TEMP_style = int(configget(self.config, "model", "TEMP_style", "1"))

        # 2: Input base maps ########################################################
        subcatch = pcr.ordinal(
            pcr.readmap(self.Dir + "/staticmaps/wflow_subcatch.map")
        )  # Determines the area of calculations (all cells > 0)
        subcatch = pcr.ifthen(subcatch > 0, subcatch)
        if self.sCatch > 0:
            subcatch = pcr.ifthen(subcatch == sCatch, subcatch)

        self.Altitude = pcr.readmap(self.Dir + "/staticmaps/wflow_dem") * pcr.scalar(
            pcr.defined(subcatch)
        )  #: The digital elevation map (DEM)
        self.TopoId = pcr.readmap(
            self.Dir + "/staticmaps/wflow_subcatch.map"
        )  #: Map define the area over which the calculations are done (mask)
        self.TopoLdd = pcr.readmap(
            self.Dir + "/staticmaps/wflow_ldd.map"
        )  #: The local drinage definition map (ldd)
        # read landuse and soilmap and make sure there are no missing points related to the
        # subcatchment map. Currently sets the lu and soil type  type to 1
        self.LandUse = pcr.readmap(
            self.Dir + "/staticmaps/wflow_landuse.map"
        )  #: Map with lan-use/cover classes
        self.LandUse = pcr.cover(self.LandUse, pcr.nominal(pcr.ordinal(subcatch) > 0))
        self.Soil = pcr.readmap(
            self.Dir + "/staticmaps/wflow_soil.map"
        )  #: Map with soil classes
        self.Soil = pcr.cover(self.Soil, pcr.nominal(pcr.ordinal(subcatch) > 0))
        self.OutputLoc = pcr.readmap(
            self.Dir + "/staticmaps/wflow_gauges.map"
        )  #: Map with locations of output gauge(s)

        # Temperature correction poer cell to add
        self.TempCor = pcrut.readmapSave(
            self.Dir + "/staticmaps/wflow_tempcor.map", 0.0
        )

        if self.scalarInput:
            self.gaugesMap = pcr.readmap(
                self.Dir + "/staticmaps/wflow_mgauges.map"
            )  #: Map with locations of rainfall/evap/temp gauge(s). Only needed if the input to the model is not in maps
        self.OutputId = pcr.readmap(
            self.Dir + "/staticmaps/wflow_subcatch.map"
        )  # location of subcatchment

        self.ZeroMap = 0.0 * pcr.scalar(subcatch)  # map with only zero's

        # 3: Input time series ###################################################
        self.Rain_ = self.Dir + "/inmaps/P"  #: timeseries for rainfall
        self.Temp_ = self.Dir + "/inmaps/TEMP"  #: temperature

        # Set static initial values here #########################################

        self.Latitude = pcr.ycoordinate(pcr.boolean(self.Altitude))
        self.Longitude = pcr.xcoordinate(pcr.boolean(self.Altitude))

        self.logger.info("Linking parameters to landuse, catchment and soil...")

        # HBV Soil params
        self.CFR = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/CFR.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.05000,
        )  # refreezing efficiency constant in refreezing of freewater in snow
        # self.FoCfmax=self.readtblDefault(self.Dir + "/" + self.intbl + "/FoCfmax.tbl",self.LandUse,subcatch,self.Soil, 0.6000)  # correcton factor for snow melt/refreezing in forested and non-forested areas
        self.Pcorr = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/Pcorr.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )  # correction factor for precipitation
        self.RFCF = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/RFCF.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )  # correction factor for rainfall
        self.SFCF = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/SFCF.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )  # correction factor for snowfall
        self.Cflux = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/Cflux.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            2.0,
        )  # maximum capillary rise from runoff response routine to soil moisture routine

        # HBV Snow parameters
        # critical temperature for snowmelt and refreezing:  TTI= 1.000
        self.TTI = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/TTI.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )
        # TT = -1.41934 # defines interval in which precipitation falls as rainfall and snowfall
        self.TT = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/TT.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            -1.41934,
        )
        # Cfmax = 3.75653 # meltconstant in temperature-index
        self.Cfmax = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/Cfmax.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            3.75653,
        )
        # WHC= 0.10000        # fraction of Snowvolume that can store water
        self.WHC = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/WHC.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.1,
        )

        # Determine real slope and cell length
        sizeinmetres = int(configget(self.config, "layout", "sizeinmetres", "0"))
        self.xl, self.yl, self.reallength = pcrut.detRealCellLength(
            self.ZeroMap, sizeinmetres
        )
        self.Slope = pcr.slope(self.Altitude)
        self.Slope = pcr.ifthen(
            pcr.boolean(self.TopoId),
            pcr.max(0.001, self.Slope * pcr.celllength() / self.reallength),
        )

        # Multiply parameters with a factor (for calibration etc) -P option in command line
        for k, v in multpars.items():
            estr = k + "=" + k + "*" + str(v)
            self.logger.info("Parameter multiplication: " + estr)
            exec(estr)

        self.SnowWater = self.ZeroMap

        # Initializing of variables
        self.logger.info("Initializing of model variables..")
        self.TopoLdd = pcr.lddmask(self.TopoLdd, pcr.boolean(self.TopoId))
        catchmentcells = pcr.maptotal(pcr.scalar(self.TopoId))

        # Used to seperate output per LandUse/management classes
        # OutZones = self.LandUse
        # pcr.report(self.reallength,"rl.map")
        # pcr.report(catchmentcells,"kk.map")
        self.QMMConv = self.timestepsecs / (
            self.reallength * self.reallength * 0.001
        )  # m3/s --> mm

        self.sumprecip = self.ZeroMap  #: accumulated rainfall for water balance
        self.sumtemp = self.ZeroMap  # accumulated runoff for water balance

        self.logger.info("Create timeseries outputs...")
        toprinttss = configsection(self.config, "outputtss")

        # Save some summary maps
        self.logger.info("Saving summary maps...")
        pcr.report(self.Cfmax, self.Dir + "/" + self.runId + "/outsum/Cfmax.map")
        pcr.report(self.TTI, self.Dir + "/" + self.runId + "/outsum/TTI.map")
        pcr.report(self.TT, self.Dir + "/" + self.runId + "/outsum/TT.map")
        pcr.report(self.WHC, self.Dir + "/" + self.runId + "/outsum/WHC.map")
        pcr.report(self.xl, self.Dir + "/" + self.runId + "/outsum/xl.map")
        pcr.report(self.yl, self.Dir + "/" + self.runId + "/outsum/yl.map")
        pcr.report(self.reallength, self.Dir + "/" + self.runId + "/outsum/rl.map")

        self.SaveDir = self.Dir + "/" + self.runId + "/"
        self.logger.info("Starting Dynamic run...")

    def resume(self):
        """ read initial state maps (they are output of a previous call to suspend()) """

        if self.reinit == 1:
            self.logger.info("Setting initial conditions to default (zero!)")
            self.FreeWater = pcr.cover(0.0)  #: Water on surface (state variable [mm])
            self.DrySnow = pcr.cover(0.0)  #: Snow amount (state variable [mm])
        else:
            self.wf_resume(self.Dir + "/instate/")

    def dynamic(self):

        self.logger.debug(
            "Step: "
            + str(int(self.thestep + self._d_firstTimeStep))
            + "/"
            + str(int(self._d_nrTimeSteps))
        )
        self.thestep = self.thestep + 1

        if self.scalarInput:
            # gaugesmap not yet finished. Should be a map with cells that
            # hold the gauges with an unique id
            Precipitation = pcr.timeinputscalar(self.precipTss, self.gaugesMap)
            # Seepage = pcr.cover(pcr.timeinputscalar(self.SeepageTss,self.SeepageLoc),0)
            Precipitation = pcrut.interpolategauges(Precipitation, self.interpolMethod)
            # self.report(PotEvaporation,'p')
            Temperature = pcr.timeinputscalar(self.tempTss, self.gaugesMap)
            Temperature = pcrut.interpolategauges(Temperature, self.interpolMethod)
            Temperature = Temperature + self.TempCor
        else:
            Precipitation = pcr.cover(self.readmap(self.Rain_, 0.0, self.P_style), 0.0)
            # Inflow=pcr.cover(self.readmap(self.Inflow),0)
            # These ar ALWAYS 0 at present!!!
            Temperature = self.readmap(self.Temp_, 0.0, self.TEMP_style)
            Temperature = Temperature + self.TempCor
            # Inflow=pcr.spatial(pcr.scalar(0.0))

        # Multiply input parameters with a factor (for calibration etc) -p option in command line
        for k, v in multdynapars.items():
            estr = k + "=" + k + "*" + str(v)
            self.logger.debug("Dynamic Parameter multiplication: " + estr)
            exec(estr)

        # Snow pack modelling degree day methods
        RainFrac = pcr.ifthenelse(
            1.0 * self.TTI == 0.0,
            pcr.ifthenelse(Temperature <= self.TT, pcr.scalar(0.0), pcr.scalar(1.0)),
            pcr.min(
                (Temperature - (self.TT - self.TTI / 2.0)) / self.TTI, pcr.scalar(1.0)
            ),
        )
        RainFrac = pcr.max(
            RainFrac, pcr.scalar(0.0)
        )  # fraction of precipitation which falls as rain
        SnowFrac = 1.0 - RainFrac  # fraction of precipitation which falls as snow
        Precipitation = (
            self.SFCF * SnowFrac * Precipitation + self.RFCF * RainFrac * Precipitation
        )  # different correction for rainfall and snowfall

        SnowFall = SnowFrac * Precipitation  #: snowfall depth
        RainFall = RainFrac * Precipitation  #: rainfall depth
        PotSnowMelt = pcr.ifthenelse(
            Temperature > self.TT, self.Cfmax * (Temperature - self.TT), pcr.scalar(0.0)
        )  # Potential snow melt, based on temperature
        PotRefreezing = pcr.ifthenelse(
            Temperature < self.TT, self.Cfmax * self.CFR * (self.TT - Temperature), 0.0
        )  # Potential refreezing, based on temperature

        # PotSnowMelt=self.FoCfmax*PotSnowMelt     	#correction for forest zones 0.6)
        # PotRefreezing=self.FoCfmax*PotRefreezing
        Refreezing = pcr.ifthenelse(
            Temperature < self.TT, pcr.min(PotRefreezing, self.FreeWater), 0.0
        )  # actual refreezing
        SnowMelt = pcr.min(PotSnowMelt, self.DrySnow)  # actual snow melt
        self.DrySnow = (
            self.DrySnow + SnowFall + Refreezing - SnowMelt
        )  # dry snow content
        self.FreeWater = self.FreeWater - Refreezing  # free water content in snow
        MaxFreeWater = self.DrySnow * self.WHC
        self.FreeWater = self.FreeWater + SnowMelt + RainFall
        InSoil = pcr.max(
            self.FreeWater - MaxFreeWater, 0.0
        )  # abundant water in snow pack which goes into soil
        self.FreeWater = self.FreeWater - InSoil
        self.Melt = InSoil

        MaxSnowPack = 10000.0
        if self.MassWasting:
            # Masswasting of snow
            # 5.67 = tan 80 graden
            SnowFluxFrac = pcr.min(0.5, self.Slope / 5.67) * pcr.min(
                1.0, self.DrySnow / MaxSnowPack
            )
            MaxFlux = SnowFluxFrac * self.DrySnow
            self.DrySnow = accucapacitystate(self.TopoLdd, self.DrySnow, MaxFlux)
            self.FreeWater = accucapacitystate(
                self.TopoLdd, self.FreeWater, SnowFluxFrac * self.FreeWater
            )
        else:
            SnowFluxFrac = self.ZeroMap
            MaxFlux = self.ZeroMap

        self.sumprecip = (
            self.sumprecip + Precipitation
        )  # accumulated rainfall for water balance

        # Get rest from ini file


# The main function is used to run the program from the command line


def main():
    caseName = "default_hbv"
    runId = "run_default"
    configfile = "wflow_pack.ini"
    _lastTimeStep = 10
    _firstTimeStep = 1

    runinfoFile = "runinfo.xml"
    timestepsecs = 86400
    wflow_cloneMap = "wflow_subcatch.map"

    """
    Perform command line execution of the model.
    """
    ## Main model starts here
    ########################################################################
    try:
        opts, args = getopt.getopt(sys.argv[1:], "Mc:QXS:hC:Ii:T:NR:u:s:P:p:Xx:U:f")
    except getopt.error as msg:
        pcrut.usage(msg)

    for o, a in opts:
        if o == "-P":
            exec("multpars =" + a)
            print("WARN: -P Does not work at the moment")
        if o == "-p":
            exec("multdynapars =" + a)
            print("WARN: -p Does not work at the moment")
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
        if o == "-h":
            usage()
        if o == "-f":
            NoOverWrite = 1

    myModel = WflowModel(wflow_cloneMap, caseName, runId, configfile)
    dynModelFw = wf_DynamicFramework(
        myModel, _lastTimeStep, firstTimestep=_firstTimeStep
    )
    dynModelFw.createRunId()

    for o, a in opts:
        if o == "-X":
            configset(myModel.config, "model", "OverWriteInit", "1", overwrite=True)
        if o == "-I":
            configset(myModel.config, "model", "reinit", "1", overwrite=True)
        if o == "-i":
            configset(myModel.config, "model", "intbl", a, overwrite=True)
        if o == "-s":
            configset(myModel.config, "model", "timestepsecs", a, overwrite=True)
        if o == "-x":
            configset(myModel.config, "model", "sCatch", a, overwrite=True)
        if o == "-c":
            configset(myModel.config, "model", "configfile", a, overwrite=True)
        if o == "-M":
            configset(myModel.config, "model", "MassWasting", "1", overwrite=True)
        if o == "-h":
            usage()

    # dynModelFw.run()
    dynModelFw._runInitial()
    dynModelFw._runResume()
    dynModelFw._runDynamic(_firstTimeStep, _lastTimeStep)
    dynModelFw._runSuspend()

    fp = open(caseName + "/" + runId + "/runinfo/configofrun.ini", "wb")
    # fp = open("runinfo/configofrun.ini",'wb')
    myModel.config.write(fp)

    os.chdir("../../")


if __name__ == "__main__":
    main()
