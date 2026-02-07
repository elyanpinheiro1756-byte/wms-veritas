import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.express as px
import qrcode
from io import BytesIO
from PIL import Image
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="VERITAS FORTUNAS - WMS", layout="wide", page_icon="📦")

# --- 2. ESTILIZAÇÃO CSS (MODO ESCURO DE ALTO CONTRASTE) ---
st.markdown("""
    <style>
    /* FUNDO GERAL - Azul Escuro Profissional */
    [data-testid="stAppViewContainer"] {
        background-color: #0f172a;
        background-image: linear-gradient(rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.95)), 
                          url("https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?ixlib=rb-4.0.3");
        background-size: cover;
        background-attachment: fixed;
    }

    /* TÍTULOS E TEXTOS */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
        text-shadow: 0px 2px 4px rgba(0,0,0,0.5);
    }
    p, label, span, div {
        color: #e2e8f0;
    }

    /* SIDEBAR (MENU LATERAL) */
    [data-testid="stSidebar"] {
        background-color: #020617;
        border-right: 1px solid #1e293b;
    }
    
    /* CARDS E CONTAINERS (Fundo Branco para Leitura de Dados) */
    .stMetric, [data-testid="stForm"], .stDataFrame, .stExpander {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* Texto dentro dos cards deve ser ESCURO para contraste */
    .stMetric label, .stMetric div, [data-testid="stForm"] p, [data-testid="stForm"] label, .stDataFrame div {
        color: #0f172a !important; 
    }
    
    /* BOTÕES */
    .stButton>button {
        background-color: #3b82f6;
        color: white !important;
        border: none;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #2563eb;
        transform: scale(1.02);
    }

    /* RODAPÉ FIXO */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #020617;
        color: #94a3b8 !important;
        text-align: center;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #1e293b;
        z-index: 99999;
    }
    footer {visibility: hidden;} /* Esconde rodapé padrão */
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXÃO SUPABASE ---
URL = "https://vvfmozwkmndsxirdaupx.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ2Zm1vendrbW5kc3hpcmRhdXB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NzI2NzYsImV4cCI6MjA4NTA0ODY3Nn0.DV7PMg2aEpy1J7_3GuAlh3G3tq12F5s2txZbTNpB_AY"

@st.cache_resource
def init_connection():
    return create_client(URL, KEY)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Erro crítico de conexão: {e}")
    st.stop()

# --- 4. FUNÇÕES DE AUTENTICAÇÃO ---
def login_usuario(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return res
    except Exception as e:
        return None

def logout_usuario():
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# --- 5. FUNÇÕES DE NEGÓCIO (WMS CORE) ---

def fetch_produtos():
    res = supabase.table("tb_produtos").select("*").execute()
    return res.data

def insert_produto(dados):
    try:
        supabase.table("tb_produtos").insert(dados).execute()
        return True
    except:
        return False

def fetch_locais():
    res = supabase.table("tb_locais").select("*").execute()
    return res.data

def fetch_estoque_disponivel(id_produto):
    res = supabase.table("tb_estoque")\
        .select("id, id_local, quantidade, tb_locais(rua, predio, nivel, apart)")\
        .eq("id_produto", id_produto)\
        .gt("quantidade", 0).execute()
    return res.data

def registrar_entrada(id_produto, id_local, qtd, lote, usuario_email):
    """Processo de Recebimento"""
    try:
        estoque_atual = supabase.table("tb_estoque")\
            .select("*")\
            .eq("id_produto", id_produto)\
            .eq("id_local", id_local).execute()

        if estoque_atual.data:
            nova_qtd = estoque_atual.data[0]['quantidade'] + qtd
            supabase.table("tb_estoque").update({"quantidade": nova_qtd})\
                .eq("id", estoque_atual.data[0]['id']).execute()
        else:
            supabase.table("tb_estoque").insert({
                "id_produto": id_produto,
                "id_local": id_local,
                "quantidade": qtd,
                "lote": lote
            }).execute()

        # Log de Movimentação
        log = {
            "tipo": "entrada", "id_produto": id_produto, "qtd": qtd, 
            "destino": id_local, "usuario": usuario_email
        }
        supabase.table("tb_movimentacoes").insert(log).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def registrar_saida(id_estoque, id_produto, id_local, qtd, cliente, usuario_email):
    """Processo de Expedição"""
    try:
        estoque = supabase.table("tb_estoque").select("quantidade").eq("id", id_estoque).single().execute()
        qtd_atual = estoque.data['quantidade']

        if qtd_atual < qtd:
            st.error("Quantidade insuficiente!")
            return False

        nova_qtd = qtd_atual - qtd
        if nova_qtd == 0:
            supabase.table("tb_estoque").delete().eq("id", id_estoque).execute()
        else:
            supabase.table("tb_estoque").update({"quantidade": nova_qtd}).eq("id", id_estoque).execute()

        log = {
            "tipo": "saida", "id_produto": id_produto, "qtd": qtd, 
            "origem": id_local, "usuario": f"{usuario_email} -> {cliente}"
        }
        supabase.table("tb_movimentacoes").insert(log).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def registrar_ajuste(id_estoque, id_produto, id_local, qtd_contada, qtd_sistema, usuario_email):
    """Inventário"""
    try:
        diferenca = qtd_contada - qtd_sistema
        if diferenca == 0: return True, "Saldo correto."
        
        supabase.table("tb_estoque").update({"quantidade": qtd_contada}).eq("id", id_estoque).execute()
        
        log = {
            "tipo": "entrada" if diferenca > 0 else "saida",
            "id_produto": id_produto, "qtd": abs(diferenca),
            "origem": id_local if diferenca < 0 else None,
            "destino": id_local if diferenca > 0 else None,
            "usuario": f"Ajuste INV: {usuario_email}"
        }
        supabase.table("tb_movimentacoes").insert(log).execute()
        return True, "Ajuste realizado."
    except Exception as e:
        return False, str(e)

# --- 6. FLUXO PRINCIPAL (MAIN) ---
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    # TELA DE LOGIN
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🔐 VERITAS FORTUNAS WMS</h1>", unsafe_allow_html=True)
        st.info("Acesso Restrito - Pinheiro Consulting")
        
        with st.form("login_form"):
            email = st.text_input("Email Corporativo")
            password = st.text_input("Senha", type="password")
            
            if st.form_submit_button("Acessar Sistema"):
                auth_res = login_usuario(email, password)
                if auth_res:
                    st.session_state.user = auth_res.user
                    st.success("Login realizado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")

else:
    # TELA DO SISTEMA (LOGADO)
    st.sidebar.title("MENU WMS")
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegação", [
        "Dashboard (KPIs)", "Visualizar Estoque", "Cadastrar Produto", 
        "Gestão de Locais", "Recebimento (Inbound)", "Expedição (Outbound)", "Inventário Cíclico"
    ])
    
    if st.sidebar.button("Sair"):
        logout_usuario()

    # --- LÓGICA DAS ABAS ---
    if menu == "Dashboard (KPIs)":
        st.title("📊 Painel de Controle Logístico")
        col1, col2 = st.columns(2)
        
        # KPI 1 - Movimentação
        res_mov = supabase.table("tb_movimentacoes").select("tipo, created_at").execute()
        df_mov = pd.DataFrame(res_mov.data)
        if not df_mov.empty:
            df_mov['data'] = pd.to_datetime(df_mov['created_at']).dt.date
            fig = px.histogram(df_mov, x="data", color="tipo", barmode="group", 
                               title="Fluxo de Movimentação", color_discrete_map={"entrada": "#22c55e", "saida": "#ef4444"})
            col1.plotly_chart(fig, use_container_width=True)
        
        # KPI 2 - Estoque
        res_est = supabase.table("tb_estoque").select("quantidade, tb_produtos(descricao)").execute()
        data_est = [{"Produto": i['tb_produtos']['descricao'], "Qtd": i['quantidade']} for i in res_est.data if i['tb_produtos']]
        if data_est:
            fig2 = px.pie(pd.DataFrame(data_est), values="Qtd", names="Produto", title="Ocupação de Estoque", hole=0.4)
            col2.plotly_chart(fig2, use_container_width=True)

    elif menu == "Visualizar Estoque":
        st.title("📋 Consulta de Estoque (Master Data)")
        data = fetch_produtos()
        if data:
            gb = GridOptionsBuilder.from_dataframe(pd.DataFrame(data))
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_selection('single')
            AgGrid(pd.DataFrame(data), gridOptions=gb.build(), height=500)
        else:
            st.info("Base de dados vazia.")

    elif menu == "Cadastrar Produto":
        st.title("🆕 Cadastro de Produtos")
        with st.form("form_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            sku = c1.text_input("SKU*")
            desc = c1.text_input("Descrição*")
            cat = c1.selectbox("Categoria", ["Geral", "Alto Valor", "Perigoso"])
            peso = c2.number_input("Peso (kg)", min_value=0.0)
            
            if st.form_submit_button("Salvar"):
                if sku and desc:
                    if insert_produto({"sku": sku, "descricao": desc, "categoria": cat, "peso_kg": peso}):
                        st.success("Produto cadastrado!")
                        time.sleep(1)
                        st.rerun()

    elif menu == "Gestão de Locais":
        st.title("📍 Mapeamento de Armazém")
        with st.form("form_local", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            rua = c1.text_input("Rua")
            predio = c2.text_input("Prédio")
            nivel = c3.text_input("Nível")
            tipo = c4.selectbox("Tipo", ["Picking", "Pulmão"])
            if st.form_submit_button("Criar Local"):
                try:
                    supabase.table("tb_locais").insert({"rua": rua, "predio": predio, "nivel": nivel, "tipo": tipo, "apart": "01"}).execute()
                    st.success("Local criado!")
                except: st.error("Erro ao criar.")

    elif menu == "Recebimento (Inbound)":
        st.title("📥 Entrada de Notas (Simulação SEFAZ)")
        prods = fetch_produtos()
        locs = fetch_locais()
        if prods and locs:
            d_prod = {f"{p['sku']} - {p['descricao']}": p['id'] for p in prods}
            d_loc = {f"{l['rua']}-{l['predio']}-{l['nivel']}": l['id'] for l in locs}
            
            with st.form("inbound"):
                p_sel = st.selectbox("Produto", list(d_prod.keys()))
                l_sel = st.selectbox("Local Destino", list(d_loc.keys()))
                qtd = st.number_input("Quantidade", min_value=1)
                nfe = st.text_input("Chave NFe (44 dígitos)")
                
                if st.form_submit_button("Processar Entrada"):
                    if registrar_entrada(d_prod[p_sel], d_loc[l_sel], qtd, nfe, st.session_state.user.email):
                        st.success("Entrada confirmada e Log gravado!")
                        time.sleep(1)
                        st.rerun()

    elif menu == "Expedição (Outbound)":
        st.title("🚚 Expedição e Separação")
        prods = fetch_produtos()
        if prods:
            d_prod = {f"{p['sku']} - {p['descricao']}": p['id'] for p in prods}
            sel = st.selectbox("Produto", list(d_prod.keys()))
            saldos = fetch_estoque_disponivel(d_prod[sel])
            
            if saldos:
                opts = {f"Local: {s['tb_locais']['rua']}-{s['tb_locais']['predio']} (Qtd: {s['quantidade']})": s for s in saldos}
                origem = st.selectbox("Retirar de:", list(opts.keys()))
                item = opts[origem]
                
                with st.form("outbound"):
                    q_saida = st.number_input("Qtd", 1, item['quantidade'])
                    cli = st.text_input("Cliente Destino")
                    if st.form_submit_button("Confirmar Picking"):
                        if registrar_saida(item['id'], d_prod[sel], item['id_local'], q_saida, cli, st.session_state.user.email):
                            st.success("Expedição realizada!")
                            time.sleep(1)
                            st.rerun()
            else: st.warning("Sem saldo disponível.")

    elif menu == "Inventário Cíclico":
        st.title("🔍 Auditoria")
        inv = supabase.table("tb_estoque").select("*, tb_produtos(descricao), tb_locais(rua, predio)").execute()
        for row in inv.data:
            desc = row['tb_produtos']['descricao'] if row['tb_produtos'] else "?"
            loc = f"{row['tb_locais']['rua']}-{row['tb_locais']['predio']}" if row['tb_locais'] else "?"
            with st.expander(f"{desc} em {loc}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Sistema", row['quantidade'])
                real = c2.number_input("Físico", 0, value=row['quantidade'], key=row['id'])
                if c3.button("Ajustar", key=f"btn_{row['id']}"):
                    ok, msg = registrar_ajuste(row['id'], row['id_produto'], row['id_local'], real, row['quantidade'], st.session_state.user.email)
                    if ok: st.success(msg); time.sleep(1); st.rerun()

    # --- RODAPÉ ---
    st.markdown("""
        <div class="footer">
            <p>VERITAS FORTUNAS WMS | Sistema Logístico Integrado | Pinheiro Consulting &copy; 2024</p>
        </div>
    """, unsafe_allow_html=True)