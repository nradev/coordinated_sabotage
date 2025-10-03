import pandas as pd


def create_component_dataframe(transformed_data):
    """
    Create a DataFrame from transformed PCA data with component columns and mean.

    Parameters:
    transformed_data (numpy.array): PCA transformed data

    Returns:
    pandas.DataFrame: DataFrame with component columns and row-wise means
    """
    df = pd.DataFrame(
        transformed_data,
        columns=[f"Component {i + 1}" for i in range(transformed_data.shape[1])],
    )
    df["Mean"] = df.mean(axis=1)
    return df
