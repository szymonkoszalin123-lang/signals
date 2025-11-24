import streamlit as st

# Ustawienie strony (Musi być pierwszą komendą Streamlit)
st.set_page_config(page_title="Moje Centrum Tradingowe", layout="wide")

# Tytuł Dashboardu
st.title("Centrum Dowodzenia")
st.markdown("---")

# Tworzymy zakładki (Tabs)
tab1, tab2 = st.tabs(["📈 Strategia TREND", "🧲 Strategia MEAN REVERSION"])

# --- ZAKŁADKA 1: TREND FOLLOWING ---
with tab1:
    st.header("System Podążania za Trendem")
    st.caption("Rynki: głównie krypto")
    
    # Tu dzieje się magia - uruchamiamy kod z drugiego pliku
    # Używamy exec(open(...).read()) aby wczytać i wykonać kod
    try:
        with open("signaltrend.py", encoding="utf-8") as f:
            code = f.read()
            # Usuwamy linię z set_page_config, bo może być wywołana tylko raz w dashboardzie
            code = code.replace("st.set_page_config", "# st.set_page_config")
            exec(code)
    except FileNotFoundError:
        st.error("Błąd: Nie znaleziono pliku 'signaltrend.py'. Upewnij się, że jest w tym samym folderze.")

# --- ZAKŁADKA 2: MEAN REVERSION ---
with tab2:
    st.header("System Powrotu do Średniej")
    st.caption("Rynki: towary, indeksy, waluty")
    
    try:
        with open("signalmeanrev.py", encoding="utf-8") as f:
            code = f.read()
            # Usuwamy linię z set_page_config
            code = code.replace("st.set_page_config", "# st.set_page_config")
            exec(code)
    except FileNotFoundError:
        st.error("Błąd: Nie znaleziono pliku 'signalmeanrev.py'. Upewnij się, że jest w tym samym folderze.")

# Stopka
st.markdown("---")
st.caption("Twoje Portfolio Systemowe v1.0")