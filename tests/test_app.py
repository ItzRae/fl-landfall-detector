from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


def test_state_filters_update_table_and_handle_empty_selection():
    frame = pd.DataFrame({
        'storm_id': ['AL012000', 'AL022001'], 'storm_name': ['FIRST', 'SECOND'],
        'landfall_datetime': pd.to_datetime(['2000-08-01', '2001-09-01']),
        'latitude': [26.0, 29.0], 'longitude': [-81.0, -95.0],
        'max_wind_kt': [80.0, 100.0], 'state': ['Florida', 'Texas'],
    })
    with patch('src.analysis.analyze_states', return_value=frame):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        assert not app.exception
        assert app.dataframe[0].value['State'].tolist() == ['Florida']
        app.sidebar.multiselect[0].set_value(['Florida', 'Texas']).run()
        assert not app.exception
        assert app.dataframe[0].value['State'].tolist() == ['Florida', 'Texas']
        app.sidebar.multiselect[0].set_value([]).run()
        assert not app.exception
        assert app.dataframe[0].value.empty
