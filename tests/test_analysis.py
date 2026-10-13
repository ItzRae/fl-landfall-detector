import csv

from analyze_landfalls import write_landfalls_csv, write_validation_summary_csv
from src.analysis import landfalls_dataframe


def test_empty_results_preserve_dashboard_and_export_schema(tmp_path):
    frame = landfalls_dataframe([])
    assert frame.empty
    assert frame['landfall_datetime'].dt.year.empty
    output = tmp_path / 'landfalls.csv'
    write_landfalls_csv([], output)
    with output.open() as file:
        assert next(csv.reader(file)) == list(frame.columns)


def test_validation_export_handles_no_matches(tmp_path):
    output = tmp_path / 'validation.csv'
    write_validation_summary_csv([], [], [], [], [], output)
    with output.open() as file:
        row = next(csv.DictReader(file))
    assert row['matched'] == '0'
    assert row['median_time_difference_min'] == ''
