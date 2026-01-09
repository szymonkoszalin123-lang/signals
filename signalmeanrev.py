import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === KONFIGURACJA STRONY ===
st.set_page_config(page_title="Sygnały Mean Reversion", layout="wide")
st.title("Generator Sygnałów Mean Reversion")
st.write("Strategia oparta na surowym RSI (bez wygładzania) i ATR")

# ==================================================
#  BAZA DANYCH "ZŁOTYCH PRZEPISÓW"
# ==================================================
ZŁOTE_PRZEPISY = {
    "--- Wybierz lub wpisz ręcznie ---": 
        ["", 1.0, 1.0, 14, 14, 2.0, 30, 70, 70, 30],
        
    "Pszenica (ZW=F)":
        ["ZW=F", 400.0, 10.0, 14, 14, 2.0, 30, 50, 80, 50],
        
    "Kakao (CC=F)":
        ["CC=F", 10.0, 10.0, 5, 14, 2.0, 10, 50, 90, 50],
        
    "Bawełna (CT=F)":
        ["CT=F", 500.0, 10.0, 5, 5, 2.0, 30, 50, 80, 40],
        
    "Srebro (SI=F)": 
        ["SI=F", 5000.0, 20.0, 5, 20, 3.0, 10, 70, 90, 50],
        
    "Złoto (GC=F)":
        ["GC=F", 100.0, 20.0, 14, 14, 2.0, 30, 60, 90, 50],
        
    "Ropa WTI (crude oil) (CL=F)":
        ["CL=F", 1000.0, 10.0, 14, 14, 2.0, 10, 60, 70, 40],
        
    "Ropa Brent (BZ=F)":
        ["BZ=F", 1000.0, 10.0, 14, 14, 2.0, 10, 60, 70, 40],
        
    "Benzyna (RB=F)":
        ["RB=F", 420.0, 10.0, 14, 14, 3.0, 10, 50, 70, 50],
        
    "UK100 (^FTSE)": 
        ["^FTSE", 10.0, 20.0, 14, 5, 2.0, 30, 50, 80, 50],
        
    "DE40 (^GDAXI)":
        ["^GDAXI", 25.0, 20.0, 14, 3, 2.0, 30, 60, 80, 50],
        
    "FRA40 (^FCHI)":
        ["^FCHI", 10.0, 20.0, 5, 14, 2.0, 20, 60, 90, 50],
        
    "EU50 (^STOXX50E)":
        ["^STOXX50E", 10.0, 20.0, 5, 5, 2.0, 30, 50, 90, 40],
        
    "JP225 (^N225)":
        ["^N225", 500.0, 20.0, 5, 5, 2.0, 10, 60, 90, 40],
        
    "US100 (^NDX)":
        ["^NDX", 20.0, 20.0, 3, 14, 2.0, 30, 60, 90, 40],
        
    "US500 (^GSPC)":
        ["^GSPC", 50.0, 20.0, 5, 14, 2.0, 20, 50, 90, 50],
        
    "VIX (^VIX)":
        ["^VIX", 4000.0, 5.0, 3, 5, 2.0, 30, 60, 70, 50],
        
    "GBP/JPY (GBPJPY=X)":
        ["GBPJPY=X", 100000.0, 30.0, 14, 14, 2.0, 30, 60, 90, 50],
        
    "GBP/PLN (GBPPLN=X)":
        ["GBPPLN=X", 100000.0, 20.0, 3, 5, 2.0, 20, 60, 70, 40]
}

# ==================================================
# 1. PANEL BOCZNY
# ==================================================
st.sidebar.header("1. Wybierz system")
wybrany_system = st.sidebar.selectbox("Wybierz z listy:", list(ZŁOTE_PRZEPISY.keys()))

if wybrany_system == "--- Wybierz z listy ---":
    defaults = ZŁOTE_PRZEPISY["--- Wybierz z listy ---"]
else:
    defaults = ZŁOTE_PRZEPISY[wybrany_system]

st.sidebar.header("2. Konfiguracja")
SYMBOL = st.sidebar.text_input("Symbol", value=defaults[0])
KAPITAL = st.sidebar.number_input("Kapitał (Equity)", value=10000.0, step=100.0)
RYZYKO_PROC = st.sidebar.number_input("Ryzyko (%)", value=4.0, step=0.5) / 100.0
MULT = st.sidebar.number_input("Wartość 1 punktu (mult)", value=defaults[1])

st.sidebar.header("3. Parametry strategii")
RSI_PERIOD = st.sidebar.number_input("Okres RSI", value=defaults[3])
ATR_PERIOD = st.sidebar.number_input("Okres ATR", value=defaults[4])
M_SL = st.sidebar.number_input("Mnożnik SL ('M')", value=defaults[5])

st.sidebar.subheader("Long")
RSI_L_ENT = st.sidebar.number_input("Wejście Long (RSI < X)", value=defaults[6])
RSI_L_EX = st.sidebar.number_input("Wyjście Long (RSI > X)", value=defaults[7])

st.sidebar.subheader("Short")
RSI_S_ENT = st.sidebar.number_input("Wejście Short (RSI > X)", value=defaults[8])
RSI_S_EX = st.sidebar.number_input("Wyjście Short (RSI < X)", value=defaults[9])

