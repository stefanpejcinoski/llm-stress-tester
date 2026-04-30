"""UI form components for Streamlit."""

from __future__ import annotations

import streamlit as st

from llm_stress_tester.constants import DEFAULT_API_PATH
from llm_stress_tester.constants import MAX_RATE_SLIDER_VALUE as MAX_RATE_SLIDER
from llm_stress_tester.constants import MIN_RATE_SLIDER_VALUE as MIN_RATE_SLIDER
from llm_stress_tester.data.prompts import SUITES_DESCRIPTIONS
from llm_stress_tester.enums import RateUnit
from llm_stress_tester.schemas import ModelEntry, TokenEntry
from llm_stress_tester.utils.rate_units import slider_to_internal_rate


def render_endpoint_form():
    """Render base URL, API path, and auth toggle."""
    st.subheader("Endpoint")
    col1, col2 = st.columns([4, 2])
    with col1:
        base_url = st.text_input(
            "Base URL",
            value="https://api.example.com",
            key="base_url",
        )
    with col2:
        api_path = st.text_input(
            "API Path",
            value=DEFAULT_API_PATH,
            key="api_path",
        )
    is_public = st.checkbox(
        "Public endpoint (no auth required)",
        value=False,
        key="is_public",
        help="Check this if the endpoint does not require API tokens.",
    )
    return base_url, api_path, is_public


def render_tokens_form() -> list[TokenEntry]:
    """Render token CSV textarea.

    Returns a list of TokenEntry.
    """
    st.subheader("API Tokens")
    st.caption("Paste tokens as CSV. Optional header: token,label")

    csv_input = st.text_area(
        "Tokens (CSV)",
        value=(
            "token,label\n"
            "sk-test-1,dev-machine\n"
            "sk-test-2,staging-machine\n"
            "sk-test-3,prod-machine"
        ),
        height=150,
        key="token_csv",
    )
    tokens: list[TokenEntry] = []
    if csv_input.strip():
        tokens = _parse_tokens(csv_input)
    st.success(f"{len(tokens)} token(s) loaded")

    st.session_state["token_count"] = len(tokens)

    return tokens


def render_rate_form():
    """Render rate and schedule controls.

    Returns (rate_unit, initial_rate, max_rate, scaling_factor, time_increment).
    """
    st.subheader("Rate & Schedule")

    rate_unit = st.radio(
        "Rate Unit",
        options=[
            (RateUnit.RPS.value, "RPS (Requests Per Second)"),
            (RateUnit.RPM.value, "RPM (Requests Per Minute)"),
        ],
        format_func=lambda x: x[1],
        index=0,
        key="rate_unit",
    )
    unit_val = rate_unit[0] if isinstance(rate_unit, tuple) else rate_unit
    try:
        rate_unit_enum = RateUnit(unit_val)
    except ValueError:
        rate_unit_enum = RateUnit.RPS

    show_rps = rate_unit_enum == RateUnit.RPS
    show_rpm = rate_unit_enum == RateUnit.RPM

    initial_val = 1
    max_val = 100

    initial_rate = st.slider(
        "Initial Rate" + ("" if show_rps else " RPM"),
        min_value=MIN_RATE_SLIDER,
        max_value=MAX_RATE_SLIDER,
        value=initial_val,
        step=1,
        key="initial_rate_slider",
        help=(
            f"That is {initial_val / 60:.3f} RPS"
            if show_rpm
            else f"That is {initial_val} RPS"
        ),
    )

    max_rate = st.slider(
        "Max Rate" + ("" if show_rps else " RPM"),
        min_value=initial_rate,
        max_value=MAX_RATE_SLIDER,
        value=max_val,
        step=1,
        key="max_rate_slider",
        help=(
            f"That is {max_val / 60:.3f} RPS"
            if show_rpm
            else f"That is {max_val} RPS"
        ),
    )

    scaling_factor = st.slider(
        "Scaling Factor",
        min_value=1.1,
        max_value=10.0,
        value=2.0,
        step=0.1,
        key="scaling_factor",
    )

    time_increment = st.slider(
        "Time Increment (seconds)",
        min_value=5,
        max_value=300,
        value=60,
        step=5,
        key="time_increment",
    )

    # Always return canonical RPS regardless of display unit.
    # load_runner, schedule, and metrics all operate in RPS internally.
    initial_rate_rps = slider_to_internal_rate(int(initial_rate), rate_unit_enum)
    max_rate_rps = slider_to_internal_rate(int(max_rate), rate_unit_enum)

    return (
        rate_unit_enum,
        initial_rate_rps,
        max_rate_rps,
        float(scaling_factor),
        float(time_increment),
    )


