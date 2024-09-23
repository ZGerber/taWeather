import numpy as np
from datetime import timedelta
from utils import load_xml_file, convert_to_seconds, parse_time_string, filter_corrections, nearest
from clouds import Clouds
from data_part import DataPart
from pathlib import Path
from plotting import plot_night
from typing import List, Dict, Tuple, Union
import re
import os
import argparse

# Sometimes runners arrive early, and codes are entered before midnight UTC.
# In these cases the time is converted to a negative number, to make comparisons possible.
MIN_SEC = 61200  # Corresponds to 11am MT  (17:00 UTC)
MAX_SEC = 86400  # Corresponds to 6pm MT (midnight UTC)


def parse_user_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--detector", help="brtax4, mdtax4, tale")
    parser.add_argument("infile")
    return parser.parse_args()


def handle_data_nocuts(child, attrib, start_time_list, stop_time_list, missing_clock_stops, n_parts):
    if "parts" in attrib:
        n_parts = int(attrib.get('parts'))
    elif child.find("clock") is not None:
        data_part_clock = child.findall("clock")
        # start = data_part_clock[0].attrib.get('start')
        stop = data_part_clock[0].attrib.get("stop")
        # if start:
        #     start_time = parse_time_string(start)
        # else:
        #     start_time = parse_time_string(attrib.get('time'))
        start_time = attrib.get("time")
        # print(convert_to_seconds(parse_time_string(start_time)))
        start_time_list.append(parse_time_string(start_time))
        if stop:
            stop_time = parse_time_string(stop)
            stop_time_list.append(stop_time)
        elif len(data_part_clock) > 1:
            stop_time = parse_time_string(data_part_clock[1].attrib.get('stop'))
            stop_time_list.append(stop_time)
        else:
            missing_clock_stops.append(len(stop_time_list) + len(missing_clock_stops))
            # print(convert_to_seconds(stop_time_list))
            # print(missing_clock_stops)
    elif child.find("clock") is None:
        n_parts = n_parts - 1  # for empty dataNOCUTS sections
    return n_parts, start_time_list, stop_time_list, missing_clock_stops


def insert_missing_stop_times(missing_clock_stops, stop_time_list, start_time_list, auto_stop_time, emergency_stop_list, other_alarms):
    for m in missing_clock_stops:
        # Insert stop time based on conditions
        if m >= len(stop_time_list):
            stop_time_list.insert(m, auto_stop_time or nearest(emergency_stop_list, start_time_list[m]))
        else:
            stop_time = get_stop_time(m, start_time_list, emergency_stop_list, other_alarms)
            if stop_time is not None:
                stop_time_list.insert(m, stop_time)


def get_stop_time(index, start_time_list, emergency_stop_list, other_alarms):
    # Check for emergency stops first
    if emergency_stop_list:
        try:
            return nearest(emergency_stop_list, start_time_list[index])
        except ValueError:
            pass  # If nearest fails, fall through to check other alarms

    # Check for other alarms if no emergency stop found or if it fails
    if other_alarms:
        try:
            return nearest(other_alarms, start_time_list[index])
        except ValueError:
            pass  # If nearest fails, fall through to next check

    # If no other alarms are available, use start time + 20 minutes
    print(f"WARNING: Could not find stop time. Using start + 20 minutes.")
    return start_time_list[index] + timedelta(minutes=20)


