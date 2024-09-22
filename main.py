import numpy as np
from utils import load_xml_file, convert_to_seconds, parse_time_string, filter_corrections
from clouds import Clouds
from data_part import DataPart
from pathlib import Path
from plotting import plot_night
from typing import List, Dict, Tuple, Union
import re
import os
import argparse


def parse_user_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--detector", help="brtax4, mdtax4, tale")
    parser.add_argument("infile")
    return parser.parse_args()


def grep_run_log(infile_path: Path) -> Tuple[
    int, Union[List[int], int], Union[List[int], int], Union[List[int], int], Dict[Union[List[int], int], str]]:
    """Extract relevant data from the log file."""
    root = load_xml_file(infile_path)
    stop_time_list = []
    start_time_list = []
    emergency_stop_list = []
    weat_code_dict = {}
    run_end_time = 0
    n_parts = 0

    for child in root.iter():
        tag, attrib = child.tag, child.attrib
        if tag == "dataNOCUTS":
            if "parts" in attrib:
                n_parts = int(attrib.get('parts'))
            else:
                data_part_clock = child.find("clock")
                start_time = parse_time_string(data_part_clock.attrib.get('start'))
                start_time_list.append(start_time)
                if data_part_clock.attrib.get("stop"):
                    stop_time = parse_time_string(data_part_clock.attrib.get('stop'))
                    stop_time_list.append(stop_time)
        elif tag == "alarm" and child.text == "Emergency Stop!":
            emergency_stop_list.append(parse_time_string(attrib.get("time")))
        elif tag == "auto-stop":
            run_end_time = parse_time_string(attrib.get('time'))
            stop_time_list.append(run_end_time)
        elif tag == "weather":
            weat_code_dict[parse_time_string(attrib.get('time'))] = child.text

    if not n_parts:
        raise SystemExit("No data parts found!")
    if not run_end_time:
        run_end_time = max(stop_time_list)

    stop_time_list = [t for t in stop_time_list if min(start_time_list) < t <= run_end_time]
    for e in emergency_stop_list:
        if e < min(start_time_list):
            continue
        if e > run_end_time:
            stop_time_list.append(e)
            break

    # Convert datetimes to seconds since midnight
    start_secs = convert_to_seconds(start_time_list)
    stop_secs = convert_to_seconds(stop_time_list)
    run_end_sec = convert_to_seconds(run_end_time)
    weat_code_secs = {convert_to_seconds(dt): code for dt, code in weat_code_dict.items()}

    return n_parts, sorted(start_secs), sorted(stop_secs), run_end_sec, weat_code_secs


def extract_weather_data(weat_code_dict: Dict[int, str], run_start: int, run_end: int) -> \
        Tuple[Dict[int, Clouds], Dict[int, Clouds], Dict[int, Clouds], Dict[int, Clouds]]:
    """
    Categorize weather code dictionary based on the detector's origin (local vs remote) and the time window.

    Args:
        weat_code_dict (Dict[int, str]): Dictionary of weather codes keyed by timestamp.
        run_start (int): Start time of the run in seconds since midnight.
        run_end (int): End time of the run in seconds since midnight.

    Returns:
        Tuple[Dict[int, Clouds], Dict[int, Clouds], Dict[int, Clouds], Dict[int, Clouds]]:
            Four dictionaries categorizing the weather codes:
            - Local detector weather codes
            - Remote detector weather codes
            - Preliminary weather codes
            - Post-run weather codes
    """
    local_weat = {}
    remote_weat = {}
    preliminary_weat = {}
    postrun_weat = {}

    for timestamp, code in weat_code_dict.items():
        match = re.findall(r'\d{7}', code)
        if timestamp < run_start:
            preliminary_weat[timestamp] = Clouds.from_string(match[0])
        elif timestamp > run_end:
            postrun_weat[timestamp] = Clouds.from_string(match[0])
        elif code.isnumeric():
            local_weat[timestamp] = Clouds.from_string(code)
        elif match:
            remote_weat[timestamp] = Clouds.from_string(match[0])
        else:
            print(f"WARNING: Entry at time={timestamp} does not contain a valid 7-digit code!")

    return local_weat, remote_weat, preliminary_weat, postrun_weat


