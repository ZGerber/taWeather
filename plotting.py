from typing import List
import numpy as np
from matplotlib import pyplot as plt


def plot_night(local_weat_list: List[int], remote_weat_list: List[int], sstart: np.ndarray, sstop: np.ndarray, smid: np.ndarray) -> None:
    """Plot the night data."""
    plt.scatter(sstart, np.zeros_like(sstart), color='black', marker="|", s=500)
    plt.scatter(sstop, np.zeros_like(sstop), color='black', marker="|", s=500)
    plt.scatter(smid, np.zeros_like(smid), color='black', marker="|", s=50)
    plt.scatter(local_weat_list, np.zeros_like(local_weat_list), color='green', marker="*", s=50, label="local")
    plt.scatter(remote_weat_list, np.zeros_like(remote_weat_list), color='red', marker="*", s=50, label="remote")
    plt.axhline(0, linestyle=":", color='black', alpha=0.3)
    plt.legend()
    plt.show()
