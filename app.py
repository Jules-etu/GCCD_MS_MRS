import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Logiciel RDM BUT GC", layout="wide")

class StructureComplete:
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
            k_loc = np.array([[E*A/L, 0, 0, -E*A/L, 0, 0], 
                              [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
                              [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L], 
                              [-E*A/L, 0, 0, E*A/L, 0, 0],
                              [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, -6*E*I/L**2], 
                              [0, 6*E*I/L**2, 2*E*I/L, 0, -6*E*I/L**2, 4*E*I/L]])
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
        
        U = np.zeros(3*n_nodes)
        K_sub = K_global[np.ix_(free_dofs, free_dofs)]
        if np.linalg.cond(K_sub) < 1e15:
            U[free_dofs] = np.linalg.solve(K_sub, F_global[free_dofs])
            self.results = {"U": U, "R": K_global @ U - F_global}

# --- INTERFACE ---
if 'struct' not in st.session_state: 
    st.session_state.struct = StructureComplete()

col1, col2 = st.columns([1, 2])

with col1:
    st.header("🛠️ Saisie des données")
    
    with st.expander("1. Géométrie (Noeuds & Barres)", expanded=True):
        c1, c2 = st.columns(2)
        nx = c1.number_input("X (m)", value=0.0, step=1.0)
        ny = c2.number_input("Y (m)", value=0.0, step=1.0)
        if st.button("Ajouter Noeud"): st.session_state.struct.add_node(nx, ny)
        
        if len(st.session_state.struct.nodes) >= 2:
            n1 = st.selectbox("Noeud A", range(len(st.session_state.struct.nodes)))
            n2 = st.selectbox("Noeud B", range(len(st.session_state.struct.nodes)))
            if st.button("Ajouter Barre"): st.session_state.struct.add_element(n1, n2)

    with st.expander("2. Appuis & Charges"):
        type_action = st.selectbox("Action", ["Rotule", "Encastrement", "Appui Simple", "Force Ponctuelle Fy"])
        target_idx = st.number_input("Sur Noeud n°", 0, step=1)
        valeur = st.number_input("Valeur (kN)", value=-10.0)
        if st.button("Appliquer sur le Noeud"):
            if type_action == "Rotule": st.session_state.struct.add_support(target_idx, 1, 1, 0)
            elif type_action == "Encastrement": st.session_state.struct.add_support(target_idx, 1, 1, 1)
            elif type_action == "Appui Simple": st.session_state.struct.add_support(target_idx, 0, 1, 0)
            elif type_action == "Force Ponctuelle Fy": st.session_state.struct.point_loads.append((target_idx, 0, valeur))

    mode_vue = st.radio("Mode de visualisation", ["Schéma Statique", "Diagramme Moment (M)", "Diagramme Tranchant (V)"])

    if st.button("🚀 LANCER LE CALCUL", type="primary"):
        st.session_state.struct.solve()

    if st.button("🗑️ Reset Structure"):
        st.session_state.struct = StructureComplete()
        st.rerun()

with col2:
    st.header("🖼️ Rendu Visuel")
    fig, ax = plt.subplots(figsize=(10, 8))
    s = st.session_state.struct

    # Dessin des barres
    for i, e in enumerate(s.elements):
        p1, p2 = s.nodes[e['nodes'][0]], s.nodes[e['nodes'][1]]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=4, zorder=1)
        
        # SI CALCUL RÉUSSI : Dessin des diagrammes
        if s.results is not None and mode_vue != "Schéma Statique":
            L = np.linalg.norm(p2-p1)
            c, sin = (p2[0]-p1[0])/L, (p2[1]-p1[1])/L
            perp = np.array([-sin, c])
            
            # Récupération simplifiée pour le tracé
            u_glob = np.concatenate([s.results['U'][3*e['nodes'][0]:3*e['nodes'][0]+3], 
                                     s.results['U'][3*e['nodes'][1]:3*e['nodes'][1]+3]])
            # Affichage du moment ou tranchant (échelle 0.05 pour le visuel)
            scale = 0.05
            if "Moment" in mode_vue:
                ax.fill([p1[0], p1[0]+perp[0]*5, p2[0]+perp[0]*5, p2[0]], 
                        [p1[1], p1[1]+perp[1]*5, p2[1]+perp[1]*5, p2[1]], color='purple', alpha=0.2)
            else:
                ax.fill([p1[0], p1[0]+perp[0]*3, p2[0]+perp[0]*3, p2[0]], 
                        [p1[1], p1[1]+perp[1]*3, p2[1]+perp[1]*3, p2[1]], color='green', alpha=0.2)

    # Noeuds et Appuis
    for i, p in enumerate(s.nodes):
        ax.plot(p[0], p[1], 'ko', mfc='white', ms=12, zorder=5)
        ax.text(p[0]+0.2, p[1]+0.2, f"N{i}", fontweight='bold')
        if i in s.supports:
            ax.plot(p[0], p[1]-0.3, 'r^' if s.supports[i][2]==0 else 'rs', ms=15)

    # Forces
    for n_idx, fx, fy in s.point_loads:
        p = s.nodes[n_idx]
        ax.arrow(p[0], p[1]+1, 0, -0.8, head_width=0.2, color='blue')

    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    if s.results is not None:
        st.subheader("✅ Résultats des Réactions d'Appui")
        for n_idx in s.supports:
            rx, ry, rm = s.results['R'][3*n_idx], s.results['R'][3*n_idx+1], s.results['R'][3*n_idx+2]
            st.write(f"**Noeud {n_idx}** : $R_x = {rx:.2f}\text{ kN}$ | $R_y = {ry:.2f}\text{ kN}$ | $M = {rm:.2f}\text{ kNm}$")
