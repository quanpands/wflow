#!/usr/bin/python
"""

Introduction
------------

Simple export library for pcraster/python delwaq link. The module can be
used to export an ldd to a delwaq pointer file and fill the input arrays.
The library includes a command-line interface that allows you to setup
a delwaq model and feed it with forcing data.

.. warning::
    
    This is an experimental version.


the wflow run should have saved at least the folowing mapstacks::

    - self.OldKinWaveVolume=vol
    - self.WaterLevel=lev
    - self.SurfaceRunoff=run
    - self.Inwater=inw  (or the different components that make up this flux)

The script always sets-up at least two Substances, Initial and Check. Initial
is present everywhere at startup and the concentration is zero
in all inputs. Check is not present at startup and set to 1 in all inputs.

The script takes an areamap that can be used to tag water as it enters the
model. This can be a landuse map, a subcatchment map etc. Furthermore water
can also be tagged based on the flux into the model.

The naming of the sustances is as follows: "Area" areamap_class inflow_number 
    
Command line options::
    
    -C: caseDir - set the wflow case directory to use
    -R: runId - set the wflow runId to use
    -T: Set last timestep
    -O: set starttime ('%Y-%m-%d% H:%M:%S')
    -a: Also write dynamic area data if this option is set
    -j: if this option is set the static data is not generated (default is on) 
    -A: sets the areamap used to specify the fraction sources. This can be
        a subcatcment map, a soil type map, a land use maps etc. Default is:
        staticmaps/wflow_subcatch.map (relative to the caseDir directory)
    -D: delwaqdir - set the basedir to create the delwaq schematisation in 
    -S: sourcemap - name of the wflow output map to use as source. 
        it should be a variable that flows into the kinematic wave routine
        inw is normally used as it contain all water per cell that flows into
        the kinematic wave function.
        Use multiple -S options to include multiple maps
    -s: Set the model timesteps in seconds (default 86400)
    -c: Name of the wflow configuration file
    -n: Name of the wflow netCDF output file, expected in caseDir/runId/. If not
        present, mapstacks will be used.

  
.. todo::

    add support for a coarser delwaq network based on supplied map.      
    
    
.. todo::
    
    Test option to seperate construction of network from filling of the input
    arrays
    
.. todo::
    
    Ad support to not only follow the kinematic wave reservoir but also
    the flow trough the soil reservoirs. Basically make three layers:
        
        #. kinematic wave reservoir (surface water)
        #. unsaturated store (only vertical flow)
        #. saturated store (horizontal and vertical flow)
    

"""
import getopt
import os.path
import struct
from datetime import *

from wflow import wf_netcdfio
from wflow.wf_DynamicFramework import *

logger = ""
volumeMapStack = "vol"
runoffMapStack = "run"
waterlevelMapStack = "lev"


def dw_WriteNrSegments(fname, nr):
    """ 
    Writes the number of segments to B3 file 
    
    B3\_nrofseg.inc
    """
    exfile = open(fname, "w")
    print(";Written by dw_WriteNrSegments", file=exfile)
    print(str(nr) + " ; nr of segments", file=exfile)
    exfile.close()


def dw_WriteNrExChnages(fname, nr):
    """ 
    Writes the number of exchnages to file (number of rows in the pointer file)
    
    B4\_nrofexch.inc
    """
    exfile = open(fname, "w")
    print(";Written by dw_WriteNrExChnages", file=exfile)
    print(str(nr) + " 0 0 ; x, y, z direction", file=exfile)
    exfile.close()


def dw_WriteBoundData(fname, areas):
    """ 
    writes B5\_bounddata.inc
    """

    areas = sorted(areas, reverse=True)
    exfile = open(fname, "w")
    print(";Written by dw_WriteBoundData", file=exfile)
    for i in areas:
        print("ITEM 'Area_%s'" % (i), file=exfile)
        print("CONCENTRATION  'Area_%s' 'Check' 'Initial'" % (i), file=exfile)
        print("DATA", file=exfile)
        print("1.0  1.0  0.0", file=exfile)
        print("", file=exfile)

    exfile.close()


def dw_WriteInitials(fname, inmaps):
    """
    B8_initials.inc
    """

    maps = ["Initial", "Check"]
    exfile = open(fname, "w")
    print("INITIALS", file=exfile)
    for rr in inmaps:
        print("'" + rr + "'", end=" ", file=exfile)
    for rr in maps:
        print("'" + rr + "'", end=" ", file=exfile)
    print(file=exfile)
    print("DEFAULTS", file=exfile)
    for rr in inmaps:
        print(str(0.0) + " ", end=" ", file=exfile)
    for rr in maps:
        print(str(1.0) + " ", end=" ", file=exfile)
    print(file=exfile)
    exfile.close()


def dw_WriteBoundlist(fname, pointer, areas, inflowtypes):
    """ 
    Writes the boundary list file
    B5\_boundlist.inc
    Numbering is abs(exchnage id)
    
    Input: 
        - fname, pointer
        
    .. todo::
        
        - add labeling of different inflows ( the information is already present)
    """
    totareas = areas
    exfile = open(fname, "w")
    print(";Written by dw_WriteBoundlist", file=exfile)
    print(";'NodeID' 'Number' 'Type'", file=exfile)
    nr_inflowtypes = len(inflowtypes)

    # for i in range(nr_inflowtypes-1):
    #    totareas = np.vstack((totareas,areas))
    totareas = areas

    arid = 0
    for i in range(len(pointer)):
        if pointer[i, 1] < 0:
            print(
                "'BD_"
                + str(np.absolute(pointer[i, 1]))
                + "'  '"
                + str(np.absolute(pointer[i, 1]))
                + "'"
                + " 'Outflow'",
                file=exfile,
            )
        elif pointer[i, 0] < 0:
            # ar = int(np.absolute(totareas[arid]))
            ar = totareas[arid]
            print(
                "'BD_"
                + str(np.absolute(pointer[i, 0]))
                + "' "
                + "'"
                + str(np.absolute(pointer[i, 0]))
                + "'"
                + " 'Area_"
                + str(ar)
                + "'",
                file=exfile,
            )
            arid = arid + 1

    exfile.close()


def dw_WritePointer(fname, pointer, binary=False):
    """ 
    WRites the pointer file
    B4\_pointer.inc
    """
    if not binary:
        # Write ASCII file
        exfile = open(fname, "w")
        print(";Written by dw_WritePointer", file=exfile)
        print(";nr of pointers is: ", str(pointer.shape[0]), file=exfile)
        savetxt(exfile, pointer, fmt="%10.0f")
        exfile.close()
    else:
        # Write binary file
        f = open(fname, "wb")
        for i in range(pointer.shape[0]):
            f.write(struct.pack("4i", *pointer[i, :]))
        f.close()


def dw_WriteSegmentOrExchangeData(ttime, fname, datablock, boundids, WriteAscii=True):
    """
    Writes a timestep to a segment/exchange data file (appends to an existing
    file or creates a new one). 
        
    Input:
        - time - time for this timestep  
        - fname - File path of the segment/exchange data file</param>
        - datablock - array with data
        - boundids to write more than 1 block
        - WriteAscii - set to 1 to alse make an ascii dump
        
    """
    # First convert the array to a 32 bit float
    totareas = datablock
    for i in range(boundids - 1):
        totareas = np.vstack((totareas, datablock))

    artow = np.array(totareas, dtype=np.float32).copy()
    timear = np.array(ttime, dtype=np.int32)
    if os.path.isfile(fname):  # append to existing file
        fp = open(fname, "ab")
        tstr = timear.tostring() + artow.tostring()
        fp.write(tstr)
        if WriteAscii:
            fpa = open(fname + ".asc", "a")
            timear.tofile(fpa, format="%d\t", sep=":")
            artow.tofile(fpa, format="%10.8f", sep="\t")
            fpa.write("\n")
    else:
        fp = open(fname, "wb")
        tstr = timear.tostring() + artow.tostring()
        fp.write(tstr)
        if WriteAscii:
            fpa = open(fname + ".asc", "w")
            timear.tofile(fpa, format="%d\t", sep=":")
            artow.tofile(fpa, format="%10.8f", sep="\t")
            fpa.write("\n")

    fp.close()
    if WriteAscii:
        fpa.close()


