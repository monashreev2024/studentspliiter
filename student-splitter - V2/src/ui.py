import streamlit as st
from datetime import datetime

from .config import BuildOptions
from .excel_io import process_excel
from .history import (
    ensure_history_store,
    build_output_filename,
    save_run,
    list_history,
    read_history_file,
    delete_history_item,
)


def inject_css():
    st.markdown(
        """
        <style>
        .block-container{max-width:900px; padding-top:1.4rem; padding-bottom:2rem;}
        footer{visibility:hidden;}

        .top{
          border-radius:16px;
          padding:16px 18px;
          border:1px solid rgba(0,0,0,.10);
          background:rgba(255,255,255,.7);
        }
        .t-title{font-size:20px; font-weight:900; margin:0;}
        .t-sub{font-size:13px; opacity:.75; margin-top:6px;}

        .card{
          margin-top:14px;
          border-radius:16px;
          padding:16px;
          border:1px solid rgba(0,0,0,.10);
          background:rgba(255,255,255,.85);
        }
        .card h3{margin:0 0 12px 0; font-size:16px; font-weight:900;}
        .muted{font-size:12px; opacity:.72;}

        div.stDownloadButton > button{
          height:44px;
          border-radius:12px;
          font-weight:900;
        }
        div.stButton > button{
          height:44px;
          border-radius:12px;
          font-weight:900;
        }

        section[data-testid="stFileUploaderDropzone"]{
          border-radius:14px;
          padding:14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app():
    inject_css()
    ensure_history_store()

    # Fixed processing rules (no confusing settings)
    opts = BuildOptions(
        group_mode="Year + Department",
        dept_source="From RegNo",
        add_summary=True,
        sort_by_regno=True,
        base_century=2000,
    )

    # Header
    st.markdown(
        """
        <div class="top">
          <div class="t-title">Student Splitter</div>
          <div class="t-sub">Upload Excel → Enter Event → Generate output Excel (saved to History) → Download.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_generate, tab_history = st.tabs(["✅ Generate", "🕘 History"])

    # -----------------------
    # TAB 1: GENERATE
    # -----------------------
    with tab_generate:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>1) Upload Excel</h3>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload", type=["xlsx", "xls"], label_visibility="collapsed")
        st.markdown('<div class="muted">Required columns: <b>regno</b>, <b>name</b></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>2) Event details</h3>", unsafe_allow_html=True)

        event_name = st.text_input("Event name", placeholder="Example: Freshers Day / Workshop / Orientation")
        event_date = st.date_input("Event date", value=datetime.now().date())

        col_a, col_b = st.columns(2)
        with col_a:
            start_time = st.time_input(
                "Start Time",
                value=datetime.now().time().replace(second=0, microsecond=0),
            )
        with col_b:
            end_time = st.time_input(
                "End Time",
                value=datetime.now().time().replace(second=0, microsecond=0),
            )

        # Validate time range
        if uploaded and event_name.strip():
            if end_time < start_time:
                st.warning("End Time should be greater than or equal to Start Time.")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>3) Generate</h3>", unsafe_allow_html=True)

        disabled = (uploaded is None) or (not event_name.strip()) or (end_time < start_time)
        st.caption("Click generate once. Output will be saved automatically in History.")

        if st.button("🚀 Generate & Save", use_container_width=True, disabled=disabled):
            try:
                with st.spinner("Generating output..."):
                    # ✅ UPDATED: pass required event arguments
                    df, summary, _old_name, out_bytes = process_excel(
                        uploaded,
                        opts,
                        event_name=event_name,
                        event_date=event_date,
                        start_time=start_time,
                        end_time=end_time,
                    )

                # filename uses start_time as main timestamp
                dt = datetime.combine(event_date, start_time)
                out_name = build_output_filename(event_name, dt)

                save_run(
                    event_name=event_name,
                    dt=dt,
                    uploaded_filename=getattr(uploaded, "name", "uploaded.xlsx"),
                    output_filename=out_name,
                    output_bytes=out_bytes,
                )

                st.session_state["latest_df"] = df
                st.session_state["latest_summary"] = summary
                st.session_state["latest_bytes"] = out_bytes
                st.session_state["latest_name"] = out_name

                st.success("Done ✅ Output saved to History.")

            except Exception as e:
                st.error(str(e))

        # Show download + preview ONLY after generate
        if "latest_bytes" in st.session_state:
            st.markdown("<hr/>", unsafe_allow_html=True)
            st.subheader("⬇️ Download")
            st.download_button(
                "Download Latest Output",
                data=st.session_state["latest_bytes"],
                file_name=st.session_state["latest_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

            st.subheader("👀 Preview")
            p1, p2 = st.tabs(["Data", "Summary"])
            with p1:
                st.dataframe(st.session_state["latest_df"].head(60), use_container_width=True)
            with p2:
                st.dataframe(st.session_state["latest_summary"], use_container_width=True)
        else:
            st.info("Upload file + enter Event name → click Generate to get download.")

        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------
    # TAB 2: HISTORY
    # -----------------------
    with tab_history:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h3>History</h3>", unsafe_allow_html=True)

        q = st.text_input("Search by event name", placeholder="Type event name…")
        items = list_history(limit=50)

        if q.strip():
            items = [x for x in items if q.lower() in (x.get("event_name", "").lower())]

        if not items:
            st.info("No saved files yet.")
        else:
            for it in items:
                with st.expander(f"{it.get('event_name','(no name)')}  •  {it.get('generated_at','')}"):
                    st.write(f"**Uploaded file:** {it.get('uploaded_filename','')}")
                    st.write(f"**Output file:** {it.get('output_filename','')}")

                    col1, col2 = st.columns(2)

                    # Download button
                    with col1:
                        b = read_history_file(it.get("file_path", ""))
                        if b:
                            st.download_button(
                                "Download",
                                data=b,
                                file_name=it.get("output_filename", "output.xlsx"),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                                key=f"hist_dl_{it.get('id','')}",
                            )

                    # Delete button
                    with col2:
                        if st.button(
                            "Delete",
                            key=f"hist_del_{it.get('id','')}",
                            use_container_width=True,
                        ):
                            delete_history_item(it.get("id", ""))
                            st.success("Deleted successfully.")
                            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)