"""A tiny stand-in for ``streamlit`` so UI code can be rendered in unit tests.

Widgets return neutral values (buttons are never clicked, selectboxes pick their
first option) and everything else is a MagicMock, which also supports
``with`` blocks. This catches NameErrors/KeyErrors in render code without
needing a running Streamlit server.
"""
from unittest.mock import MagicMock


class FakeState(dict):
    """dict with attribute access, like ``st.session_state``."""

    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value


def make_fake_streamlit(**state):
    fake = MagicMock(name="streamlit")
    fake.session_state = FakeState(state)

    def columns(spec, **_kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(count)]

    def selectbox(_label, options=(), index=0, **_kwargs):
        options = list(options)
        if not options:
            return None
        return options[index or 0] if (index or 0) < len(options) else options[0]

    def select_slider(_label, options=(), value=None, **_kwargs):
        options = list(options)
        return value if value is not None else (options[0] if options else None)

    fake.columns.side_effect = columns
    fake.selectbox.side_effect = selectbox
    fake.select_slider.side_effect = select_slider
    fake.button.return_value = False
    fake.form_submit_button.return_value = False
    fake.radio.return_value = None
    fake.checkbox.return_value = False
    fake.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]
    return fake