def dw_mkDelwaqPointers(ldd, amap, difboun, layers):
    """
    An ldd is used to determine the from-to relations for delwaq using
    the PCraster up/downstreams commands.
    *amap* is used to link boundaries to the segments for delwaq (negative 
    numbers). These are area based boundaries. Diffboun is a 
    python dictionary with inflows for each
    cell.
    
    Input:
        - ldd
        - map to determine the active points)
        - difboun : number of inflow boundaries per cell
        - layers [nr of soil layers (only vertical flow)]. 
    
    .. note:: Only one layer at present (layers must be 1)
        
    Output:
        - pointer, fromto, outflows, boundaries, segment
        - matrix with 4 colums: from to, zero, zero.
        - catchid

    .. note::  use savetxt("pointer.inc",pointer,fmt='%10.0f') to save this
        for use with delwaq
       
       
    .. note:: The pointers list first contains the "internal" fluxes in
        the kinematic wave reservoir, next the fluxes (1-n) into the 
        kinematic wave reservoir.
            
        
    .. todo:: 
        Add exta column with boundary labels (of the inflows)    
        
    """
    # Firts make sure there is at least on outflow in the model
    ptid = pcr.uniqueid(pcr.boolean(amap))
    flowto = pcr.downstream(ldd, ptid)
    # Fix if downsteam is no pit.In that case flowto is missing, set it so itself
    hasflowto = pcr.defined(flowto)
    flowto = pcr.ifthenelse(pcr.defined(ptid) != hasflowto, ptid, flowto)

    # find all upstream cells (these must be set negative)
    upbound = pcr.upstream(ldd, 1.0)
    upbound = pcr.ifthen(amap > 0, upbound)
    # Find the lower boundaries (and pits). These flow to themselves

    # make into flatted numpy arrays
    np_ptid = pcr.pcr2numpy(ptid, np.nan).flatten()
    np_flowto = pcr.pcr2numpy(flowto, np.nan).flatten()
    np_catchid = pcr.pcr2numpy(pcr.scalar(amap), -999).flatten()
    np_upbound = pcr.pcr2numpy(upbound, np.nan).flatten()

    # remove all non-active cells
    np_catchid = np_catchid[np_catchid > 0.0]
    np_upbound = np_upbound[np.isfinite(np_upbound)]
    np_flowto = np_flowto[np.isfinite(np_flowto)]
    np_ptid = np_ptid[np.isfinite(np_ptid)]
    np_flowto = np_flowto.reshape(len(np_flowto), 1)
    np_ptid = np_ptid.reshape(len(np_ptid), 1)
    np_catchid = np_catchid.reshape(len(np_catchid), 1)
    # Now make catchid a list
    np_catchid = np_catchid.flatten()
    np_catchid = np.array(np.int_(np_catchid), dtype="|S").tolist()
    # find all downstream segments (flowto == ptid)
    # now set the flowto points (outflows, usually just one) also to negative
    lowerck = np.absolute(np_ptid) == np.absolute(np_flowto)
    # mak epointer matrix and add to zero zolumns
    orgpointer = np.hstack(
        (
            np_ptid,
            np_flowto,
            np.zeros((len(np_flowto), 1)),
            np.zeros((len(np_flowto), 1)),
        )
    )
    pointer = orgpointer.copy()
    # Pointer labels:
    #    negative: outflow boundary
    #    zero    : internal flow
    #    positive: inflow boundary
    pointer_labels = np.zeros((len(np_flowto)), dtype=numpy.int)
    extraboun = []
    # Add the inflow boundaries here.
    cells = pointer[:, 0]
    cells = cells.reshape(len(cells), 1)
    bounid = cells.copy()
    zzerocol = np.zeros((len(np_flowto), 1), dtype=numpy.int)

    # outflow to pointer
    # point -> - point
    lopt = np_ptid[lowerck]
    lopt = lopt.reshape(len(lopt), 1)
    zerocol = np.zeros((len(lopt), 1))
    lowerids = np.arange(1, len(lopt) + 1) * -1
    # of = np.hstack((lopt,lopt * -1.0,zerocol,zerocol))
    lowerids = lowerids.reshape(len(lowerids), 1)
    of = np.hstack((lopt, lowerids, zerocol, zerocol))

    # Now remove double pointer to itself and replace by lower boundary
    lowerck = pointer[:, 0] == pointer[:, 1]
    pointer[lowerck, :] = of
    pointer_labels[lowerck] = -1
    start = np.absolute(lowerids.min()) + 1
    bouns = 1
    for idd in range(1, difboun + 1):
        bounid = np.arange(start, (len(cells) + start)).reshape((len(cells), 1)) * -1.0
        if bouns == 1:
            extraboun = np.hstack((bounid, cells, zzerocol, zzerocol))
        else:
            extraboun = np.vstack(
                (extraboun, np.hstack((bounid, cells, zzerocol, zzerocol)))
            )
        pointer_labels = np.hstack((pointer_labels, zzerocol[:, 0] + bouns))
        bouns = bouns + 1
        start = start + len(cells)

    res = []
    for idd in range(1, difboun + 1):
        ct = list(np_catchid)
        print("ct: ")
        print(np.unique(ct))
        for i in range(0, len(np_catchid)):
            ct[i] = np_catchid[i] + "_" + str(idd)
        res = res + ct
    print(np.unique(res))
    np_catchid = res
    # pointer = np.vstack((pointer,extraboun))
    # now catchment id's
    # zerocol = np.zeros((len(np_catchid),1))
    # extraboun= np.hstack((np_catchid,cells,zerocol,zerocol))
    # print np_catchid

    if len(extraboun) > 0:
        pointer = np.vstack((pointer, extraboun))

    return ptid, pointer, pointer_labels, np_ptid.flatten(), np_catchid


def dw_pcrToDataBlock(pcrmap):
    """
    Converts a pcrmap to a numpy array.that is flattend and from which
    missing values are removed. Used for generating delwaq data
    """
    ttar = pcr.pcr2numpy(pcrmap, np.nan).flatten()
    ttar = ttar[np.isfinite(ttar)]

    return ttar


def _readTS(name, ts):
    """
    Read a pcraster map for a timestep without using the dynamic framework 
    """
    mname = os.path.basename(name)
    #  now generate timestep
    tsje = "%0.11d" % ts
    ff = mname + tsje[len(mname) :]
    ff = ff[:8] + "." + ff[8:]
    name = os.path.dirname(name) + "/" + ff
    mapje = pcr.readmap(name)

    return mapje


