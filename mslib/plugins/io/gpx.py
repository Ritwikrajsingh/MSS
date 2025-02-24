# -*- coding: utf-8 -*-
"""

    mslib.plugins.io.csv
    ~~~~~~~~~~~~~~~~~~~~

    plugin for gpx format flight track export

    This file is part of mss.

    :copyright: Copyright 2008-2014 Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
    :copyright: Copyright 2011-2014 Marc Rautenhaus (mr)
    :copyright: Copyright 2021 Johannes Roettenbacher
    :copyright: Copyright 2016-2022 by the mss team, see AUTHORS.
    :license: APACHE-2.0, see LICENSE for details.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import os
from fs import open_fs
import gpxpy


def save_to_gpx(filename, name, waypoints):
    if not filename:
        raise ValueError("fileexportname to save flight track cannot be None")
    _dirname, _name = os.path.split(filename)
    _fs = open_fs(_dirname)
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    # add metadata
    gpx.name = name
    gpx.description = "MSS flight track export"

    # create waypoints
    for i, wp in enumerate(waypoints):
        loc = str(wp.location)
        wp_name = loc if loc else str(i)
        gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(wp.lat, wp.lon, name=wp_name))

    with _fs.open(_name, "w") as fh:
        fh.write(gpx.to_xml())