if SYMBOL == "":
    st.info("Wybierz system lub wpisz symbol.")
    st.stop()

# ==================================================
# 2. OBLICZENIA (WERSJA SUROWA / RAW)
# ==================================================
@st.cache_data
def get_data_and_indicators(symbol, rsi_p, atr_p):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]

        # --- 1. RSI (WERSJA SUROWA / CLASSIC SMA) ---
        # To jest wersja, o którą prosiłeś - bez wygładzania Wildera
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # --- 2. ATR (WERSJA SUROWA / CLASSIC SMA) ---
        # Tutaj też używamy prostej średniej, żeby było spójnie
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift())
        df['tr2'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=atr_p).mean()

        return df
    except Exception as e:
        return None

df = get_data_and_indicators(SYMBOL, RSI_PERIOD, ATR_PERIOD)

if df is None:
    st.error(f"Błąd danych dla {SYMBOL}")
    st.stop()

last_bar = df.iloc[-1]
prev_bar = df.iloc[-2]
last_date = df.index[-1].strftime('%Y-%m-%d')

current_price = last_bar['close']
rsi_val = last_bar['rsi']
atr_val = last_bar['atr']

# ==================================================
# 3. LOGIKA
# ==================================================

st.info(f"Analiza dla dnia: **{last_date}** | Cena: **{current_price:.4f}**")

c1, c2, c3, c4 = st.columns(4)
c1.metric("RSI", f"{rsi_val:.2f}", delta=f"{rsi_val - prev_bar['rsi']:.2f}")
c2.metric("ATR", f"{atr_val:.4f}")
c3.metric("Long <", f"{RSI_L_ENT}")
c4.metric("Short >", f"{RSI_S_ENT}")

st.divider()

# SYGNAŁY
signal_long = rsi_val < RSI_L_ENT
signal_short = rsi_val > RSI_S_ENT

if signal_long:
    st.success("**SYGNAŁ KUPNA (LONG)!** RSI przebiło podłogę.")
    
    sl_price = current_price - (M_SL * atr_val)
    risk_per_lot = (current_price - sl_price) * MULT
    
    risk_cash = KAPITAL * RYZYKO_PROC
    vol = 0
    if risk_per_lot > 0:
        vol = risk_cash / risk_per_lot
        
    st.markdown(f"""
    * **Sugerowany wolumen:** `{vol:.4f} lota`
    * **Cena wejścia:** `{current_price:.4f}`
    * **Stop Loss:** `{sl_price:.4f}`
    * **Cel (TP):** Zamknij ręcznie, gdy RSI > **{RSI_L_EX}**.
    """)

elif signal_short:
    st.error("**SYGNAŁ SPRZEDAŻY (SHORT)!** RSI przebiło sufit.")
    
    sl_price = current_price + (M_SL * atr_val)
    risk_per_lot = (sl_price - current_price) * MULT
    
    risk_cash = KAPITAL * RYZYKO_PROC
    vol = 0
    if risk_per_lot > 0:
        vol = risk_cash / risk_per_lot
        
    st.markdown(f"""
    * **Sugerowany wolumen:** `{vol:.4f} lota`
    * **Cena wejścia:** `{current_price:.4f}`
    * **Stop Loss:** `{sl_price:.4f}`
    * **Cel (TP):** Zamknij ręcznie, gdy RSI < **{RSI_S_EX}**.
    """)

else:
    st.warning("**BRAK SYGNAŁÓW.**")
    if rsi_val < 50:
        st.caption(f"Do Longa brakuje spadku RSI o: {rsi_val - RSI_L_ENT:.2f} pkt.")
    else:
        st.caption(f"Do Shorta brakuje wzrostu RSI o: {RSI_S_ENT - rsi_val:.2f} pkt.")

st.divider()

# ZARZĄDZANIE
st.header("Zarządzanie (Wyjścia)")
c_l, c_s = st.columns(2)
with c_l:
    st.markdown("**Masz LONGA?**")
    if rsi_val > RSI_L_EX: st.success(f"**ZAMKNIJ!** RSI ({rsi_val:.2f}) > {RSI_L_EX}")
    else: st.info("Trzymaj.")
with c_s:
    st.markdown("**Masz SHORTA?**")
    if rsi_val < RSI_S_EX: st.success(f"**ZAMKNIJ!** RSI ({rsi_val:.2f}) < {RSI_S_EX}")
    else: st.info("Trzymaj.")

# WYKRES
st.divider()
df_plot = df.tail(100)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})

ax1.plot(df_plot.index, df_plot['close'], color='black', label='Cena')
ax1.grid(True, alpha=0.3)
ax1.set_title(f"Cena {SYMBOL}")

ax2.plot(df_plot.index, df_plot['rsi'], color='purple', label='RSI (Raw)')
ax2.axhline(RSI_L_ENT, color='green', linestyle='--')
ax2.axhline(RSI_S_ENT, color='red', linestyle='--')
ax2.axhline(RSI_L_EX, color='blue', linestyle=':')
ax2.axhline(RSI_S_EX, color='orange', linestyle=':')
ax2.set_ylim(0, 100)
ax2.grid(True, alpha=0.3)
ax2.legend(["RSI", "L Ent", "S Ent", "L Ex", "S Ex"], loc='upper left', fontsize='small')


st.pyplot(fig)