def render_users_form() -> tuple[int, int, int]:
    """Render user count controls.

    Returns (min_users, max_users, users_increment).
    Capped by token count from render_tokens_form().
    """
    st.subheader("Users")

    max_token_count = min(
        st.session_state.get("token_count", 0),
        100,
    )

    if max_token_count < 1:
        st.warning("No API tokens loaded. Set API tokens first to cap users.")
        min_users = st.number_input(
            "Min Users",
            min_value=1,
            value=1,
            step=1,
            key="min_users",
        )
        max_users = st.number_input(
            "Max Users",
            min_value=min_users,
            value=2,
            step=1,
            key="max_users",
        )
        users_increment = st.number_input(
            "Users Increment",
            min_value=1,
            value=1,
            step=1,
            key="users_increment",
        )
        return min_users, max_users, users_increment

    st.caption(f"API tokens loaded: {max_token_count}")
    st.caption("Max users will be capped by token count.")

    col1, col2 = st.columns(2)

    with col1:
        min_users = st.number_input(
            "Min Users",
            min_value=1,
            max_value=max_token_count,
            value=1,
            step=1,
            key="min_users",
        )

    with col2:
        max_users = st.number_input(
            "Max Users",
            min_value=min_users,
            max_value=max_token_count,
            value=min(max_token_count, 5),
            step=1,
            key="max_users",
        )

    users_increment = st.number_input(
        "Users Increment",
        min_value=1,
        max_value=max(1, max_token_count - min_users),
        value=1,
        step=1,
        key="users_increment",
    )

    return min_users, max_users, users_increment


def render_models_form() -> list[ModelEntry]:
    """Render model name and percentage inputs.

    Returns a list of ModelEntry.
    """
    st.subheader("Models & Traffic Split")
    model_count = st.number_input(
        "Number of Models",
        min_value=1,
        max_value=10,
        value=2,
        step=1,
        key="model_count",
    )

    models: list[ModelEntry] = []

    cols = st.columns(2)
    for i in range(model_count):
        with cols[i % 2]:
            name = st.text_input(
                f"Model {i + 1} Name",
                placeholder="e.g. gpt-4o, claude-3-sonnet, llama-3",
                key=f"model_name_{i}",
            )
            pct = st.slider(
                f"{name.strip() or 'Model ' + str(i + 1)} Traffic %",
                min_value=0,
                max_value=100,
                value=100 if i == 0 else 0,
                step=1,
                key=f"model_pct_{i}",
            )
            if name.strip():
                models.append(
                    ModelEntry(model=name.strip(), percentage=float(pct)),
                )

    return models


def render_benchmark_form() -> str:
    """Render benchmark suite selector.

    Returns the selected benchmark suite key (lowercase string).
    """
    st.subheader("Benchmark Suite")

    options = list(SUITES_DESCRIPTIONS.keys())
    labels = [
        f"{SUITES_DESCRIPTIONS[opt][0]} — {SUITES_DESCRIPTIONS[opt][1]}"
        for opt in options
    ]
    label_to_key = {labels[j]: options[j] for j in range(len(labels))}

    selected_label = st.selectbox(
        "Select Suite",
        options=labels,
        index=len(labels) // 2,
        key="benchmark_suite",
    )
    return label_to_key[selected_label]


def render_advanced_form(timeout, num_rows):
    """Render advanced settings.

    Returns (timeout, num_rows).
    """
    st.subheader("Advanced Settings")
    col1, col2 = st.columns(2)
    with col1:
        timeout = st.number_input(
            "Request Timeout (seconds)",
            min_value=1,
            max_value=600,
            value=timeout,
            step=1,
            key="timeout",
        )
    with col2:
        num_rows = st.number_input(
            "Max Rows to Show in Raw Table",
            min_value=10,
            max_value=10000,
            value=num_rows,
            step=100,
            key="num_rows_display",
        )
    return timeout, num_rows


def _parse_tokens(csv_text: str) -> list[TokenEntry]:
    """Parse a CSV string of tokens into a list of TokenEntry."""
    from llm_stress_tester.utils.token_csv import parse_token_csv

    tokens, errors = parse_token_csv(csv_text)
    for err in errors:
        st.error(err)
    if errors:
        st.warning(f"{len(errors)} issue(s) found in CSV")
    return tokens