def grep_run_log(infile_path: Path) -> Tuple[
    int, Union[List[int], int], Union[List[int], int], Union[List[int], int], Dict[Union[List[int], int], str]]:
    """Extract relevant data from the log file."""
    root = load_xml_file(infile_path)
    stop_time_list = []
    start_time_list = []
    emergency_stop_list = []
    missing_clock_stops = []
    other_alarms = []
    weat_code_dict = {}
    # run_end_time = None
    auto_stop_time = None
    n_parts = 0

    for child in root.iter():
        tag, attrib = child.tag, child.attrib
        if tag == "dataNOCUTS":
            n_parts, start_time_list, stop_time_list, missing_clock_stops = handle_data_nocuts(child, attrib,
                                                                                               start_time_list,
                                                                                               stop_time_list,
                                                                                               missing_clock_stops,
                                                                                               n_parts)
        elif tag == "alarm":
            if child.text == "Emergency Stop!":
                emergency_stop_list.append(parse_time_string(attrib.get("time")))
            elif re.search(r'^(Sky thread exception!)', child.text):
                other_alarms.append(parse_time_string(attrib.get('time')))
        elif tag == "auto-restart":
            if child.find("auto-stop") is not None:
                # print(child.find("auto-stop").attrib.get('time'))
                other_alarms.append(parse_time_string(child.find("auto-stop").attrib.get('time')))
        elif tag == "auto-stop":
            auto_stop_time = parse_time_string(attrib.get('time'))
        elif tag == "weather":
            weat_code_dict[parse_time_string(attrib.get('time'))] = child.text
        else:
            continue

    if not n_parts:
        raise SystemExit("No data parts found!")

    # If missing clock stops, need to decide if Emergency Stop or auto-stop
    if missing_clock_stops:
        insert_missing_stop_times(missing_clock_stops, stop_time_list, start_time_list, auto_stop_time,
                                  emergency_stop_list, other_alarms)
    run_end_time = sorted(stop_time_list)[-1]
    stop_time_list = [t for t in stop_time_list if min(start_time_list) < t <= run_end_time]

    # Convert datetimes to seconds since midnight
    start_secs = convert_to_seconds(start_time_list)
    stop_secs = convert_to_seconds(stop_time_list)
    run_end_sec = convert_to_seconds(run_end_time)
    emergency_secs = convert_to_seconds(emergency_stop_list)
    weat_code_secs = {convert_to_seconds(dt): code for dt, code in weat_code_dict.items()}

    # for start, stop, end, weat in zip(start_secs, stop_secs, run_end_sec, weat_code_secs):
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
        local_match = re.findall(r'\d{7}', code)
        remote_match = re.match(r'\[(.*?)]\s*(\d{7})', code, re.I)
        if MIN_SEC < timestamp < MAX_SEC:
            timestamp = timestamp - 43200 * 2
        if timestamp < run_start:
            preliminary_weat[timestamp] = Clouds.from_string(local_match[0])
        elif timestamp > run_end:
            postrun_weat[timestamp] = Clouds.from_string(local_match[0])
        elif remote_match:
            remote_weat[timestamp] = Clouds.from_string(remote_match.group(2))
        elif local_match:
            local_weat[timestamp] = Clouds.from_string(local_match[0])
        else:
            print(f"WARNING: Entry at time={timestamp} does not contain a valid 7-digit code!")

    return local_weat, remote_weat, preliminary_weat, postrun_weat


def insert_remote_timestamps(local, remote, max_diff=3600):
    new_local = local.copy()  # Start with the existing local timestamps
    new_remote = remote.copy()  # Start with the existing remote timestamps
    # new_local_weat = local_weat.copy()
    # new_remote_weat = remote_weat.copy()
    changes_made = True  # Track if changes were made

    while changes_made:
        changes_made = False  # Reset flag for this iteration
        for i in range(len(new_local) - 1):
            start = new_local[i]
            end = new_local[i + 1]

            if end - start > max_diff:
                midpoint = (start + end) / 2

                # Find the remote timestamps that fall between start and end
                candidates = [r for r in remote if start < r < end]

                if candidates:
                    # Find the candidate closest to the midpoint
                    closest_candidate = min(candidates, key=lambda x: abs(x - midpoint))
                    new_local.append(closest_candidate)
                    new_remote.remove(closest_candidate)
                    changes_made = True  # A change was made

        # Sort the list to maintain order after insertions
        new_local = sorted(new_local)
        new_remote = sorted(new_remote)
    return new_local, new_remote


