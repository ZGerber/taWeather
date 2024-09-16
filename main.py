import numpy as np
from utils import load_xml_file, time2sec, str2dt, get_weat_by_det, remove_corrections
from clouds import Clouds
from pathlib import Path
from plotting import plot_night
from typing import List, Dict, Tuple
from datetime import datetime


def grep_run_log(infile_path: Path) -> Tuple[List[datetime], List[datetime], int, Dict[int, str]]:
    """Extract relevant data from the log file."""
    root = load_xml_file(infile_path)
    stop_time_list = []
    start_time_list = []
    weat_code_dict = {}
    run_end_time = 0

    for child in root.iter():
        tag, attrib = child.tag, child.attrib
        if tag == "stop-data":
            stop_time = str2dt(attrib.get('time'))
            stop_time_list.append(stop_time)
        elif tag == "clock" and "stop" in attrib:
            stop_time = str2dt(attrib['stop'])
            stop_time_list.append(stop_time)
        elif tag == "auto-stop":
            run_end_time = str2dt(attrib['time'])
            stop_time_list.append(run_end_time)
        elif tag == "dataNOCUTS" and "time" in attrib:
            start_time = str2dt(attrib['time'])
            start_time_list.append(start_time)
        elif tag == "clouds" and "time" in attrib and "code" in attrib:
            weat_code_dict[str2dt(attrib['time'])] = attrib['code']

    # Convert datetimes to seconds since midnight
    start_secs = time2sec(start_time_list)
    stop_secs = time2sec(stop_time_list)
    run_end_sec = time2sec(run_end_time)
    weat_code_secs = {time2sec(dt): code for dt, code in weat_code_dict.items()}

    return start_secs, stop_secs, run_end_sec, weat_code_secs


if __name__ == "__main__":
    # Update the path to point to your XML file
    path_to_log = Path("~/software/txhybrid/src/reconstruction/y2024m05d29.mdtax4.log")

    # Extract data from the log file
    start_secs, stop_secs, run_end_sec, weather_dict = grep_run_log(path_to_log)

    # Calculate mid points between start and stop times
    mid_secs = (start_secs + stop_secs) / 2

    # Remove corrections from weather codes
    weat_sec_keys = remove_corrections(np.array(list(weather_dict.keys())))

    # Split weather data into local and remote detectors
    local_weat, remote_weat, preliminary_weat, postrun_weat = get_weat_by_det(
        weather_dict, start_secs[0], stop_secs[-1])

    # Plot the night data
    plot_night(local_weat, remote_weat, start_secs, stop_secs, mid_secs)
