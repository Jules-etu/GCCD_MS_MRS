import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

class Structure2D:
    def __init__(self):
        self.nodes = [] # Liste de (x, y)
        self.elements = [] # Liste de (node_i, node_j)
        self.supports = {} # {node_index: (fix_x, fix_y, fix_rot)}
        self.point_loads = [] # (node_index, fx, fy, m)
        
    def add_node(self, x, y):
        self.nodes.append(np.array([x, y]))
        return len(self.nodes) - 1

    def add_element(self, n1, n2):
        self.elements.append((n1, n2))

    def add_support(self, node_idx, tx, ty, rot):
        self.supports[node_idx] = (tx, ty, rot)

    def add_load(self, node_idx, fx, fy, m):
        self.point_loads.append((node_idx, fx, fy, m))

# --- INTERFACE ---
def main():
    st.set_page_config(page_title="Portique & Poutre Continue", layout="wide")
    st.title("🏗️ Analyse de Portiques et Poutres Multi-appuis")

    if 'struct' not in st.session_state:
        st.session_state.struct = Structure2D()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("1. Géométrie du Portique")
        
        # Ajout de Noeuds
        with st.expander("Ajouter un Noeud (Coordonnées)", expanded=True):
            cx = st.number_input("X (m)", value=0.0)
            cy = st.number_input("Y (m)", value=0.0)
            if st.button("Ajouter Noeud"):
                st.session_state.struct.add_node(cx, cy)

        # Ajout de Barres
        if len(st.session_state.struct.nodes) >= 2:
            with st.expander("Ajouter une Barre (Élément)"):
                n_idx = list(range(len(st.session_state.struct.nodes)))
                n1 = st.selectbox("Noeud de départ", n_idx, format_func=lambda i: f"N{i} ({st.session_state.struct.nodes[i]})")
                n2 = st.selectbox("Noeud d'arrivée", n_idx, format_func=lambda i: f"N{i} ({st.session_state.struct.nodes[i]})")
                if st.button("Relier"):
                    if n1 != n2:
                        st.session_state.struct.add_element(n1, n2)
                    else:
                        st.error("Sélectionnez deux noeuds différents")

        # Gestion des Appuis (Plus de 2 possibles)
        st.header("2. Appuis & Charges")
        if st.session_state.struct.nodes:
            with st.expander("Ajouter un Appui"):
                target_n = st.selectbox("Sur le Noeud", range(len(st.session_state.struct.nodes)))
                t_type = st.selectbox("Type", ["Appui Simple (Vertical)", "Rotule (X+Y)", "Encastrement"])
                if st.button("Fixer"):
                    if t_type == "Appui Simple (Vertical)":
                        st.session_state.struct.add_support(target_n, 0, 1, 0)
                    elif t_type == "Rotule (X+Y)":
                        st.session_state.struct.add_support(target_n, 1, 1, 0)
                    else:
                        st.session_state.struct.add_support(target_n, 1, 1, 1)

            with st.expander("Ajouter une Charge Ponctuelle"):
                node_l = st.selectbox("Noeud cible", range(len(st.session_state.struct.nodes)), key="load_node")
                fx = st.number_input("Force Horizontale Fx (kN)", value=0.0)
                fy = st.number_input("Force Verticale Fy (kN)", value=-10.0)
                if st.button("Appliquer Charge"):
                    st.session_state.struct.add_load(node_l, fx, fy, 0)

        if st.button("🗑️ Reset Structure", type="primary"):
            st.session_state.struct = Structure2D()
            st.rerun()

    with col2:
        st.header("Visualisation de la Structure")
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Dessiner les barres
        for (n1_idx, n2_idx) in st.session_state.struct.elements:
            p1 = st.session_state.struct.nodes[n1_idx]
            p2 = st.session_state.struct.nodes[n2_idx]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=3, label='Barre' if n1_idx==0 else "")

        # Dessiner les noeuds
        for i, node in enumerate(st.session_state.struct.nodes):
            ax.plot(node[0], node[1], 'go', markersize=8)
            ax.text(node[0], node[1]+0.2, f"N{i}", fontsize=12, fontweight='bold')

        # Dessiner les appuis
        for n_idx, (tx, ty, rot) in st.session_state.struct.supports.items():
            p = st.session_state.struct.nodes[n_idx]
            if tx and ty and rot: # Encastrement
                ax.plot(p[0], p[1], 'rs', markersize=12)
            else:
                ax.plot(p[0], p[1], 'r^', markersize=12)

        # Dessiner les charges
        for n_idx, fx, fy, m in st.session_state.struct.point_loads:
            p = st.session_state.struct.nodes[n_idx]
            if fy != 0:
                ax.arrow(p[0], p[1]+1, 0, -0.8, head_width=0.1, fc='blue', ec='blue')
            if fx != 0:
                ax.arrow(p[0]-1, p[1], 0.8, 0, head_width=0.1, fc='blue', ec='blue')

        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig)

        st.info("""
        **Note Technique :** Pour résoudre ce système (Portique Hyperstatique), vous devez intégrer 
        une matrice de rigidité élémentaire $[K]_e$ pour chaque barre :
        $$[K]_e = \\frac{E}{L} \\begin{bmatrix} A & \dots \\\\ \dots & \\frac{12I}{L^2} \\end{bmatrix}$$
        Voulez-vous que j'ajoute la fonction de résolution matricielle complète ?
        """)

if __name__ == "__main__":
    main()

