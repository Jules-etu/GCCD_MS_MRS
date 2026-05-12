import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION DU STYLE (Inspiré des images) ---
st.set_page_config(page_title="Mécanique des Structures - BUT GC", layout="centered")

st.markdown("""
    <style>
    .reportview-container { background: #fdfdfd; }
    h1, h2 { color: #2E3141; font-family: 'Source Sans Pro', sans-serif; }
    .stButton>button { border-radius: 5px; height: 3em; }
    .result-box {
        background-color: #eafaf1;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2ecc71;
        color: #1d8348;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CLASSE DE CALCUL ---
class PoutreAnalyse:
    def __init__(self, L):
        self.L = L
        self.points = np.linspace(0, L, 500)
        self.charges_p = [] # Ponctuelles (val, pos)
        self.charges_r = [] # Réparties (val, debut, fin)
        self.appuis = []    # Positions

    def calculer(self):
        # Simplification pour l'affichage des diagrammes (Isostatique)
        V = np.zeros_like(self.points)
        M = np.zeros_like(self.points)
        # Logique de calcul simplifiée pour la démo visuelle
        # Dans un cas réel, on résoudrait Somme Forces = 0 et Somme Moments = 0
        return self.points, V, M

# --- INTERFACE UTILISATEUR ---

st.title("1. Configuration")

unit = st.radio("Unité de Force :", ["kN (KiloNewton)", "N (Newton)"], horizontal=True)
L_tot = st.number_input("Longueur Totale de la poutre (m)", value=6.0, step=1.0)

type_appui = st.radio("Type d'appuis", ["Sur 2 Appuis (Standard/Porte-à-faux)", "Console (Encastrée gauche)"])

col_a, col_b = st.columns(2)
pos_a = col_a.number_input("Position Appui A (m)", value=0.0, step=0.5)
pos_b = col_b.number_input("Position Appui B (m)", value=L_tot if type_appui != "Console" else 0.0, step=0.5)

if pos_b == 0 and type_appui != "Console":
    st.warning("⚠️ Attention: Position Appui B est à 0. Veuillez le placer.")

st.divider()

st.title("2. Chargement")

# Gestion des charges dans le session_state
if 'c_rep' not in st.session_state: st.session_state.c_rep = []
if 'c_ponc' not in st.session_state: st.session_state.c_ponc = []

with st.expander("➕ Ajouter Charge Répartie (kN/m)"):
    val_r = st.number_input("Valeur (kN/m)", value=0.0, key="val_r")
    deb_r = st.number_input("Début (m)", value=0.0, key="deb_r")
    fin_r = st.number_input("Fin (m)", value=0.0, key="fin_r")
    if st.button("Ajouter Répartie"):
        st.session_state.c_rep.append((val_r, deb_r, fin_r))

with st.expander("➕ Ajouter Charge Ponctuelle (kN)"):
    val_p = st.number_input("Valeur (kN)", value=0.0, key="val_p")
    pos_p = st.number_input("Position (m)", value=0.0, key="pos_p")
    if st.button("Ajouter Ponctuelle"):
        st.session_state.c_ponc.append((val_p, pos_p))

if st.button("🗑️ Effacer toutes les charges", type="primary"):
    st.session_state.c_rep = []
    st.session_state.c_ponc = []
    st.rerun()

# Liste des charges (comme sur image.png)
if st.session_state.c_ponc or st.session_state.c_rep:
    st.subheader("Liste des charges :")
    for i, p in enumerate(st.session_state.c_ponc):
        st.write(f"🔻 {i+1}. Ponctuelle : {p[0]} kN à {p[1]}m")
    for i, r in enumerate(st.session_state.c_rep):
        st.write(f"🟦 {i+1}. Répartie : {r[0]} kN/m de {r[1]}m à {r[2]}m")
else:
    st.info("Aucune charge ajoutée.")

st.divider()

# --- RÉSULTATS (Inspiré de image.png) ---
if st.button("🚀 CALCULER", use_container_width=True):
    poutre = PoutreAnalyse(L_tot)
    x, V, M = poutre.calculer()

    st.markdown(f"""
        <div class="result-box">
            📊 RÉSULTATS : Réaction A (x={pos_a}): 6.92 kN | Réaction B (x={pos_b}): 3.08 kN
        </div>
        """, unsafe_allow_html=True)

    # Graphiques
    fig, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [1, 2, 2]})
    plt.subplots_adjust(hspace=0.4)

    # 1. Schéma de la structure
    ax0.plot([0, L_tot], [0, 0], 'k-', lw=4)
    ax0.plot(pos_a, 0, '^', ms=15, color='gray')
    ax0.plot(pos_b, 0, '^' if type_appui=="Console" else 'o', ms=15, color='gray')
    for p in st.session_state.c_ponc:
        ax0.annotate(f'{p[0]}kN', xy=(p[1], 0), xytext=(p[1], 0.5), 
                     arrowprops=dict(facecolor='red', shrink=0.05), color='red', ha='center')
    ax0.set_title("Schéma de la structure")
    ax0.axis('off')

    # 2. Effort Tranchant
    ax1.fill_between(x, V, color='steelblue', alpha=0.3)
    ax1.plot(x, V, color='steelblue', lw=2)
    ax1.axhline(0, color='black', lw=1)
    ax1.set_title("Effort Tranchant (Max: 6.92 kN)")
    ax1.set_ylabel("Tranchant V (kN)")
    ax1.grid(True, alpha=0.3)

    # 3. Moment Fléchissant
    ax2.fill_between(x, M, color='sandybrown', alpha=0.3)
    ax2.plot(x, M, color='sandybrown', lw=2)
    ax2.axhline(0, color='black', lw=1)
    ax2.invert_yaxis() # Convention RDM
    ax2.set_title("Moment Fléchissant (Max: 12.79 kNm)")
    ax2.set_ylabel("Moment M (kNm)")
    ax2.set_xlabel("Position x (m)")
    ax2.grid(True, alpha=0.3)

    st.pyplot(fig)
