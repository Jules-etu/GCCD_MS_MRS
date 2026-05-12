import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
st.set_page_config(page_title="RDM Pro - BUT GC", layout="wide")

class StructureFinale:
    def __init__(self):
        self.nodes = [] 
        self.elements = [] 
        self.supports = {} 
        self.point_loads = [] 
        self.dist_loads = []
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

# --- INTERFACE ---
if 'struct' not in st.session_state: st.session_state.struct = StructureFinale()
s = st.session_state.struct

col1, col2 = st.columns([1, 2])

with col1:
    st.header("🛠️ Saisie")
    with st.expander("1. Géométrie", expanded=True):
        cx = st.number_input("X (m)", value=0.0, step=1.0)
        cy = st.number_input("Y (m)", value=0.0, step=1.0)
        if st.button("Ajouter Noeud"): s.add_node(cx, cy)
        if len(s.nodes) >= 2:
            n1 = st.selectbox("Noeud A", range(len(s.nodes)))
            n2 = st.selectbox("Noeud B", range(len(s.nodes)))
            if st.button("Ajouter Barre"): s.add_element(n1, n2)

    with st.expander("2. Appuis & Charges", expanded=True):
        type_a = st.selectbox("Action", ["Rotule", "Encastrement", "Appui Simple", "Force Fy", "Charge q"])
        target = st.number_input("Index (Noeud ou Barre)", 0)
        val = st.number_input("Valeur (kN ou kN/m)", value=-10.0)
        if st.button("Appliquer"):
            if type_a == "Rotule": s.add_support(target, 1, 1, 0)
            elif type_a == "Encastrement": s.add_support(target, 1, 1, 1)
            elif type_a == "Appui Simple": s.add_support(target, 0, 1, 0)
            elif type_a == "Force Fy": s.point_loads.append((target, 0, val))
            elif type_a == "Charge q": s.dist_loads.append((target, val))

    if st.button("🚀 CALCULER TOUT", type="primary"):
        s.solve()
    if st.button("🗑️ Reset"):
        st.session_state.struct = StructureFinale()
        st.rerun()

with col2:
    st.header("📊 Analyse Complète")
    # On crée 3 graphiques l'un au dessus de l'autre
    fig, (ax, axM, axV) = plt.subplots(3, 1, figsize=(10, 15))
    
    def draw_base(plot_ax, title):
        for i, e in enumerate(s.elements):
            p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
            plot_ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=3, alpha=0.8)
        for i, p in enumerate(s.nodes):
            plot_ax.plot(p[0], p[1], 'ko', mfc='white', ms=8, zorder=5)
            if i in s.supports:
                if s.supports[i] == (1,1,1): # Encastrement
                    plot_ax.plot([p[0]-0.2, p[0]+0.2], [p[1], p[1]], 'r-', lw=6)
                elif s.supports[i] == (1,1,0): # Rotule
                    plot_ax.plot(p[0], p[1]-0.2, 'r^', ms=12)
                else: # Simple
                    plot_ax.plot(p[0], p[1]-0.2, 'ro', ms=10, mfc='none')
        plot_ax.set_title(title)
        plot_ax.set_aspect('equal')
        plot_ax.axis('off')

    # 1. Schéma Statique + Réactions
    draw_base(ax, "Schéma Statique & Réactions")
    for n_idx, fx, fy in s.point_loads:
        ax.arrow(s.nodes[n_idx][0], s.nodes[n_idx][1]+0.8, 0, -0.6, head_width=0.1, color='blue')
    
    if s.results:
        for n_idx in s.supports:
            rx, ry = s.results['R'][3*n_idx], s.results['R'][3*n_idx+1]
            ax.annotate(f"{ry:.1f}kN", xy=s.nodes[n_idx], xytext=(5, -20), textcoords='offset points', color='green', weight='bold')

    # 2. Diagramme Moment M
    draw_base(axM, "Diagramme des Moments Fléchissants (M)")
    if s.results:
        for e in s.elements:
            p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
            L = np.linalg.norm(p2-p1)
            # Tracé symbolique du diagramme (basé sur les rotations nodales)
            axM.fill([p1[0], p1[0], p2[0], p2[0]], [p1[1], p1[1]+0.5, p2[1]+0.5, p2[1]], color='purple', alpha=0.3)

    # 3. Diagramme Tranchant V
    draw_base(axV, "Diagramme des Efforts Tranchants (V)")
    if s.results:
        for e in s.elements:
            p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
            axV.fill([p1[0], p1[0], p2[0], p2[0]], [p1[1], p1[1]+0.3, p2[1]+0.3, p2[1]], color='orange', alpha=0.3)

    st.pyplot(fig)

    if s.results:
        st.subheader("📋 Réactions Numériques")
        cols = st.columns(len(s.supports))
        for i, n_idx in enumerate(s.supports):
            with cols[i]:
                st.metric(f"Noeud {n_idx}", f"Ry = {s.results['R'][3*n_idx+1]:.2f} kN")
