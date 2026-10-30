from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from simulation import COLUMNS, SimulationConfig, one_sample_t_test, run_simulation


ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
MAX_ANIMATION_EVENTS = 6000
PAGES = ["🏦 Simulation", "📈 Results", "🧪 T-Test", "📄 Dataset"]

st.set_page_config(page_title="Bank Queue Lab", page_icon="🏦", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html, body, .stApp {font-family:'DM Sans',sans-serif}
.stApp {background:linear-gradient(145deg,#f5f8ff 0%,#f7f9fc 45%,#f4fbf8 100%)}
h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em}
.hero {padding:1.25rem 1.5rem;border-radius:22px;background:linear-gradient(120deg,#102a43,#164e63 65%,#087e8b);color:white;margin-bottom:1.1rem;box-shadow:0 12px 34px #0e749022}
.hero h1 {color:#fff;margin:.2rem 0 0;padding:0}.hero p {color:#d8edf1;margin:.35rem 0 0}.eyebrow {text-transform:uppercase;letter-spacing:.13em;font-size:.72rem;font-weight:700;color:#a9d8df}
.metric-card {background:#fff;padding:1rem 1.15rem;border:1px solid #e6edf3;border-radius:16px;box-shadow:0 5px 18px #102a4309}
.metric-label {font-size:.76rem;color:#607587;font-weight:600}.metric-value {font:800 1.55rem 'Manrope';color:#102a43;margin-top:.2rem}.metric-sub {font-size:.73rem;color:#8697a5}
.section-note {color:#607587;font-size:.9rem}
[data-testid="stSidebar"] {background:#f7fbfc}
</style>
""", unsafe_allow_html=True)


def metric_cards(items):
    cols = st.columns(len(items))
    for col, (label, value, sub) in zip(cols, items):
        col.markdown(
            f"<div class='metric-card'><div class='metric-label'>{label}</div>"
            f"<div class='metric-value'>{value}</div><div class='metric-sub'>{sub}</div></div>",
            unsafe_allow_html=True,
        )


def counter_summary(customer_df: pd.DataFrame, counters: int) -> pd.DataFrame:
    """Customers served and mean wait for every counter (idle counters show 0)."""
    table = customer_df.groupby("counter_id", as_index=False).agg(
        customers_served=("customer_id", "count"), mean_wait=("waiting_time", "mean"))
    full = pd.DataFrame({"counter_id": range(1, counters + 1)})
    return full.merge(table, on="counter_id", how="left").fillna(0).astype(
        {"customers_served": int})


def create_run(config: SimulationConfig, benchmark_value: float, alpha_value: float):
    customer_df, timeline_events, summary = run_simulation(config)
    test_result = one_sample_t_test(customer_df["waiting_time"], benchmark_value, alpha_value)
    st.session_state.update(
        simulation_df=customer_df,
        simulation_events=timeline_events,
        simulation_summary=summary,
        test_result=test_result,
        config=config,
        benchmark=benchmark_value,
        alpha=alpha_value,
    )
    customer_df.to_csv(RESULTS / "customer_data.csv", index=False)
    (RESULTS / "summary.json").write_text(
        json.dumps({**summary, **test_result}, indent=2), encoding="utf-8"
    )
    counter_summary(customer_df, config.counters).to_csv(RESULTS / "counter_summary.csv", index=False)


with st.sidebar:
    st.markdown("## 🏦 Bank Queue Lab")
    selected_page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.divider()
    st.markdown("### ⚙️ Simulation setup")
    counters = st.slider("Service counters", 1, 10, 3, key="input_counters")
    duration = st.number_input("Arrival period (seconds)", 30, 3600, 240, step=30, key="input_duration")
    arrival = st.number_input("Mean arrival interval (seconds)", 0.1, 300.0, 3.0, step=0.5, key="input_arrival")
    service = st.number_input("Mean service time (seconds)", 0.1, 600.0, 7.0, step=0.5, key="input_service")
    seed = st.number_input("Random seed", 0, 2_147_483_647, 42, step=1, key="input_seed")
    st.markdown("### 📊 Test settings")
    benchmark = st.number_input("Wait benchmark (seconds)", 0.0, 3600.0, 300.0, step=10.0,
                                help="5 minutes = 300 seconds.", key="input_benchmark")
    alpha = st.select_slider("Significance level (α)", options=[0.01, 0.05, 0.10], value=0.05,
                             key="input_alpha")
    run = st.button("▶ Run / update simulation", type="primary", width="stretch")
    st.caption("All time values are in seconds. Customer data are synthetic.")

if run:
    create_run(SimulationConfig(int(counters), float(duration), float(arrival), float(service), int(seed)),
               float(benchmark), float(alpha))

has_run = "simulation_df" in st.session_state
if has_run:
    df = st.session_state.simulation_df
    events = st.session_state.simulation_events
    summary = st.session_state.simulation_summary
    test = st.session_state.test_result
    config = st.session_state.config
else:  # nothing has been simulated yet: show zeros and empty tables
    config = SimulationConfig(int(counters), float(duration), float(arrival), float(service), int(seed))
    df = pd.DataFrame(columns=COLUMNS)
    events = []
    summary = {"customers": 0, "duration": config.duration, "end_time": 0.0,
               "counters": config.counters, "seed": config.seed}
    test = one_sample_t_test([], float(benchmark), float(alpha))

page_title = {
    PAGES[0]: ("Live Simulation", "Watch customers arrive, wait in line, receive service, and leave."),
    PAGES[1]: ("Simulation Results", "Explore customer waiting times and counter performance."),
    PAGES[2]: ("Statistical Analysis", "Compare the simulated mean waiting time with your benchmark."),
    PAGES[3]: ("Customer Dataset", "Review and download the generated customer-level records."),
}
title, subtitle = page_title[selected_page]
st.markdown(
    f"<div class='hero'><div class='eyebrow'>Bank Queue Simulation</div>"
    f"<h1>{title}</h1><p>{subtitle}</p></div>",
    unsafe_allow_html=True,
)
if run:
    st.success("Simulation updated with the settings in the sidebar.")


if selected_page == PAGES[0]:
    st.markdown("### Customer flow")
    st.markdown(
        "<p class='section-note'>Press Play to start. New customers appear one by one; choose a slower speed or pause at any time.</p>",
        unsafe_allow_html=True,
    )
    if not has_run:
        st.info("Nothing has been simulated yet. Choose your settings and press **Run / update simulation**.")
    elif df.empty:
        st.warning("No customers arrived in this simulation. Increase the arrival period or try another random seed.")
    elif len(events) > MAX_ANIMATION_EVENTS:
        st.info(f"This run has {summary['customers']:,} customers, which is too many to animate smoothly. "
                "Lower the arrival period or raise the mean arrival interval to watch the animation; "
                "Results, T-Test, and Dataset still work.")
    else:
        events_json = json.dumps(events, separators=(",", ":"))
        flow_html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
        *{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:#fff;color:#183449}}
        .box{{border:1px solid #e4ecf1;border-radius:18px;padding:18px;background:linear-gradient(135deg,#fbfdff,#f4faf9)}}
        .top{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
        button,select{{border:0;border-radius:10px;padding:10px 14px;font-weight:700;background:#0f766e;color:white;cursor:pointer}}
        button{{min-width:118px}}button:active{{transform:scale(.98)}}select{{background:#e8f2f3;color:#183449}}
        .time{{margin-left:auto;font-weight:700;color:#547184}}
        .bank{{display:grid;grid-template-columns:1.1fr 1fr 1.2fr;gap:12px;align-items:stretch}}
        .zone{{background:white;border:1px solid #e1eaf0;border-radius:14px;padding:12px;min-height:175px}}
        .zone h3{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#6b8291;margin:0 0 12px}}
        .count{{float:right;color:#087e65;background:#e6f5ef;border-radius:20px;padding:3px 8px;letter-spacing:0;text-transform:none}}
        .people{{display:flex;gap:7px;flex-wrap:wrap;align-content:flex-start}}
        .person{{width:31px;height:31px;border-radius:50%;background:#dff4ee;color:#087e65;display:grid;place-items:center;font-size:11px;font-weight:700;border:1px solid #bfe8dc}}
        .counter-list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:8px}}
        .counter{{border-radius:12px;background:#eff6fa;padding:10px;min-height:78px}}
        .counter strong{{font-size:12px;color:#426174}}.served{{margin-top:9px;display:flex;gap:6px;align-items:center;font-size:12px;color:#126e6c;font-weight:600}}
        .empty{{font-size:12px;color:#9aabb5}}input[type=range]{{width:100%;margin-top:16px;accent-color:#0f766e}}
        @media(max-width:650px){{.bank{{grid-template-columns:1fr}}.time{{margin-left:0}}}}
        </style></head><body><div class="box"><div class="top">
        <button id="play" type="button">▶ Play</button>
        <select id="speed" aria-label="Animation speed"><option value="650">Slow</option><option value="300" selected>Normal</option><option value="110">Fast</option></select>
        <span class="time" id="clock"></span></div><div class="bank">
        <section class="zone"><h3>Waiting line <span class="count" id="wait-count">0 waiting</span></h3><div id="queue" class="people"></div></section>
        <section class="zone"><h3>Service counters</h3><div id="counters" class="counter-list"></div></section>
        <section class="zone"><h3>Recently completed</h3><div id="done" class="people"></div></section>
        </div><input id="timeline" aria-label="Simulation timeline" type="range" min="0" max="0" value="0"></div>
        <script>
        const events={events_json};
        const maxTime={summary['end_time']:.4f};
        const counterCount={config.counters};
        let index=0, timer=null, isPlaying=false, queue=[], busy={{}}, done=[];
        const range=document.getElementById('timeline'), playButton=document.getElementById('play');
        range.max=events.length;
        function person(id){{return '<span class="person" title="Customer '+id+'">'+id+'</span>'}}
        function render(){{
          document.getElementById('queue').innerHTML=queue.length?queue.map(person).join(''):'<span class="empty">No customers waiting</span>';
          document.getElementById('wait-count').textContent=queue.length+' waiting';
          let cards='';for(let n=1;n<=counterCount;n++){{let id=busy[n];cards+='<div class="counter"><strong>Counter '+n+'</strong><div class="served">'+(id?person(id):'<span class="empty">Available</span>')+'</div></div>'}}
          document.getElementById('counters').innerHTML=cards;
          document.getElementById('done').innerHTML=done.slice(-12).map(person).join('')||'<span class="empty">No completed services</span>';
          const time=index?events[Math.min(index-1,events.length-1)].time:0;
          document.getElementById('clock').textContent='Time '+time.toFixed(1)+' / '+maxTime.toFixed(1)+' seconds';range.value=index;
        }}
        function applyEvent(e){{if(e.type==='arrival')queue.push(e.customer_id);if(e.type==='service_start'){{queue=queue.filter(id=>id!==e.customer_id);busy[e.counter_id]=e.customer_id}}if(e.type==='departure'){{delete busy[e.counter_id];done.push(e.customer_id)}}}}
        function stopPlayback(label){{isPlaying=false;if(timer!==null){{clearTimeout(timer);timer=null}}playButton.textContent=label}}
        function step(){{if(!isPlaying)return;if(index>=events.length){{stopPlayback('↻ Replay');return}}applyEvent(events[index++]);render();if(index>=events.length){{stopPlayback('↻ Replay');return}}timer=setTimeout(step,Number(document.getElementById('speed').value))}}
        playButton.addEventListener('click',function(){{
          if(isPlaying){{stopPlayback('▶ Resume');return}}
          if(index>=events.length){{index=0;queue=[];busy={{}};done=[];render()}}
          isPlaying=true;playButton.textContent='❚❚ Pause';step();
        }});
        document.getElementById('speed').addEventListener('change',function(){{if(isPlaying){{if(timer!==null)clearTimeout(timer);timer=setTimeout(step,Number(this.value))}}}});
        range.addEventListener('input',function(){{stopPlayback('▶ Play');index=Number(this.value);queue=[];busy={{}};done=[];for(let j=0;j<index;j++)applyEvent(events[j]);render()}});
        render();
        </script></body></html>"""
        if hasattr(st, "iframe"):  # newer Streamlit; components.v1.html is being removed
            st.iframe(flow_html, height=300)
        else:
            components.html(flow_html, height=300, scrolling=False)
    st.markdown("### Current simulation")
    metric_cards([
        ("Customers", f"{summary['customers']:,}", "arrived in this run"),
        ("Service counters", str(config.counters), "ready to serve"),
        ("Arrival period", f"{config.duration:g} s", "new arrivals stop after this time"),
    ])


elif selected_page == PAGES[1]:
    st.markdown("### Waiting-time overview")
    metric_cards([
        ("Mean wait", f"{test['mean']:.2f} s", "average customer wait"),
        ("Median wait", f"{test['median']:.2f} s", "middle customer wait"),
        ("Longest wait", f"{test['maximum']:.2f} s", "maximum in this run"),
        ("Customers", f"{summary['customers']:,}", "served in this run"),
    ])
    left, right = st.columns(2)
    if not df.empty:
        with left:
            plot_df = df.assign(counter_id=df["counter_id"].astype(str))
            chart = px.scatter(plot_df, x="customer_id", y="waiting_time", color="counter_id",
                               category_orders={"counter_id": [str(i) for i in range(1, config.counters + 1)]},
                               labels={"customer_id":"Customer", "waiting_time":"Wait (seconds)", "counter_id":"Counter"},
                               title="Waiting time for each customer")
            chart.add_hline(y=test["benchmark"], line_dash="dash", line_color="#e27851",
                            annotation_text="Benchmark", annotation_position="top left")
            chart.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=390,
                                margin=dict(l=10,r=10,t=55,b=10), font_color="#425c6c")
            st.plotly_chart(chart, width="stretch")
        with right:
            hist = px.histogram(df, x="waiting_time", nbins=24, color_discrete_sequence=["#19a58c"],
                                labels={"waiting_time":"Wait (seconds)"}, title="Distribution of customer waits")
            hist.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=390,
                               margin=dict(l=10,r=10,t=55,b=10), font_color="#425c6c", showlegend=False)
            st.plotly_chart(hist, width="stretch")
        st.markdown("### Counter performance")
        counts = counter_summary(df, config.counters)
        bar = px.bar(counts, x="counter_id", y="customers_served", color="mean_wait",
                     color_continuous_scale="Teal",
                     labels={"counter_id":"Counter", "customers_served":"Customers served", "mean_wait":"Mean wait (s)"},
                     title="Customers served by counter")
        bar.update_layout(plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", height=330,
                          margin=dict(l=10,r=10,t=55,b=10), font_color="#425c6c")
        st.plotly_chart(bar, width="stretch")
    else:
        st.info("Press **Run / update simulation** to see charts." if not has_run else
                "There are no customers to chart. Try another seed or a longer arrival period.")


elif selected_page == PAGES[2]:
    st.markdown("### Descriptive statistics")
    metric_cards([
        ("Mean", f"{test['mean']:.2f} s", "sample mean waiting time"),
        ("Median", f"{test['median']:.2f} s", "middle waiting time"),
        ("Maximum", f"{test['maximum']:.2f} s", "longest waiting time"),
        ("Sample size", str(test["n"]), "customers with wait records"),
    ])
    st.markdown("### One-sample t-test")
    st.markdown("**H₀:** μ = benchmark &nbsp;&nbsp; **H₁:** μ ≠ benchmark (two-sided)", unsafe_allow_html=True)
    st.write(f"Benchmark: **{test['benchmark']:.2f} seconds** · Significance level: **α = {test['alpha']:.2f}**")
    if not has_run:
        st.info("Press **Run / update simulation** to run the t-test.")
    elif test["p_value"] is None:
        st.warning(test["decision"])
    else:
        a, b, c = st.columns(3)
        a.metric("t statistic", "undefined" if test["t_statistic"] is None else f"{test['t_statistic']:.4f}")
        b.metric("p value", f"{test['p_value']:.6g}")
        c.metric(f"{(1-test['alpha'])*100:.0f}% confidence interval",
                 f"[{test['confidence_interval'][0]:.2f}, {test['confidence_interval'][1]:.2f}] s")
        st.info(test["decision"])
    st.caption("A p-value below α is evidence that the modeled mean differs from the benchmark. This test describes this synthetic run; it is not a statement about a real bank.")


else:
    st.markdown("### Customer records")
    st.caption("Times are in seconds. These records are generated by the simulation and are not real bank data.")
    st.dataframe(df, width="stretch", hide_index=True)
    summary_payload = {**summary, **test, "mean_arrival_interval": config.mean_arrival_interval,
                       "mean_service_time": config.mean_service_time, "benchmark_unit": "seconds"}
    counter_data = counter_summary(df, config.counters)
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇ Customer dataset (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "customer_data.csv", "text/csv", width="stretch", disabled=not has_run)
    d2.download_button("⬇ Run summary (JSON)", json.dumps(summary_payload, indent=2).encode(),
                       "summary.json", "application/json", width="stretch", disabled=not has_run)
    d3.download_button("⬇ Counter summary (CSV)", counter_data.to_csv(index=False).encode(),
                       "counter_summary.csv", "text/csv", width="stretch", disabled=not has_run)
    with st.expander("Dataset fields"):
        st.write("customer_id, arrival_time, service_time, waiting_time, service_start, departure_time, and counter_id. All time fields are in seconds.")
