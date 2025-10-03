import numpy as np
from sklearn.decomposition import PCA


def apply_pca_transformation(data_matrix, n_components=2):
    """
    Apply PCA transformation to the input data matrix.

    Parameters:
    data_matrix (numpy.array): The 2D data matrix.
    n_components (int): Number of components for PCA.

    Returns:
    tuple: (transformed_data, pca_model)
        - transformed_data (numpy.array): PCA transformed data
        - pca_model: Fitted PCA model
    """
    pca = PCA(n_components=n_components)
    transformed_data = pca.fit_transform(data_matrix)
    return transformed_data, pca
