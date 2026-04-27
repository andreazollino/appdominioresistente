import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import pandas as pd
from io import BytesIO

# 1. Configurazione Pagina
st.set_page_config(page_title="VCASLU Pro - Final Edition", layout="wide")

st.title("Verifica Dominio N-M")

# --- INIZIALIZZAZIONE MEMORIA ---
if 'history' not in st.session_state:
    st.session_state.history = []

def clean_value(x):
    if x is None or pd.isna(x): return np.nan
    if isinstance(x, str): x = x.replace(' ', '').replace(',', '.')
    try: return float(x)
    except: return np.nan

def format_it(val):
    if val is None: return "-"
    return f"{val:.3f}".replace('.', ',')

# --- 2. INPUT DATI ---
col_in, col_out = st.columns([1, 2])

with col_in:
    st.subheader("1. Definizione Dominio ($N_{Rd}, M_{Rd}$)")
    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame({
            'N [kN]': [""],
            'M [kNm]': [""]
        })

    edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)

    st.subheader("2. Carico Agente ($N_{Ed}, M_{Ed}$)")
    n_ed_input = st.text_input("N_ed [kN]", value="")
    m_ed_input = st.text_input("M_ed [kNm]", value="")

# --- 3. LOGICA DI CALCOLO ---
df_clean = edited_df.copy()
df_clean['N [kN]'] = df_clean['N [kN]'].apply(clean_value)
df_clean['M [kNm]'] = df_clean['M [kNm]'].apply(clean_value)
df_clean = df_clean.dropna()

n_ed = clean_value(n_ed_input)
m_ed = clean_value(m_ed_input)
m_rd = None
rho = None

if len(df_clean) >= 2:
    # Identificazione frontiera (Superiore se Med > 0, Inferiore se Med < 0)
    df_calc = df_clean[df_clean['M [kNm]'] >= 0] if m_ed >= 0 else df_clean[df_clean['M [kNm]'] <= 0]
    df_calc = df_calc.sort_values(by='N [kN]').drop_duplicates(subset='N [kN]')
    
    if len(df_calc) >= 2:
        f_interp = interp1d(df_calc['N [kN]'], df_calc['M [kNm]'], kind='linear', fill_value="extrapolate")
        if df_calc['N [kN]'].min() <= n_ed <= df_calc['N [kN]'].max():
            m_rd = float(f_interp(n_ed))
            rho = abs(m_ed / m_rd) if m_rd != 0 else 0

# --- 4. GENERAZIONE GRAFICO E METRICHE ---
if len(df_clean) >= 2:
    with col_out:
        # VISUALIZZAZIONE RISULTATI (Metriche in alto)
        if m_rd is not None:
            res_col1, res_col2 = st.columns(2)
            res_col1.metric("M_rd (Resistente)", format_it(m_rd) + " kNm")
            res_col2.metric("Coefficiente ρ (Sfruttamento)", format_it(rho), 
                           delta=format_it(1-rho) + " margine",
                           delta_color="normal" if rho <= 1 else "inverse")

        # Creazione Plot
        fig, ax = plt.subplots(figsize=(10, 8))
        n_vals = df_clean['N [kN]'].values
        m_vals = df_clean['M [kNm]'].values
        n_closed = np.append(n_vals, n_vals[0])
        m_closed = np.append(m_vals, m_vals[0])
        
        ax.plot(n_closed, m_closed, color='#1f77b4', linewidth=2.5, label='Frontiera ($N_{Rd}, M_{Rd}$)', zorder=2)
        ax.fill(n_closed, m_closed, color='#1f77b4', alpha=0.15, zorder=1)
        ax.scatter(n_vals, m_vals, color='black', s=45, edgecolors='white', label='Punti Dominio', zorder=3)
        
        if m_rd is not None:
            ax.plot(n_ed, m_ed, 'ro', markersize=10, label='Progetto ($E_d$)', zorder=5)
            ax.vlines(n_ed, 0, m_rd, colors='red', linestyles='--', linewidth=1.5)
            ax.plot(n_ed, m_rd, 'rx', markersize=12, mew=3, label='Capacità ($R_d$)', zorder=4)

        ax.set_xlabel("$N_{Rd}$ [kN]", fontsize=12, fontweight='bold')
        ax.set_ylabel("$M_{Rd}$ [kNm]", fontsize=12, fontweight='bold')
        ax.axhline(0, color='black', lw=1.5, zorder=2)
        ax.axvline(0, color='black', lw=1.5, zorder=2)
        ax.grid(True, which='both', linestyle='--', alpha=0.5)
        ax.legend(loc='upper right', frameon=True, shadow=True)
        
        st.pyplot(fig)

        # PULSANTE SALVATAGGIO
        if st.button("💾 Salva Calcolo in Cronologia"):
            buf = BytesIO()
            fig.savefig(buf, format="png")
            st.session_state.history.append({
                "Ora": pd.Timestamp.now().strftime("%H:%M:%S"),
                "Ned": n_ed, "Med": m_ed, "Mrd": m_rd, "Rho": rho, "Grafico": buf
            })
            st.rerun()

# --- 5. CRONOLOGIA ---
if st.session_state.history:
    st.divider()
    st.subheader("📜 Cronologia Calcoli")
    hist_df = pd.DataFrame([{
        "Ora": e["Ora"], "N_ed": format_it(e["Ned"]), "M_ed": format_it(e["Med"]), 
        "M_rd": format_it(e["Mrd"]), "ρ": format_it(e["Rho"]),
        "Esito": "✅ OK" if e["Rho"] is not None and e["Rho"] <= 1 else "❌ NO"
    } for e in st.session_state.history])
    st.table(hist_df)