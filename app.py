import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

class Structure2D:
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

    def add_support(self, node_idx, tx, ty, rot):
        self.supports[node_idx] = (tx, ty, rot)

    def add_load(self, node_idx, fx, fy, m):
        self.point_loads.append((node_idx, fx, fy, m))

    def solve(self):
        n_nodes = len(self.nodes)
        if n_nodes < 2 or not self.elements: return
        
        K_global = np.zeros((3*n_nodes, 3*n_nodes))
        F_global = np.zeros(3*n_nodes)

        # Assemblage de la matrice de rigidité
        for elem in self.elements:
            n1, n2 = elem['nodes']
            p1, p2 = self.nodes[n1], self.nodes[n2]
            L = np.linalg.norm(p2 - p1)
            cos, sin = (p2[0]-p1[0])/L, (p2[1]-p1[1])/L
            T = np.array([[cos, sin, 0, 0, 0, 0], [-sin, cos, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
                          [0, 0, 0, cos, sin, 0], [0, 0, 0, -sin, cos, 0], [0, 0, 0, 0, 0, 1]])
            
            E, I, A = elem['E'], elem['I'], elem['A']
            k_local = np.array([
                [E*A/L, 0, 0, -E*A/L, 0, 0],
                [0, 12*E*I/L**3, 6*E*I/L**2, 0, -12*E*I/L**3, 6*E*I/L**2],
                [0, 6*E*I/L**2, 4*E*I/L, 0, -6*E*I/L**2, 2*E*I/L],
                [-E*A/L, 0, 0, E*A/L, 0, 0],
                [0, -12*E*I/L**3, -6*E*I/L**2, 0, 12*E*I/L**3, -6*E*I/L**2],
                [0, 6*E*I/L**2, 2*E*I/L, 0, -6*E*I/L**2, 4*E*I/L]
            ])
            k_global_elem = T.T @ k_local @ T
            idx = [3*n1, 3*n1+1, 3*n1+2, 3*n2, 3*n2+1, 3*n2+2]
            for i in range(6):
                for j in range(6):
                    K_global[idx[i], idx[j]] += k_global_elem[i, j]

        # Forces nodales
        for node_idx, fx, fy, m in self.point_loads:
            F_global[3*node_idx:3*node_idx+3] += [fx, fy, m]

        # Application des conditions aux limites (Appuis)
        free_dofs = np.ones(3*n_nodes, dtype=bool)
        for node_idx, (tx, ty, rot) in self.supports.items():
            if tx: free_dofs[3*node_idx] = False
            if ty: free_dofs[3*node_idx+1] = False
            if rot: free_dofs[3*node_idx+2] = False
        
        U = np.zeros(3*n_nodes)
        K_sub = K_global[np.ix_(free_dofs, free_dofs)]
        F_sub = F_global[free_dofs]
        
        if np.linalg.det(K_sub) != 0:
            U[free_dofs] = np.linalg.solve(K_sub, F_sub)
            reactions = K_global @ U - F_global
            self.results = {"U": U, "R": reactions}
            return self.results
        return None

def main():
    st.set_page_config(page_title="Calcul Portique BUT GC", layout="wide")
    st.title("🏗️ Analyse Structurelle : Portiques & Poutres")

    if 'struct' not in st.session_state:
        st.session_state.struct = Structure2D()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("🛠️ Modélisation")
        # --- Saisie Simplifiée (Noeuds/Barres/Appuis) ---
        with st.expander("Ajouter Noeud"):
            nx, ny = st.number_input("X"), st.number_input("Y")
            if st.button("Valider Noeud"): st.session_state.struct.add_node(nx, ny)

        if len(st.session_state.struct.nodes) >= 2:
            with st.expander("Ajouter Barre"):
                n1 = st.number_input("De N", 0, len(st.session_state.struct.nodes)-1)
                n2 = st.number_input("À N", 0, len(st.session_state.struct.nodes)-1)
                if st.button("Lier"): st.session_state.struct.add_element(int(n1), int(n2))

        with st.expander("Appuis & Charges"):
            target = st.selectbox("Cible", range(len(st.session_state.struct.nodes)))
            type_a = st.selectbox("Appui", ["Libre", "Rotule", "Encastrement"])
            f_val = st.number_input("Charge Fy (kN)", value=-10.0)
            if st.button("Appliquer"):
                if type_a == "Rotule": st.session_state.struct.add_support(target, 1, 1, 0)
                elif type_a == "Encastrement": st.session_state.struct.add_support(target, 1, 1, 1)
                st.session_state.struct.add_load(target, 0, f_val, 0)

        if st.button("🚀 LANCER LE CALCUL", type="primary"):
            res = st.session_state.struct.solve()
            if res: st.success("Calcul terminé !")
            else: st.error("Structure instable ou manque d'appuis.")

    with col2:
        st.subheader("📊 Résultats & Graphiques")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
        struct = st.session_state.struct
        # Graphique 1 : Géométrie et Réactions
        for elem in struct.elements:
            p1, p2 = struct.nodes[elem['nodes'][0]], struct.nodes[elem['nodes'][1]]
            ax1.plot([p1[0], p2[0]], [p1[1], p2[1]], 'k-', lw=2)

        if struct.results:
            # Affichage des Réactions
            for n_idx, (tx, ty, rot) in struct.supports.items():
                rx = struct.results['R'][3*n_idx]
                ry = struct.results['R'][3*n_idx+1]
                ax1.text(struct.nodes[n_idx][0], struct.nodes[n_idx][1]-0.5, 
                         f"Rx:{rx:.1f}\nRy:{ry:.1f}", color='red', fontsize=9)
            
            # Graphique 2 : Allure de la Déformée (exagérée)
            for elem in struct.elements:
                n1, n2 = elem['nodes']
                p1, p2 = struct.nodes[n1], struct.nodes[n2]
                u1 = struct.results['U'][3*n1:3*n1+2]
                u2 = struct.results['U'][3*n2:3*n2+2]
                ax2.plot([p1[0]+u1[0]*10, p2[0]+u2[0]*10], [p1[1]+u1[1]*10, p2[1]+u2[1]*10], 'b--', label="Déformée")

        ax1.set_title("Géométrie et Réactions d'Appuis")
        ax2.set_title("Visualisation de la Déformée (Facteur x10)")
        st.pyplot(fig)

        if struct.results:
            st.info(f"**Contrainte Maximale estimée :** {np.max(np.abs(struct.results['U']))*210000:.2f} MPa (Simulation)")

if __name__ == "__main__":
    main()