if __name__ == "__main__":
    # os.environ["detector"] = "brtax4"
    args = parse_user_args()
    detector = args.detector
    infile = args.infile

    # Load the detector environmental variable
    # detector = os.environ["detector"]

    # Update the path to point to your XML file
    path_to_log = Path(args.infile)

    print(f"\nParsing weather from {path_to_log.stem} ...")

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
    max_secs = np.asarray(start_secs) + 20 * 60

    # Remove corrections from weather codes
    weat_sec_keys = filter_corrections(list(weather_dict.keys()))

    # Split weather data into local and remote detectors
    local_weat, remote_weat, preliminary_weat, postrun_weat = extract_weather_data(weather_dict,
                                                                                   min(start_secs),
                                                                                   max(stop_secs))
    # Extract timestamps of local and remote entries from the dictionary keys
    local_timestamps = [k for k in local_weat]
    remote_timestamps = [k for k in remote_weat]

    # If more than one preliminary weat code, only take the most recent.
    if preliminary_weat:
        preliminary_code = list(preliminary_weat.values())[-1]
        preliminary_time = int(list(preliminary_weat.keys())[-1])

        # Add the preliminary weather and time as a local source:
        local_timestamps.append(preliminary_time)
        local_weat[preliminary_time] = preliminary_code
    else:
        preliminary_code = None
        preliminary_time = None

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
    local_timestamps_filtered = filter_corrections(local_timestamps, time_window=600)
    remote_timestamps_filtered = filter_corrections(remote_timestamps, time_window=600)
    local_weat_filtered = [local_weat[t] for t in local_timestamps_filtered]
    remote_weat_filtered = [remote_weat[t] for t in remote_timestamps_filtered]

    if detector == "brtax4":
        night_weat = {}
        updated_local_timestamps, updated_remote_timestamps = insert_remote_timestamps(local_timestamps_filtered,
                                                                                       remote_timestamps_filtered,
                                                                                       max_diff=3600 * 2)
        local_timestamps_filtered = updated_local_timestamps
        remote_timestamps_filtered = updated_remote_timestamps

        for t in local_timestamps_filtered:
            if t in local_weat.keys():
                night_weat[t] = local_weat[t]
            elif t in remote_weat.keys():
                night_weat[t] = remote_weat[t]
        local_timestamps_filtered = list(night_weat.keys())
        local_weat_filtered = list(night_weat.values())

    # Create dictionary of DataPart objects. Start with the preliminary weather code ("part 0").
    if preliminary_code and preliminary_time:
        data_parts = {0: DataPart(0, 0, 0, 0, 0, preliminary_code, preliminary_time, "local")}
    else:
        data_parts = {0: DataPart(0, 0, 0, 0, 0, None, None, None)}
    output_files = {}

    # Loop over data parts and assign weather codes and timestamps to each part.
    for part_num, (part_start, part_mid, part_end, part_max) in enumerate(
            zip(start_secs, mid_secs, stop_secs, max_secs), 1):
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
        data_part_outfile = Path(
            f"/home/zane/software/txhybrid/weather_files/{detector}/{year}{month}{day}/y{year}m{month.zfill(2)}d{day.zfill(2)}p{str(part_num).zfill(3)}.{detector}.weather.log")
        output_files[part_num] = data_part_outfile
        # with open(data_part_outfile, "w") as weat_out:
    #
    # for (_, dp) in data_parts.items():
    #     print(dp)

    # Plot the night data
    # plot_night(local_timestamps_filtered, remote_timestamps_filtered, np.asarray(start_secs), np.asarray(stop_secs), mid_secs)
    #
    # plot_night(updated_local_timestamps, updated_remote_timestamps,
    #                np.asarray(start_secs), np.asarray(stop_secs),
    #                mid_secs)
    # plot_night(updated_local_timestamps, [], np.asarray(start_secs), np.asarray(stop_secs),
    #                mid_secs)

    for i, dp in data_parts.items():
        if dp.part_number == 0:
            if not dp.weat_code:
                dp.weat_code = data_parts[1].weat_code
            continue
        else:
            out = output_files.get(dp.part_number)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as outfile:
                if dp.part_number == n_data_parts:
                    outfile.write(
                        f"{dp.start_time}   {data_parts[i - 1].weat_code.to_string()}   {dp.weat_code.to_string()}   {dp.weat_code.to_string()}\n")
                else:
                    outfile.write(
                        f"{dp.start_time}   {data_parts[i - 1].weat_code.to_string()}   {dp.weat_code.to_string()}   {data_parts[i + 1].weat_code.to_string()}\n")

    # for (_, dp) in data_parts.items():
    #     print(dp)
