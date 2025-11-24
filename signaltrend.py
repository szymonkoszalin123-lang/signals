import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === KONFIGURACJA STRONY ===
st.set_page_config(page_title="Generator Sygnałów v2.0", layout="wide")
st.title("📡 Generator Sygnałów v2.0 (Zarządca Portfela)")
st.write("Wybierz system z portfela. Parametry zostaną załadowane automatycznie.")

# ==================================================
#  Baza Danych "ZŁOTYCH PRZEPISÓW"
# ==================================================
# Format:
# "Nazwa Wyświetlana": [SYMBOL, MULT, DŹWIGNIA, IN, OUT, EMA, M, K]
# --------------------------------------------------

ZŁOTE_PRZEPISY = {
    # Domyślny pusty
    "--- Wybierz system z portfela ---": 
        ["", 0.0, 0.0, 0, 0, 0, 0.0, 0.0],
    
    # --- MISTRZOWIE KRYPTO ---
    "Bitcoin": 
        ["BTC-USD", 1.0, 2.0, 60, 30, 100, 5.0, 4.0],
        
    "Ethereum": 
        ["ETH-USD", 1.0, 2.0, 60, 10, 50, 3.0, 4.5],
        
    "Solana": 
        ["SOL-USD", 1.0, 2.0, 5, 20, 30, 4.5, 4.5],
        
    "Polkadot": 
        ["DOT-USD", 1.0, 2.0, 5, 30, 30, 3.0, 4.0],

    "Kusama": 
        ["KSM-USD", 1.0, 2.0, 10, 30, 30, 4.5, 4.5],
        
    "Dogecoin": 
        ["DOGE-USD", 1.0, 2.0, 5, 10, 100, 5.0, 5.0],
        
    "Gala":
        ["GALA-USD", 1.0, 2.0, 10, 20, 50, 5.0, 5.0],

    # --- MISTRZOWIE SUROWCÓW ---
    "Bydło": 
        ["LE=F", 400.0, 10.0, 40, 25, 30, 2.5, 5.0],
        
    # --- SYSTEMY ZAPASOWE / ZAWIESZONE ---
    "Nasdaq 100": 
        ["^NDX", 20.0, 20.0, 40, 50, 50, 4.5, 5.0],
        
    "Ropa WTI": 
        ["CL=F", 1000.0, 10.0, 20, 10, 30, 2.5, 3.5]
}
ATR_PERIOD = 14 # Utrzymujemy stały ATR (nie optymalizowaliśmy go)

# ==================================================
# 1. PANEL BOCZNY - WYBÓR SYSTEMU I KAPITAŁU
# ==================================================

st.sidebar.header("1. Wybierz System")
wybrany_system_nazwa = st.sidebar.selectbox(
    "Wybierz system z portfela:", 
    list(ZŁOTE_PRZEPISY.keys())
)

# Jeśli nic nie wybrano, zatrzymaj aplikację
if wybrany_system_nazwa == "--- Wybierz system z portfela ---":
    st.info("Wybierz system z panelu bocznego, aby wygenerować sygnał.")
    st.stop()

# --- Automatyczne pobranie parametrów ---
try:
    przepis = ZŁOTE_PRZEPISY[wybrany_system_nazwa]
    SYMBOL = przepis[0]
    MULT = przepis[1]
    LEVERAGE = przepis[2]
    IN_PERIOD = przepis[3]
    OUT_PERIOD = przepis[4]
    EMA_PERIOD = przepis[5]
    M_SL = przepis[6]
    K_TSL = przepis[7]
except Exception as e:
    st.error(f"Wystąpił błąd przy ładowaniu przepisu: {e}")
    st.stop()

# --- Pozostałe ustawienia w panelu bocznym ---
st.sidebar.header("2. Wprowadź Kapitał")
KAPITAL = st.sidebar.number_input("Twój Kapitał (Wartość Konta)", value=10000.0, step=100.0)
RYZYKO_PROC = st.sidebar.number_input("Ryzyko na Transakcję (%)", value=4.0, step=0.5) / 100.0

