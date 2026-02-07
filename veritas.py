# --- MÓDULO DE GESTÃO DE DOCAS (WMS ELITE) ---

st.header("🚛 Gestão de Docas e Pátio")

def modulo_docas():
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.subheader("Agendar Camião")
        with st.form("form_docas"):
            transportadora = st.text_input("Transportadora")
            placa = st.text_input("Placa do Veículo")
            doca_destino = st.selectbox("Atribuir Doca", ["Doca 01 - Recebimento", "Doca 02 - Expedição", "Doca 03 - Crossdocking"])
            prioridade = st.select_slider("Prioridade", options=["Baixa", "Média", "Urgente"])
            
            if st.form_submit_button("Confirmar Agendamento"):
                # Aqui registamos no Supabase ou Auditoria
                registrar_log("Portaria", f"Camião {placa} atribuído à {doca_destino}")
                st.success(f"Veículo {placa} autorizado para a {doca_destino}")

    with col_d2:
        st.subheader("Painel de Ocupação")
        # Simulação de painel visual
        st.info("📦 **Doca 01:** Ocupada (Carregando)")
        st.success("✅ **Doca 02:** Livre")
        st.warning("⏳ **Doca 03:** Aguardando Manobra")

modulo_docas()