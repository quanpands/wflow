#!/usr/bin/python

# Wflow is Free software, see below:
#
# Copyright (c) J. Schellekens/Deltares 2005-2014
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


"""
Run the wflow_sbm hydrological model..

usage

::
    
    wflow_sbm [-h][-v level][-F runinfofile][-L logfile][-C casename][-R runId]
          [-c configfile][-T last_step][-S first_step][-s seconds][-W][-E][-N][-U discharge]
          [-P parameter multiplication][-X][-f][-I][-i tbl_dir][-x subcatchId][-u updatecols]
          [-p inputparameter multiplication][-l loglevel]

    -X: save state at the end of the run over the initial conditions at the start        
    
    -f: Force overwrite of existing results    
    
    -T: Set last timestep
    
    -S: Set the start timestep (default = 1)
    
    -s: Set the model timesteps in seconds
    
    -I: re-initialize the initial model conditions with default
    
    -i: Set input table directory (default is intbl)
    
    -x: Apply multipliers (-P/-p ) for subcatchment only (e.g. -x 1)
    
    -C: set the name  of the case (directory) to run
    
    -R: set the name runId within the current case
    
    -L: set the logfile
    
    -E: Switch on reinfiltration of overland flow
    
    -c: name of wflow the configuration file (default: Casename/wflow_sbm.ini). 
    
    -h: print usage information
    
    -W: If set, this flag indicates that an ldd is created for the water level
        for each timestep. If not the water is assumed to flow according to the 
        DEM. Wflow will run a lot slower with this option. Most of the time
        (shallow soil, steep topography) you do not need this option. Also, if you 
        need it you migth actually need another model.
        
    -U: The argument to this option should be a .tss file with measured discharge in
        [m^3/s] which the progam will use to update the internal state to match 
        the measured flow. The number of columns in this file should match the 
        number of gauges in the wflow\_gauges.map file.
    
    -u: list of gauges/columns to use in update. Format:
        -u [1 , 4 ,13]
        The above example uses column 1, 4 and 13
        
    -P: set parameter change string (e.g: -P "self.FC = self.FC * 1.6") for non-dynamic variables

    -p: set parameter change string (e.g: -P "self.Precipitation = self.Precipitation * 1.11") for
        dynamic variables

    -l: loglevel (must be one of DEBUG, INFO, WARNING, ERROR)



"""

# TODO: add Et reduction in unsat zone based on deficit

import os.path

import pcraster.framework
from wflow.wf_DynamicFramework import *
from wflow.wflow_adapt import *
from wflow.wflow_funcs import *

wflow = "wflow_sbm: "

updateCols = []


def usage(*args):
    sys.stdout = sys.stderr
    """Way"""
    for msg in args:
        print(msg)
    print(__doc__)
    sys.exit(0)


def actEvap_SBM(
    RootingDepth, WTable, UStoreDepth, SatWaterDepth, PotTrans, smoothpar, ust=0
):
    """
    Actual evaporation function:
    Actual evaporation function:

    - first try to get demand from the saturated zone, using the rootingdepth as a limiting factor
    - secondly try to get the remaining water from the unsaturated store
    - it uses an S-Curve the make sure roots het wet/dry gradually (basically)
      representing a root-depth distribution

      if ust is True, all ustore is deems to be avaiable fro the roots a

    Input:
    
        - RootingDepth,WTable, UStoreDepth,SatWaterDepth, PotTrans, smoothpar
        
    Output: 
    
        - ActEvap,  SatWaterDepth,  UStoreDepth ActEvapUStore
    """

    # Step 1 from saturated zone, use rootingDepth as a limiting factor
    # rootsinWater = WTable < RootingDepth
    # ActEvapSat = pcr.ifthenelse(rootsinWater,pcr.min(PotTrans,SatWaterDepth),0.0)
    # new method:
    # use sCurve to determine if the roots are wet.At the moment this ise set
    # to be a 0-1 curve
    wetroots = sCurve(WTable, a=RootingDepth, c=smoothpar)
    # wetroots = pcr.ifthenelse(WTable <= RootingDepth, pcr.scalar(1.0), pcr.scalar(0.0))
    ActEvapSat = pcr.min(PotTrans * wetroots, SatWaterDepth)

    SatWaterDepth = SatWaterDepth - ActEvapSat
    RestPotEvap = PotTrans - ActEvapSat

    # now try unsat store
    # AvailCap = pcr.min(1.0, pcr.max(0.0, (WTable - RootingDepth) / (RootingDepth + 1.0)))

    if ust >= 1:
        AvailCap = UStoreDepth * 0.99
    else:
        AvailCap = pcr.max(
            0.0,
            pcr.ifthenelse(
                WTable < RootingDepth, pcr.cover(1.0), RootingDepth / (WTable + 1.0)
            ),
        )
    MaxExtr = AvailCap * UStoreDepth
    ActEvapUStore = pcr.min(MaxExtr, RestPotEvap, UStoreDepth)
    UStoreDepth = UStoreDepth - ActEvapUStore

    ActEvap = ActEvapSat + ActEvapUStore

    return ActEvap, SatWaterDepth, UStoreDepth, ActEvapUStore


def SnowPackHBV(Snow, SnowWater, Precipitation, Temperature, TTI, TT, TTM, Cfmax, WHC):
    """
    HBV Type snowpack modelling using a Temperature degree factor. All correction
    factors (RFCF and SFCF) are set to 1. The refreezing efficiency factor is set to 0.05.

    :param Snow:
    :param SnowWater:
    :param Precipitation:
    :param Temperature:
    :param TTI:
    :param TT:
    :param TTM:
    :param Cfmax:
    :param WHC:
    :return: Snow,SnowMelt,Precipitation
    """

    RFCF = 1.0  # correction factor for rainfall
    CFR = 0.05000  # refreeing efficiency constant in refreezing of freewater in snow
    SFCF = 1.0  # correction factor for snowfall

    RainFrac = pcr.ifthenelse(
        1.0 * TTI == 0.0,
        pcr.ifthenelse(Temperature <= TT, pcr.scalar(0.0), pcr.scalar(1.0)),
        pcr.min((Temperature - (TT - TTI / 2)) / TTI, pcr.scalar(1.0)),
    )
    RainFrac = pcr.max(
        RainFrac, pcr.scalar(0.0)
    )  # fraction of precipitation which falls as rain
    SnowFrac = 1 - RainFrac  # fraction of precipitation which falls as snow
    Precipitation = (
        SFCF * SnowFrac * Precipitation + RFCF * RainFrac * Precipitation
    )  # different correction for rainfall and snowfall

    SnowFall = SnowFrac * Precipitation  # snowfall depth
    RainFall = RainFrac * Precipitation  # rainfall depth
    PotSnowMelt = pcr.ifthenelse(
        Temperature > TTM, Cfmax * (Temperature - TTM), pcr.scalar(0.0)
    )  # Potential snow melt, based on temperature
    PotRefreezing = pcr.ifthenelse(
        Temperature < TTM, Cfmax * CFR * (TTM - Temperature), 0.0
    )  # Potential refreezing, based on temperature
    Refreezing = pcr.ifthenelse(
        Temperature < TTM, pcr.min(PotRefreezing, SnowWater), 0.0
    )  # actual refreezing
    # No landuse correction here
    SnowMelt = pcr.min(PotSnowMelt, Snow)  # actual snow melt
    Snow = Snow + SnowFall + Refreezing - SnowMelt  # dry snow content
    SnowWater = SnowWater - Refreezing  # free water content in snow
    MaxSnowWater = Snow * WHC  # Max water in the snow
    SnowWater = (
        SnowWater + SnowMelt + RainFall
    )  # Add all water and potentially supersaturate the snowpack
    RainFall = pcr.max(SnowWater - MaxSnowWater, 0.0)  # rain + surpluss snowwater
    SnowWater = SnowWater - RainFall

    return Snow, SnowWater, SnowMelt, RainFall, SnowFall


def GlacierMelt(GlacierStore, Snow, Temperature, TT, Cfmax):
    """
    Glacier modelling using a Temperature degree factor. Melting
    only occurs if the snow cover > 10 mm


    :ivar GlacierStore:
    :ivar Snow: Snow pack on top of Glacier
    :ivar Temperature:

    :returns: GlacierStore,GlacierMelt,
    """

    PotMelt = pcr.ifthenelse(
        Temperature > TT, Cfmax * (Temperature - TT), pcr.scalar(0.0)
    )  # Potential snow melt, based on temperature

    GlacierMelt = pcr.ifthenelse(
        Snow > 10.0, pcr.min(PotMelt, GlacierStore), pcr.cover(0.0)
    )  # actual Glacier melt
    GlacierStore = GlacierStore - GlacierMelt  # dry snow content

    return GlacierStore, GlacierMelt