def dw_CreateDwRun(thedir):
    """"
    create the dir to save delwaq info in
    """
    if not os.path.isdir(thedir):
        os.makedirs(thedir + "/fixed/")
        os.makedirs(thedir + "/includes_deltashell/")
        os.makedirs(thedir + "/includes_flow/")
        os.makedirs(thedir + "/debug/")
    if os.path.exists(thedir + "/includes_flow/area.dat"):
        os.remove(thedir + "/includes_flow/area.dat")
    if os.path.exists(thedir + "/includes_flow/flow.dat"):
        os.remove(thedir + "/includes_flow/flow.dat")
    if os.path.exists(thedir + "/includes_flow/volume.dat"):
        os.remove(thedir + "/includes_flow/volume.dat")
    if os.path.exists(thedir + "/includes_flow/length.dat"):
        os.remove(thedir + "/includes_flow/length.dat")
    if os.path.exists(thedir + "/includes_flow/surface.dat"):
        os.remove(thedir + "/includes_flow/surface.dat")
    if os.path.exists(thedir + "/includes_flow/area.dat.asc"):
        os.remove(thedir + "/includes_flow/area.dat.asc")
    if os.path.exists(thedir + "/includes_flow/flow.dat.asc"):
        os.remove(thedir + "/includes_flow/flow.dat.asc")
    if os.path.exists(thedir + "/includes_flow/volume.dat.asc"):
        os.remove(thedir + "/includes_flow/volume.dat.asc")
    if os.path.exists(thedir + "/includes_flow/length.dat.asc"):
        os.remove(thedir + "/includes_flow/length.dat.asc")
    if os.path.exists(thedir + "/includes_flow/surface.dat.asc"):
        os.remove(thedir + "/includes_flow/surface.dat.asc")
    # prepare hydfile directory
    comdir = os.sep.join([thedir, "com"])
    if os.path.isdir(comdir):
        shutil.rmtree(comdir)
    os.mkdir(comdir)


def dw_Write_Times(dwdir, T0, timeSteps, timeStepSec):
    """
    Writes B1_T0.inc, B2_outputtimers.inc, B2_sysclock.inc and /B2_simtimers.inc
    Assumes daily timesteps for now!
    """
    # B1_T0.inc
    exfile = open(dwdir + "/B1_T0.inc", "w")
    print(
        "'T0: " + T0.strftime("%Y.%m.%d %H:%M:%S") + "  (scu=       1s)'", file=exfile
    )
    exfile.close()

    # B2_outputtimers.inc
    timeRange = timedelta(seconds=timeStepSec * timeSteps)

    days = int(timeStepSec / 86400)
    hours = int(timeStepSec / 3600)
    minutes = int(timeStepSec / 60)
    seconds = int(timeStepSec - minutes * 60)
    minutes -= hours * 60
    hours -= days * 24
    timestepstring = "  %03d%02d%02d%02d" % (days, hours, minutes, seconds)

    exfile = open(dwdir + "/B2_outputtimers.inc", "w")
    etime = T0 + timeRange
    print(
        "  "
        + T0.strftime("%Y/%m/%d-%H:%M:%S")
        + "  "
        + etime.strftime("%Y/%m/%d-%H:%M:%S")
        + timestepstring,
        file=exfile,
    )
    print(
        "  "
        + T0.strftime("%Y/%m/%d-%H:%M:%S")
        + "  "
        + etime.strftime("%Y/%m/%d-%H:%M:%S")
        + timestepstring,
        file=exfile,
    )
    print(
        "  "
        + T0.strftime("%Y/%m/%d-%H:%M:%S")
        + "  "
        + etime.strftime("%Y/%m/%d-%H:%M:%S")
        + timestepstring,
        file=exfile,
    )
    exfile.close()

    # B2_simtimers.inc
    exfile = open(dwdir + "/B2_simtimers.inc", "w")
    print("  " + T0.strftime("%Y/%m/%d-%H:%M:%S"), file=exfile)
    print("  " + etime.strftime("%Y/%m/%d-%H:%M:%S"), file=exfile)
    print("  0 ; timestep constant", file=exfile)
    print("; dddhhmmss format for timestep", file=exfile)
    print(timestepstring + " ; timestep", file=exfile)
    exfile.close()

    # B2_sysclock.inc
    exfile = open(dwdir + "/B2_sysclock.inc", "w")
    print("%7d 'DDHHMMSS' 'DDHHMMSS'  ; system clock" % timeStepSec, file=exfile)
    exfile.close()


def dw_Write_Substances(fname, areas):
    """
    Writes the B1_sublist.inc file
    input:
        
        it writes substances for the areas and an initial and mass balance 
        check substance
        
    """

    exfile = open(fname, "w")
    areas = sorted(areas, reverse=True)
    print("; number of active and inactive substances", file=exfile)
    print("%d         0" % (len(areas) + 2), file=exfile)
    print("; active substances", file=exfile)
    print("1             'Initial' ; ", file=exfile)
    print("2             'Check' ; ", file=exfile)
    j = 2
    for i in areas:
        j = j + 1
        print("%d            'Area_%s'" % (j, i), file=exfile)
    print("; passive substances", file=exfile)

    exfile.close()


def dw_Write_B2_outlocs(fname, gauges, segs):
    """
    Write an output loc file based on the wflow_gauges
    map.
    """
    segs = pcr.ifthenelse(gauges > 0, segs, np.nan)
    gauges = pcr.ifthenelse(gauges > 0, pcr.scalar(gauges), np.nan)
    np_gauges = pcr.pcr2numpy(gauges, np.nan).flatten()
    np_segs = pcr.pcr2numpy(segs, np.nan).flatten()

    np_gauges = np_gauges[np.isfinite(np_gauges)]
    np_segs = np_segs[np.isfinite(np_segs)]

    if len(np_segs) != len(np_gauges):
        logger.error("Gauges and segments do not match!")

    pts = np.size(np_segs)
    exfile = open(fname, "w")
    print("%d ; nr of locations" % pts, file=exfile)
    print("; 'outlocname' numberofsegments segment list", file=exfile)
    i = 0
    for loc in np_gauges:
        print(" '%d' 1 %d" % (loc, np_segs[i]), file=exfile)
        i = i + 1
    exfile.close()


def dw_GetGridDimensions(ptid_map):
    """
    Returns number of cells in 1st and 2nd grid directions.

    input:
    - ptid_map : PCRaster map with unique id's
    """
    # find number of cells in m and n directions
    zero_map = pcr.scalar(ptid_map) * 0.0
    allx = dw_pcrToDataBlock(pcr.xcoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))))
    i = 0
    diff = round(builtins.abs(allx[i] - allx[i + 1]), 5)
    diff_next = diff
    while diff_next == diff:
        i += 1
        diff_next = builtins.abs(allx[i] - allx[i + 1])
        diff_next = round(diff_next, 5)
    m = i + 1
    n = allx.shape[0] / m
    m, n = n, m
    return m, n


