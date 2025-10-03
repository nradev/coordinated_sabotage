import numpy as np
import matplotlib.pyplot as plt


def create_variance_plot(pca_model):
    """
    Create a plot showing cumulative explained variance.

    Parameters:
    pca_model: Fitted PCA model

    Returns:
    matplotlib.axes._axes.Axes: Plot of cumulative explained variance
    """
    fig, ax = plt.subplots()
    ax.plot(np.cumsum(pca_model.explained_variance_ratio_))
    ax.set_xlabel("Number of Components")
    ax.set_ylabel("Cumulative Explained Variance")
    return ax
