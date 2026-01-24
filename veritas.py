import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import random
import segno
import io
import base64
import subprocess
import sys

# --- AUTO-INSTALAÇÃO DE EMERGÊNCIA ---
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from fpdf import FPDF
except ImportError:
    try:
        install('fpdf')
        from fpdf import FPDF
    except:
        st.warning("Atenção: O módulo de PDF não pôde ser instalado automaticamente. O sistema funcionará, mas a exportação de PDF ficará desativada.")

# --- BANCO DE DADOS (ESTRUTURA TOTVS) ---
conn = sqlite3.connect('veritas_master.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS operacoes 
             (sku TEXT, data TEXT, tipo TEXT, nf TEXT, cte TEXT, 
              cliente TEXT, item TEXT, unidade TEXT, qtd INTEGER, 
              locacao TEXT, destino TEXT, avaria TEXT, obs TEXT)''')
conn.commit()

# --- ENGINE VISUAL GEMINI IA ---
def aplicar_visual_pro(contexto):
    img_login = "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=2070"
    img_op = "https://images.unsplash.com/photo-1553413077-190dd305871c?q=80&w=2070"
    url = img_login if contexto == "login" else img_op

    st.markdown(f"""
        <style>
        .stApp {{
            background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url("{url}");
            background-size: cover; background-attachment: fixed;
        }}
        .gemini-title {{
            background: linear-gradient(180deg, #FFD700 0%, #B8860B 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 85px; font-weight: 900; text-align: center;
            font-family: 'Inter', sans-serif; letter-spacing: -3px; margin: 0;
            filter: drop-shadow(0px 10px 20px rgba(255, 215, 0, 0.4));
        }}
        .louros {{ text-align: center; font-size: 55px; color: #FFD700; margin-top: -35px; margin-bottom: 25px; }}
        .tag-print {{
            background: white; color: black; padding: 25px; border: 8px solid #FFD700;
            border-radius: 15px; width: 400px; margin: auto; text-align: center;
            font-family: 'Courier New', monospace;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'print_tag' not in st.session_state: st.session_state.print_tag = None

if not st.session_state.logado:
    aplicar_visual_pro("login")
    st.markdown('<br><h1 class="gemini-title">VERITAS FORTUNAS</h1>', unsafe_allow_html=True)
    st.markdown('<div class="louros">🌿 🌿</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div style="background:rgba(0,0,0,0.9); padding:40px; border-radius:25px; border:1px solid #FFD700;">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["🔐 ACESSO", "📝 NOVO OPERADOR", "❓ ESQUECI PIN"])
        with t1:
            u = st.text_input("Usuário").upper()
            s = st.text_input("PIN (6 dígitos)", type="password")
            if st.button("🚩 INICIAR"):
                if len(s) == 6: st.session_state.logado = True; st.rerun()
                else: st.error("O PIN deve conter exatamente 6 dígitos.")
        with t2:
            st.info("Cadastros exigem validação da diretoria.")
        st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.print_tag:
    aplicar_visual_pro("operacional")
    t = st.session_state.print_tag
    st.markdown('<br><br>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="tag-print">
            <h1 style="border-bottom: 2px solid black; margin-bottom:10px;">VERITAS FORTUNAS</h1>
            <p style="font-size: 24px;"><b>ITEM:</b> {t['item']}</p>
            <p><b>LOC:</b> {t['loc']} | <b>QTD:</b> {t['qtd']} {t['unid']}</p>
            <div style="margin:20px 0;">
                <img src="data:image/png;base64,{t['qr']}" width="200">
            </div>
            <h2>SKU: {t['sku']}</h2>
            <p style="font-size:12px;">Data: {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("⬅ VOLTAR"): st.session_state.print_tag = None; st.rerun()

else:
    aplicar_visual_pro("operacional")
    with st.sidebar:
        st.markdown('<h1 style="color:#FFD700; text-align:center;">🌿 VF 🌿</h1>', unsafe_allow_html=True)
        aba = st.radio("MÓDULOS", ["📊 Dashboard BI", "📥 Recebimento", "📤 Expedição", "📋 Inventário & Auditoria"])
        if st.button("ENCERRAR"): st.session_state.logado = False; st.rerun()

    st.markdown('<h1 class="gemini-title" style="font-size:45px;">VERITAS FORTUNAS</h1>', unsafe_allow_html=True)
    df = pd.read_sql("SELECT * FROM operacoes", conn)

    if aba == "📊 Dashboard BI":
        st.header("📊 Inteligência de Dados")
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            sub1, sub2 = st.tabs(["📈 Balanço Mensal", "📉 Saldo de Estoque"])
            with sub1:
                df['Mes'] = df['data'].dt.strftime('%m/%Y')
                fig = px.bar(df.groupby(['Mes', 'tipo'])['qtd'].sum().reset_index(), x='Mes', y='qtd', color='tipo', 
                             barmode='group', color_discrete_map={'ENTRADA': '#FFD700', 'EXPEDIÇÃO': '#8B0000'}, template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)
            with sub2:
                res = df.groupby(['item', 'locacao']).agg({'qtd': 'sum'}).reset_index().query("qtd > 0")
                st.dataframe(res, use_container_width=True)

    elif aba == "📥 Recebimento":
        st.header("📥 Inbound - Recebimento")
        with st.form("f_rec", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nf, cte, cli = c1.text_input("NF").upper(), c2.text_input("CT-e").upper(), c3.text_input("Cliente").upper()
            item = st.text_input("Item").upper()
            d1, d2, d3 = st.columns(3)
            unid, qtd, loc = d1.selectbox("Unid", ["UN", "KG"]), d2.number_input("Qtd", 1), d3.text_input("Loc").upper()
            st.divider()
            avaria = st.radio("Possui Avaria?", ["NÃO", "SIM"])
            obs = st.text_area("Observações").upper()
            
            if st.form_submit_button("📜 CONFIRMAR"):
                sku = f"VF{random.randint(1000, 9999)}"
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO operacoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                          (sku, dt, 'ENTRADA', nf, cte, cli, item, unid, qtd, loc, 'CD MASTER', avaria, obs))
                conn.commit()
                qr = segno.make(f"SKU:{sku}")
                buf = io.BytesIO(); qr.save(buf, kind='png', scale=5)
                st.session_state.print_tag = {'item': item, 'loc': loc, 'qtd': qtd, 'unid': unid, 'qr': base64.b64encode(buf.getvalue()).decode(), 'sku': sku}
                st.rerun()

    elif aba == "📤 Expedição":
        st.header("📤 Outbound - Expedição")
        saldo = df.groupby(['item', 'locacao'])['qtd'].sum().reset_index().query("qtd > 0")
        if not saldo.empty:
            it = st.selectbox("Escolha o Item", saldo['item'].unique())
            lc = st.selectbox("Locação", saldo[saldo['item']==it]['locacao'].unique())
            mq = int(saldo[(saldo['item']==it) & (saldo['locacao']==lc)]['qtd'].values[0])
            c1, c2 = st.columns(2)
            qo = c1.number_input(f"Qtd (Máx {mq})", 1, mq)
            ds = c2.text_input("Destino Final").upper()
            if st.button("🔥 EXPEDIR"):
                dt_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO operacoes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                         ("OUT", dt_s, 'EXPEDIÇÃO', 'SAIDA', 'SAIDA', 'CD MASTER', it, 'UN', -qo, lc, ds, 'NÃO', 'OK'))
                conn.commit(); st.rerun()

    elif aba == "📋 Inventário & Auditoria":
        st.header("📋 Estoque Real")
        inv = df.groupby(['item', 'locacao', 'cliente', 'avaria'])['qtd'].sum().reset_index().query("qtd > 0")
        st.dataframe(inv, use_container_width=True)
        st.divider()
        st.subheader("🔎 Auditoria")
        st.dataframe(df.sort_values('data', ascending=False), use_container_width=True)