import streamlit as st
from deep_translator import GoogleTranslator
import speech_recognition as sr
import os
import io
import csv
import json
import base64
import asyncio
from datetime import datetime

# Optional high-quality TTS engine; app falls back to gTTS if unavailable.
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

from gtts import gTTS

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Voice & Text Translator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# CUSTOM CSS
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 45%, #0f172a 100%);
            color: #e2e8f0;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* ---------- HERO ---------- */
        .hero { text-align: center; padding: 1.2rem 1rem 0.6rem 1rem; }
        .hero h1 {
            font-size: clamp(1.6rem, 3.2vw, 2.4rem);
            font-weight: 800;
            line-height: 1.25;
            white-space: normal;
            background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .hero p { color: #94a3b8; font-size: 1.0rem; margin-top: 0; }

        /* ---------- GLASS CARDS ---------- */
        .card {
            background: rgba(255, 255, 255, 0.045);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
            transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
        }
        .card:hover {
            border-color: rgba(167, 139, 250, 0.45);
            box-shadow: 0 0 0 1px rgba(167,139,250,0.15), 0 10px 34px rgba(124, 58, 237, 0.25);
        }
        .card-title {
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #a78bfa;
            margin-bottom: 0.6rem;
        }

        textarea {
            background: rgba(255, 255, 255, 0.03) !important;
            color: #e2e8f0 !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        /* ---------- BUTTONS ---------- */
        .stButton > button {
            width: 100%;
            background: linear-gradient(90deg, #7c3aed, #2563eb);
            color: white;
            font-weight: 700;
            font-size: 0.95rem;
            padding: 0.65rem 0;
            border-radius: 12px;
            border: none;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            box-shadow: 0 4px 18px rgba(124, 58, 237, 0.35);
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(124, 58, 237, 0.65), 0 8px 24px rgba(37, 99, 235, 0.45);
        }

        /* Secondary / utility buttons (swap, reset, copy) get a subtler style
           via the .util-btn wrapper class applied through container. */
        div[data-testid="stHorizontalBlock"] .stButton > button {
            padding: 0.55rem 0;
            font-size: 0.85rem;
        }

        .char-count { color: #64748b; font-size: 0.8rem; text-align: right; margin-top: -0.6rem; }

        a.download-link {
            display: inline-block;
            margin-top: 0.8rem;
            padding: 0.55rem 1rem;
            border-radius: 10px;
            background: rgba(52, 211, 153, 0.15);
            border: 1px solid rgba(52, 211, 153, 0.4);
            color: #34d399 !important;
            text-decoration: none !important;
            font-weight: 600;
            font-size: 0.9rem;
            transition: background 0.2s ease, box-shadow 0.2s ease;
        }
        a.download-link:hover {
            background: rgba(52, 211, 153, 0.25);
            box-shadow: 0 0 14px rgba(52, 211, 153, 0.35);
        }

        [data-testid="stAudioInput"] {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1.5px dashed rgba(167, 139, 250, 0.5) !important;
            border-radius: 12px !important;
            padding: 0.6rem !important;
        }

        section[data-testid="stSidebar"] {
            background: #0b1024;
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        /* ---------- STATUS PILLS / BADGES ---------- */
        .pill {
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            background: rgba(167, 139, 250, 0.15);
            border: 1px solid rgba(167, 139, 250, 0.4);
            color: #c4b5fd;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.4rem;
        }
        .pill-green {
            background: rgba(52, 211, 153, 0.15);
            border-color: rgba(52, 211, 153, 0.4);
            color: #34d399;
        }
        .pill-red {
            background: rgba(248, 113, 113, 0.15);
            border-color: rgba(248, 113, 113, 0.4);
            color: #f87171;
        }
        .pill-amber {
            background: rgba(251, 191, 36, 0.15);
            border-color: rgba(251, 191, 36, 0.4);
            color: #fbbf24;
        }
        .status-row { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.4rem; }
        .status-label { color: #94a3b8; font-size: 0.8rem; }

        /* ---------- HISTORY ---------- */
        .history-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
            margin-bottom: 0.6rem;
            transition: border-color 0.2s ease;
        }
        .history-item:hover { border-color: rgba(167,139,250,0.35); }
        .history-meta { color: #64748b; font-size: 0.75rem; margin-bottom: 0.3rem; }
        .history-orig { color: #cbd5e1; font-size: 0.9rem; }
        .history-trans { color: #34d399; font-size: 0.9rem; font-weight: 600; margin-top: 0.2rem; }

        /* Remove default Streamlit block gaps that created blank boxes */
        div.block-container { padding-top: 1.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# LANGUAGE CONFIG
# ----------------------------------------------------------------------------
TARGET_LANGUAGES = {
    "Spanish": "es", "French": "fr", "German": "de", "Marathi": "mr",
    "Hindi": "hi", "Japanese": "ja", "Chinese (Simplified)": "zh-CN",
    "Italian": "it", "Russian": "ru", "Arabic": "ar", "English": "en",
}

# Source languages for speech recognition, mapped to BCP-47 codes.
# "Auto-Detect" has no fixed BCP-47 code for recognition; we default the
# recognizer to English but run translation with source="auto" regardless.
SOURCE_SPEECH_LANGUAGES = {
    "Auto-Detect": "en-US",
    "English": "en-US",
    "Hindi": "hi-IN",
    "Marathi": "mr-IN",
    "Spanish": "es-ES",
    "French": "fr-FR",
    "German": "de-DE",
}

# gTTS-supported languages (fallback TTS engine)
GTTS_SUPPORTED = {
    "af", "ar", "bg", "bn", "bs", "ca", "cs", "cy", "da", "de", "el", "en",
    "eo", "es", "et", "fi", "fr", "gu", "or", "hi", "hr", "hu", "hy", "id",
    "is", "it", "ja", "jw", "km", "kn", "ko", "la", "lv", "mk", "ml", "mr",
    "my", "ne", "nl", "no", "pl", "pt", "ro", "ru", "si", "sk", "sq", "sr",
    "su", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "zh-CN",
}

# Default Edge TTS neural voice per target language code.
EDGE_VOICE_MAP = {
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "mr": "mr-IN-AarohiNeural",
    "hi": "hi-IN-SwaraNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "it": "it-IT-ElviraNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "en": "en-US-JennyNeural",
}

# Playback speed options for TTS output (client-side <audio> playbackRate)
SPEED_OPTIONS = {"0.75x": 0.75, "1.0x": 1.0, "1.25x": 1.25}

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".translator_history.json")


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def get_binary_file_downloader_html(bin_file_bytes, filename, file_label="File"):
    bin_str = base64.b64encode(bin_file_bytes).decode()
    return (
        f'<a class="download-link" href="data:application/octet-stream;base64,{bin_str}" '
        f'download="{filename}">⬇ Download {file_label}</a>'
    )


def transcribe_audio(audio_file, source_lang_code):
    """Transcribe an st.audio_input recording using Google Speech Recognition."""
    recognizer = sr.Recognizer()
    audio_bytes = io.BytesIO(audio_file.getvalue())
    with sr.AudioFile(audio_bytes) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data, language=source_lang_code)


def run_async(coro):
    """Run an async coroutine from Streamlit's sync context."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _edge_tts_bytes(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    audio_chunks = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.extend(chunk["data"])
    return bytes(audio_chunks)


def synthesize_speech(text, target_lang_code):
    """
    Generate speech audio for `text` in `target_lang_code`.
    Tries Edge TTS first (fast, natural voices); falls back to gTTS
    automatically if Edge TTS is unavailable, has no matching voice, or fails.
    Returns (audio_bytes, engine_used) or (None, None) if no engine could
    produce audio for this language.
    """
    if EDGE_TTS_AVAILABLE and target_lang_code in EDGE_VOICE_MAP:
        try:
            voice = EDGE_VOICE_MAP[target_lang_code]
            audio_bytes = run_async(_edge_tts_bytes(text, voice))
            if audio_bytes:
                return audio_bytes, "Edge TTS"
        except Exception:
            pass  # fall through to gTTS

    if target_lang_code in GTTS_SUPPORTED:
        try:
            tts = gTTS(text=text, lang=target_lang_code)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.getvalue(), "gTTS"
        except Exception:
            pass

    return None, None


def load_history():
    """Load persisted history from local JSON file on disk."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history():
    """Persist history to local JSON file on disk."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def history_to_csv_bytes():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Time", "Source Language", "Target Language", "Original Text", "Translated Text"])
    for item in st.session_state.history:
        writer.writerow([item["time"], item["source_lang"], item["target_lang"], item["original"], item["translated"]])
    return output.getvalue().encode("utf-8")


def history_to_txt_bytes():
    lines = []
    for item in st.session_state.history:
        lines.append(f"[{item['time']}] {item['source_lang']} → {item['target_lang']}")
        lines.append(f"  Original:    {item['original']}")
        lines.append(f"  Translated:  {item['translated']}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def copy_to_clipboard_button(text_to_copy, key):
    """Renders a JS-powered copy-to-clipboard button using components."""
    safe_text = json.dumps(text_to_copy)
    html_code = f"""
        <div style="margin-top:0.4rem;">
        <button id="copy-btn-{key}" style="
            width:100%;
            background: linear-gradient(90deg, #059669, #10b981);
            color:white; font-weight:700; font-size:0.85rem;
            padding:0.55rem 0; border-radius:12px; border:none;
            cursor:pointer; box-shadow:0 4px 14px rgba(16,185,129,0.35);
            transition: transform 0.15s ease;
        " onmouseover="this.style.transform='translateY(-2px)'"
          onmouseout="this.style.transform='translateY(0)'"
          onclick="navigator.clipboard.writeText({safe_text});
                   this.innerText='✅ Copied!';
                   setTimeout(()=>{{this.innerText='📋 Copy Result';}}, 1500);">
            📋 Copy Result
        </button>
        </div>
    """
    st.components.v1.html(html_code, height=55)


# ----------------------------------------------------------------------------
# SESSION STATE
# ----------------------------------------------------------------------------
if "recognized_text" not in st.session_state:
    st.session_state.recognized_text = ""
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "show_options" not in st.session_state:
    st.session_state.show_options = True
if "src_lang_name" not in st.session_state:
    st.session_state.src_lang_name = "Auto-Detect"
if "tgt_lang_name" not in st.session_state:
    st.session_state.tgt_lang_name = "Spanish"
if "text_area_value" not in st.session_state:
    st.session_state.text_area_value = ""
if "last_translated" not in st.session_state:
    st.session_state.last_translated = ""
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "last_engine" not in st.session_state:
    st.session_state.last_engine = None
if "reset_flag" not in st.session_state:
    st.session_state.reset_flag = False

if st.session_state.reset_flag:
    st.session_state.recognized_text = ""
    st.session_state.text_area_value = ""
    st.session_state.reset_flag = False

# ----------------------------------------------------------------------------
# SIDEBAR — SETTINGS
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    show_toggle_label = "⏩ Hide Options" if st.session_state.show_options else "📑 Show Options"
    if st.button(show_toggle_label, key="toggle_options"):
        st.session_state.show_options = not st.session_state.show_options
        st.rerun()

    st.markdown("---")

    # System health as styled badges instead of raw text
    st.markdown('<div class="status-row"><span class="status-label">TTS Engine</span>'
                + (f'<span class="pill pill-green">Edge TTS ✅</span>' if EDGE_TTS_AVAILABLE
                   else f'<span class="pill pill-amber">gTTS fallback</span>')
                + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-row"><span class="status-label">Speech Recognition</span>'
                '<span class="pill pill-green">Google STT</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="status-row"><span class="status-label">Translator</span>'
                '<span class="pill pill-green">Google Translate</span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### 🕘 History ({len(st.session_state.history)})")

    hist_col1, hist_col2 = st.columns(2)
    with hist_col1:
        if st.button("🗑️ Clear"):
            st.session_state.history = []
            save_history()
            st.rerun()
    with hist_col2:
        pass

    if st.session_state.history:
        st.download_button(
            "⬇ Export CSV",
            data=history_to_csv_bytes(),
            file_name="translation_history.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            "⬇ Export TXT",
            data=history_to_txt_bytes(),
            file_name="translation_history.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with st.expander("View translation history", expanded=False):
        if not st.session_state.history:
            st.caption("No translations yet.")
        else:
            for item in reversed(st.session_state.history):
                st.markdown(
                    f"""
                    <div class="history-item">
                        <div class="history-meta">{item['time']} • {item['source_lang']} → {item['target_lang']}</div>
                        <div class="history-orig">🗣️ {item['original']}</div>
                        <div class="history-trans">➡️ {item['translated']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("---")
    st.caption("Built with Streamlit • deep-translator • edge-tts / gTTS • SpeechRecognition")

# ----------------------------------------------------------------------------
# HERO
# ----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🌐 Real-Time Voice & Text Translator</h1>
        <p>Speak into your mic or type text to translate instantly — with natural spoken output.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# TABBED NAVIGATION
# ----------------------------------------------------------------------------
tab_translate, tab_history, tab_settings = st.tabs(["🎙️ Translator", "📜 History", "⚙️ Settings"])

# ============================================================================
# TAB: TRANSLATOR
# ============================================================================
with tab_translate:

    if st.session_state.show_options:
        # ---------------- Language selectors + swap button ----------------
        lc1, lc_swap, lc2 = st.columns([5, 1, 5])

        with lc1:
            source_lang_name = st.selectbox(
                "🎙️ Spoken language (source)",
                list(SOURCE_SPEECH_LANGUAGES.keys()),
                index=list(SOURCE_SPEECH_LANGUAGES.keys()).index(st.session_state.src_lang_name)
                if st.session_state.src_lang_name in SOURCE_SPEECH_LANGUAGES else 0,
                help="Used for speech recognition accuracy when you record audio. Choose Auto-Detect if unsure.",
                key="src_select",
            )
            st.session_state.src_lang_name = source_lang_name

        with lc_swap:
            st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            if st.button("🔁", key="swap_langs", help="Swap source and target languages"):
                cur_src = st.session_state.src_lang_name
                cur_tgt = st.session_state.tgt_lang_name
                # Only swap if the current source has a valid matching target entry
                if cur_src in TARGET_LANGUAGES and cur_tgt in SOURCE_SPEECH_LANGUAGES:
                    st.session_state.src_lang_name = cur_tgt
                    st.session_state.tgt_lang_name = cur_src
                else:
                    st.warning("This language pair can't be fully swapped (no matching speech-recognition locale). Target language kept, source reset to Auto-Detect.")
                    st.session_state.src_lang_name = "Auto-Detect"
                    st.session_state.tgt_lang_name = cur_src if cur_src in TARGET_LANGUAGES else st.session_state.tgt_lang_name
                st.rerun()

        with lc2:
            target_lang_name = st.selectbox(
                "🌍 Translate to (target)",
                list(TARGET_LANGUAGES.keys()),
                index=list(TARGET_LANGUAGES.keys()).index(st.session_state.tgt_lang_name)
                if st.session_state.tgt_lang_name in TARGET_LANGUAGES else 0,
                key="tgt_select",
            )
            st.session_state.tgt_lang_name = target_lang_name

        speed_label = st.select_slider(
            "🔊 Playback speed", options=list(SPEED_OPTIONS.keys()), value="1.0x"
        )
    else:
        # Compact / focus mode — keep last selections, no widgets shown
        source_lang_name = st.session_state.src_lang_name
        target_lang_name = st.session_state.tgt_lang_name
        speed_label = "1.0x"
        st.caption(f"🎙️ {source_lang_name} → 🌍 {target_lang_name}  •  (Options hidden — click **📑 Show Options** in sidebar)")

    source_lang_code = SOURCE_SPEECH_LANGUAGES[source_lang_name]
    target_lang_code = TARGET_LANGUAGES[target_lang_name]
    playback_rate = SPEED_OPTIONS[speed_label]

    st.markdown("<br>", unsafe_allow_html=True)

    # Full-width focus mode collapses the two columns into one wide column
    if st.session_state.show_options:
        col1, col2 = st.columns(2, gap="large")
    else:
        col1 = st.container()
        col2 = st.container()

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="card-title">🎤 Input — {source_lang_name}</div>',
            unsafe_allow_html=True,
        )

        audio_record = st.audio_input("Record audio")

        if audio_record:
            with st.spinner(f"Transcribing speech ({source_lang_name})..."):
                try:
                    st.session_state.recognized_text = transcribe_audio(audio_record, source_lang_code)
                    st.success(f"**Transcribed:** {st.session_state.recognized_text}")
                except sr.UnknownValueError:
                    st.warning("Could not understand the audio. Please try speaking clearly.")
                except sr.RequestError as e:
                    st.error(f"Speech recognition service error: {e}")

        text_input = st.text_area(
            "Or type / edit the source text here",
            value=st.session_state.recognized_text or st.session_state.text_area_value,
            height=150,
            placeholder="Type here, or record audio above...",
            key="source_text_area",
        )
        source_text = text_input if text_input else st.session_state.recognized_text
        st.session_state.text_area_value = source_text

        st.markdown(f'<div class="char-count">{len(source_text)} characters</div>', unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            translate_clicked = st.button("🔁 Translate", key="translate_btn")
        with btn_col2:
            if st.button("🧹 Reset / Clear", key="reset_btn"):
                st.session_state.reset_flag = True
                st.session_state.last_translated = ""
                st.session_state.last_audio = None
                st.session_state.last_engine = None
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-title">Output — {target_lang_name}</div>', unsafe_allow_html=True)

        if translate_clicked and source_text.strip():
            try:
                with st.spinner("Translating..."):
                    translate_source = "auto" if source_lang_name == "Auto-Detect" else "auto"
                    translated_text = GoogleTranslator(
                        source=translate_source, target=target_lang_code
                    ).translate(source_text)

                st.session_state.last_translated = translated_text

                with st.spinner("Generating audio..."):
                    audio_bytes, engine_used = synthesize_speech(translated_text, target_lang_code)
                st.session_state.last_audio = audio_bytes
                st.session_state.last_engine = engine_used

                # Log to history + persist
                st.session_state.history.append(
                    {
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_lang": source_lang_name,
                        "target_lang": target_lang_name,
                        "original": source_text,
                        "translated": translated_text,
                    }
                )
                save_history()

            except Exception as e:
                st.error(f"Translation error: {e}")
        elif translate_clicked:
            st.info("Please enter or record some text first.")

        if st.session_state.last_translated:
            st.text_area(
                "Translation result",
                st.session_state.last_translated,
                height=150,
                label_visibility="collapsed",
            )

            copy_to_clipboard_button(st.session_state.last_translated, key="result")

            if st.session_state.last_audio:
                pill_class = "pill-green" if st.session_state.last_engine == "Edge TTS" else "pill"
                st.markdown(
                    f'<span class="{pill_class}">{st.session_state.last_engine}</span>'
                    f'<span class="pill">{speed_label}</span>',
                    unsafe_allow_html=True,
                )

                b64_audio = base64.b64encode(st.session_state.last_audio).decode()
                st.components.v1.html(
                    f"""
                    <audio id="tts-audio" controls autoplay style="width:100%; margin-top:0.5rem;">
                        <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
                    </audio>
                    <script>
                        const audioEl = document.getElementById('tts-audio');
                        if (audioEl) {{ audioEl.playbackRate = {playback_rate}; }}
                    </script>
                    """,
                    height=70,
                )

                st.markdown(
                    get_binary_file_downloader_html(st.session_state.last_audio, "translation.mp3", "Audio File"),
                    unsafe_allow_html=True,
                )
            else:
                st.caption("🔇 Text-to-speech isn't available for this language.")
        else:
            st.info("Record audio or enter text on the left, then click Translate.")

        st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# TAB: HISTORY
# ============================================================================
with tab_history:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📜 Translation History</div>', unsafe_allow_html=True)

    top_col1, top_col2, top_col3 = st.columns(3)
    with top_col1:
        if st.button("🗑️ Clear All History", key="clear_hist_tab"):
            st.session_state.history = []
            save_history()
            st.rerun()
    with top_col2:
        if st.session_state.history:
            st.download_button(
                "⬇ Export .CSV",
                data=history_to_csv_bytes(),
                file_name="translation_history.csv",
                mime="text/csv",
                key="csv_export_tab",
                use_container_width=True,
            )
    with top_col3:
        if st.session_state.history:
            st.download_button(
                "⬇ Export .TXT",
                data=history_to_txt_bytes(),
                file_name="translation_history.txt",
                mime="text/plain",
                key="txt_export_tab",
                use_container_width=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.history:
        st.caption("No translations yet. Head to the Translator tab to get started.")
    else:
        for item in reversed(st.session_state.history):
            st.markdown(
                f"""
                <div class="history-item">
                    <div class="history-meta">{item['time']} • {item['source_lang']} → {item['target_lang']}</div>
                    <div class="history-orig">🗣️ {item['original']}</div>
                    <div class="history-trans">➡️ {item['translated']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# TAB: SETTINGS
# ============================================================================
with tab_settings:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">⚙️ System Status</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-row"><span class="status-label">TTS Engine</span>'
                + (f'<span class="pill pill-green">Edge TTS ✅ (neural voices)</span>' if EDGE_TTS_AVAILABLE
                   else f'<span class="pill pill-amber">gTTS fallback (edge-tts not installed)</span>')
                + '</div>', unsafe_allow_html=True)

    st.markdown('<div class="status-row"><span class="status-label">Speech Recognition</span>'
                '<span class="pill pill-green">Google Speech Recognition</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="status-row"><span class="status-label">Translation Engine</span>'
                '<span class="pill pill-green">Google Translate (deep-translator)</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="status-row"><span class="status-label">History Storage</span>'
                f'<span class="pill pill-green">Local file • {len(st.session_state.history)} entries</span></div>',
                unsafe_allow_html=True)

    if not EDGE_TTS_AVAILABLE:
        st.markdown(
            '<div class="status-row"><span class="status-label">Tip</span>'
            '<span class="pill pill-red">Run: pip install edge-tts</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown('<div class="card-title">🎚️ Defaults</div>', unsafe_allow_html=True)
    st.caption(f"Current source language: **{st.session_state.src_lang_name}**")
    st.caption(f"Current target language: **{st.session_state.tgt_lang_name}**")
    st.caption("Change these from the Translator tab's dropdowns, or use the 🔁 swap button.")

    st.markdown("---")
    if st.button("🗑️ Wipe All History Permanently", key="wipe_settings"):
        st.session_state.history = []
        save_history()
        st.success("History cleared.")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)