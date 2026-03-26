import streamlit as st
import pandas as pd
import json
import time
import os
import plotly.express as px  # <--- CERTIFIQUE-SE QUE ESTA LINHA ESTÁ AQUI
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
from relatorios import gerar_pdf_filtrado

# --- 1. FUNÇÃO POP-UP (MODAL) DE EDIÇÃO TOTAL ---
# Esta função usa o st.dialog para criar a janela flutuante de edição
@st.dialog("📝 Editar Cadastro Completo")
def editar_participante_dialog(dados, db):
    st.markdown(f"Alterando registro de: **{dados['nome']}**")
    
    with st.form("form_edicao_total"):
        col1, col2 = st.columns(2)
        
        with col1:
            novo_nome = st.text_input("Nome Completo", value=dados.get('nome', ''))
            novo_cpf = st.text_input("CPF", value=dados.get('cpf', ''))
            novo_depto = st.selectbox("Departamento", ["JGE", "AGE", "OUTRO"], 
                                     index=["JGE", "AGE", "OUTRO"].index(dados.get('departamento', 'JGE')))
            novo_valor = st.number_input("Valor Total (R$)", value=float(dados.get('valor_total', 0)))
        
        with col2:
            nova_unidade = st.text_input("Regional / Unidade", value=dados.get('unidade', ''))
            novo_transporte = st.selectbox("Transporte", ["Ônibus", "Carro"], 
                                          index=0 if dados.get('transporte') == "Ônibus" else 1)
            novo_alojamento = st.selectbox("Alojamento", ["Sim", "Não"], 
                                          index=0 if dados.get('alojamento') == "Sim" else 1)
            novo_pago = st.selectbox("Status", ["Pago", "Pendente"], 
                                    index=0 if dados.get('pago') == "Pago" else 1)
            
        st.divider()
        if st.form_submit_button("💾 SALVAR ALTERAÇÕES", use_container_width=True):
            try:
                # Atualização direta no Firebase usando o ID único
                db.collection("participantes").document(dados['id_firebase']).update({
                    "nome": novo_nome.upper(),
                    "cpf": novo_cpf,
                    "departamento": novo_depto,
                    "valor_total": novo_valor,
                    "unidade": nova_unidade,
                    "transporte": novo_transporte,
                    "alojamento": novo_alojamento,
                    "pago": novo_pago
                })
                st.cache_data.clear() # 👈 ADICIONADO: Limpa a memória para ler o novo dado
                st.success("✅ Dados atualizados com sucesso!")
                time.sleep(1)
                st.rerun() # Recarrega a página para atualizar a tabela
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")
# --- CONEXÃO COM FIREBASE (VERSÃO CORRIGIDA) ---
@st.cache_resource
def get_db():
    # 1. Tenta carregar do arquivo local primeiro (Para não dar erro de Secrets no Windows)
    if os.path.exists('chave.json'):
        with open('chave.json') as f:
            key_dict = json.load(f)
        creds = service_account.Credentials.from_service_account_info(key_dict)
    # 2. Se não houver arquivo, tenta os segredos da Web (Streamlit Cloud)
    else:
        try:
            key_dict = json.loads(st.secrets["textkey"])
            creds = service_account.Credentials.from_service_account_info(key_dict)
        except Exception as e:
            st.error("Erro: Arquivo 'chave.json' não encontrado e segredos da web ausentes.")
            st.stop()
    
    return firestore.Client(credentials=creds)

db = get_db()

# --- FUNÇÕES DE CRUD FIREBASE ---


@st.cache_data(ttl=600) # 👈 Cache para economizar cota
def buscar_participantes():
    try:
        docs = db.collection("participantes").stream()
        lista = []
        for doc in docs:
            d = doc.to_dict()
            d['id_firebase'] = doc.id  # Garante que o ID do documento esteja nos dados
            lista.append(d)
        
        df = pd.DataFrame(lista)
        
        # Correção para colunas ausentes em registros antigos
        if not df.empty:
            if 'departamento' not in df.columns: df['departamento'] = "JGE"
            if 'is_crianca' not in df.columns: df['is_crianca'] = False
            
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