if __name__ == "__main__":
    # os.environ["detector"] = "brtax4"
    args = parse_user_args()
    detector = args.detector
    infile = args.infile

    # Load the detector environmental variable
    # detector = os.environ["detector"]

    # Update the path to point to your XML file
    path_to_log = Path(args.infile)

    print(f"Parsing weather from {path_to_log.stem} ... ...  \n")

    logfile_info = re.findall(r'\d+', path_to_log.stem)
    year = logfile_info[0]
    month = logfile_info[1]
    day = logfile_info[2]
    data_part_number = logfile_info[3]

    # Extract data from the log file
    n_data_parts, start_secs, stop_secs, run_end_sec, weather_dict = grep_run_log(path_to_log)

    # Calculate mid points between start and stop times
    mid_secs = (np.asarray(start_secs) + np.asarray(stop_secs)) / 2

    # The maximum amount of time that a data part can last:
    max_secs = np.asarray(start_secs) + 20*60

    # Remove corrections from weather codes
    weat_sec_keys = filter_corrections(list(weather_dict.keys()))

    # Split weather data into local and remote detectors
    local_weat, remote_weat, preliminary_weat, postrun_weat = extract_weather_data(weather_dict,
                                                                                   min(start_secs),
                                                                                   max(stop_secs))
    # Extract timestamps of local and remote entries from the dictionary keys
    local_timestamps  = [k for k in local_weat]
    remote_timestamps = [k for k in remote_weat]

    # If more than one preliminary (postrun) weat code, only take the most recent (first).
    preliminary_code = list(preliminary_weat.values())[-1]
    preliminary_time = int(list(preliminary_weat.keys())[-1])

    # Add the preliminary weather and time as a local source:
    local_timestamps.append(preliminary_time)
    local_weat[preliminary_time] = preliminary_code

    local_timestamps = sorted(local_timestamps)
    remote_timestamps = sorted(remote_timestamps)

    # If there was a weather code entered after the end of the last data part, add it as a local source.
    # If there are more than one, only keep the first one.
    if postrun_weat:
        postrun_code = list(postrun_weat.values())[0]
        postrun_time = int(list(postrun_weat.keys())[0])
        local_timestamps.append(postrun_time)
        local_weat[postrun_time] = postrun_code

    # Remove codes that are entered too close together.
    # These are assumed to be corrections made by the runner.
    local_timestamps_filtered  = filter_corrections(local_timestamps, time_window=600)
    remote_timestamps_filtered = filter_corrections(remote_timestamps, time_window=600)
    local_weat_filtered        = [local_weat[t] for t in local_timestamps_filtered]
    remote_weat_filtered       = [remote_weat[t] for t in remote_timestamps_filtered]

    # Create dictionary of DataPart objects. Start with the preliminary weather code ("part 0").
    data_parts = {0: DataPart(0, 0, 0, 0, 0, preliminary_code, preliminary_time, "local")}
    output_files = {}

    # Loop over data parts and assign weather codes and timestamps to each part.
    for part_num, (part_start, part_mid, part_end, part_max) in enumerate(zip(start_secs, mid_secs, stop_secs, max_secs), 1):
        ind = np.searchsorted(local_timestamps_filtered, part_mid)
        timestamp_before = local_timestamps_filtered[ind - 1]
        weight_before = np.abs(part_mid - timestamp_before)
        weat_before = local_weat_filtered[ind - 1]

        try:
            timestamp_after = local_timestamps_filtered[ind]
            weat_after = local_weat_filtered[ind]
            weight_after = np.abs(part_mid - local_timestamps_filtered[ind])
        except IndexError:
            timestamp_after = -1
            weat_after = weat_before
            weight_after = weight_before

        if part_start < timestamp_before <= part_end:
            weat_time_during = timestamp_before
        elif part_start < timestamp_after <= part_end:
            weat_time_during = timestamp_after
        else:
            weat_time_during = -1

        weat_during = Clouds.compare_clouds(weat_before,
                                            weat_after,
                                            weight_before,
                                            weight_after,
                                            "twavg")

        part_info = DataPart(part_num,
                             part_start,
                             part_end,
                             int(part_mid),
                             part_max,
                             weat_during,
                             weat_time_during,
                             "local")

        data_parts[part_info.part_number] = part_info
        data_part_outfile = Path(f"/home/zane/software/txhybrid/weather_files/{detector}/{year}{month}{day}/y{year}m{month.zfill(2)}d{day.zfill(2)}p{str(part_num).zfill(3)}.{detector}.weather.log")
        output_files[part_num] = data_part_outfile
        # with open(data_part_outfile, "w") as weat_out:

    for (_, dp) in data_parts.items():
        print(dp)

    # Plot the night data
    plot_night(local_timestamps, remote_timestamps, np.asarray(start_secs), np.asarray(stop_secs), mid_secs)
    # print(output_files)

    for i, dp in data_parts.items():
        if dp.part_number == 0:
            continue
        else:
            out = output_files.get(dp.part_number)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as outfile:
                if dp.part_number == n_data_parts:
                    outfile.write(f"{dp.start_time}   {data_parts[i-1].weat_code.to_string()}   {dp.weat_code.to_string()}   {dp.weat_code.to_string()}\n")
                else:
                    outfile.write(f"{dp.start_time}   {data_parts[i-1].weat_code.to_string()}   {dp.weat_code.to_string()}   {data_parts[i+1].weat_code.to_string()}\n")