# --- Wyświetlanie załadowanych parametrów ---
st.sidebar.header("3. Aktywne Parametry")
st.sidebar.success(f"Załadowano: {wybrany_system_nazwa}")
st.sidebar.markdown(f"""
* **Symbol:** `{SYMBOL}`
* **Mult:** `{MULT}`
* **Dźwignia:** `{LEVERAGE}`
* **IN:** `{IN_PERIOD}`, **OUT:** `{OUT_PERIOD}`, **EMA:** `{EMA_PERIOD}`
* **M:** `{M_SL}`, **K:** `{K_TSL}`
""")


# ==================================================
# 2. POBIERANIE I OBLICZANIE DANYCH (Bez zmian)
# ==================================================
@st.cache_data
def get_data_and_indicators(symbol, in_p, out_p, ema_p, atr_p):
    df = yf.download(symbol, period="2y", interval="1d", progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [col.lower() for col in df.columns]

    df['ema'] = df['close'].ewm(span=ema_p, adjust=False).mean()
    df['highest_in'] = df['high'].rolling(window=in_p).max().shift(1)
    df['lowest_in'] = df['low'].rolling(window=in_p).min().shift(1)
    df['lowest_out'] = df['low'].rolling(window=out_p).min().shift(1)
    df['highest_out'] = df['high'].rolling(window=out_p).max().shift(1)
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift())
    df['tr2'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['atr'] = df['tr'].ewm(alpha=1/atr_p, adjust=False).mean()
    return df

df = get_data_and_indicators(SYMBOL, IN_PERIOD, OUT_PERIOD, EMA_PERIOD, ATR_PERIOD)

if df is None:
    st.error(f"Nie udało się pobrać danych dla {SYMBOL}. Sprawdź symbol.")
    st.stop()

last_bar = df.iloc[-1]
prev_bar = df.iloc[-2]
last_date = df.index[-1].strftime('%Y-%m-%d')

# ==================================================
# 3. LOGIKA DECYZYJNA (Bez zmian)
# ==================================================

current_price = last_bar['close']
atr_value = last_bar['atr']
ema_value = last_bar['ema']
upper_band = last_bar['highest_in']
lower_band = last_bar['lowest_in']

trend_up = current_price > ema_value
trend_down = current_price < ema_value
breakout_up = current_price > upper_band
breakout_down = current_price < lower_band

# ==================================================
# 4. WYŚWIETLANIE WYNIKÓW
# ==================================================

st.info(f"Analiza dla dnia: **{last_date}** (Cena Zamknięcia: {current_price:.4f})")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Aktualna Cena", f"{current_price:.4f}")
col2.metric("Wartość ATR", f"{atr_value:.4f}")
col3.metric("Filtr Trendu (EMA)", f"{ema_value:.4f}", delta="Wzrostowy" if trend_up else "Spadkowy")
col4.metric(f"Szczyt/Dołek ({IN_PERIOD}-dni)", f"{upper_band:.2f} / {lower_band:.2f}")

st.divider()

st.header("🚦 Sygnały Wejścia (Na jutro/dziś)")

signal_found = False

# Logika LONG
if breakout_up and trend_up:
    st.success(f"✅ **SYGNAŁ KUPNA (LONG)!** Cena przebiła szczyt {IN_PERIOD}-dniowy i jest nad EMA.")
    signal_found = True
    entry_price = current_price
    sl_price = entry_price - (M_SL * atr_value)
    risk_per_point = (entry_price - sl_price) * MULT
    
    cash_risk = KAPITAL * RYZYKO_PROC
    if risk_per_point > 0:
        position_size = cash_risk / risk_per_point
    else:
        position_size = 0
    
    st.markdown(f"""
    ### 📋 Plan Transakcji:
    * **Kierunek:** KUPNO (Long)
    * **Cena Wejścia:** {entry_price:.4f} (Cena Market)
    * **Stop Loss:** {sl_price:.4f} (Odległość: {M_SL} x ATR)
    * **Sugerowany Wolumen:** **{position_size:.4f} lota**
    * *Ryzykowana kwota:* {cash_risk:.2f} (ok. {RYZYKO_PROC*100:.1f}%)
    """)

# Logika SHORT
elif breakout_down and trend_down:
    st.error(f"🔻 **SYGNAŁ SPRZEDAŻY (SHORT)!** Cena przebiła dołek {IN_PERIOD}-dniowy i jest pod EMA.")
    signal_found = True
    entry_price = current_price
    sl_price = entry_price + (M_SL * atr_value)
    risk_per_point = (sl_price - entry_price) * MULT
    
    cash_risk = KAPITAL * RYZYKO_PROC
    if risk_per_point > 0:
        position_size = cash_risk / risk_per_point
    else:
        position_size = 0
        
    st.markdown(f"""
    ### 📋 Plan Transakcji:
    * **Kierunek:** SPRZEDAŻ (Short)
    * **Cena Wejścia:** {entry_price:.4f} (Cena Market)
    * **Stop Loss:** {sl_price:.4f} (Odległość: {M_SL} x ATR)
    * **Sugerowany Wolumen:** **{position_size:.4f} lota**
    * *Ryzykowana kwota:* {cash_risk:.2f} (ok. {RYZYKO_PROC*100:.1f}%)
    """)

else:
    st.warning("✋ **BRAK NOWYCH SYGNAŁÓW WEJŚCIA.** Czekaj cierpliwie.")
    if trend_up:
        dist = (upper_band - current_price)
        st.caption(f"Jesteśmy w trendzie wzrostowym, ale brakuje wybicia. Do szczytu brakuje: {dist:.4f}")
    elif trend_down:
        dist = (current_price - lower_band)
        st.caption(f"Jesteśmy w trendzie spadkowym, ale brakuje wybicia. Do dołka brakuje: {dist:.4f}")

st.divider()

# --- SEKCJA C: ZARZĄDZANIE OTWARTĄ POZYCJĄ (Trailing Stop) ---
st.header("🛡️ Zarządzanie Otwartą Pozycją (Sygnały Wyjścia)")
st.write("Jeśli **JUŻ MASZ** otwartą pozycję, oto gdzie powinien znajdować się Twój Stop Loss na dziś:")

highest_recent = df['high'].rolling(window=IN_PERIOD).max().iloc[-1]
lowest_recent = df['low'].rolling(window=IN_PERIOD).min().iloc[-1]

tsl_long = highest_recent - (K_TSL * atr_value)
tsl_short = lowest_recent + (K_TSL * atr_value)

col_sl1, col_sl2 = st.columns(2)

with col_sl1:
    st.markdown("### Dla Pozycji DŁUGIEJ (Long)")
    st.markdown(f"Teoretyczny Trailing SL powinien być na: **{tsl_long:.4f}**")
    st.caption(f"(Najwyższy szczyt {highest_recent:.4f} - {K_TSL}xATR)")
    
    if current_price < df.iloc[-1]['lowest_out']:
        st.error(f"🚨 **SYGNAŁ WYJŚCIA (Kanał OUT)!** Cena spadła poniżej minimum z {OUT_PERIOD} dni ({df.iloc[-1]['lowest_out']:.4f}). Zamknij Longa.")

with col_sl2:
    st.markdown("### Dla Pozycji KRÓTKIEJ (Short)")
    st.markdown(f"Teoretyczny Trailing SL powinien być na: **{tsl_short:.4f}**")
    st.caption(f"(Najniższy dołek {lowest_recent:.4f} + {K_TSL}xATR)")

    if current_price > df.iloc[-1]['highest_out']:
        st.error(f"🚨 **SYGNAŁ WYJŚCIA (Kanał OUT)!** Cena wzrosła powyżej maksimum z {OUT_PERIOD} dni ({df.iloc[-1]['highest_out']:.4f}). Zamknij Shorta.")

# ==================================================
# 5. WYKRES (Bez zmian)
# ==================================================
st.divider()
st.subheader("Wizualizacja Rynku (Ostatnie 100 dni)")

df_plot = df.tail(100)
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_plot.index, df_plot['close'], label='Cena', color='black', linewidth=1.5)
ax.plot(df_plot.index, df_plot['ema'], label=f'EMA ({EMA_PERIOD})', color='blue', linestyle='--', alpha=0.7)
ax.plot(df_plot.index, df_plot['highest_in'], label=f'Max ({IN_PERIOD})', color='green', alpha=0.5)
ax.plot(df_plot.index, df_plot['lowest_in'], label=f'Min ({IN_PERIOD})', color='red', alpha=0.5)

ax.set_title(f"{SYMBOL} - Analiza Techniczna")
ax.legend()
ax.grid(True, alpha=0.3)

st.pyplot(fig)