def dw_WriteWaqGeom(fname, ptid_map, ldd_map):
    """
    Writes Delwaq netCDF geometry file (*_waqgeom.nc).

    input:
    - fname    : output file name (without file extension)
    - ptid_map : PCRaster map with unique id's
    """
    # Get coordinates

    zero_map = pcr.scalar(ptid_map) * 0.0
    pcr.setglobaloption("coorul")  # upper-left cell corners
    xxul = pcr.pcr2numpy(pcr.xcoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    yyul = pcr.pcr2numpy(pcr.ycoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    pcr.setglobaloption("coorlr")  # lower-right cell corners
    xxlr = pcr.pcr2numpy(pcr.xcoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    yylr = pcr.pcr2numpy(pcr.ycoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)

    # Convert pcr maps to numpy arrays

    np_ptid = pcr.pcr2numpy(ptid_map, -1)
    np_ldd = pcr.pcr2numpy(ldd_map, -1)
    np_ldd[np_ldd == 255] = 0

    # Number of segments in horizontal dimension

    nosegh = int(numpy.max(np_ptid))

    # Waqgeom dimensions

    n_net_node = 0
    n_net_link = 0
    n_net_link_pts = 2
    n_net_elem = nosegh
    n_net_elem_max_node = 4  # all elements are rectangles
    n_flow_link = nosegh - 1  # one per element, except for outlet
    n_flow_link_pts = 2

    # Prepare waqgeom data structures

    nodes_x = []
    nodes_y = []
    nodes_z = []
    net_links = []
    elem_nodes = numpy.zeros((n_net_elem, n_net_elem_max_node), dtype=numpy.int)
    flow_links = numpy.zeros((n_flow_link, n_flow_link_pts), dtype=numpy.int)
    flow_link_x = numpy.zeros((n_flow_link), dtype=numpy.float)
    flow_link_y = numpy.zeros((n_flow_link), dtype=numpy.float)

    # Keep track of nodes and links as dataset grows

    i_node = 0  # index of last node
    i_flink = 0  # index of last flow link

    # PCR cell id's start at 1, we need it zero based

    np_ptid = np_ptid - 1

    # Wflow map dimensions

    m, n = np_ptid.shape

    # Helper function

    def add_node(i, j, corner):
        # Get coordinates
        if corner == UL:
            x = xxul[i, j]
            y = yyul[i, j]
        elif corner == LR:
            x = xxlr[i, j]
            y = yylr[i, j]
        elif corner == UR:
            x = xxlr[i, j]
            y = yyul[i, j]
        elif corner == LL:
            x = xxul[i, j]
            y = yylr[i, j]
        else:
            assert 0
        # Add node coordinates
        nodes_x.append(x)
        nodes_y.append(y)
        nodes_z.append(0)

    # Cell corners

    UL, UR, LR, LL = 0, 1, 2, 3

    # Process all cells from upper-left to lower-right

    for i in range(m):
        for j in range(n):
            # Current element index
            i_elem = int(np_ptid[i, j])
            if i_elem < 0:
                # Skip inactive segment
                continue

            # Get index of neighbouring elements that could have been processed before

            if i == 0:
                i_elem_up_left = -1
                i_elem_up = -1
                i_elem_up_right = -1
            elif j == 0:
                i_elem_up_left = -1
                i_elem_up = int(np_ptid[i - 1, j])
                i_elem_up_right = int(np_ptid[i - 1, j + 1])
            elif j == n - 1:
                i_elem_up_left = int(np_ptid[i - 1, j - 1])
                i_elem_up = int(np_ptid[i - 1, j])
                i_elem_up_right = -1
            else:
                i_elem_up_left = int(np_ptid[i - 1, j - 1])
                i_elem_up = int(np_ptid[i - 1, j])
                i_elem_up_right = int(np_ptid[i - 1, j + 1])

            if j == 0:
                i_elem_left = -1
            else:
                i_elem_left = int(np_ptid[i, j - 1])

            # Update nodes:
            # If left or upper neighbours are active, some nodes of current cell
            # have been added already.

            # UL node
            if i_elem_left < 0 and i_elem_up_left < 0 and i_elem_up < 0:
                add_node(i, j, UL)
                elem_nodes[i_elem, UL] = i_node
                i_node += 1
            elif i_elem_left >= 0:
                elem_nodes[i_elem, UL] = elem_nodes[i_elem_left, UR]
            elif i_elem_up_left >= 0:
                elem_nodes[i_elem, UL] = elem_nodes[i_elem_up_left, LR]
            elif i_elem_up >= 0:
                elem_nodes[i_elem, UL] = elem_nodes[i_elem_up, LL]

            # UR node
            if i_elem_up < 0 and i_elem_up_right < 0:
                add_node(i, j, UR)
                elem_nodes[i_elem, UR] = i_node
                i_node += 1
            elif i_elem_up >= 0:
                elem_nodes[i_elem, UR] = elem_nodes[i_elem_up, LR]
            elif i_elem_up_right >= 0:
                elem_nodes[i_elem, UR] = elem_nodes[i_elem_up_right, LL]
            if i_elem_up < 0:
                # add UL-UR link
                net_links.append((elem_nodes[i_elem, UL], elem_nodes[i_elem, UR]))

            # LL node
            if i_elem_left < 0:
                add_node(i, j, LL)
                elem_nodes[i_elem, LL] = i_node
                i_node += 1
                # add UL-LL link
                net_links.append((elem_nodes[i_elem, UL], elem_nodes[i_elem, LL]))
            else:
                elem_nodes[i_elem, LL] = elem_nodes[i_elem_left, LR]

            # LR node
            add_node(i, j, LR)
            elem_nodes[i_elem, LR] = i_node
            i_node += 1
            # add LL-LR link
            net_links.append((elem_nodes[i_elem, LL], elem_nodes[i_elem, LR]))
            # add UR-LR link
            net_links.append((elem_nodes[i_elem, UR], elem_nodes[i_elem, LR]))

            # Update flow links based on local drain direction
            # TODO: diagonal flow links between cells that have only one node in common?

            direction = np_ldd[i, j]
            i_other = -1
            if direction == 1:
                i_other = np_ptid[i + 1, j - 1]  # to lower left
            elif direction == 2:
                i_other = np_ptid[i + 1, j]  # to lower
            elif direction == 3:
                i_other = np_ptid[i + 1, j + 1]  # to lower right
            elif direction == 4:
                i_other = np_ptid[i, j - 1]  # to left
            elif direction == 6:
                i_other = np_ptid[i, j + 1]  # to right
            elif direction == 7:
                i_other = np_ptid[i - 1, j - 1]  # to upper right
            elif direction == 8:
                i_other = np_ptid[i - 1, j]  # to upper
            elif direction == 9:
                i_other = np_ptid[i - 1, j + 1]  # to upper left
            if i_other >= 0:
                flow_links[i_flink, :] = i_elem, i_other
                i_flink += 1

    # Convert data to numpy arrays

    nodes_x = numpy.array(nodes_x)
    nodes_y = numpy.array(nodes_y)
    nodes_z = numpy.array(nodes_z)
    net_links = numpy.array(net_links)

    # Update dimensions

    n_net_node = nodes_x.shape[0]
    n_net_link = net_links.shape[0]

    # Create netCDF file in classic format

    f = netCDF4.Dataset(fname + "_waqgeom.nc", "w", format="NETCDF3_CLASSIC")

    # Create dimensions

    f.createDimension("dim", 1)
    f.createDimension("nNetNode", n_net_node)
    f.createDimension("nNetLink", n_net_link)
    f.createDimension("nNetLinkPts", n_net_link_pts)
    f.createDimension("nNetElem", n_net_elem)
    f.createDimension("nNetElemMaxNode", n_net_elem_max_node)
    f.createDimension("nFlowLink", n_flow_link)
    f.createDimension("nFlowLinkPts", n_flow_link_pts)

    # Create variables

    v_msh = f.createVariable("mesh", "i4", ("dim",))
    v_pcs = f.createVariable("projected_coordinate_system", "i4", ())
    v_nnx = f.createVariable("NetNode_x", "f8", ("nNetNode",))
    v_nny = f.createVariable("NetNode_y", "f8", ("nNetNode",))
    v_nnz = f.createVariable("NetNode_z", "f8", ("nNetNode",))
    v_nlk = f.createVariable("NetLink", "i4", ("nNetLink", "nNetLinkPts"))
    v_nen = f.createVariable(
        "NetElemNode", "i4", ("nNetElem", "nNetElemMaxNode"), fill_value=0
    )
    v_flk = f.createVariable("FlowLink", "i4", ("nFlowLink", "nFlowLinkPts"))
    v_flt = f.createVariable("FlowLinkType", "i4", ("nFlowLink",))
    v_flx = f.createVariable("FlowLink_xu", "f8", ("nFlowLink",))
    v_fly = f.createVariable("FlowLink_yu", "f8", ("nFlowLink",))

    # Variable attributes

    v_msh.long_name = "Delft3D FM aggregated mesh"
    v_msh.cf_role = "mesh_topology"
    v_msh.topology_dimension = "2 d"
    v_msh.node_coordinates = "NetNode_x NetNode_y"
    v_msh.face_node_connectivity = "NetElemNode"
    v_msh.edge_node_connectivity = "NetLink"
    v_msh.edge_face_connectivity = "FlowLink"

    # v_pcs.name = "Unknown projected"
    v_pcs.epsg = 4326
    v_pcs.grid_mapping_name = "Unknown projected"
    v_pcs.longitude_of_prime_meridian = 0.0
    # v_pcs.semi_major_axis = 6378137.
    # v_pcs.semi_minor_axis = 6356752.314245
    v_pcs.inverse_flattening = 298.257223563
    v_pcs.epsg_code = "EPSG:4326"
    v_pcs.value = "value is equal to EPSG code"

    v_nnx.units = "degrees_east"
    v_nnx.standard_name = "longitude"
    v_nnx.long_name = "longitude"

    v_nny.units = "degrees_north"
    v_nny.standard_name = "latitude"
    v_nny.long_name = "latitude"

    v_nnz.units = "m"
    v_nnz.positive = "up"
    v_nnz.standard_name = "sea_floor_depth"
    v_nnz.long_name = "Bottom level at net nodes (flow element's corners)"
    v_nnz.coordinates = "NetNode_x NetNode_y"

    v_nlk.long_name = "link between two netnodes"
    v_nlk.start_index = 1

    v_nen.long_name = "Net element defined by nodes"
    v_nen.start_index = 1
    # v_nen._FillValue = 0

    v_flk.long_name = "link/interface between two flow elements"
    v_flk.start_index = 1

    v_flt.long_name = "type of flowlink"
    v_flt.valid_range = 1, 2
    v_flt.flag_values = 1, 2
    v_flt.flag_meanings = "link_between_1D_flow_elements link_between_2D_flow_elements"

    v_flx.units = "degrees_east"
    v_flx.standard_name = "longitude"
    v_flx.long_name = "x-Coordinate of velocity point on flow link."

    v_fly.units = "degrees_north"
    v_fly.standard_name = "latitude"
    v_fly.long_name = "y-Coordinate of velocity point on flow link."

    # Global attributes

    f.institution = "Deltares"
    f.references = "http://www.deltares.nl"
    time_string = time.strftime("%b %d %Y, %H:%M:%S")
    f.source = "Wflow, Deltares, %s." % time_string
    offset_s = -time.altzone
    offset_m = int((offset_s % 3600) / 60)
    offset_h = int((offset_s / 60 - offset_m) / 60)
    time_string = time.strftime("%Y-%m-%dT%H:%M:%S") + "+%02i%02i" % (
        offset_h,
        offset_m,
    )
    f.history = "Created on %s, wflow_delwaq.py" % time_string
    f.Conventions = "CF-1.6 UGRID-0.9"

    # Data

    v_nnx[:] = nodes_x
    v_nny[:] = nodes_y
    v_nnz[:] = nodes_z
    v_nlk[:, :] = net_links + 1  # uses 1-based indexes
    v_nen[:, :] = elem_nodes + 1  # uses 1-based indexes
    v_flk[:, :] = flow_links + 1  # uses 1-based indexes
    v_flt[:] = 2
    v_flx[:] = 0
    v_fly[:] = 0

    f.close()


def dw_WriteBndFile(fname, ptid_map, pointer, pointer_labels, areas, source_ids):
    """
    Writes Delwaq *.bnd file.

    input:
    - fname          : output file name (without file extension)
    - ptid_map       : PCRaster map with unique id's
    - pointer        : delwaq pointers
    - pointer_labels : numpy array with pointer types
    - areas          : area id per inflow
    - source_ids     : list of source names

    A unique boundary is generated per source for all segments in a given area.
    A unique boundary is generated for each outflow.
    """
    buff = ""
    np_ptid = pcr.pcr2numpy(ptid_map, -1)
    area_ids = unique(areas)

    # Upper-left and lower-right Coordinates

    zero_map = pcr.scalar(ptid_map) * 0.0
    pcr.setglobaloption("coorul")  # upper-left cell corners
    xxul = pcr.pcr2numpy(pcr.xcoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    yyul = pcr.pcr2numpy(pcr.ycoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    pcr.setglobaloption("coorlr")  # lower-right cell corners
    xxlr = pcr.pcr2numpy(pcr.xcoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)
    yylr = pcr.pcr2numpy(pcr.ycoordinate(pcr.boolean(pcr.cover(zero_map + 1, 1))), -1)

    # Map dimensions

    m, n = np_ptid.shape

    # Build grid cell index lookup

    cell_indexes = {}
    for i in range(m):
        for j in range(n):
            if np_ptid[i, j] > 0:
                cell_indexes[np_ptid[i, j]] = (i, j)

    # Counter for number of boundaries

    n_boundaries = 0

    # Outflows

    for i_count, i_pointer in enumerate(numpy.where(pointer_labels < 0)[0]):
        segnum = pointer[i_pointer, 0]
        bndnum = pointer[i_pointer, 1]
        buff += "Outflow_%i\n" % (i_count + 1)
        buff += "1\n"
        n_boundaries += 1

        # Find a cell edge with no active neighbour

        i, j = cell_indexes[segnum]
        if i == 0 or np_ptid[i - 1, j] < 0:
            # first row or upper neighbour inactive: use upper edge
            point_a = xxul[i, j], yyul[i, j]
            point_b = xxlr[i, j], yyul[i, j]
        elif j == 0 or np_ptid[i, j - 1] < 0:
            # first column or left neighbour inactive: use left edge
            point_a = xxul[i, j], yylr[i, j]
            point_b = xxul[i, j], yyul[i, j]
        elif i == m - 1 or np_ptid[i + 1, j] < 0:
            # last row or lower neighbour inactive: use lower edge
            point_a = xxul[i, j], yylr[i, j]
            point_b = xxlr[i, j], yylr[i, j]
        elif j == n - 1 or np_ptid[i, j + 1]:
            # last column or right neighbour inactive: use right edge
            point_a = xxlr[i, j], yyul[i, j]
            point_b = xxlr[i, j], yylr[i, j]
        else:
            # no inactive neighbour: use upper left corner
            point_a = xxul[i, j], yyul[i, j]
            point_b = point_a

        buff += "%i %e %e %e %e\n" % (
            bndnum,
            point_a[0],
            point_a[1],
            point_b[0],
            point_b[1],
        )

    # Sort inflows per area and source

    d = {area_id: {source_id: [] for source_id in source_ids} for area_id in area_ids}
    for i_inflow, i_pointer in enumerate(numpy.where(pointer_labels > 0)[0]):
        source_id = source_ids[pointer_labels[i_pointer] - 1]
        area_id = areas[i_inflow]
        d[area_id][source_id].append(i_pointer)

    # Generate inflow boundaries for each area-source pair

    for area_id in area_ids:
        for source_id in source_ids:
            if not d[area_id][source_id]:
                continue
            buff += "Inflow_%s_%s\n" % (area_id, source_id)
            buff += "%i\n" % (len(d[area_id][source_id]))
            n_boundaries += 1
            for i_pointer in d[area_id][source_id]:
                segnum = pointer[i_pointer, 1]
                bndnum = pointer[i_pointer, 0]
                # Compute center coordinates of cell
                i, j = cell_indexes[segnum]
                x = (xxul[i, j] + xxlr[i, j]) * 0.5
                y = (yyul[i, j] + yylr[i, j]) * 0.5
                buff += "%i %e %e %e %e\n" % (bndnum, x, y, x, y)

    # Write file
    f = open(fname + ".bnd", "w")
    f.write("%i\n" % n_boundaries)
    f.write(buff)
    f.close()


def dw_WriteSurfaceFile(fname, block):
    """
    Generates a Delwaq surface (*.srf) file.
    """
    f = open(fname, "wb")
    f.write(struct.pack("i", 0))
    f.write(struct.pack("%if" % len(block), *block))
    f.close()


def dw_WriteAttributesFile(fname, noseg):
    """
    Generates a Delwaq atributes (*.atr) file.

    input:
    - fname : file name to write to
    - noseg : number of delwaq segments
    """
    line_length = 100
    n_lines = noseg // line_length
    remaining_length = noseg % line_length

    buff = ""
    buff += "         ; DELWAQ_COMPLETE_ATTRIBUTES\n"
    buff += "    2    ; two blocks with input\n"
    buff += "    1    ; number of attributes, they are :\n"
    buff += "    1    ;  '1' is active '0' is no\n"
    buff += "    1    ; data follows in this fil\n"
    buff += "    1    ; all data is given without defaults\n"
    buff += ";    layer:            1\n"
    for iline in range(n_lines):
        buff += " ".join(["1" for _ in range(line_length)])
        buff += "\n"
    buff += " ".join(["1" for _ in range(remaining_length)])
    buff += "\n"

    buff += "    1    ; number of attributes, they are :\n"
    buff += "    2    ;  '1' has surface '3' has bottom\n"
    buff += "         ;  '0' has both    '2' has none\n"
    buff += "    1    ; data follows in this file\n"
    buff += "    1    ; all data is given without defaults\n"
    buff += ";    layer:            1\n"
    for iline in range(n_lines):
        buff += " ".join(["0" for _ in range(line_length)])
        buff += "\n"
    buff += " ".join(["0" for _ in range(remaining_length)])
    buff += "\n"

    buff += "    0    ; no time dependent attributes\n"
    f = open(fname, "w")
    f.write(buff)
    f.close()


def dw_WriteHydFile(fname, d):
    """
    Generates a Delwaq *.hyd file.

    d is dict holding all the required data:
        - d['runid']  : current run id
        - d['tref']   : reference time of simulation as datetime
        - d['tstart'] : start time of simulation as datetime
        - d['tstop']  : stop time of simulation as datetime
        - d['tstep']  : timestep of simulation as timedelta
        - d['m']      : number of grid cells in 1st direction
        - d['n']      : number of grid cells in 2nd direction
    """

    def datetime2str(dt):
        return "{:04}{:02}{:02}{:02}{:02}{:02}".format(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
        )

    def timedelta2str(td):
        return "{:04}{:02}{:02}{}".format(
            0, 0, td.days, time.strftime("%H%M%S", time.gmtime(td.seconds))
        )

    buff = ""
    buff += "task      full-coupling\n"
    buff += "geometry  unstructured\n"
    buff += "horizontal-aggregation       no\n"
    buff += "minimum-vert-diffusion-used  no\n"
    buff += "vertical-diffusion           calculated\n"
    buff += "description\n"
    buff += "'%-60s'\n" % "Generated by Wflow"
    buff += "'%s'\n" % (" " * 60)
    buff += "'%s'\n" % (" " * 60)
    buff += "end-description\n"
    buff += "reference-time           '%s'\n" % (datetime2str(d["tref"]))
    buff += "hydrodynamic-start-time  '%s'\n" % (datetime2str(d["tstart"]))
    buff += "hydrodynamic-stop-time   '%s'\n" % (datetime2str(d["tstop"]))
    buff += "hydrodynamic-timestep    '%s'\n" % (timedelta2str(d["tstep"]))
    buff += "conversion-ref-time      '%s'\n" % (datetime2str(d["tref"]))
    buff += "conversion-start-time    '%s'\n" % (datetime2str(d["tstart"]))
    buff += "conversion-stop-time     '%s'\n" % (datetime2str(d["tstop"]))
    buff += "conversion-timestep      '%s'\n" % (timedelta2str(d["tstep"]))
    buff += "grid-cells-first-direction              %7i\n" % d["noseg"]
    buff += "grid-cells-second-direction             %7i\n" % 1
    buff += "number-hydrodynamic-layers              %7i\n" % 1
    buff += "number-horizontal-exchanges             %7i\n" % d["noqh"]
    buff += "number-vertical-exchanges               %7i\n" % d["noqv"]
    buff += "number-water-quality-segments-per-layer %7i\n" % d["nosegh"]
    buff += "number-water-quality-layers      1\n"
    buff += "hydrodynamic-file        none\n"
    buff += "aggregation-file         none\n"
    buff += "boundaries-file          '%s.bnd'\n" % d["runid"]
    buff += "waqgeom-file             '%s_waqgeom.nc'\n" % d["runid"]
    buff += "volumes-file             '%s.vol'\n" % d["runid"]
    buff += "areas-file               '%s.are'\n" % d["runid"]
    buff += "flows-file               '%s.flo'\n" % d["runid"]
    buff += "pointers-file            '%s.poi'\n" % d["runid"]
    buff += "lengths-file             '%s.len'\n" % d["runid"]
    buff += "salinity-file            none\n"
    buff += "temperature-file         none\n"
    buff += "vert-diffusion-file      none\n"
    buff += "horizontal-surfaces-file '%s.srf'\n" % d["runid"]
    buff += "depths-file              none\n"
    buff += "discharges-file          none\n"
    buff += "chezy-coefficients-file  none\n"
    buff += "shear-stresses-file      none\n"
    buff += "walking-discharges-file  none\n"
    buff += "attributes-file          '%s.atr'\n" % d["runid"]
    buff += "constant-dispersion\n"
    buff += "   first-direction    0.0000E+00\n"
    buff += "   second-direction   0.0000E+00\n"
    buff += "   third-direction    0.0000E+00\n"
    buff += "end-constant-dispersion\n"
    buff += "hydrodynamic-layers\n"
    buff += "          1.000\n"
    buff += "end-hydrodynamic-layers\n"
    buff += "water-quality-layers\n"
    buff += "        1.000\n"
    buff += "end-water-quality-layers\n"
    buff += "discharges\n"
    buff += "end-discharges\n"
    f = open(fname, "w")
    f.write(buff)
    f.close()


# TODO: fix this for pcraster maps
def read_timestep(nc, var, timestep, logger, caseId, runId):
    """
    Returns a map of the given variable at the given timestep.
    """
    if nc is not None:
        pcrmap, succes = nc.gettimestep(timestep, logger, var=var)
        assert succes
        return pcrmap
    else:
        return _readTS(caseId + "/" + runId + "/outmaps/" + var, timestep)


def usage(*args):
    sys.stdout = sys.stderr
    for msg in args:
        print(msg)
    print(__doc__)
    sys.exit(0)


pointer = ""


def main():

    from dateutil import parser

    # global caseId, runId
    caseId = "default_hbv"
    runId = "run_default"
    dwdir = "dw_rhine"
    areamap = "staticmaps/wflow_subcatch.map"
    timeSteps = 1
    timestepsecs = 86400
    configfile = "wflow_sbm.ini"
    sourcesMap = []
    WriteAscii = False
    Write_Dynamic = False
    Write_Structure = True
    # T0 = datetime.strptime("2000-01-01 00:00:00",'%Y-%m-%d %H:%M:%S')

    try:
        opts, args = getopt.getopt(sys.argv[1:], "adD:C:R:S:hT:s:O:A:jc:n:")
    except getopt.error as msg:
        pcrut.usage(msg)

    nc_outmap_file = None

    for o, a in opts:
        if o == "-C":
            caseId = a
        if o == "-R":
            runId = a
        if o == "-D":
            dwdir = a
        if o == "-d":
            Write_Dynamic = True
        if o == "-f":
            Write_Structure = False
        if o == "-s":
            timestepsecs = int(a)
        if o == "-S":
            sourcesMap.append(a)
        if o == "-h":
            usage()
        # if o == '-T': timeSteps = int(a)
        if o == "-A":
            areamap = a.strip()
        if o == "-c":
            configfile = a.strip()
        # if o == '-O': T0 = datetime.strptime(a,'%Y-%m-%d %H:%M:%S')
        if o == "-n":
            nc_outmap_file = a.strip()

    global pointer
    dw_CreateDwRun(dwdir)

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(caseId + "/" + configfile)

    timestepsecs = int(configget(config, "model", "timestepsecs", str(timestepsecs)))

    st = configget(config, "run", "starttime", "None")
    runlengthdetermination = configget(config, "run", "runlengthdetermination", "steps")

    logger = pcrut.setlogger(dwdir + "/debug/wflow_delwaq.log", "wflow_delwaq")

    if st == "None":  # try from the runinfo file
        rinfo_str = configget(config, "run", "runinfo", "None")
        if rinfo_str != "None":
            T0 = wflow_adapt.getStartTimefromRuninfo(caseId + "/" + rinfo_str)
            datetimeend = wflow_adapt.getEndTimefromRuninfo(caseId + "/" + rinfo_str)
        else:
            logger.error(
                "Not enough information in the [run] section. Need start and end time or a runinfo.xml file...."
            )
            sys.exit(1)
    else:
        T0 = parser.parse(st)
        ed = configget(self._userModel().config, "run", "endtime", "None")
        if ed != "None":
            datetimeend = parser.parse(ed)
        else:
            logger.error("No end time given with start time: [run] endtime = " + ed)
            sys.exit(1)

    if runlengthdetermination == "steps":
        runStateTime = T0 - datetime.timedelta(seconds=timestepsecs)
    else:
        runStateTime = T0

    timeSteps = (
        calendar.timegm(datetimeend.utctimetuple())
        - calendar.timegm(runStateTime.utctimetuple())
    ) / timestepsecs

    #: we need one delwaq calculation timesteps less than hydrology
    # timeSteps = timeSteps # need one more hydrological timestep as dw timestep
    firstTimeStep = 0

    # caseid = "default_hbv"
    logger.info("T0 of run: " + str(T0))
    boundids = len(sourcesMap)  # extra number of exchanges for all bounds

    # Number of exchnages is elements minus number of outflows!!

    # Get subcatchment data
    logger.info("Reading basemaps")

    wflow_subcatch = (
        caseId
        + "/"
        + configget(config, "model", "wflow_subcatch", "/staticmaps/wflow_subcatch.map")
    )
    pcr.setclone(wflow_subcatch)
    amap = pcr.scalar(pcr.readmap(caseId + "/" + areamap))
    modelmap = pcr.readmap(wflow_subcatch)
    ldd = pcr.readmap(
        caseId
        + "/"
        + configget(config, "model", "wflow_ldd", "/staticmaps/wflow_ldd.map")
    )
    gauges = pcr.readmap(
        caseId
        + "/"
        + configget(config, "model", "wflow_gauges", "/staticmaps/wflow_gauges.map")
    )
    if nc_outmap_file is not None:
        nc_outmap_file = caseId + "/" + runId + "/" + nc_outmap_file

    # Some models yield a reallength.map, others a rl.map.
    rl_map_file = caseId + "/" + runId + "/outsum/rl.map"
    if not os.path.exists(rl_map_file):
        rl_map_file = caseId + "/" + runId + "/outsum/reallength.map"
    cellsize = float(pcr.pcr2numpy(pcr.readmap(rl_map_file), np.nan)[0, 0])
    logger.info("Cellsize model: " + str(cellsize))

    # Limit areas map to modelmap (subcatchments)
    amap = pcr.ifthen(modelmap > 0, amap)
    ldd = pcr.ifthen(amap > 0, ldd)
    pcr.report(amap, dwdir + "/debug/area.map")
    pcr.report(ldd, dwdir + "/debug/ldd.map")
    pcr.report(modelmap, dwdir + "/debug/modelmap.map")

    thecells = pcr.pcr2numpy(modelmap, np.nan).flatten()
    nrcells = len(thecells)
    nractcells = len(thecells[np.isfinite(thecells)])

    logger.info("Total number gridcells (including inactive): " + str(nrcells))
    logger.info("Total number of used gridcells: " + str(nractcells))

    # find all upstream cells (these must be set negative)
    upbound = pcr.upstream(ldd, 1.0)
    upbound = pcr.ifthen(upbound == 0, upbound)
    upar = pcr.pcr2numpy(pcr.scalar(upbound), np.nan).flatten()
    logger.info(
        "Number of upstream cells (without upstream connection): "
        + str(len(upar[np.isfinite(upar)]))
    )
    pcr.report(upbound, dwdir + "/debug/upbound.map")

    if Write_Structure:
        # get pointer an boundaries from ldd, subcatch and defined boundaries (P only now)
        ptid, pointer, pointer_labels, segments, areas = dw_mkDelwaqPointers(
            ldd, amap, boundids, 1
        )

        save(dwdir + "/debug/pointer.npy", pointer)
        save(dwdir + "/debug/segments.npy", segments)
        save(dwdir + "/debug/areas.npy", areas)

        # Write id maps to debug area
        pcr.report(ptid, dwdir + "/debug/ptid.map")
        logger.info("Unique areas: " + str(unique(areas)))
        # logger.info("Number of area inflows: " + str(len(areas) * boundids))
        logger.info("Number of segments: " + str(len(segments.flatten())))
        logger.info(
            "Number of internal flows: " + str(len(pointer_labels[pointer_labels == 0]))
        )
        logger.info("outflow  ids: " + str(pointer[pointer[:, 1] < 0, 0:2]))
        logger.info("source maps: " + str(sourcesMap))

        NOSQ = segments.shape[0]
        NOQ = pointer.shape[0]

        dw_WriteNrSegments(dwdir + "/includes_deltashell/B3_nrofseg.inc", NOSQ)
        # Write pointer file
        # TODO: add sources maps here (no only one source supported)
        dw_WritePointer(dwdir + "/includes_deltashell/B4_pointer.inc", pointer)
        # Write the number of exchanges
        dw_WriteNrExChnages(dwdir + "/includes_deltashell/B4_nrofexch.inc", NOQ)
        dw_WriteBoundlist(
            dwdir + "/includes_deltashell/B5_boundlist.inc", pointer, areas, sourcesMap
        )
        dw_WriteBoundData(
            dwdir + "/includes_deltashell/B5_bounddata.inc", unique(areas)
        )

        dw_WriteInitials(dwdir + "/includes_deltashell/B8_initials.inc", sourcesMap)
        dw_Write_Substances(
            dwdir + "/includes_deltashell/B1_sublist.inc", unique(areas)
        )
        dw_Write_B2_outlocs(dwdir + "/includes_deltashell/B2_outlocs.inc", gauges, ptid)

    internalflowwidth = pcr.readmap(caseId + "/" + runId + "/outsum/Bw.map")
    internalflowlength = pcr.readmap(caseId + "/" + runId + "/outsum/DCL.map")
    surface_map = internalflowwidth * internalflowlength
    surface_block = dw_pcrToDataBlock(surface_map)
    logger.info("Writing surface.dat. Nr of points: " + str(np.size(surface_block)))
    dw_WriteSegmentOrExchangeData(
        0, dwdir + "/includes_flow/surface.dat", surface_block, 1, WriteAscii
    )

    # create dummy length file
    length_block = np.zeros(pointer.shape[0] * 2) + 0.5
    # write  length file
    logger.info("Writing length.dat. Nr of points: " + str(np.size(length_block)))
    dw_WriteSegmentOrExchangeData(
        0, dwdir + "/includes_flow/length.dat", length_block, 1, WriteAscii
    )

    # write static data for hyd-file set
    comroot = os.sep.join([dwdir, "com", runId])
    mmax, nmax = dw_GetGridDimensions(ptid)
    dw_WritePointer(comroot + ".poi", pointer, binary=True)
    dw_WriteSurfaceFile(comroot + ".srf", surface_block)
    dw_WriteSegmentOrExchangeData(0, comroot + ".len", length_block, 1, WriteAscii)

    logger.info("Writing waq geometry file")
    dw_WriteWaqGeom(comroot, ptid, ldd)

    logger.info("Writing boundary file")
    dw_WriteBndFile(comroot, ptid, pointer, pointer_labels, areas, sourcesMap)

    # mask to filter out inactive segments
    zero_map = 0.0 * pcr.scalar(ptid)

    # Open nc outputmaps file
    if nc_outmap_file is not None:
        nc = wf_netcdfio.netcdfinput(
            nc_outmap_file, logger, ["vol", "kwv", "run", "lev", "inw"]
        )
    else:
        nc = None

    ts = 1

    if Write_Dynamic:
        dw_Write_Times(dwdir + "/includes_deltashell/", T0, timeSteps - 1, timestepsecs)

        for i in range(firstTimeStep, timeSteps * timestepsecs, timestepsecs):

            volume_map = read_timestep(nc, "vol", ts, logger, caseId, runId)
            volume_block = dw_pcrToDataBlock(volume_map)

            # volume for each timestep and number of segments

            logger.info(
                "Writing volumes.dat. Nr of points: " + str(np.size(volume_block))
            )
            dw_WriteSegmentOrExchangeData(
                i, dwdir + "/includes_flow/volume.dat", volume_block, 1, WriteAscii
            )

            # Now write the flows (exchnages)
            # First read the flows in the kinematic wave reservoir (internal exchnages)
            flow = read_timestep(nc, "run", ts, logger, caseId, runId)
            flow_block_Q = dw_pcrToDataBlock(flow)
            # now the inw
            flowblock = flow_block_Q

            wlevel = read_timestep(nc, "lev", ts, logger, caseId, runId)
            areadyn = wlevel * internalflowwidth
            area_block_Q = dw_pcrToDataBlock(areadyn)
            area_block = area_block_Q

            # Now read the inflows in each segment (water that enters the kinamatic
            # wave reservoir). Also write the areas
            for source in sourcesMap:
                logger.info("Step: " + str(ts) + " source: " + str(source))
                thesource = read_timestep(nc, source, ts, logger, caseId, runId)
                thesource = zero_map + thesource
                flow_block_IN = dw_pcrToDataBlock(thesource)
                flowblock = np.hstack((flowblock, flow_block_IN))
                area_block = np.hstack((area_block, surface_block))

            logger.info("Writing flow.dat. Nr of points: " + str(np.size(flowblock)))
            dw_WriteSegmentOrExchangeData(
                i, dwdir + "/includes_flow/flow.dat", flowblock, 1, WriteAscii
            )
            logger.info("Writing area.dat. Nr of points: " + str(np.size(area_block)))
            dw_WriteSegmentOrExchangeData(
                i, dwdir + "/includes_flow/area.dat", area_block, 1, WriteAscii
            )

            # write dynamic data for hyd-file set
            dw_WriteSegmentOrExchangeData(
                i, comroot + ".vol", volume_block, 1, WriteAscii
            )
            dw_WriteSegmentOrExchangeData(i, comroot + ".flo", flowblock, 1, WriteAscii)
            dw_WriteSegmentOrExchangeData(
                i, comroot + ".are", area_block, 1, WriteAscii
            )

            ts = ts + 1

        """
        Write last volume block with current kinwavevol
        """
        ts = ts - 1
        i = i + timestepsecs
        logger.info("Writing last step..")

        logger.info("Writing area.dat. Nr of points: " + str(np.size(area_block)))
        dw_WriteSegmentOrExchangeData(
            i, dwdir + "/includes_flow/area.dat", area_block, 1, WriteAscii
        )

        # logger.info("Writing surface.dat. Nr of points: " + str(np.size(surface_block)))
        # dw_WriteSegmentOrExchangeData(i,dwdir + '/includes_flow/surface.dat',surface_block,1,WriteAscii)

        logger.info("Writing flow.dat. Nr of points: " + str(np.size(flowblock)))
        dw_WriteSegmentOrExchangeData(
            i, dwdir + "/includes_flow/flow.dat", flowblock, 1, WriteAscii
        )

        volume_map = read_timestep(nc, "voln", ts, logger, caseId, runId)
        volume_block = dw_pcrToDataBlock(volume_map)
        logger.info("Writing volumes.dat. Nr of points: " + str(np.size(volume_block)))
        dw_WriteSegmentOrExchangeData(
            i, dwdir + "/includes_flow/volume.dat", volume_block, 1, WriteAscii
        )

        # for hyd-file set
        dw_WriteSegmentOrExchangeData(i, comroot + ".are", area_block, 1, WriteAscii)
        dw_WriteSegmentOrExchangeData(i, comroot + ".flo", flowblock, 1, WriteAscii)
        dw_WriteSegmentOrExchangeData(i, comroot + ".vol", volume_block, 1, WriteAscii)

        # Generate attribute file
        atr_file = comroot + ".atr"
        logger.info("Writing attribute file to '%s'" % atr_file)
        dw_WriteAttributesFile(atr_file, NOSQ)

        # Generate hyd-file
        hyd_file = comroot + "_unstructured.hyd"
        logger.info("Writing hyd-file to '%s'" % hyd_file)
        hydinfo = {}
        hydinfo["runid"] = runId
        hydinfo["tref"] = T0
        hydinfo["tstart"] = T0
        hydinfo["tstop"] = T0 + timedelta(seconds=(timeSteps - 1) * timestepsecs)
        hydinfo["tstep"] = timedelta(seconds=timestepsecs)
        hydinfo["noseg"] = NOSQ
        hydinfo["nosegh"] = NOSQ
        hydinfo["noqh"] = pointer.shape[0]
        hydinfo["noqv"] = 0
        dw_WriteHydFile(hyd_file, hydinfo)


if __name__ == "__main__":
    main()
