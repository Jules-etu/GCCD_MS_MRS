import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="RDM BUT GC - Analyse de Structure", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stExpander { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

class StructureGC:
    def __init__(self):
        self.nodes = [] 
        self.elements = [] 
        self.supports = {} 
        self.point_loads = [] 
        self.results = None

    def add_node(self, x, y):
        self.nodes.append(np.array([float(x), float(y)]))
        return len(self.nodes) - 1

    def add_element(self, n1, n2, E=210e6, I=1e-4, A=1e-2):
        self.elements.append({'nodes': (n1, n2), 'E': E, 'I': I, 'A': A})

    def solve(self):
        n_nodes = len(self.nodes)
        if n_nodes < 2 or not self.elements: return
        K_global = np.zeros((3*n_nodes, 3*n_nodes))
        F_global = np.zeros(3*n_nodes)

        for elem in self.elements:
            n1, n2 = elem['nodes']
            p1, p2 = self.nodes[n1], self.nodes[n2]
            L = np.linalg.norm(p2 - p1)
            c, s = (p2[0]-p1[0])/L, (p2[1]-p1[1])/L
            T = np.array([[c, s, 0, 0, 0, 0], [-s, c, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
                          [0, 0, 0, c, s, 0], [0, 0, 0, -s, c, 0], [0, 0, 0, 0, 0, 1]])
            E, I, A = elem['E'], elem['I'], elem['A']
            k_loc = np.array([[E*A/L, 0, 0, -E*A/L, 0, 0], [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
                              [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L], [-E*A/L, 0, 0, E*A/L, 0, 0],
                              [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, -6*E*I/L**2], [0, 6*E*I/L**2, 2*E*I/L, 0, -6*E*I/L**2, 4*E*I/L]])
            k_glob = T.T @ k_loc @ T
            idx = [3*n1, 3*n1+1, 3*n1+2, 3*n2, 3*n2+1, 3*n2+2]
            for r in range(6):
                for col in range(6): K_global[idx[r], idx[col]] += k_glob[r, col]

        for n_idx, fx, fy in self.point_loads:
            F_global[3*n_idx] += fx
            F_global[3*n_idx+1] += fy

        free_dofs = np.ones(3*n_nodes, dtype=bool)
        for n_idx, (tx, ty, rot) in self.supports.items():
            if tx: free_dofs[3*n_idx] = False
            if ty: free_dofs[3*n_idx+1] = False
            if rot: free_dofs[3*n_idx+2] = False
        
        K_sub = K_global[np.ix_(free_dofs, free_dofs)]
        if np.linalg.cond(K_sub) < 1e15:
            U = np.zeros(3*n_nodes)
            U[free_dofs] = np.linalg.solve(K_sub, F_global[free_dofs])
            self.results = {"U": U, "R": K_global @ U - F_global}

# --- INITIALISATION ---
if 'struct' not in st.session_state:
    st.session_state.struct = StructureGC()
s = st.session_state.struct

# --- MISE EN PAGE ---
st.title("🏛️ Plateforme d'Ingénierie Structurelle")
st.sidebar.header("📋 Menu de Contrôle")

# Sidebar pour les actions globales
if st.sidebar.button("🗑️ Réinitialiser le projet"):
    st.session_state.struct = StructureGC()
    st.rerun()

col_input, col_viz = st.columns([1, 1.5])

with col_input:
    st.subheader("1. Modélisation")
    
    with st.expander("📍 Nœuds & Géométrie", expanded=True):
        c1, c2 = st.columns(2)
        x = c1.number_input("Coordonnée X", value=0.0, step=1.0)
        y = c2.number_input("Coordonnée Y", value=0.0, step=1.0)
        if st.button("Ajouter le point"): s.add_node(x, y)
        
        if len(s.nodes) >= 2:
            st.divider()
            n1 = st.selectbox("De Nœud", range(len(s.nodes)), key="n1")
            n2 = st.selectbox("À Nœud", range(len(s.nodes)), key="n2")
            if st.button("Tracer la barre"): s.add_element(n1, n2)

    with st.expander("🏗️ Liaisons & Forces", expanded=True):
        type_a = st.selectbox("Objet à ajouter", ["Encastrement", "Appui Simple", "Force Fy (kN)"])
        idx = st.number_input("Index du nœud cible", 0, max_value=max(0, len(s.nodes)-1))
        val = st.number_input("Valeur de la force", value=-10.0) if "Force" in type_a else 0
        
        if st.button("Valider l'élément"):
            if type_a == "Encastrement": s.supports[idx] = (1, 1, 1)
            elif type_a == "Appui Simple": s.supports[idx] = (0, 1, 0)
            else: s.point_loads.append((idx, 0, val))

    st.divider()
    lancer_calcul = st.button("🚀 LANCER L'ANALYSE FINALE", type="primary")

with col_viz:
    st.subheader("2. Visualisation")
    
    # --- GRAPHIQUE DE SAISIE (Toujours visible) ---
    fig_saisie, ax_s = plt.subplots(figsize=(8, 5))
    for e in s.elements:
        p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
        ax_s.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=3)
    for i, p in enumerate(s.nodes):
        ax_s.plot(p[0], p[1], 'o', mfc='white', mec='black', ms=10)
        ax_s.text(p[0]+0.1, p[1]+0.1, f"N{i}", fontsize=9, fontweight='bold')
        if i in s.supports:
            if s.supports[i] == (1,1,1): # Encastrement
                ax_s.plot([p[0]-0.2, p[0]+0.2], [p[1], p[1]], 'r-', lw=5)
            else: # Appui simple
                ax_s.plot(p[0], p[1]-0.2, 'ro', ms=8, mfc='none')
    
    ax_s.set_title("Schéma de conception")
    ax_s.set_aspect('equal')
    ax_s.axis('off')
    st.pyplot(fig_saisie)

    # --- AFFICHAGE DES RÉSULTATS (Uniquement après calcul) ---
    if lancer_calcul:
        s.solve()
        if s.results:
            st.success("Analyse terminée. Consultez les diagrammes ci-dessous.")
            
            # Création des diagrammes
            fig_res, (ax_m, ax_v) = plt.subplots(2, 1, figsize=(8, 10))
            
            def plot_diag(plot_ax, title, color):
                for e in s.elements:
                    p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
                    plot_ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=2)
                    # Dessin schématique du diagramme
                    plot_ax.fill_between([p1[0], p2[0]], [p1[1], p1[1]], [p1[1]+0.5, p2[1]+0.5], color=color, alpha=0.3)
                plot_ax.set_title(title)
                plot_ax.set_aspect('equal')
                plot_ax.axis('off')

            plot_diag(ax_m, "Diagramme des Moments (M)", "purple")
            plot_diag(ax_v, "Efforts Tranchants (V)", "orange")
            st.pyplot(fig_res)

            # Réactions
            st.subheader("📍 Réactions aux appuis")
            c_res = st.columns(len(s.supports))
            for i, n_idx in enumerate(s.supports):
                ry = s.results['R'][3*n_idx+1]
                c_res[i].metric(f"Nœud {n_idx}", f"{ry:.2f} kN", "Réaction Verticale")
        else:
            st.error("Erreur : La structure est instable (manque d'appuis).")
