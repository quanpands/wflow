-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

Format: 3.0 (quilt)
Source: gdal
Binary: libgdal20, libgdal-dev, libgdal-doc, gdal-bin, gdal-data, python-gdal, python3-gdal, libgdal-perl, libgdal-perl-doc, libgdal-java
Architecture: any all
Version: 2.2.3+dfsg-2
Maintainer: Debian GIS Project <pkg-grass-devel@lists.alioth.debian.org>
Uploaders: Francesco Paolo Lovergine <frankie@debian.org>, Bas Couwenberg <sebastic@debian.org>
Homepage: http://www.gdal.org/
Standards-Version: 4.1.3
Vcs-Browser: https://anonscm.debian.org/cgit/pkg-grass/gdal.git
Vcs-Git: https://anonscm.debian.org/git/pkg-grass/gdal.git
Testsuite: autopkgtest
Build-Depends: debhelper (>= 9.20160114), dh-autoreconf, dh-python, d-shlibs, default-jdk-headless, doxygen, graphviz, ant, chrpath, libarmadillo-dev, libcurl4-gnutls-dev | libcurl-ssl-dev, libdap-dev, libdoxygen-filter-perl, libepsilon-dev (>= 0.9.1-1~), libexpat1-dev, libfreexl-dev (>= 1.0.0), libfyba-dev, libgeos-dev, libgeotiff-dev, libgif-dev, libhdf4-alt-dev, libhdf5-dev (>= 1.8.8), libjpeg-dev, libjson-c-dev, libkml-dev (>= 1.3.0~rc0-3), liblzma-dev, libmodern-perl-perl, default-libmysqlclient-dev, libnetcdf-dev (>= 1:4.0.0), libogdi3.2-dev, libopenjp2-7-dev, libpcre3-dev, libpng-dev, libpoppler-private-dev, libpq-dev, libproj-dev, libqhull-dev, libspatialite-dev (>= 4.3.0-3~), libsqlite3-dev, libtiff-dev, liburiparser-dev, libwebp-dev, libxerces-c-dev, libxml2-dev, netcdf-bin, patch, python-all-dev (>= 2.6.6-3~), python-numpy, python3-all-dev, python3-numpy, swig, unixodbc-dev (>= 2.2.11), zlib1g-dev
Build-Conflicts: automake1.11, python-setuptools
Package-List:
 gdal-bin deb science optional arch=any
 gdal-data deb science optional arch=all
 libgdal-dev deb libdevel optional arch=any
 libgdal-doc deb doc optional arch=all
 libgdal-java deb java optional arch=any
 libgdal-perl deb perl optional arch=any
 libgdal-perl-doc deb doc optional arch=all
 libgdal20 deb libs optional arch=any
 python-gdal deb python optional arch=any
 python3-gdal deb python optional arch=any
Checksums-Sha1:
 0d617de3db642fceff0843ce1f30ae1dd9aa183d 8812900 gdal_2.2.3+dfsg.orig.tar.xz
 e3dafca98b88916885c6e7987a9c7e17e6b23893 178768 gdal_2.2.3+dfsg-2.debian.tar.xz
Checksums-Sha256:
 3f99d84541ec6f174da137166c1002b50ed138dde51d05180ad5c8dd49721057 8812900 gdal_2.2.3+dfsg.orig.tar.xz
 a545f89efa6815eb5d529f2114e9a04a4ba61df233752541369cee92009fc9c0 178768 gdal_2.2.3+dfsg-2.debian.tar.xz
Files:
 7bbbcb850c42019b6c78884761de992d 8812900 gdal_2.2.3+dfsg.orig.tar.xz
 1775467fc82f7b5c7ab60db357f4f3e2 178768 gdal_2.2.3+dfsg-2.debian.tar.xz

-----BEGIN PGP SIGNATURE-----

iQIzBAEBCgAdFiEEgYLeQXBWQI1hRlDRZ1DxCuiNSvEFAlp5edMACgkQZ1DxCuiN
SvGaaBAAuDxtf3j5GnJu5X69MppuictUKImFip1zmhN3iheMd6hFYmAwahgUQgKp
yW+38np7HJ2jKK3xb7P1stRXqbBjCx+d5jQ+t/wzVcOZU0JzIW7hU2PSkOoIYOYi
fr2EikOpCin6G1MUZ54BC4PnWYcw5F5MdUbZjuOiwm96FKkRzA5ikXwCuogmrWSp
/CiAsUiao4FhQp7ZiR/AvHqJ74fMRCiRCFW/qlzOgidiQs06brWfJlrsxzzVUhvo
+f/Zf0GAnz5iFmpzyTU6G1n7HDyR6heH7dkfHM48TB0dba5FnC0daLyc/T0HX6JK
h3nCkLS3CwGMixMqqMNeiYSGjLWc74Ncj7RhXVUL3H9EMOdx7iKmH+NgFSuIQmJZ
hr6Bkbcuv7rUrfPMTpxIwY+F1pjPxcdQYoi6j8g7RpeVj1i6wReI1bmtMYCQtLrz
NkF5i/bAWDbGsAWlq4LjK256SlGls7eeiIACpwoQOEEUNoC1Px56Hv6yqULYGs0w
riGyHLHFL9brcmJEFQx4nmic5nIIIouXU+Xea4KlnEnS6/7ediMYBeiYJGaAkQO3
3Rg5XMgl7uXI3uJ2JS+KRGGnfGvIfyQDItXfJJ3u+PoG3M6ACcspA7AUcIUJeO5U
2ipT34aGacOHSXoNThIqsAVLXdVL+71qJy3yxR6b++VYL6XZtLg=
=XmIQ
-----END PGP SIGNATURE-----