def salvar_participante(dados):
    try:
        # Se tiver CPF, usamos o CPF como ID. Se não, geramos um ID baseado no nome e hora.
        # Isso evita duplicados e permite cadastrar quem não tem CPF.
        if dados['cpf'] and dados['cpf'] != "NÃO INFORMADO" and len(dados['cpf']) > 5:
            id_doc = dados['cpf']
        else:
            id_doc = f"{dados['nome'].replace(' ', '_')}_{int(time.time())}"
        
        db.collection("participantes").document(id_doc).set(dados)
        st.cache_data.clear() # 👈 Limpa o cache para a nova pessoa aparecer na lista
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SCCUADP 2026", layout="wide", page_icon="🎫")

# --- CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #001F3F !important; border-right: 2px solid #87CEEB; }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #FFFFFF !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div > div { border-radius: 10px !important; border: 1px solid #87CEEB !important; }
    [data-testid="stMetric"] { background-color: #f0f8ff; padding: 15px; border-radius: 15px; border-left: 5px solid #87CEEB; }
    div.stButton > button:first-child { background-color: #87CEEB !important; color: #001F3F !important; font-weight: bold; border-radius: 20px; width: 100%; }
    .sidebar-title { color: #87CEEB !important; text-align: center; font-weight: bold; font-size: 26px; margin-bottom: 0px; }
    .sidebar-sub { color: #FFFFFF !important; text-align: center; font-size: 14px; margin-bottom: 20px; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<p class="sidebar-title">⛪ AD PARAÍSO</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-sub">SCCUADP 2026</p>', unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=80)
    st.markdown("---")
    choice = st.radio("NAVEGAÇÃO PRINCIPAL", ["📊 Dashboard", "📝 Novo Cadastro", "📋 Gestão de Registros"])
    st.markdown("---")
    st.caption("📍 Paraíso do Tocantins - TO")

# --- MÓDULO DASHBOARD (VERSÃO CORRIGIDA) ---
if choice == "📊 Dashboard":
    st.title("📊 Painel de Indicadores")
    df = buscar_participantes()

    if not df.empty:
        # CORREÇÃO AQUI: Usamos 'valor_total' em vez de 'qtd_cupons'
        # O .fillna(0) evita erros se algum registro antigo estiver vazio
        valor_pago = df[df['pago'] == 'Pago']['valor_total'].fillna(0).sum()
        valor_pendente = df[df['pago'] == 'Pendente']['valor_total'].fillna(0).sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Financeiro Pago", f"R$ {valor_pago:.2f}", f"Pendente: R$ {valor_pendente:.2f}", delta_color="inverse")
        m2.metric("Passageiros Ônibus", len(df[df['transporte'] == 'Ônibus']))
        m3.metric("Alojamento", len(df[df['alojamento'] == 'Sim']))
        m4.metric("Total Inscritos", len(df))
        

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📦 Distribuição de Blocos/Inscrições")
            # Ajustado para a coluna 'bloco' que é a nova padrão
            df_counts = df['bloco'].value_counts().reset_index()
            df_counts.columns = ['Tipo', 'Qtd']
            fig = px.bar(df_counts, x='Tipo', y='Qtd', color='Tipo', color_discrete_sequence=px.colors.sequential.Blues_r)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
           st.subheader("🌍 Regional/Unidade")
            # Garante que o gráfico não dê erro se houver unidade vazia
           df_pizza = df.copy()
           df_pizza['unidade'] = df_pizza['unidade'].fillna("Não Informado")
           fig_un = px.pie(df_pizza, names='unidade', hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
           st.plotly_chart(fig_un, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado no Firebase.")

# --- MÓDULO CADASTRO (VERSÃO ATUALIZADA 2026) ---
elif choice == "📝 Novo Cadastro":
    st.title("📝 Novo Cadastro - UMADETINS 2026")
    
    with st.form("cadastro_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome Completo").upper()
            cpf = st.text_input("CPF (Somente números)")
            unidade = st.selectbox("Regional", ["Matriz", "Regional 1", "Regional 2", "Regional 3", "Regional 4", "Regional 5", "Regional 6"])
            depto = st.selectbox("Departamento", ["JGE", "AGE", "OUTRO"])
            is_crianca = st.checkbox("É criança? (Isento de inscrição)")
            
        with col2:
            transp = st.radio("Logística de Transporte", ["Ônibus", "Carro"], horizontal=True)
            aloj = st.radio("Necessita Alojamento?", ["Não", "Sim"], horizontal=True)
            bloco = st.selectbox("Retirou Bloco?", ["Não", "Sim (100 cupons)", "Sim (150 cupons)"])
            pago = st.selectbox("Status de Pagamento", ["Pendente", "Pago"])
         

        # --- LÓGICA DE CÁLCULO DE VALORES ---
        valor_total = 0
        
    
        if is_crianca:
            # Crianças: R$ 137 se ônibus, R$ 0 se carro
            valor_total = 137 if transp == "Ônibus" else 0
            info_msg = f"👶 Criança: Passagem R$ {valor_total},00"
        else:
            # REGRA DE OURO: Se for Ônibus (com ou sem bloco), é R$ 300
            if transp == "Ônibus":
                valor_total = 300
            # Se for de Carro, depende do bloco
            elif "100" in bloco:
                valor_total = 200
            elif "150" in bloco:
                valor_total = 300
            else:
                valor_total = 163  # Inscrição avulsa (Carro e sem bloco)
            
            info_msg = f"👤 Adulto: Total R$ {valor_total},00"

        st.info(f"💰 {info_msg} | 🚗 Transporte: {transp}")

        if st.form_submit_button("🚀 Finalizar Inscrição"):
            # Validamos apenas o Nome, já que o CPF é opcional para alguns
            if nome:
                # Se o CPF estiver vazio, marcamos como não informado
                cpf_final = cpf if cpf else "NÃO INFORMADO"
                
                dados = {
                    "nome": nome, 
                    "cpf": cpf_final, 
                    "unidade": unidade, 
                    "departamento": depto, 
                    "is_crianca": is_crianca,
                    "transporte": transp, 
                    "alojamento": aloj, 
                    "bloco": bloco, 
                    "valor_total": valor_total,
                    "pago": pago, 
                    "data_registro": datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                
                if salvar_participante(dados):
                    st.success(f"✅ {nome} cadastrado com sucesso!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("⚠️ Por favor, preencha pelo menos o Nome Completo.")
                
elif choice == "📋 Gestão de Registros":
    st.title("📋 Gestão Estratégica SCCUADP")
    
    if st.sidebar.button("🔄 Sincronizar Banco"):
        st.cache_data.clear()
        st.rerun()
    
    df = buscar_participantes()
    
    if not df.empty:
        # --- ÁREA DE FILTROS EXPANSÍVEL (6 FILTROS) ---
        with st.expander("🔍 Filtros Avançados", expanded=True):
            # Primeira linha de filtros
            c1, c2, c3 = st.columns(3)
            opcoes_unidade = sorted(df['unidade'].dropna().unique())
            f_unidade = c1.multiselect("Filtrar Regional:", options=opcoes_unidade)
            f_depto = c2.multiselect("Filtrar Departamento:", options=["JGE", "AGE", "OUTRO"])
            f_transporte = c3.multiselect("Filtrar Transporte:", options=df['transporte'].unique())
            
            # Segunda linha de filtros (Aumentada para 3 colunas)
            c4, c5, c6 = st.columns(3)
            f_alojamento = c4.multiselect("Filtrar Alojamento:", options=["Sim", "Não"], help="Sim = Alojamento / Não = Hotel ou Próprio")
            f_crianca = c5.multiselect("Filtrar Criança:", options=["Sim", "Não"], help="Filtra por is_crianca")
            
            # NOVO FILTRO: Cupons / Blocos
            opcoes_bloco = sorted(df['bloco'].dropna().unique())
            f_bloco = c6.multiselect("Filtrar Cupons/Blocos:", options=opcoes_bloco)

        # --- LÓGICA DE FILTRO (Vazio = Tudo) ---
        df_f = df.copy()
        
        if f_unidade:
            df_f = df_f[df_f['unidade'].isin(f_unidade)]
        if f_depto:
            df_f = df_f[df_f['departamento'].isin(f_depto)]
        if f_transporte:
            df_f = df_f[df_f['transporte'].isin(f_transporte)]
        if f_alojamento:
            df_f = df_f[df_f['alojamento'].isin(f_alojamento)]
        if f_crianca:
            val_crianca = [True if v == "Sim" else False for v in f_crianca]
            df_f = df_f[df_f['is_crianca'].isin(val_crianca)]
        
        # APLICAÇÃO DO NOVO FILTRO
        if f_bloco:
            df_f = df_f[df_f['bloco'].isin(f_bloco)]

        # --- EXIBIÇÃO E RELATÓRIO ---
        col_resumo, col_pdf = st.columns([3, 1])
        with col_resumo:
            st.info(f"📊 **{len(df_f)}** registros encontrados com os filtros atuais.")
        
        with col_pdf:
            pdf_bytes = gerar_pdf_filtrado(df_f)
            st.download_button(
                label="📄 Gerar PDF",
                data=pdf_bytes,
                file_name=f"Relatorio_Filtrado_{datetime.now().strftime('%d_%m')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        # Tabela com dados filtrados e busca por nome
        busca = st.text_input("🔍 Busca rápida por nome:", "").upper()
        if busca:
            df_f = df_f[df_f['nome'].str.contains(busca, na=False)]
            
        st.dataframe(df_f, use_container_width=True, hide_index=True)

        st.divider()

        # --- SEÇÃO DE AÇÕES (EDIÇÃO E EXCLUSÃO) ---
        col_edit, col_del = st.columns(2)

        with col_edit:
            st.subheader("📝 Editar Registro")
            lista_nomes = sorted(df_f['nome'].tolist())
            pessoa_sel = st.selectbox(
                "Pesquisar para editar:", 
                options=[""] + lista_nomes,
                format_func=lambda x: "Selecione um nome..." if x == "" else x,
                key="select_edit"
            )
            
            if pessoa_sel:
                dados_pessoa = df_f[df_f['nome'] == pessoa_sel].iloc[0]
                if st.button(f"🛠️ Abrir Ficha de {pessoa_sel}", use_container_width=True):
                    editar_participante_dialog(dados_pessoa, db)

        with col_del:
            st.subheader("🗑️ Remover Registro")
            pessoa_del = st.selectbox(
                "Pesquisar para apagar:", 
                options=[""] + lista_nomes,
                format_func=lambda x: "Selecione para excluir..." if x == "" else x,
                key="select_del"
            )
            
            if pessoa_del:
                confirmar = st.checkbox(f"Confirmo a exclusão definitiva de {pessoa_del}")
                if st.button("❌ EXCLUIR REGISTRO", type="primary", use_container_width=True):
                    if confirmar:
                        id_firebase = df_f[df_f['nome'] == pessoa_del].iloc[0]['id_firebase']
                        db.collection("participantes").document(id_firebase).delete()
                        st.cache_data.clear()
                        st.error("Registro removido!")
                        time.sleep(1)
                        st.rerun()
    else:
        st.info("O banco de dados está vazio.")
