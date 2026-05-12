import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Conception Portique GC", layout="wide")

class StructureSimple:
    def __init__(self):
        self.nodes = [] 
        self.elements = [] 
        self.supports = {} 
        self.loads = []

    def add_node(self, x, y):
        self.nodes.append(np.array([float(x), float(y)]))

    def add_element(self, n1, n2):
        self.elements.append((n1, n2))

    def add_support(self, node_idx, type_a):
        self.supports[node_idx] = type_a

# --- GESTION DU STATE ---
if 's' not in st.session_state:
    st.session_state.s = StructureSimple()

st.title("🏗️ Aide à la Saisie de Structure")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🛠️ Configuration en direct")
    
    # --- NOEUDS ---
    with st.expander("1. Placer les Noeuds", expanded=True):
        c1, c2 = st.columns(2)
        nx = c1.number_input("X (m)", value=0.0, step=0.5)
        ny = c2.number_input("Y (m)", value=0.0, step=0.5)
        if st.button("Poser le Noeud"):
            st.session_state.s.add_node(nx, ny)

    # --- ÉLÉMENTS (BARRES) ---
    if len(st.session_state.s.nodes) >= 2:
        with st.expander("2. Tracer les Barres"):
            indices = list(range(len(st.session_state.s.nodes)))
            n1 = st.selectbox("Départ", indices, format_func=lambda i: f"N{i}")
            n2 = st.selectbox("Arrivée", indices, format_func=lambda i: f"N{i}")
            if st.button("Relier"):
                if n1 != n2: st.session_state.s.add_element(n1, n2)

    # --- APPUIS ---
    if st.session_state.s.nodes:
        with st.expander("3. Définir les Appuis"):
            target = st.selectbox("Sur Noeud", range(len(st.session_state.s.nodes)), key="supp")
            type_a = st.selectbox("Type d'appui", ["Appui Simple", "Rotule", "Encastrement"])
            if st.button("Fixer l'appui"):
                st.session_state.s.add_support(target, type_a)

    if st.button("🗑️ Effacer tout", type="primary"):
        st.session_state.s = StructureSimple()
        st.rerun()

with col2:
    st.subheader("👀 Visualisation du Schéma Statique")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    s = st.session_state.s
    
    # 1. Dessin des barres (La poutre ou le portique)
    for (n1, n2) in s.elements:
        p1, p2 = s.nodes[n1], s.nodes[n2]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='#2c3e50', lw=5, zorder=1)
    
    # 2. Dessin des noeuds
    for i, p in enumerate(s.nodes):
        ax.scatter(p[0], p[1], color='white', edgecolor='black', s=100, zorder=3)
        ax.text(p[0]+0.1, p[1]+0.1, f"N{i}", fontsize=12, fontweight='bold')

    # 3. Dessin des appuis (Visuels comme sur l'image)
    for idx, type_a in s.supports.items():
        p = s.nodes[idx]
        if type_a == "Rotule":
            ax.plot(p[0], p[1]-0.2, 'r^', markersize=20) # Triangle
        elif type_a == "Encastrement":
            ax.plot([p[0]-0.2, p[0]+0.2], [p[1], p[1]], 'r-', lw=8) # Barre épaisse
            ax.plot([p[0], p[0]], [p[1], p[1]-0.3], 'r-', lw=2)
        else: # Appui simple
            ax.plot(p[0], p[1]-0.2, 'ro', markersize=15, mfc='none') # Cercle

    # Réglages axes
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.6)
    plt.xlim(-1, 10) # À adapter selon la taille saisie
    plt.ylim(-1, 6)
    st.pyplot(fig)

    st.info("💡 Vérifie ici que ta structure ressemble bien au schéma voulu avant de cliquer sur 'Calculer'.")
