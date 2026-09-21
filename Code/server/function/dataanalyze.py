import pandas as pd
import numpy as np

class DataAnalyzer:
    """
    A class that helps analyze a pandas DataFrame by inferring column types and 
    providing an English description of the data.
    """

    def __init__(self, sample_size: int = 50):
        """
        :param sample_size: Number of samples to take for date/datetime inference.
        """
        self.sample_size = sample_size

    def guess_column_type(self, series: pd.Series) -> str:
        """
        Infer the column type from a pandas Series.
        Potential types include:
          - numeric (int/float)
          - date/datetime
          - category
          - string/object
        
        This is a simple demonstration and can be adjusted for specific business rules.
        """
        if pd.api.types.is_numeric_dtype(series):
            return "quantitative"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "date/datetime"

        # Attempt to parse date/datetime from random samples
        sample_data = series.dropna().sample(
            min(self.sample_size, len(series)), 
            random_state=42
        )
        converted = 0
        for val in sample_data:
            try:
                _ = pd.to_datetime(val, errors='raise')
                converted += 1
            except (ValueError, TypeError):
                pass
        if len(sample_data) > 0 and converted / len(sample_data) > 0.8:
            return "date/datetime"

        # Check if unique ratio is low enough to treat as category
        unique_ratio = series.nunique(dropna=True) / len(series)
        if unique_ratio < 0.1:
            return "category"

        return "nominal"

    def analyze_dataframe_in_english(self, df: pd.DataFrame) -> str:
        """
        Automatically infer the data type of each column in a DataFrame,
        and return an English description. 
        If a column is inferred as 'category', list out its unique categories.
        """
        # Basic info
        num_rows, num_cols = df.shape

        # Build the description
        description = (
            f"This tabular data has {num_rows} rows and {num_cols} columns in total.\n\n"
            "Below is a brief summary of each column:\n"
        )

        for col in df.columns:
            col_type = self.guess_column_type(df[col])

            if col_type == "category":
                # Collect all unique categories
                unique_values = df[col].dropna().unique()
                category_str = ", ".join(map(str, unique_values[:50]))  
                description += (
                    f" - Column '{col}' is represents categorical data. "
                    f"The distinct categories include: {category_str}.\n"
                )
            else:
                description += f" - Column '{col}' is to be {col_type}.\n"

        return description