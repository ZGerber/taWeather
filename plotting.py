from typing import Dict
import numpy as np
from matplotlib import pyplot as plt
from clouds import Clouds

def plot_night(local_weat_dict: Dict[int, Clouds], remote_weat_dict: Dict[int, Clouds], sstart: np.ndarray, sstop: np.ndarray, smid: np.ndarray) -> None:
    """Plot the night data."""
    plt.scatter(sstart, np.zeros_like(sstart), color='black', marker="|", s=500)
    plt.scatter(sstop, np.zeros_like(sstop), color='black', marker="|", s=500)
    plt.scatter(smid, np.zeros_like(smid), color='black', marker="|", s=50)
    plt.scatter(local_weat_dict.keys(), np.zeros_like(local_weat_dict), color='green', marker="*", s=50)
    plt.scatter(remote_weat_dict.keys(), np.zeros_like(remote_weat_dict), color='red', marker="*", s=50)
    plt.axhline(0, linestyle=":", color='black', alpha=0.3)
    plt.show()