class WflowModel(pcraster.framework.DynamicModel):
    """
    .. versionchanged:: 0.91
        - Calculation of GWScale moved to resume() to allow fitting.

    .. versionadded:: 0.91
        - added S-curve for freezing soil infiltration reduction calculations

    .. todo::
        - add slope based quick-runoff -> less percolation on hillslopes...
  """

    def __init__(self, cloneMap, Dir, RunDir, configfile):
        pcraster.framework.DynamicModel.__init__(self)

        self.caseName = os.path.abspath(Dir)
        self.clonemappath = os.path.join(os.path.abspath(Dir), "staticmaps", cloneMap)
        pcr.setclone(self.clonemappath)
        self.runId = RunDir
        self.Dir = os.path.abspath(Dir)
        self.configfile = configfile
        self.SaveDir = os.path.join(self.Dir, self.runId)

    def irrigationdemand(self, pottrans, acttrans, irareas):
        """
        Determine irrigation water demand from the difference bewteen potential
        transpiration and actual transpiration.

        :param pottrans: potential transpiration (epot minus interception and soil/open water evaporation)
        :param acttrans: actual transpiration
        :param ir_areas: maps of irrigation areas

        :return: demand
        """

        Et_diff = pcr.areaaverage(pottrans - acttrans, pcr.nominal(irareas))
        # Now determine demand in m^3/s for each area
        sqmarea = pcr.areatotal(self.reallength * self.reallength, pcr.nominal(irareas))
        m3sec = Et_diff * sqmarea / 1000.0 / self.timestepsecs

        return Et_diff, m3sec

    def updateRunOff(self):
        """
      Updates the kinematic wave reservoir. Should be run after updates to Q
      """
        self.WaterLevel = (self.Alpha * pow(self.SurfaceRunoff, self.Beta)) / self.Bw
        # wetted perimeter (m)
        P = self.Bw + (2 * self.WaterLevel)
        # Alpha
        self.Alpha = self.AlpTerm * pow(P, self.AlpPow)
        self.OldKinWaveVolume = self.KinWaveVolume
        self.KinWaveVolume = self.WaterLevel * self.Bw * self.DCL

    def stateVariables(self):
        """
        returns a list of state variables that are essential to the model.
        This list is essential for the resume and suspend functions to work.

        This function is specific for each model and **must** be present.

       :var self.SurfaceRunoff: Surface runoff in the kin-wave resrvoir [m^3/s]
       :var self.SurfaceRunoffDyn: Surface runoff in the dyn-wave resrvoir [m^3/s]
       :var self.WaterLevel: Water level in the kin-wave resrvoir [m]
       :var self.WaterLevelDyn: Water level in the dyn-wave resrvoir [m^]
       :var self.Snow: Snow pack [mm]
       :var self.SnowWater: Snow pack water [mm]
       :var self.TSoil: Top soil temperature [oC]
       :var self.UStoreDepth: Water in the Unsaturated Store [mm]
       :var self.SatWaterDepth: Water in the saturated store [mm]
       :var self.CanopyStorage: Amount of water on the Canopy [mm]
       :var self.ReservoirVolume: Volume of each reservoir [m^3]
       :var self.GlacierStore: Thickness of the Glacier in a gridcell [mm]
       """

        states = [
            "SurfaceRunoff",
            "WaterLevel",
            "SatWaterDepth",
            "Snow",
            "TSoil",
            "UStoreDepth",
            "SnowWater",
            "CanopyStorage",
        ]

        if hasattr(self, "GlacierFrac"):
            states.append("GlacierStore")

        if hasattr(self, "ReserVoirLocs"):
            states.append("ReservoirVolume")

        return states

    def supplyCurrentTime(self):
        """
      gets the current time in seconds after the start of the run
      """
        return self.currentTimeStep() * self.timestepsecs

    def suspend(self):

        self.logger.info("Saving initial conditions...")
        self.wf_suspend(os.path.join(self.SaveDir, "outstate"))

        if self.OverWriteInit:
            self.logger.info("Saving initial conditions over start conditions...")
            self.wf_suspend(self.SaveDir + "/instate/")

    def parameters(self):
        """
        Define all model parameters here that the framework should handle for the model
        See wf_updateparameters and the parameters section of the ini file
        If you use this make sure to all wf_updateparameters at the start of the dynamic section
        and at the start/end of the initial section
        """
        modelparameters = []

        # Static model parameters e.g.
        # modelparameters.append(self.ParamType(name="RunoffGeneratingGWPerc",stack="intbl/RunoffGeneratingGWPerc.tbl",type="static",default=0.1))
        # 3: Input time series ###################################################
        self.P_mapstack = self.Dir + configget(
            self.config, "inputmapstacks", "Precipitation", "/inmaps/P"
        )  # timeseries for rainfall
        self.PET_mapstack = self.Dir + configget(
            self.config, "inputmapstacks", "EvapoTranspiration", "/inmaps/PET"
        )  # timeseries for rainfall"/inmaps/PET"          # potential evapotranspiration
        self.TEMP_mapstack = self.Dir + configget(
            self.config, "inputmapstacks", "Temperature", "/inmaps/TEMP"
        )  # timeseries for rainfall "/inmaps/TEMP"          # global radiation
        self.Inflow_mapstack = self.Dir + configget(
            self.config, "inputmapstacks", "Inflow", "/inmaps/IF"
        )  # timeseries for rainfall "/inmaps/IF" # in/outflow locations (abstractions)

        # Meteo and other forcing
        modelparameters.append(
            self.ParamType(
                name="Precipitation",
                stack=self.P_mapstack,
                type="timeseries",
                default=0.0,
                verbose=True,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="PotenEvap",
                stack=self.PET_mapstack,
                type="timeseries",
                default=0.0,
                verbose=True,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="Temperature",
                stack=self.TEMP_mapstack,
                type="timeseries",
                default=10.0,
                verbose=True,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="Inflow",
                stack=self.Inflow_mapstack,
                type="timeseries",
                default=0.0,
                verbose=False,
                lookupmaps=[],
            )
        )

        modelparameters.append(
            self.ParamType(
                name="IrrigationAreas",
                stack="staticmaps/wflow_irrigationareas.map",
                type="staticmap",
                default=0.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="IrrigationSurfaceIntakes",
                stack="staticmaps/wflow_irrisurfaceintakes.map",
                type="staticmap",
                default=0.0,
                verbose=False,
                lookupmaps=[],
            )
        )
        modelparameters.append(
            self.ParamType(
                name="IrrigationSurfaceReturn",
                stack="staticmaps/wflow_irrisurfacereturns.map",
                type="staticmap",
                default=0.0,
                verbose=False,
                lookupmaps=[],
            )
        )

        return modelparameters

    def initial(self):
        """
        Initial part of the model, executed only once. Reads all static data from disk


        *Soil*

        :var M.tbl: M parameter in the SBM model. Governs the decay of Ksat with depth [-]
        :var thetaR.tbl: Residual water content [mm/mm]
        :var thetaS.tbl: Saturated water content (porosity) [mm/mm]
        :var KsatVer.tbl: Saturated conductivity [mm/d]
        :var PathFrac.tbl: Fraction of compacted area per grid cell [-]
        :var InfiltCapSoil.tbl: Soil infiltration capacity [m/d]
        :var InfiltCapPath.tbl: Infiltration capacity of the compacted areas [mm/d]
        :var SoilMinThickness.tbl: Minimum wdepth of the soil [mm]
        :var SoilWaterCapacity.tbl: Maximum depth of the soil [m]
        :var RootingDepth.tbl: Depth of the roots [mm]
        :var MaxLeakage.tbl: Maximum leakage out of the soil profile [mm/d]
        :var CapScale.tbl: Scaling factor in the Capilary rise calculations (100) [mm/d]
        :var RunoffGeneratingGWPerc: Fraction of the soil depth that contributes to subcell runoff (0.1) [-]
        :var rootdistpar.tbl: Determine how roots are linked to water table. The number
            should be negative. A more negative  number means that all roots are wet if the water
            table is above the lowest part of the roots.
            A less negative number smooths this. [mm] (default = -80000)

        *Canopy*

        :var CanopyGapFraction.tbl: Fraction of precipitation that does not hit the canopy directly [-]
        :var MaxCanopyStorage.tbl: Canopy interception storage capacity [mm]
        :var EoverR.tbl: Ratio of average wet canopy evaporation rate over rainfall rate [-]

        *Surface water*

        :var N.tbl: Manning's N parameter
        :var N_river.tbl: Manning's N parameter for cells marked as river


        *Snow and frozen soil modelling parameters*

        :var cf_soil.tbl: Soil infiltration reduction factor when soil is frozen [-] (< 1.0)
        :var TTI.tbl: critical temperature for snowmelt and refreezing  (1.000) [oC]
        :var TT.tbl: defines interval in which precipitation falls as rainfall and snowfall (-1.41934) [oC]
        :var Cfmax.tbl: meltconstant in temperature-index ( 3.75653) [-]
        :var WHC.tbl: fraction of Snowvolume that can store water (0.1) [-]
        :var w_soil.tbl: Soil temperature smooth factor. Given for daily timesteps. (0.1125) [-] Wigmosta, M. S., L. J. Lane, J. D. Tagestad, and A. M. Coleman (2009).

        """
        global statistics
        global multpars
        global updateCols

        self.thestep = pcr.scalar(0)
        self.basetimestep = 86400
        self.SSSF = False
        pcr.setglobaloption("unittrue")

        self.logger.info("running for " + str(self.nrTimeSteps()) + " timesteps")

        # Set and get defaults from ConfigFile here ###################################
        self.Tslice = int(configget(self.config, "model", "Tslice", "1"))
        self.reinit = int(configget(self.config, "run", "reinit", "0"))
        self.OverWriteInit = int(configget(self.config, "model", "OverWriteInit", "0"))
        self.updating = int(configget(self.config, "model", "updating", "0"))
        self.updateFile = configget(self.config, "model", "updateFile", "no_set")
        self.LateralMethod = int(configget(self.config, "model", "lateralmethod", "1"))
        self.maxitsupply = int(configget(self.config, "model", "maxitsupply", "5"))
        self.UST = int(configget(self.config, "model", "Whole_UST_Avail", "0"))

        if self.LateralMethod == 1:
            self.logger.info(
                "Applying the original topog_sbm lateral transfer formulation"
            )
        elif self.LateralMethod == 2:
            self.logger.warning("Using alternate wflow lateral transfer formulation")

        self.sCatch = int(configget(self.config, "model", "sCatch", "0"))
        self.intbl = configget(self.config, "model", "intbl", "intbl")

        self.modelSnow = int(configget(self.config, "model", "ModelSnow", "1"))
        sizeinmetres = int(configget(self.config, "layout", "sizeinmetres", "0"))
        alf = float(configget(self.config, "model", "Alpha", "60"))
        # TODO: make this into a list for all gauges or a map
        Qmax = float(configget(self.config, "model", "AnnualDischarge", "300"))
        self.UpdMaxDist = float(configget(self.config, "model", "UpdMaxDist", "100"))

        self.MaxUpdMult = float(configget(self.config, "model", "MaxUpdMult", "1.3"))
        self.MinUpdMult = float(configget(self.config, "model", "MinUpdMult", "0.7"))
        self.UpFrac = float(configget(self.config, "model", "UpFrac", "0.8"))

        # self.ExternalQbase=int(configget(self.config,'model','ExternalQbase','0'))
        self.waterdem = int(configget(self.config, "model", "waterdem", "0"))
        WIMaxScale = float(configget(self.config, "model", "WIMaxScale", "0.8"))
        self.reInfilt = int(configget(self.config, "model", "reInfilt", "0"))
        self.MassWasting = int(configget(self.config, "model", "MassWasting", "0"))

        # static maps to use (normally default)
        wflow_subcatch = configget(
            self.config, "model", "wflow_subcatch", "staticmaps/wflow_subcatch.map"
        )
        wflow_dem = configget(
            self.config, "model", "wflow_dem", "staticmaps/wflow_dem.map"
        )
        wflow_ldd = configget(
            self.config, "model", "wflow_ldd", "staticmaps/wflow_ldd.map"
        )
        wflow_river = configget(
            self.config, "model", "wflow_river", "staticmaps/wflow_river.map"
        )
        wflow_riverlength = configget(
            self.config,
            "model",
            "wflow_riverlength",
            "staticmaps/wflow_riverlength.map",
        )
        wflow_riverlength_fact = configget(
            self.config,
            "model",
            "wflow_riverlength_fact",
            "staticmaps/wflow_riverlength_fact.map",
        )
        wflow_landuse = configget(
            self.config, "model", "wflow_landuse", "staticmaps/wflow_landuse.map"
        )
        wflow_soil = configget(
            self.config, "model", "wflow_soil", "staticmaps/wflow_soil.map"
        )
        wflow_gauges = configget(
            self.config, "model", "wflow_gauges", "staticmaps/wflow_gauges.map"
        )
        wflow_inflow = configget(
            self.config, "model", "wflow_inflow", "staticmaps/wflow_inflow.map"
        )
        wflow_riverwidth = configget(
            self.config, "model", "wflow_riverwidth", "staticmaps/wflow_riverwidth.map"
        )

        # 2: Input base maps ########################################################
        subcatch = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_subcatch), 0.0, fail=True)
        )  # Determines the area of calculations (all cells > 0)
        subcatch = pcr.ifthen(subcatch > 0, subcatch)

        self.Altitude = self.wf_readmap(
            os.path.join(self.Dir, wflow_dem), 0.0, fail=True
        )  # * pcr.scalar(pcr.defined(subcatch)) # DEM
        self.TopoLdd = pcr.ldd(
            self.wf_readmap(os.path.join(self.Dir, wflow_ldd), 0.0, fail=True)
        )  # Local
        self.TopoId = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_subcatch), 0.0, fail=True)
        )  # area map
        self.River = pcr.cover(
            pcr.boolean(
                self.wf_readmap(os.path.join(self.Dir, wflow_river), 0.0, fail=True)
            ),
            0,
        )

        self.RiverLength = pcr.cover(
            self.wf_readmap(os.path.join(self.Dir, wflow_riverlength), 0.0), 0.0
        )
        # Factor to multiply riverlength with (defaults to 1.0)
        self.RiverLengthFac = self.wf_readmap(
            os.path.join(self.Dir, wflow_riverlength_fact), 1.0
        )

        # read landuse and soilmap and make sure there are no missing points related to the
        # subcatchment map. Currently sets the lu and soil type  type to 1
        self.LandUse = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_landuse), 0.0, fail=True)
        )
        self.LandUse = pcr.cover(self.LandUse, pcr.ordinal(subcatch > 0))
        self.Soil = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_soil), 0.0, fail=True)
        )
        self.Soil = pcr.cover(self.Soil, pcr.ordinal(subcatch > 0))
        self.OutputLoc = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_gauges), 0.0, fail=True)
        )  # location of output gauge(s)
        self.InflowLoc = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_inflow), 0.0)
        )  # location abstractions/inflows.
        self.RiverWidth = self.wf_readmap(os.path.join(self.Dir, wflow_riverwidth), 0.0)
        # Experimental
        self.RunoffGenSigmaFunction = int(
            configget(self.config, "model", "RunoffGenSigmaFunction", "0")
        )
        self.SubCatchFlowOnly = int(
            configget(self.config, "model", "SubCatchFlowOnly", "0")
        )
        self.OutputId = pcr.ordinal(
            self.wf_readmap(os.path.join(self.Dir, wflow_subcatch), 0.0, fail=True)
        )  # location of subcatchment
        # Temperature correction poer cell to add

        self.TempCor = self.wf_readmap(
            self.Dir
            + configget(
                self.config,
                "model",
                "TemperatureCorrectionMap",
                "staticmaps/wflow_tempcor.map",
            ),
            0.0,
        )

        self.ZeroMap = 0.0 * pcr.scalar(subcatch)  # map with only zero's

        # Set static initial values here #########################################
        self.pi = 3.1416
        self.e = 2.7183
        self.SScale = 100.0
        self.Latitude = pcr.ycoordinate(pcr.boolean(self.Altitude))
        self.Longitude = pcr.xcoordinate(pcr.boolean(self.Altitude))

        # Read parameters NEW Method
        self.logger.info("Linking parameters to landuse, catchment and soil...")
        self.wf_updateparameters()

        self.RunoffGeneratingGWPerc = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/RunoffGeneratingGWPerc.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.1,
        )

        if hasattr(self, "LAI"):
            # Sl must also be defined
            if not hasattr(self, "Sl"):
                logging.error(
                    "Sl (specific leaf storage) not defined! Needed becausee LAI is defined."
                )
                logging.error("Please add it to the modelparameters section. e.g.:")
                logging.error(
                    "Sl=inmaps/clim/LCtoSpecificLeafStorage.tbl,tbl,0.5,1,inmaps/clim/LC.map"
                )
            if not hasattr(self, "Kext"):
                logging.error(
                    "Kext (canopy extinction coefficient) not defined! Needed becausee LAI is defined."
                )
                logging.error("Please add it to the modelparameters section. e.g.:")
                logging.error(
                    "Kext=inmaps/clim/LCtoSpecificLeafStorage.tbl,tbl,0.5,1,inmaps/clim/LC.map"
                )
            if not hasattr(self, "Swood"):
                logging.error(
                    "Swood wood (branches, trunks) canopy storage not defined! Needed becausee LAI is defined."
                )
                logging.error("Please add it to the modelparameters section. e.g.:")
                logging.error(
                    "Swood=inmaps/clim/LCtoBranchTrunkStorage.tbl,tbl,0.5,1,inmaps/clim/LC.map"
                )

            self.Cmax = self.Sl * self.LAI + self.Swood
            self.CanopyGapFraction = pcr.exp(-self.Kext * self.LAI)
            # TODO: Add MAXLAI and CWf lookup
        else:
            self.Cmax = self.readtblDefault(
                self.Dir + "/" + self.intbl + "/MaxCanopyStorage.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                1.0,
            )
            self.CanopyGapFraction = self.readtblDefault(
                self.Dir + "/" + self.intbl + "/CanopyGapFraction.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                0.1,
            )
            self.EoverR = self.readtblDefault(
                self.Dir + "/" + self.intbl + "/EoverR.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                0.1,
            )

        if not hasattr(self, "DemandReturnFlowFraction"):
            self.DemandReturnFlowFraction = self.ZeroMap

        self.RootingDepth = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/RootingDepth.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            750.0,
        )  # rooting depth
        #: rootdistpar determien how roots are linked to water table.

        self.rootdistpar = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/rootdistpar.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            -8000,
        )  # rrootdistpar

        # Soil parameters
        # infiltration capacity if the soil [mm/day]
        self.InfiltCapSoil = (
            self.readtblDefault(
                self.Dir + "/" + self.intbl + "/InfiltCapSoil.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                100.0,
            )
            * self.timestepsecs
            / self.basetimestep
        )
        self.CapScale = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/CapScale.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            100.0,
        )  #

        # infiltration capacity of the compacted
        self.InfiltCapPath = (
            self.readtblDefault(
                self.Dir + "/" + self.intbl + "/InfiltCapPath.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                10.0,
            )
            * self.timestepsecs
            / self.basetimestep
        )
        self.MaxLeakage = (
            self.readtblDefault(
                self.Dir + "/" + self.intbl + "/MaxLeakage.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                0.0,
            )
            * self.timestepsecs
            / self.basetimestep
        )
        self.MaxPercolation = (
            self.readtblDefault(
                self.Dir + "/" + self.intbl + "/MaxPercolation.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                0.0,
            )
            * self.timestepsecs
            / self.basetimestep
        )

        # areas (paths) in [mm/day]
        # Fraction area with compacted soil (Paths etc.)
        self.PathFrac = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/PathFrac.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.01,
        )
        # thickness of the soil
        self.SoilThickness = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/SoilThickness.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            2000.0,
        )
        self.thetaR = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/thetaR.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.01,
        )
        self.thetaS = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/thetaS.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.6,
        )
        # minimum thickness of soild
        self.SoilMinThickness = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/SoilMinThickness.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            500.0,
        )

        # FirstZoneKsatVer = $2\inmaps\FirstZoneKsatVer.map
        self.KsatVer = (
            self.readtblDefault(
                self.Dir + "/" + self.intbl + "/KsatVer.tbl",
                self.LandUse,
                subcatch,
                self.Soil,
                3000.0,
            )
            * self.timestepsecs
            / self.basetimestep
        )
        self.MporeFrac = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/MporeFrac.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.0,
        )

        self.KsatHorFrac = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/KsatHorFrac.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )

        if hasattr(self, "ReserVoirLocs"):
            # Check if we have reservoirs
            tt = pcr.pcr2numpy(self.ReserVoirLocs, 0.0)
            self.nrres = tt.max()
            if self.nrres > 0:
                self.logger.info("A total of " + str(self.nrres) + " reservoirs found.")
                self.ReserVoirDownstreamLocs = pcr.downstream(
                    self.TopoLdd, self.ReserVoirLocs
                )
                self.TopoLddOrg = self.TopoLdd
                self.TopoLdd = pcr.lddrepair(
                    pcr.cover(
                        pcr.ifthen(pcr.boolean(self.ReserVoirLocs), pcr.ldd(5)),
                        self.TopoLdd,
                    )
                )
        else:
            self.nrres = 0

        # Check if we have irrigation areas
        tt = pcr.pcr2numpy(self.IrrigationAreas, 0.0)
        self.nrirri = tt.max()

        self.Beta = pcr.scalar(0.6)  # For sheetflow

        self.M = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/M.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            300.0,
        )  # Decay parameter in Topog_sbm
        self.N = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/N.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.072,
        )  # Manning overland flow
        self.NRiver = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/N_River.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.036,
        )  # Manning river
        self.WaterFrac = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/WaterFrac.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            0.0,
        )  # Fraction Open water
        self.et_RefToPot = self.readtblDefault(
            self.Dir + "/" + self.intbl + "/et_reftopot.tbl",
            self.LandUse,
            subcatch,
            self.Soil,
            1.0,
        )  # Fraction Open water
        if self.modelSnow:
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
            self.TTM = self.readtblDefault(
                self.Dir + "/" + self.intbl + "/TTM.tbl",
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
            # Wigmosta, M. S., L. J. Lane, J. D. Tagestad, and A. M. Coleman (2009).
            self.w_soil = (
                self.readtblDefault(
                    self.Dir + "/" + self.intbl + "/w_soil.tbl",
                    self.LandUse,
                    subcatch,
                    self.Soil,
                    0.9 * 3.0 / 24.0,
                )
                * self.timestepsecs
                / self.basetimestep
            )

            self.cf_soil = pcr.min(
                0.99,
                self.readtblDefault(
                    self.Dir + "/" + self.intbl + "/cf_soil.tbl",
                    self.LandUse,
                    subcatch,
                    self.Soil,
                    0.038,
                ),
            )  # Ksat reduction factor fro frozen soi
            # We are modelling gletchers

        # Determine real slope and cell length

        self.xl, self.yl, self.reallength = pcrut.detRealCellLength(
            self.ZeroMap, sizeinmetres
        )
        self.Slope = pcr.slope(self.Altitude)
        # self.Slope=pcr.ifthen(pcr.boolean(self.TopoId),pcr.max(0.001,self.Slope*celllength()/self.reallength))
        self.Slope = pcr.max(0.00001, self.Slope * pcr.celllength() / self.reallength)
        Terrain_angle = pcr.scalar(pcr.atan(self.Slope))

        self.wf_multparameters()

        self.N = pcr.ifthenelse(self.River, self.NRiver, self.N)

        # Determine river width from DEM, upstream area and yearly average discharge
        # Scale yearly average Q at outlet with upstream are to get Q over whole catchment
        # Alf ranges from 5 to > 60. 5 for hardrock. large values for sediments
        # "Noah J. Finnegan et al 2005 Controls on the channel width of rivers:
        # Implications for modeling fluvial incision of bedrock"

        upstr = pcr.catchmenttotal(1, self.TopoLdd)
        Qscale = upstr / pcr.mapmaximum(upstr) * Qmax
        W = (
            (alf * (alf + 2.0) ** (0.6666666667)) ** (0.375)
            * Qscale ** (0.375)
            * (pcr.max(0.0001, pcr.windowaverage(self.Slope, pcr.celllength() * 4.0)))
            ** (-0.1875)
            * self.N ** (0.375)
        )
        # Use supplied riverwidth if possible, else calulate
        self.RiverWidth = pcr.ifthenelse(self.RiverWidth <= 0.0, W, self.RiverWidth)

        # Only allow reinfiltration in river cells by default

        if not hasattr(self, "MaxReinfilt"):
            self.MaxReinfilt = pcr.ifthenelse(
                self.River, self.ZeroMap + 999.0, self.ZeroMap
            )

        # soil thickness based on topographical index (see Environmental modelling: finding simplicity in complexity)
        # 1: calculate wetness index
        # 2: Scale the capacity (now actually a max capacity) based on the index, also apply a minmum capacity
        WI = pcr.ln(
            pcr.accuflux(self.TopoLdd, 1) / self.Slope
        )  # Topographical wetnesss. Scale WI by zone/subcatchment assuming these ara also geological units
        WIMax = pcr.areamaximum(WI, self.TopoId) * WIMaxScale
        self.SoilThickness = pcr.max(
            pcr.min(self.SoilThickness, (WI / WIMax) * self.SoilThickness),
            self.SoilMinThickness,
        )

        self.SoilWaterCapacity = self.SoilThickness * (self.thetaS - self.thetaR)

        # limit roots to top 99% of first zone
        self.RootingDepth = pcr.min(self.SoilThickness * 0.99, self.RootingDepth)

        # subgrid runoff generation, determine CC (sharpness of S-Curve) for upper
        # en lower part and take average
        self.DemMax = pcr.readmap(self.Dir + "/staticmaps/wflow_demmax")
        self.DrainageBase = pcr.readmap(self.Dir + "/staticmaps/wflow_demmin")
        self.CClow = pcr.min(
            100.0, -ln(1.0 / 0.1 - 1) / pcr.min(-0.1, self.DrainageBase - self.Altitude)
        )
        self.CCup = pcr.min(
            100.0, -ln(1.0 / 0.1 - 1) / pcr.min(-0.1, self.Altitude - self.DemMax)
        )
        self.CC = (self.CClow + self.CCup) * 0.5

        # Which columns/gauges to use/ignore in updating
        self.UpdateMap = self.ZeroMap

        if self.updating:
            _tmp = pcr.pcr2numpy(self.OutputLoc, 0.0)
            gaugear = _tmp
            touse = numpy.zeros(gaugear.shape, dtype="int")

            for thecol in updateCols:
                idx = (gaugear == thecol).nonzero()
                touse[idx] = thecol

            self.UpdateMap = pcr.numpy2pcr(pcr.Nominal, touse, 0.0)
            # Calculate distance to updating points (upstream) annd use to scale the correction
            # ldddist returns zero for cell at the gauges so add 1.0 tp result
            self.DistToUpdPt = pcr.cover(
                pcr.min(
                    ldddist(self.TopoLdd, pcr.boolean(pcr.cover(self.UpdateMap, 0)), 1)
                    * self.reallength
                    / pcr.celllength(),
                    self.UpdMaxDist,
                ),
                self.UpdMaxDist,
            )

        # Initializing of variables
        self.logger.info("Initializing of model variables..")
        self.TopoLdd = pcr.lddmask(self.TopoLdd, pcr.boolean(self.TopoId))
        catchmentcells = pcr.maptotal(pcr.scalar(self.TopoId))

        # Limit lateral flow per subcatchment (make pits at all subcatch boundaries)
        # This is very handy for Ribasim etc...
        if self.SubCatchFlowOnly > 0:
            self.logger.info("Creating subcatchment-only drainage network (ldd)")
            ds = pcr.downstream(self.TopoLdd, self.TopoId)
            usid = pcr.ifthenelse(ds != self.TopoId, self.TopoId, 0)
            self.TopoLdd = pcr.lddrepair(
                pcr.ifthenelse(pcr.boolean(usid), pcr.ldd(5), self.TopoLdd)
            )

        # Used to seperate output per LandUse/management classes
        OutZones = self.LandUse

        self.QMMConv = self.timestepsecs / (
            self.reallength * self.reallength * 0.001
        )  # m3/s --> actial mm of water over the cell
        # self.QMMConvUp = 1000.0 * self.timestepsecs / ( pcr.catchmenttotal(pcr.cover(1.0), self.TopoLdd) * self.reallength * self.reallength)  #m3/s --> mm over upstreams
        temp = (
            pcr.catchmenttotal(pcr.cover(1.0), self.TopoLdd)
            * self.reallength
            * 0.001
            * 0.001
            * self.reallength
        )
        self.QMMConvUp = pcr.cover(self.timestepsecs * 0.001) / temp
        self.ToCubic = (
            self.reallength * self.reallength * 0.001
        ) / self.timestepsecs  # m3/s
        self.KinWaveVolume = self.ZeroMap
        self.OldKinWaveVolume = self.ZeroMap
        self.sumprecip = self.ZeroMap  # accumulated rainfall for water balance
        self.sumevap = self.ZeroMap  # accumulated evaporation for water balance
        self.sumrunoff = self.ZeroMap  # accumulated runoff for water balance
        self.sumint = self.ZeroMap  # accumulated interception for water balance
        self.sumleakage = self.ZeroMap
        self.CumReinfilt = self.ZeroMap
        self.sumoutflow = self.ZeroMap
        self.sumsnowmelt = self.ZeroMap
        self.CumRad = self.ZeroMap
        self.SnowMelt = self.ZeroMap
        self.CumPrec = self.ZeroMap
        self.CumInwaterMM = self.ZeroMap
        self.CumInfiltExcess = self.ZeroMap
        self.CumExfiltWater = self.ZeroMap
        self.CumSurfaceWater = self.ZeroMap
        self.watbal = self.ZeroMap
        self.CumEvap = self.ZeroMap
        self.CumPotenEvap = self.ZeroMap
        self.CumPotenTrans = self.ZeroMap
        self.CumInt = self.ZeroMap
        self.CumRad = self.ZeroMap
        self.CumLeakage = self.ZeroMap
        self.CumPrecPol = self.ZeroMap
        self.SatWaterFlux = self.ZeroMap
        self.SumCellWatBal = self.ZeroMap
        self.PathInfiltExceeded = self.ZeroMap
        self.SoilInfiltExceeded = self.ZeroMap
        self.CumOutFlow = self.ZeroMap
        self.CumCellInFlow = self.ZeroMap
        self.CumIF = self.ZeroMap
        self.CumActInfilt = self.ZeroMap
        self.IRSupplymm = self.ZeroMap
        self.Aspect = pcr.scalar(pcr.aspect(self.Altitude))  # aspect [deg]
        self.Aspect = pcr.ifthenelse(self.Aspect <= 0.0, pcr.scalar(0.001), self.Aspect)
        # On Flat areas the Aspect function fails, fill in with average...
        self.Aspect = pcr.ifthenelse(
            pcr.defined(self.Aspect),
            self.Aspect,
            pcr.areaaverage(self.Aspect, self.TopoId),
        )
        # Set DCL to riverlength if that is longer that the basic length calculated from grid
        drainlength = detdrainlength(self.TopoLdd, self.xl, self.yl)

        # Multiply with Factor (taken from upscaling operation, defaults to 1.0 if no map is supplied
        self.DCL = drainlength * pcr.max(1.0, self.RiverLengthFac)

        self.DCL = pcr.max(self.DCL, self.RiverLength)  # m

        # water depth (m)
        # set width for kinematic wave to cell width for all cells
        self.Bw = detdrainwidth(self.TopoLdd, self.xl, self.yl)
        # However, in the main river we have real flow so set the width to the
        # width of the river

        self.Bw = pcr.ifthenelse(self.River, self.RiverWidth, self.Bw)

        # Add rivers to the WaterFrac, but check with waterfrac map and correct
        self.RiverFrac = pcr.min(
            1.0,
            pcr.ifthenelse(
                self.River, (self.RiverWidth * self.DCL) / (self.xl * self.yl), 0
            ),
        )
        self.WaterFrac = pcr.min(1.0, self.WaterFrac + self.RiverFrac)

        # term for Alpha
        # Correct slope for extra length of the river in a gridcel
        riverslopecor = drainlength / self.DCL
        # pcr.report(riverslopecor,"cor.map")
        # pcr.report(self.Slope * riverslopecor,"slope.map")
        self.AlpTerm = pow((self.N / (pcr.sqrt(self.Slope * riverslopecor))), self.Beta)
        # power for Alpha
        self.AlpPow = (2.0 / 3.0) * self.Beta
        # initial approximation for Alpha
        # calculate catchmentsize
        self.upsize = pcr.catchmenttotal(self.xl * self.yl, self.TopoLdd)
        self.csize = pcr.areamaximum(self.upsize, self.TopoId)
        # Save some summary maps
        self.logger.info("Saving summary maps...")

        if self.updating:
            pcr.report(
                self.DistToUpdPt,
                self.Dir + "/" + self.runId + "/outsum/DistToUpdPt.map",
            )

        # self.IF = self.ZeroMap
        self.logger.info("End of initial section")

    def default_summarymaps(self):
        """
          Returns a list of default summary-maps at the end of a run.
          This is model specific. You can also add them to the [summary]section of the ini file but stuff
          you think is crucial to the model should be listed here
          """
        lst = [
            "self.RiverWidth",
            "self.Cmax",
            "self.csize",
            "self.upsize",
            "self.EoverR",
            "self.RootingDepth",
            "self.CanopyGapFraction",
            "self.InfiltCapSoil",
            "self.InfiltCapPath",
            "self.PathFrac",
            "self.thetaR",
            "self.thetaS",
            "self.SoilMinThickness",
            "self.KsatVer",
            "self.M",
            "self.SoilWaterCapacity",
            "self.et_RefToPot",
            "self.Slope",
            "self.CC",
            "self.N",
            "self.RiverFrac",
            "self.WaterFrac",
            "self.xl",
            "self.yl",
            "self.reallength",
            "self.DCL",
            "self.Bw",
            "self.PathInfiltExceeded",
            "self.SoilInfiltExceeded",
        ]

        return lst

    def resume(self):

        if self.reinit == 1:
            self.logger.info("Setting initial conditions to default")
            self.SatWaterDepth = self.SoilWaterCapacity * 0.85
            self.UStoreDepth = self.SoilWaterCapacity * 0.0
            self.WaterLevel = self.ZeroMap
            self.SurfaceRunoff = self.ZeroMap
            self.Snow = self.ZeroMap
            self.SnowWater = self.ZeroMap
            self.TSoil = self.ZeroMap + 10.0
            self.CanopyStorage = self.ZeroMap
            if hasattr(self, "ReserVoirLocs"):
                self.ReservoirVolume = self.ResMaxVolume * self.ResTargetFullFrac
            if hasattr(self, "GlacierFrac"):
                self.GlacierStore = self.wf_readmap(
                    os.path.join(self.Dir, "staticmaps", "GlacierStore.map"),
                    55.0 * 1000,
                )
        else:
            self.logger.info("Setting initial conditions from state files")
            self.wf_resume(os.path.join(self.Dir, "instate"))

        P = self.Bw + (2.0 * self.WaterLevel)
        self.Alpha = self.AlpTerm * pow(P, self.AlpPow)
        self.OldSurfaceRunoff = self.SurfaceRunoff

        self.SurfaceRunoffMM = self.SurfaceRunoff * self.QMMConv
        # Determine initial kinematic wave volume
        self.KinWaveVolume = self.WaterLevel * self.Bw * self.DCL
        self.OldKinWaveVolume = self.KinWaveVolume

        self.QCatchmentMM = self.SurfaceRunoff * self.QMMConvUp
        self.InitialStorage = self.SatWaterDepth + self.UStoreDepth + self.CanopyStorage
        self.CellStorage = self.SatWaterDepth + self.UStoreDepth

        # Determine actual water depth
        self.zi = pcr.max(
            0.0, self.SoilThickness - self.SatWaterDepth / (self.thetaS - self.thetaR)
        )
        # TOPOG_SBM type soil stuff
        self.f = (self.thetaS - self.thetaR) / self.M
        # NOTE:: This line used to be in the initial section. As a result
        # NOTE:: This line rused to be in the initial section. As a result
        # simulations will now be different as it used to be before
        # the rescaling of the SoilThickness
        self.GWScale = (
            (self.DemMax - self.DrainageBase)
            / self.SoilThickness
            / self.RunoffGeneratingGWPerc
        )

    def dynamic(self):
        """
        Stuf that is done for each timestep of the model

        Below a list of variables that can be save to disk as maps or as
        timeseries (see ini file for syntax):

        Dynamic variables
        ~~~~~~~~~~~~~~~~~

        All these can be saved per timestep if needed (see the config file [outputmaps] section).

        :var self.Precipitation: Gross precipitation [mm]
        :var self.Temperature: Air temperature [oC]
        :var self.PotenEvap: Potential evapotranspiration [mm]
        :var self.PotTransSoil: Potential Transpiration/Openwater and soil evap (after subtracting Interception from PotenEvap) [mm]
        :var self.Transpiration: plant/tree transpiration [mm]
        :var self.ActEvapOpenWater: actual open water evaporation [mm]
        :var self.soilevap: base soil evaporation [mm]
        :var self.Interception: Actual rainfall interception [mm]
        :var self.ActEvap: Actual evaporation (transpiration + Soil evap + open water evap) [mm]
        :var self.SurfaceRunoff: Surface runoff in the kinematic wave [m^3/s]
        :var self.SurfaceRunoffDyn: Surface runoff in the dyn-wave resrvoir [m^3/s]
        :var self.SurfaceRunoffCatchmentMM: Surface runoff in the dyn-wave reservoir expressed in mm over the upstream (catchment) area
        :var self.WaterLevelDyn: Water level in the dyn-wave resrvoir [m^]
        :var self.ActEvap: Actual EvapoTranspiration [mm] (minus interception losses)
        :var self.ExcessWater: Water that cannot infiltrate due to saturated soil [mm]
        :var self.InfiltExcess: Infiltration excess water [mm]
        :var self.WaterLevel: Water level in the kinematic wave [m] (above the bottom)
        :var self.ActInfilt: Actual infiltration into the unsaturated zone [mm]
        :var self.CanopyStorage: actual canopystorage (only for subdaily timesteps) [mm]
        :var self.SatWaterDepth: Amount of water in the saturated store [mm]
        :var self.UStoreDepth: Amount of water in the unsaturated store [mm]
        :var self.zi: depth of the water table in mm below the surface [mm]
        :var self.Snow: Snow depth [mm]
        :var self.SnowWater: water content of the snow [mm]
        :var self.TSoil: Top soil temperature [oC]
        :var self.SatWaterDepth: amount of available water in the saturated part of the soil [mm]
        :var self.UStoreDepth: amount of available water in the unsaturated zone [mm]
        :var self.Transfer: downward flux from unsaturated to saturated zone [mm]
        :var self.CapFlux: capilary flux from saturated to unsaturated zone [mm]
        :var self.CanopyStorage: Amount of water on the Canopy [mm]
        :var self.RunoffCoeff: Runoff coefficient (Q/P) for each cell taking into account the whole upstream area [-]
        :var self.SurfaceWaterSupply: the negative Inflow (water demand) that could be met from the surfacewater [m^3/s]
        :var: self.QCatchmentMM: Catchment runoff in mm for the upstream area


        Static variables
        ~~~~~~~~~~~~~~~~

        :var self.Altitude: The altitude of each cell [m]
        :var self.Bw: Width of the river [m]
        :var self.River: booolean map indicating the presence of a river [-]
        :var self.DLC: length of the river within a cell [m]
        :var self.ToCubic: Mutiplier to convert mm to m^3/s for fluxes
        """
        # Read forcing data and dynamic parameters

        self.wf_updateparameters()
        self.Precipitation = pcr.max(0.0, self.Precipitation)

        # NB This may interfere with lintul link
        if hasattr(self, "LAI"):
            # Sl must also be defined
            ##TODO: add MAXLAI and CWf
            self.Cmax = self.Sl * self.LAI + self.Swood
            self.CanopyGapFraction = pcr.exp(-self.Kext * self.LAI)
            self.Ewet = (1 - pcr.exp(-self.Kext * self.LAI)) * self.PotenEvap
            self.EoverR = pcr.ifthenelse(
                self.Precipitation > 0.0,
                pcr.min(
                    0.25,
                    pcr.cover(self.Ewet / pcr.max(0.0001, self.Precipitation), 0.0),
                ),
                0.0,
            )
            if hasattr(self, "MAXLAI") and hasattr(self, "CWf"):
                # Adjust rootinggdept
                self.ActRootingDepth = self.CWf * (
                    self.RootingDepth * self.LAI / pcr.max(0.001, self.MAXLAI)
                ) + ((1 - self.CWf) * self.RootingDepth)
            else:
                self.ActRootingDepth = self.RootingDepth
        else:
            self.ActRootingDepth = self.RootingDepth

        # Apply forcing data corrections
        self.PotenEvap = self.PotenEvap * self.et_RefToPot
        if self.modelSnow:
            self.Temperature = self.Temperature + self.TempCor

        self.wf_multparameters()

        self.OrgStorage = self.UStoreDepth + self.SatWaterDepth
        self.OldCanopyStorage = self.CanopyStorage
        self.PotEvap = self.PotenEvap  #

        if self.modelSnow:
            self.TSoil = self.TSoil + self.w_soil * (self.Temperature - self.TSoil)
            # return Snow,SnowWater,SnowMelt,RainFall
            self.Snow, self.SnowWater, self.SnowMelt, self.PrecipitationPlusMelt, self.SnowFall = SnowPackHBV(
                self.Snow,
                self.SnowWater,
                self.Precipitation,
                self.Temperature,
                self.TTI,
                self.TT,
                self.TTM,
                self.Cfmax,
                self.WHC,
            )
            MaxSnowPack = 10000.0
            if self.MassWasting:
                # Masswasting of dry snow
                # 5.67 = tan 80 graden
                SnowFluxFrac = pcr.min(0.5, self.Slope / 5.67) * pcr.min(
                    1.0, self.Snow / MaxSnowPack
                )
                MaxFlux = SnowFluxFrac * self.Snow
                self.Snow = accucapacitystate(self.TopoLdd, self.Snow, MaxFlux)
            else:
                SnowFluxFrac = self.ZeroMap
                MaxFlux = self.ZeroMap

            self.SnowCover = pcr.ifthenelse(self.Snow > 0, pcr.scalar(1), pcr.scalar(0))
            self.NrCell = pcr.areatotal(self.SnowCover, self.TopoId)

            if hasattr(self, "GlacierFrac"):
                """
                Run Glacier module and add the snowpack on-top of it.
                Snow becomes ice when pressure is about 830 k/m^2, e.g 8300 mm
                If below that a max amount of 2mm/day can be converted to glacier-ice
                """
                # TODO: document glacier module
                self.snowdist = sCurve(self.Snow, a=8300.0, c=0.06)
                self.Snow2Glacier = pcr.ifthenelse(
                    self.Snow > 8300, self.snowdist * (self.Snow - 8300), self.ZeroMap
                )

                self.Snow2Glacier = pcr.ifthenelse(
                    self.GlacierFrac > 0.0, self.Snow2Glacier, self.ZeroMap
                )
                # Max conversion to 8mm/day
                self.Snow2Glacier = (
                    pcr.min(self.Snow2Glacier, 8.0)
                    * self.timestepsecs
                    / self.basetimestep
                )

                self.Snow = self.Snow - (self.Snow2Glacier * self.GlacierFrac)

                self.GlacierStore, self.GlacierMelt = GlacierMelt(
                    self.GlacierStore + self.Snow2Glacier,
                    self.Snow,
                    self.Temperature,
                    self.G_TT,
                    self.G_Cfmax,
                )
                # Convert to mm per grid cell and add to snowmelt
                self.GlacierMelt = self.GlacierMelt * self.GlacierFrac
                self.PrecipitationPlusMelt = (
                    self.PrecipitationPlusMelt + self.GlacierMelt
                )
        else:
            self.PrecipitationPlusMelt = self.Precipitation

        ##########################################################################
        # Interception according to a modified Gash model
        ##########################################################################
        if self.timestepsecs >= (23 * 3600):
            self.ThroughFall, self.Interception, self.StemFlow, self.CanopyStorage = rainfall_interception_gash(
                self.Cmax,
                self.EoverR,
                self.CanopyGapFraction,
                self.PrecipitationPlusMelt,
                self.CanopyStorage,
                maxevap=self.PotEvap,
            )

            self.PotTransSoil = pcr.cover(
                pcr.max(0.0, self.PotEvap - self.Interception), 0.0
            )  # now in mm
        else:
            NetInterception, self.ThroughFall, self.StemFlow, LeftOver, Interception, self.CanopyStorage = rainfall_interception_modrut(
                self.PrecipitationPlusMelt,
                self.PotEvap,
                self.CanopyStorage,
                self.CanopyGapFraction,
                self.Cmax,
            )
            self.PotTransSoil = pcr.cover(pcr.max(0.0, LeftOver), 0.0)  # now in mm
            self.Interception = NetInterception

        # Start with the soil calculations
        # --------------------------------
        # Code to be able to force zi from the outside
        #
        self.SatWaterDepth = (self.thetaS - self.thetaR) * (
            self.SoilThickness - self.zi
        )

        self.AvailableForInfiltration = (
            self.ThroughFall + self.StemFlow + self.IRSupplymm
        )

        UStoreCapacity = self.SoilWaterCapacity - self.SatWaterDepth - self.UStoreDepth

        # Runoff from water bodies and river network
        self.RunoffOpenWater = (
            pcr.min(1.0, self.RiverFrac + self.WaterFrac)
            * self.AvailableForInfiltration
        )
        # self.RunoffOpenWater = self.ZeroMap
        self.AvailableForInfiltration = (
            self.AvailableForInfiltration - self.RunoffOpenWater
        )

        if self.RunoffGenSigmaFunction:
            self.AbsoluteGW = self.DemMax - (self.zi * self.GWScale)
            # Determine saturated fraction of cell
            self.SubCellFrac = sCurve(self.AbsoluteGW, c=self.CC, a=self.Altitude + 1.0)
            # Make sure total of SubCellFRac + WaterFRac + RiverFrac <=1 to avoid double counting
            Frac_correction = pcr.ifthenelse(
                (self.SubCellFrac + self.RiverFrac + self.WaterFrac) > 1.0,
                self.SubCellFrac + self.RiverFrac + self.WaterFrac - 1.0,
                0.0,
            )
            self.SubCellRunoff = (
                self.SubCellFrac - Frac_correction
            ) * self.AvailableForInfiltration
            self.SubCellGWRunoff = pcr.min(
                self.SubCellFrac * self.SatWaterDepth,
                pcr.max(
                    0.0,
                    self.SubCellFrac
                    * self.Slope
                    * self.KsatVer
                    * self.KsatHorFrac
                    * pcr.exp(-self.f * self.zi),
                ),
            )
            self.SatWaterDepth = self.SatWaterDepth - self.SubCellGWRunoff
            self.AvailableForInfiltration = (
                self.AvailableForInfiltration - self.SubCellRunoff
            )
        else:
            self.AbsoluteGW = self.DemMax - (self.zi * self.GWScale)
            self.SubCellFrac = pcr.spatial(pcr.scalar(0.0))
            self.SubCellGWRunoff = pcr.spatial(pcr.scalar(0.0))
            self.SubCellRunoff = pcr.spatial(pcr.scalar(0.0))

        # First determine if the soil infiltration capacity can deal with the
        # amount of water
        # split between infiltration in undisturbed soil and compacted areas (paths)
        SoilInf = self.AvailableForInfiltration * (1 - self.PathFrac)
        PathInf = self.AvailableForInfiltration * self.PathFrac
        if self.modelSnow:
            # soilInfRedu = pcr.ifthenelse(self.TSoil < 0.0 , self.cf_soil, 1.0)
            bb = 1.0 / (1.0 - self.cf_soil)
            soilInfRedu = sCurve(self.TSoil, a=self.ZeroMap, b=bb, c=8.0) + self.cf_soil
        else:
            soilInfRedu = 1.0
        MaxInfiltSoil = pcr.min(self.InfiltCapSoil * soilInfRedu, SoilInf)

        self.SoilInfiltExceeded = self.SoilInfiltExceeded + pcr.scalar(
            self.InfiltCapSoil * soilInfRedu < SoilInf
        )
        InfiltSoil = pcr.min(MaxInfiltSoil, UStoreCapacity)
        self.UStoreDepth = self.UStoreDepth + InfiltSoil
        UStoreCapacity = UStoreCapacity - InfiltSoil
        self.AvailableForInfiltration = self.AvailableForInfiltration - InfiltSoil

        MaxInfiltPath = pcr.min(self.InfiltCapPath * soilInfRedu, PathInf)
        self.PathInfiltExceeded = self.PathInfiltExceeded + pcr.scalar(
            self.InfiltCapPath * soilInfRedu < PathInf
        )
        InfiltPath = pcr.min(MaxInfiltPath, UStoreCapacity)
        self.UStoreDepth = self.UStoreDepth + InfiltPath
        UStoreCapacity = UStoreCapacity - InfiltPath
        self.AvailableForInfiltration = self.AvailableForInfiltration - InfiltPath

        self.ActInfilt = InfiltPath + InfiltSoil

        self.InfiltExcess = pcr.ifthenelse(
            UStoreCapacity > 0.0, self.AvailableForInfiltration, 0.0
        )
        self.ExcessWater = self.AvailableForInfiltration  # Saturation overland flow
        self.CumInfiltExcess = self.CumInfiltExcess + self.InfiltExcess

        # Limit rootingdepth (if set externally)
        self.ActRootingDepth = pcr.min(self.SoilThickness * 0.99, self.ActRootingDepth)

        # Determine transpiration
        # Split between bare soil/open water and vegetation
        self.potsoilopenwaterevap = (1.0 - self.CanopyGapFraction) * self.PotTransSoil
        self.PotTrans = self.PotTransSoil - self.potsoilopenwaterevap

        self.SaturationDeficit = self.SoilWaterCapacity - self.SatWaterDepth
        # Linear reduction of soil moisture evaporation based on deficit

        # Determine Open Water EVAP. Later subtract this from water that
        # enters the Kinematic wave
        self.RestEvap = self.potsoilopenwaterevap
        self.ActEvapOpenWater = pcr.min(
            self.WaterLevel * 1000.0 * self.WaterFrac, self.WaterFrac * self.RestEvap
        )
        self.RestEvap = self.RestEvap - self.ActEvapOpenWater

        # Next the rest is used for soil evaporation
        self.soilevap = self.RestEvap * pcr.max(
            0.0, pcr.min(1.0, self.SaturationDeficit / self.SoilWaterCapacity)
        )
        self.soilevap = pcr.min(self.soilevap, self.UStoreDepth)
        self.UStoreDepth = self.UStoreDepth - self.soilevap

        # rest is used for transpiration

        self.PotTrans = self.PotTransSoil - self.soilevap - self.ActEvapOpenWater

        self.Transpiration, self.SatWaterDepth, self.UStoreDepth, self.ActEvapUStore = actEvap_SBM(
            self.ActRootingDepth,
            self.zi,
            self.UStoreDepth,
            self.SatWaterDepth,
            self.PotTrans,
            self.rootdistpar,
            ust=self.UST,
        )

        self.ActEvap = self.Transpiration + self.soilevap + self.ActEvapOpenWater
        # Run only if we have irrigation areas or an externally given demand, determine irrigation demand based on potrans and acttrans
        if self.nrirri > 0 or hasattr(self, "IrriDemandExternal"):
            if not hasattr(self, "IrriDemandExternal"):  # if not given
                self.IrriDemand, self.IrriDemandm3 = self.irrigationdemand(
                    self.PotTrans, self.Transpiration, self.IrrigationAreas
                )
                IRDemand = (
                    idtoid(
                        self.IrrigationAreas,
                        self.IrrigationSurfaceIntakes,
                        self.IrriDemandm3,
                    )
                    * -1.0
                )
            else:
                IRDemand = self.IrriDemandExternal
            # loop over irrigation areas and assign Q to linked river extraction points
            self.Inflow = pcr.cover(IRDemand, self.Inflow)

        ##########################################################################
        # Transfer of water from unsaturated to saturated store...################
        ##########################################################################
        # Determine saturation deficit. NB, as noted by Vertessy and Elsenbeer 1997
        # this deficit does NOT take into account the water in the unsaturated zone

        # Optional Macrco-Pore transfer
        self.MporeTransfer = self.ActInfilt * self.MporeFrac
        self.SatWaterDepth = self.SatWaterDepth + self.MporeTransfer
        self.UStoreDepth = self.UStoreDepth - self.MporeTransfer

        self.SaturationDeficit = self.SoilWaterCapacity - self.SatWaterDepth

        self.zi = pcr.max(
            0.0, self.SoilThickness - self.SatWaterDepth / (self.thetaS - self.thetaR)
        )  # Determine actual water depth
        Ksat = self.KsatVer * pcr.exp(-self.f * self.zi)

        self.DeepKsat = self.KsatVer * pcr.exp(-self.f * self.SoilThickness)

        # now the actual transfer to the saturated store..
        self.Transfer = pcr.min(
            self.UStoreDepth,
            pcr.ifthenelse(
                self.SaturationDeficit <= 0.00001,
                0.0,
                Ksat * self.UStoreDepth / (self.SaturationDeficit + 1),
            ),
        )

        MaxCapFlux = pcr.max(
            0.0, pcr.min(Ksat, self.ActEvapUStore, UStoreCapacity, self.SatWaterDepth)
        )
        # No capilary flux is roots are in water, max flux if very near to water, lower flux if distance is large
        CapFluxScale = pcr.ifthenelse(
            self.zi > self.ActRootingDepth,
            self.CapScale
            / (self.CapScale + self.zi - self.ActRootingDepth)
            * self.timestepsecs
            / self.basetimestep,
            0.0,
        )
        self.CapFlux = MaxCapFlux * CapFluxScale

        # Determine Ksat at base
        self.DeepTransfer = pcr.min(self.SatWaterDepth, self.DeepKsat)
        # ActLeakage = 0.0
        # Now add leakage. to deeper groundwater
        self.ActLeakage = pcr.cover(
            pcr.max(0.0, pcr.min(self.MaxLeakage, self.DeepTransfer)), 0
        )
        self.Percolation = pcr.cover(
            pcr.max(0.0, pcr.min(self.MaxPercolation, self.DeepTransfer)), 0
        )

        # self.ActLeakage = pcr.ifthenelse(self.Seepage > 0.0, -1.0 * self.Seepage, self.ActLeakage)
        self.SatWaterDepth = (
            self.SatWaterDepth
            + self.Transfer
            - self.CapFlux
            - self.ActLeakage
            - self.Percolation
        )
        self.UStoreDepth = self.UStoreDepth - self.Transfer + self.CapFlux

        # Determine % saturated taking into account subcell fraction
        self.Sat = pcr.max(
            self.SubCellFrac,
            pcr.scalar(self.SatWaterDepth >= (self.SoilWaterCapacity * 0.999)),
        )

        ##########################################################################
        # Horizontal (downstream) transport of water #############################
        ##########################################################################

        self.zi = pcr.max(
            0.0, self.SoilThickness - self.SatWaterDepth / (self.thetaS - self.thetaR)
        )  # Determine actual water depth

        # Re-Determine saturation deficit. NB, as noted by Vertessy and Elsenbeer 1997
        # this deficit does NOT take into account the water in the unsaturated zone
        self.SaturationDeficit = self.SoilWaterCapacity - self.SatWaterDepth

        # self.logger.debug("Waterdem set to Altitude....")
        self.WaterDem = self.Altitude - (self.zi * 0.001)
        self.waterSlope = pcr.max(
            0.000001, pcr.slope(self.WaterDem) * pcr.celllength() / self.reallength
        )
        if self.waterdem:
            self.waterLdd = pcr.lddcreate(self.WaterDem, 1e35, 1e35, 1e35, 1e35)

        # TODO: We should make a couple ot iterations here...
        if self.waterdem:
            Lateral = (
                self.KsatVer
                * self.KsatHorFrac
                * self.waterSlope
                * pcr.exp(-self.SaturationDeficit / self.M)
            )
            MaxHor = pcr.max(0.0, pcr.min(Lateral, self.SatWaterDepth))
            self.SatWaterFlux = accucapacityflux(
                self.waterLdd, self.SatWaterDepth, MaxHor
            )
            self.SatWaterDepth = accucapacitystate(
                self.waterLdd, self.SatWaterDepth, MaxHor
            )
        else:
            Lateral = (
                self.KsatVer
                * self.KsatHorFrac
                * self.waterSlope
                * pcr.exp(-self.SaturationDeficit / self.M)
            )
            MaxHor = pcr.max(0.0, pcr.min(Lateral, self.SatWaterDepth))
            # MaxHor = self.ZeroMap
            self.SatWaterFlux = accucapacityflux(
                self.TopoLdd, self.SatWaterDepth, MaxHor
            )
            self.SatWaterDepth = accucapacitystate(
                self.TopoLdd, self.SatWaterDepth, MaxHor
            )

        ##########################################################################
        # Determine returnflow from first zone          ##########################
        ##########################################################################
        self.ExfiltWaterFrac = sCurve(
            self.SatWaterDepth, a=self.SoilWaterCapacity, c=5.0
        )
        self.ExfiltWater = self.ExfiltWaterFrac * (
            self.SatWaterDepth - self.SoilWaterCapacity
        )
        # self.ExfiltWater=ifthenelse (self.SatWaterDepth - self.SoilWaterCapacity > 0 , self.SatWaterDepth - self.SoilWaterCapacity , 0.0)
        self.SatWaterDepth = self.SatWaterDepth - self.ExfiltWater

        # Re-determine UStoreCapacity
        self.zi = pcr.max(
            0.0, self.SoilThickness - self.SatWaterDepth / (self.thetaS - self.thetaR)
        )  # Determine actual water depth

        self.ExfiltFromUstore = pcr.ifthenelse(
            self.zi == 0.0,
            pcr.ifthenelse(self.UStoreDepth > 0.0, self.UStoreDepth, self.ZeroMap),
            self.ZeroMap,
        )

        self.ExfiltWater = self.ExfiltWater + self.ExfiltFromUstore
        self.UStoreDepth = self.UStoreDepth - self.ExfiltFromUstore
        UStoreCapacity = self.SoilWaterCapacity - self.SatWaterDepth - self.UStoreDepth

        Ksat = self.KsatVer * pcr.exp(-self.f * self.zi)

        # Estimate water that may reinfilt
        SurfaceWater = self.WaterLevel / 1000.0  # SurfaceWater (mm)
        self.CumSurfaceWater = self.CumSurfaceWater + SurfaceWater

        # Estimate water that may re-infiltrate
        # - Never more that 70% of the available water
        # - self.MaxReinFilt: a map with reinfilt locations (usually the river mask) can be supplied)
        # - take into account that the river may not cover the whole cell
        if self.reInfilt:
            self.reinfiltwater = pcr.min(
                self.MaxReinfilt,
                pcr.max(
                    0,
                    pcr.min(
                        SurfaceWater * self.RiverWidth / self.reallength * 0.7,
                        pcr.min(
                            self.InfiltCapSoil * (1.0 - self.PathFrac), UStoreCapacity
                        ),
                    ),
                ),
            )
            self.CumReinfilt = self.CumReinfilt + self.reinfiltwater
            self.UStoreDepth = self.UStoreDepth + self.reinfiltwater
        else:
            self.reinfiltwater = self.ZeroMap

        # The Max here may lead to watbal error. However, if inwaterMMM becomes < 0, the kinematic wave becomes very slow......
        if self.reInfilt:
            self.InwaterMM = (
                self.ExfiltWater
                + self.ExcessWater
                + self.SubCellRunoff
                + self.SubCellGWRunoff
                + self.RunoffOpenWater
                - self.reinfiltwater
                - self.ActEvapOpenWater
            )
        else:
            self.InwaterMM = pcr.max(
                0.0,
                self.ExfiltWater
                + self.ExcessWater
                + self.SubCellRunoff
                + self.SubCellGWRunoff
                + self.RunoffOpenWater
                - self.reinfiltwater
                - self.ActEvapOpenWater,
            )

        self.Inwater = self.InwaterMM * self.ToCubic  # m3/s

        # only run the reservoir module if needed
        if self.nrres > 0:
            self.ReservoirVolume, self.Outflow, self.ResPercFull, self.DemandRelease = simplereservoir(
                self.ReservoirVolume,
                self.SurfaceRunoff,
                self.ResMaxVolume,
                self.ResTargetFullFrac,
                self.ResMaxRelease,
                self.ResDemand,
                self.ResTargetMinFrac,
                self.ReserVoirLocs,
                timestepsecs=self.timestepsecs,
            )
            self.OutflowDwn = pcr.upstream(
                self.TopoLddOrg, pcr.cover(self.Outflow, pcr.scalar(0.0))
            )
            self.Inflow = self.OutflowDwn + pcr.cover(self.Inflow, self.ZeroMap)
        else:
            self.Inflow = pcr.cover(self.Inflow, self.ZeroMap)

        self.ExfiltWaterCubic = self.ExfiltWater * self.ToCubic
        self.SubCellGWRunoffCubic = self.SubCellGWRunoff * self.ToCubic
        self.SubCellRunoffCubic = self.SubCellRunoff * self.ToCubic
        self.InfiltExcessCubic = self.InfiltExcess * self.ToCubic
        self.ReinfiltCubic = -1.0 * self.reinfiltwater * self.ToCubic

        # self.Inwater = self.Inwater + self.Inflow   # Add abstractions/inflows in m^3/sec
        # Check if we do not try to abstract more runoff then present
        self.InflowKinWaveCell = pcr.upstream(
            self.TopoLdd, self.SurfaceRunoff
        )  # NG The extraction should be equal to the discharge upstream cell. You should not make the abstraction depended on the downstream cell, because they are correlated. During a stationary sum they will get equal to each other.
        MaxExtract = self.InflowKinWaveCell + self.Inwater  # NG
        # MaxExtract = self.SurfaceRunoff + self.Inwater
        self.SurfaceWaterSupply = pcr.ifthenelse(
            self.Inflow < 0.0, pcr.min(MaxExtract, -1.0 * self.Inflow), self.ZeroMap
        )
        self.OldSurfaceRunoff = self.SurfaceRunoff  # NG Store for iteration
        self.OldInwater = self.Inwater
        self.Inwater = self.Inwater + pcr.ifthenelse(
            self.SurfaceWaterSupply > 0, -1.0 * self.SurfaceWaterSupply, self.Inflow
        )

        ##########################################################################
        # Runoff calculation via Kinematic wave ##################################
        ##########################################################################
        # per distance along stream
        q = self.Inwater / self.DCL
        # discharge (m3/s)
        self.SurfaceRunoff = pcr.kinematic(
            self.TopoLdd,
            self.SurfaceRunoff,
            q,
            self.Alpha,
            self.Beta,
            self.Tslice,
            self.timestepsecs,
            self.DCL,
        )  # m3/s

        # If inflow is negative we have abstractions. Check if demand can be met (by looking
        # at the flow in the upstream cell) and iterate if needed
        self.nrit = 0
        self.breakoff = 0.0001
        if float(pcr.mapminimum(pcr.spatial(self.Inflow))) < 0.0:
            while True:
                self.nrit += 1
                oldsup = self.SurfaceWaterSupply
                self.InflowKinWaveCell = pcr.upstream(self.TopoLdd, self.SurfaceRunoff)
                ##########################################################################
                # Iterate to make a better estimation for the supply #####################
                # (Runoff calculation via Kinematic wave) ################################
                ##########################################################################
                MaxExtract = self.InflowKinWaveCell + self.OldInwater
                self.SurfaceWaterSupply = pcr.ifthenelse(
                    self.Inflow < 0.0,
                    pcr.min(MaxExtract, -1.0 * self.Inflow),
                    self.ZeroMap,
                )
                # Fraction of demand that is not used but flows back into the river get fracttion and move to return locations
                self.DemandReturnFlow = pcr.cover(
                    idtoid(
                        self.IrrigationSurfaceIntakes,
                        self.IrrigationSurfaceReturn,
                        self.DemandReturnFlowFraction * self.SurfaceWaterSupply,
                    ),
                    0.0,
                )

                self.Inwater = (
                    self.OldInwater
                    + pcr.ifthenelse(
                        self.SurfaceWaterSupply > 0,
                        -1.0 * self.SurfaceWaterSupply,
                        self.Inflow,
                    )
                    + self.DemandReturnFlow
                )
                # per distance along stream
                q = self.Inwater / self.DCL
                # discharge (m3/s)
                self.SurfaceRunoff = pcr.kinematic(
                    self.TopoLdd,
                    self.OldSurfaceRunoff,
                    q,
                    self.Alpha,
                    self.Beta,
                    self.Tslice,
                    self.timestepsecs,
                    self.DCL,
                )  # m3/s
                self.SurfaceRunoffMM = (
                    self.SurfaceRunoff * self.QMMConv
                )  # SurfaceRunoffMM (mm) from SurfaceRunoff (m3/s)

                self.InflowKinWaveCell = pcr.upstream(
                    self.TopoLdd, self.OldSurfaceRunoff
                )
                deltasup = float(pcr.mapmaximum(abs(oldsup - self.SurfaceWaterSupply)))

                if deltasup < self.breakoff or self.nrit >= self.maxitsupply:
                    break

            self.InflowKinWaveCell = pcr.upstream(self.TopoLdd, self.SurfaceRunoff)
            self.updateRunOff()
        else:
            self.SurfaceRunoffMM = (
                self.SurfaceRunoff * self.QMMConv
            )  # SurfaceRunoffMM (mm) from SurfaceRunoff (m3/s)
            self.updateRunOff()

        # Now add the supply that is linked to irrigation areas to extra precip
        if self.nrirri > 0:
            # loop over irrigation areas and spread-out the supply over the area
            IRSupplymm = idtoid(
                self.IrrigationSurfaceIntakes,
                self.IrrigationAreas,
                self.SurfaceWaterSupply * (1 - self.DemandReturnFlowFraction),
            )
            sqmarea = pcr.areatotal(
                self.reallength * self.reallength, pcr.nominal(self.IrrigationAreas)
            )

            self.IRSupplymm = pcr.cover(
                IRSupplymm / (sqmarea / 1000.0 / self.timestepsecs), 0.0
            )

        self.MassBalKinWave = (
            (-self.KinWaveVolume + self.OldKinWaveVolume) / self.timestepsecs
            + self.InflowKinWaveCell
            + self.Inwater
            - self.SurfaceRunoff
        )

        Runoff = self.SurfaceRunoff

        # Updating
        # --------
        # Assume a tss file with as many columns as outputlocs. Start updating for each non-missing value and start with the
        # first column (nr 1). Assumes that outputloc and columns match!

        if self.updating:
            self.QM = (
                pcr.timeinputscalar(self.updateFile, self.UpdateMap) * self.QMMConv
            )

            # Now update the state. Just add to the Ustore
            # self.UStoreDepth =  result
            # No determine multiplication ratio for each gauge influence area.
            # For missing gauges 1.0 is assumed (no change).
            # UpDiff = pcr.areamaximum(QM,  self.UpdateMap) - pcr.areamaximum(self.SurfaceRunoffMM, self.UpdateMap)
            UpRatio = pcr.areamaximum(self.QM, self.UpdateMap) / pcr.areamaximum(
                self.SurfaceRunoffMM, self.UpdateMap
            )

            UpRatio = pcr.cover(pcr.areaaverage(UpRatio, self.TopoId), 1.0)
            # Now split between Soil and Kyn  wave
            self.UpRatioKyn = pcr.min(
                self.MaxUpdMult,
                pcr.max(self.MinUpdMult, (UpRatio - 1.0) * self.UpFrac + 1.0),
            )
            UpRatioSoil = pcr.min(
                self.MaxUpdMult,
                pcr.max(self.MinUpdMult, (UpRatio - 1.0) * (1.0 - self.UpFrac) + 1.0),
            )

            # update/nudge self.UStoreDepth for the whole upstream area,
            # not sure how much this helps or worsens things
            UpdSoil = True
            if UpdSoil:
                toadd = (self.UStoreDepth * UpRatioSoil) - self.UStoreDepth
                self.UStoreDepth = self.UStoreDepth + toadd

            # Update the kinematic wave reservoir up to a maximum upstream distance
            MM = (1.0 - self.UpRatioKyn) / self.UpdMaxDist
            self.UpRatioKyn = MM * self.DistToUpdPt + self.UpRatioKyn
            self.SurfaceRunoff = self.SurfaceRunoff * self.UpRatioKyn
            self.SurfaceRunoffMM = (
                self.SurfaceRunoff * self.QMMConv
            )  # SurfaceRunoffMM (mm) from SurfaceRunoff (m3/s)
            self.updateRunOff()
            Runoff = self.SurfaceRunoff

        # Determine Soil moisture profile
        # 1: average volumetric soil in total unsat store
        self.SMVol = (pcr.cover(self.UStoreDepth / self.zi, 0.0) + self.thetaR) * (
            self.thetaS - self.thetaR
        )
        self.SMRootVol = (
            pcr.cover(self.UStoreDepth / pcr.min(self.ActRootingDepth, self.zi), 0.0)
            + self.thetaR
        ) * (self.thetaS - self.thetaR)
        # 2:
        ##########################################################################
        # water balance ###########################################
        ##########################################################################

        self.QCatchmentMM = self.SurfaceRunoff * self.QMMConvUp
        self.RunoffCoeff = pcr.cover(
            self.QCatchmentMM
            / pcr.catchmenttotal(self.PrecipitationPlusMelt, self.TopoLdd),
            self.ZeroMap,
        )
        # self.AA = pcr.catchmenttotal(self.PrecipitationPlusMelt, self.TopoLdd)
        # self.BB = pcr.catchmenttotal(pcr.cover(1.0), self.TopoLdd)
        # Single cell based water budget. snow not included yet.

        self.CellStorage = self.UStoreDepth + self.SatWaterDepth
        self.DeltaStorage = self.CellStorage - self.OrgStorage
        OutFlow = self.SatWaterFlux
        if self.waterdem:
            CellInFlow = pcr.upstream(self.waterLdd, pcr.scalar(self.SatWaterFlux))
        else:
            CellInFlow = pcr.upstream(self.TopoLdd, pcr.scalar(self.SatWaterFlux))

        self.CumOutFlow = self.CumOutFlow + OutFlow
        self.CumActInfilt = self.CumActInfilt + self.ActInfilt
        self.CumCellInFlow = self.CumCellInFlow + CellInFlow
        self.CumPrec = self.CumPrec + self.Precipitation
        self.CumEvap = self.CumEvap + self.ActEvap
        self.CumPotenTrans = self.CumPotenTrans + self.PotTrans
        self.CumPotenEvap = self.CumPotenEvap + self.PotenEvap

        self.CumInt = self.CumInt + self.Interception

        self.SnowCover = pcr.ifthenelse(
            self.Snow > 0.0, self.ZeroMap + 1.0, self.ZeroMap
        )
        self.CumLeakage = self.CumLeakage + self.ActLeakage
        self.CumInwaterMM = self.CumInwaterMM + self.InwaterMM
        self.CumExfiltWater = self.CumExfiltWater + self.ExfiltWater

        self.SoilWatbal = (
            self.ActInfilt
            + self.reinfiltwater
            + CellInFlow
            - self.Transpiration
            - self.soilevap
            - self.ExfiltWater
            - self.SubCellGWRunoff
            - self.DeltaStorage
            - self.SatWaterFlux
        )

        self.InterceptionWatBal = (
            self.PrecipitationPlusMelt
            - self.Interception
            - self.StemFlow
            - self.ThroughFall
            - (self.OldCanopyStorage - self.CanopyStorage)
        )
        self.SurfaceWatbal = (
            self.PrecipitationPlusMelt
            - self.Interception
            - self.ExcessWater
            - self.RunoffOpenWater
            - self.SubCellRunoff
            - self.ActInfilt
            - (self.OldCanopyStorage - self.CanopyStorage)
        )

        self.watbal = self.SoilWatbal + self.SurfaceWatbal


def main(argv=None):
    """
    Perform command line execution of the model.


    """
    caseName = "default_sbm"
    global multpars
    runId = "run_default"
    configfile = "wflow_sbm.ini"
    _lastTimeStep = 1
    _firstTimeStep = 0
    LogFileName = "wflow.log"
    runinfoFile = "runinfo.xml"
    timestepsecs = 86400
    wflow_cloneMap = "wflow_subcatch.map"
    _NoOverWrite = 1
    global updateCols
    loglevel = logging.DEBUG

    if argv is None:
        argv = sys.argv[1:]
        if len(argv) == 0:
            usage()
            return
    ########################################################################
    ## Process command-line options                                        #
    ########################################################################
    try:
        opts, args = getopt.getopt(argv, "XF:L:hC:Ii:v:S:T:WR:u:s:EP:p:Xx:U:fOc:l:")
    except getopt.error as msg:
        pcrut.usage(msg)

    for o, a in opts:
        if o == "-C":
            caseName = a
        if o == "-R":
            runId = a
        if o == "-c":
            configfile = a
        if o == "-L":
            LogFileName = a
        if o == "-s":
            timestepsecs = int(a)
        if o == "-T":
            _lastTimeStep = int(a)
        if o == "-S":
            _firstTimeStep = int(a)
        if o == "-h":
            usage()
        if o == "-f":
            _NoOverWrite = 0
        if o == "-l":
            exec("loglevel = logging." + a)

    starttime = dt.datetime(1990, 1, 1)

    if _lastTimeStep < _firstTimeStep:
        print(
            "The starttimestep ("
            + str(_firstTimeStep)
            + ") is smaller than the last timestep ("
            + str(_lastTimeStep)
            + ")"
        )
        usage()

    myModel = WflowModel(wflow_cloneMap, caseName, runId, configfile)
    dynModelFw = wf_DynamicFramework(
        myModel, _lastTimeStep, firstTimestep=_firstTimeStep, datetimestart=starttime
    )
    dynModelFw.createRunId(
        NoOverWrite=_NoOverWrite,
        level=loglevel,
        logfname=LogFileName,
        model="wflow_sbm",
        doSetupFramework=False,
    )

    for o, a in opts:
        if o == "-P":
            left = a.split("=")[0]
            right = a.split("=")[1]
            configset(
                myModel.config, "variable_change_once", left, right, overwrite=True
            )
        if o == "-p":
            left = a.split("=")[0]
            right = a.split("=")[1]
            configset(
                myModel.config, "variable_change_timestep", left, right, overwrite=True
            )
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
            configset(myModel.config, "model", "MassWasting", "0", overwrite=True)
        if o == "-Q":
            configset(myModel.config, "model", "ExternalQbase", "1", overwrite=True)
        if o == "-U":
            configset(myModel.config, "model", "updateFile", a, overwrite=True)
            configset(myModel.config, "model", "updating", "1", overwrite=True)
        if o == "-u":
            zz = []
            exec("zz =" + a)
            updateCols = zz
        if o == "-E":
            configset(myModel.config, "model", "reInfilt", "1", overwrite=True)
        if o == "-R":
            runId = a
        if o == "-W":
            configset(myModel.config, "model", "waterdem", "1", overwrite=True)

    dynModelFw.setupFramework()
    dynModelFw.logger.info("Command line: " + str(argv))
    dynModelFw._runInitial()
    dynModelFw._runResume()
    dynModelFw._runDynamic(0, 0)
    dynModelFw._runSuspend()
    dynModelFw._wf_shutdown()


if __name__ == "__main__":
    main()
