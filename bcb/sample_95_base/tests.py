from task import task_func

import unittest
import pandas as pd


class TestCases(unittest.TestCase):
    def test_reproducibility(self):
        df1 = task_func(random_seed=42)
        df2 = task_func(random_seed=42)
        pd.testing.assert_frame_equal(df1, df2)

    def test_dataframe_structure(self):
        df = task_func()
        self.assertEqual(list(df.columns), ["Month", "Category", "Sales"])
        self.assertEqual(len(df), 60)  # 12 months * 5 categories

    def test_invalid_categories(self):
        with self.assertRaises(ValueError):
            task_func(categories="Not a list")

    def test_invalid_months(self):
        with self.assertRaises(ValueError):
            task_func(months=123)

    def test_custom_categories_and_months(self):
        custom_categories = ["A", "B", "C"]
        custom_months = ["Jan", "Feb"]
        df = task_func(categories=custom_categories, months=custom_months)
        self.assertEqual(len(df), len(custom_categories) * len(custom_months))
        self.assertTrue(set(df["Category"]).issubset(custom_categories))
        self.assertTrue(set(df["Month"]).issubset(custom_months))

    def test_values(self):
        df = task_func()
        df_list = df.apply(lambda row: ",".join(row.values.astype(str)), axis=1).tolist()
        with open("df_contents.txt", "w") as file:
            file.write(str(df_list))
