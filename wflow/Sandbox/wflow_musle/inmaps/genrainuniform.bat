gdal_translate -of PCRaster -ot Float32 clone.asc clone.map
pcrcalc P0000000.001 = clone.map + %1
pcrcalc P0000000.002 = clone.map + %1
pcrcalc P0000000.003 = clone.map + %1
pcrcalc P0000000.004 = clone.map + %1
pcrcalc P0000000.005 = clone.map + %1
pcrcalc P0000000.006 = clone.map + %1
pcrcalc P0000000.007 = clone.map + %1
pcrcalc P0000000.008 = clone.map + %1
pcrcalc P0000000.009 = clone.map + %1
pcrcalc P0000000.010 = clone.map + %1


pause