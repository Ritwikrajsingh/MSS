# -*- coding: utf-8 -*-
"""

    mslib.utils.airdata
    ~~~~~~~~~~~~~~~~

    Functions for getting and downloading airspaces and airports.

    This file is part of mss.

    :copyright: Copyright 2021 May Bär
    :copyright: Copyright 2021-2022 by the mss team, see AUTHORS.
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


import csv
import defusedxml.ElementTree as etree
import humanfriendly
import os
import requests
import re as regex
from PyQt5 import QtWidgets
import logging
import time

from mslib.msui.constants import MSS_CONFIG_PATH


_airspaces = []
_airports = []
_airports_mtime = 0
_airspaces_mtime = {}
_airspace_url = "https://storage.googleapis.com/29f98e10-a489-4c82-ae5e-489dbcd4912f"
_airspace_download_url = "https://storage.googleapis.com/storage/v1/b/29f98e10-a489-4c82-ae5e-489dbcd4912f/o/" \
                         "{}_asp.xml?alt=media"
# Updated Dec 07 2021
_airspace_cache = \
    [('al_asp.xml', '2817'), ('ar_asp.xml', '262968'), ('at_asp.xml', '20933'), ('au_asp.xml', '1686931'),
     ('ba_asp.xml', '20865'), ('be_asp.xml', '70624'), ('bg_asp.xml', '4696'), ('bh_asp.xml', '23073'),
     ('br_asp.xml', '250204'), ('ca_asp.xml', '1011153'), ('ch_asp.xml', '28961'), ('co_asp.xml', '38061'),
     ('cz_asp.xml', '143524'), ('de_asp.xml', '217490'), ('dk_asp.xml', '19854'), ('ee_asp.xml', '17761'),
     ('es_asp.xml', '255423'), ('fi_asp.xml', '25058'), ('fr_asp.xml', '319716'), ('gb_asp.xml', '1410038'),
     ('gr_asp.xml', '55492'), ('hr_asp.xml', '135531'), ('hu_asp.xml', '52526'), ('ie_asp.xml', '61167'),
     ('is_asp.xml', '10499'), ('it_asp.xml', '1063320'), ('jp_asp.xml', '540727')]


def download_progress(file_path, url, progress_callback=lambda f: logging.info(f"{int(f)}KB Downloaded")):
    """
    Downloads the file at the given url to file_path and keeps track of the progress
    """
    try:
        with open(file_path, "wb+") as file:
            logging.info(f"Downloading to {file_path}. This might take a while.")
            response = requests.get(url, stream=True, timeout=5)
            length = response.headers.get("content-length")
            if length is None:  # no content length header
                file.write(response.content)
            else:
                dl = 0
                for data in response.iter_content(chunk_size=1024 * 1024):
                    dl += len(data)
                    file.write(data)
                    progress_callback(dl / 1024)
    except requests.exceptions.RequestException:
        os.remove(file_path)
        QtWidgets.QMessageBox.information(None, "Download failed", f"{url} was unreachable, please try again later.")


def get_airports(force_download=False):
    """
    Gets or downloads the airports.csv in ~/.config/mss and returns all airports within
    """
    global _airports, _airports_mtime
    file_exists = os.path.exists(os.path.join(MSS_CONFIG_PATH, "airports.csv"))

    if _airports and file_exists and os.path.getmtime(os.path.join(MSS_CONFIG_PATH, "airports.csv")) == _airports_mtime:
        return _airports

    is_outdated = file_exists \
        and (time.time() - os.path.getmtime(os.path.join(MSS_CONFIG_PATH, "airports.csv"))) > 60 * 60 * 24 * 30

    if (force_download or is_outdated or not file_exists) \
            and QtWidgets.QMessageBox.question(None, "Allow download", f"You selected airports to be "
                                               f"{'drawn' if not force_download else 'downloaded (~10 MB)'}." +
                                               ("\nThe airports file first needs to be downloaded or updated (~10 MB)."
                                                if not force_download else "") + "\nIs now a good time?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) \
            == QtWidgets.QMessageBox.Yes:
        download_progress(os.path.join(MSS_CONFIG_PATH, "airports.csv"), "https://ourairports.com/data/airports.csv")

    if os.path.exists(os.path.join(MSS_CONFIG_PATH, "airports.csv")):
        with open(os.path.join(MSS_CONFIG_PATH, "airports.csv"), "r", encoding="utf8") as file:
            _airports_mtime = os.path.getmtime(os.path.join(MSS_CONFIG_PATH, "airports.csv"))
            return list(csv.DictReader(file, delimiter=","))

    else:
        return []


def get_available_airspaces():
    """
    Gets and returns all available airspaces and their sizes from openaip
    """
    try:
        directory = requests.get(_airspace_url, timeout=5)
        if directory.status_code == 404:
            return _airspace_cache
        airspaces = regex.findall(r">(.._asp\.xml)<", directory.text)
        sizes = regex.findall(r".._asp.xml.*?<Size>([0-9]+)<\/Size", directory.text)
        airspaces = [airspace for airspace in zip(airspaces, sizes) if airspace[-1] != "0"]
        return airspaces
    except requests.exceptions.RequestException:
        return _airspace_cache


def update_airspace(force_download=False, countries=["de"]):
    """
    Downloads the requested airspaces from their respective country code if it is over a month old
    """
    global _airspaces, _airspaces_mtime
    for country in countries:
        location = os.path.join(MSS_CONFIG_PATH, f"{country}_asp.xml")
        url = _airspace_download_url.format(country)
        data = [airspace for airspace in get_available_airspaces() if airspace[0].startswith(country)][0]
        file_exists = os.path.exists(location)

        is_outdated = file_exists and (time.time() - os.path.getmtime(location)) > 60 * 60 * 24 * 30

        if (force_download or is_outdated or not file_exists) \
                and QtWidgets.QMessageBox.question(
                    None, "Allow download",
                    f"The selected {country} airspace needs to be downloaded "
                    f"({humanfriendly.format_size(int(data[-1]))})\nIs now a good time?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) \
                == QtWidgets.QMessageBox.Yes:
            download_progress(location, url)


def get_airspaces(countries=[]):
    """
    Gets the .xml files in ~/.config/mss and returns all airspaces within
    """
    global _airspaces, _airspaces_mtime
    reload = False
    files = [f"{country}_asp.xml" for country in countries]
    update_airspace(countries=countries)
    files = [file for file in files if os.path.exists(os.path.join(MSS_CONFIG_PATH, file))]

    if _airspaces and len(files) == len(_airspaces_mtime):
        for file in files:
            if file not in _airspaces_mtime or \
                    os.path.getmtime(os.path.join(MSS_CONFIG_PATH, file)) != _airspaces_mtime[file]:
                reload = True
                break
        if not reload:
            return _airspaces

    _airspaces_mtime = {}
    _airspaces = []
    for file in files:
        fpath = os.path.join(MSS_CONFIG_PATH, file)
        airspace = etree.parse(fpath)
        airspace = airspace.find("AIRSPACES")
        for elem in airspace:
            try:
                airspace_data = {
                    "name": elem.find("NAME").text,
                    "polygon": elem.find("GEOMETRY").find("POLYGON").text,
                    "top": float(elem.find("ALTLIMIT_TOP").find("ALT").text),
                    "top_unit": elem.find("ALTLIMIT_TOP").find("ALT").get("UNIT"),
                    "bottom": float(elem.find("ALTLIMIT_BOTTOM").find("ALT").text),
                    "bottom_unit": elem.find("ALTLIMIT_BOTTOM").find("ALT").get("UNIT"),
                    "country": elem.find("COUNTRY").text
                }
            except TypeError as ex:
                logging.debug("Problem %s in airspaces file %s", (ex, fpath))
                logging.info("A few data of %s is ignored because of an incompatible format.", fpath)
                continue

            # Convert to kilometers
            airspace_data["top"] /= 3281 if airspace_data["top_unit"] == "F" else 32.81
            airspace_data["bottom"] /= 3281 if airspace_data["bottom_unit"] == "F" else 32.81
            airspace_data["top"] = round(airspace_data["top"], 2)
            airspace_data["bottom"] = round(airspace_data["bottom"], 2)
            airspace_data.pop("top_unit")
            airspace_data.pop("bottom_unit")

            airspace_data["polygon"] = [(float(data.split(" ")[0]), float(data.split(" ")[-1]))
                                        for data in airspace_data["polygon"].split(",")]
            _airspaces.append(airspace_data)
            _airspaces_mtime[file] = os.path.getmtime(os.path.join(MSS_CONFIG_PATH, file))
    return _airspaces
