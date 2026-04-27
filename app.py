import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuração da página para dispositivos móveis
st.set_page_config(page_title="Solutel Mobile", layout="centered")

# Funções de Base de Dados


def init_db():
    conn = sqlite3.connect("solutel_mobile.db")
    cursor = conn.cursor()
    # Tabela de estoque atual
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque_tecnico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE,
            quantidade INTEGER
        )
    """)
    # Tabela de histórico de movimentações
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            quantidade INTEGER,
            tecnico TEXT,
            cliente_os TEXT,
            tipo TEXT,
            data TEXT
        )
    """)

    # Adicionar itens iniciais se a tabela de estoque estiver vazia
    cursor.execute("SELECT COUNT(*) FROM estoque_tecnico")
    if cursor.fetchone()[0] == 0:
        itens_iniciais = []
        cursor.executemany(
            "INSERT INTO estoque_tecnico (item, quantidade) VALUES (?, ?)", itens_iniciais)

    conn.commit()
    conn.close()


def get_data():
    conn = sqlite3.connect("solutel_mobile.db")
    df = pd.read_sql_query(
        "SELECT item as 'Item', quantidade as 'Qtd' FROM estoque_tecnico", conn)
    conn.close()
    return df


def get_history():
    conn = sqlite3.connect("solutel_mobile.db")
    df = pd.read_sql_query("""
        SELECT data as 'Data', tecnico as 'Técnico', item as 'Item', 
               quantidade as 'Qtd', tipo as 'Operação', cliente_os as 'Cliente/OS' 
        FROM historico ORDER BY id DESC
    """, conn)
    conn.close()
    return df


def registrar_movimentacao(item, qtd_mudanca, tecnico, cliente_os, tipo):
    conn = sqlite3.connect("solutel_mobile.db")
    cursor = conn.cursor()
    # Atualiza o estoque
    cursor.execute(
        "UPDATE estoque_tecnico SET quantidade = quantidade + ? WHERE item = ?", (qtd_mudanca, item))
    # Registra no histórico
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute("""
        INSERT INTO historico (item, quantidade, tecnico, cliente_os, tipo, data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (item, abs(qtd_mudanca), tecnico, cliente_os, tipo, data_atual))
    conn.commit()
    conn.close()


def delete_item(item):
    conn = sqlite3.connect("solutel_mobile.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM estoque_tecnico WHERE item = ?", (item,))
    conn.commit()
    conn.close()


# Inicializar Base de Dados
init_db()

st.title("🌐 Solutel - Estoque Técnico")
st.markdown("---")

menu = ["📋 Consultar",
        "⬇️ Dar Baixa (Saída)", "⬆️ Adicionar Item", "📜 Histórico", "🗑️ Remover Item"]
escolha = st.sidebar.radio("Navegação", menu)

if escolha == "📋 Consultar":
    st.subheader("Itens no Veículo/Estoque")
    df = get_data()
    if df.empty:
        st.info("Nenhum item cadastrado no estoque.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    if st.button("🔄 Atualizar Lista"):
        st.rerun()

elif escolha == "⬇️ Dar Baixa (Saída)":
    st.subheader("Retirada de Material")
    df = get_data()

    if df.empty:
        st.warning("O estoque está vazio.")
    else:
        item_sel = st.selectbox("Selecione o Item", df["Item"])
        qtd_atual = df[df["Item"] == item_sel]["Qtd"].values[0]

        st.info(f"Estoque atual de {item_sel}: {qtd_atual}")

        # Campos de identificação
        tecnico = st.text_input(
            "Seu Nome (Técnico Responsável) *", placeholder="Obrigatório")

        qtd_retirar = st.number_input("Quantidade a retirar", min_value=1, max_value=int(
            qtd_atual) if int(qtd_atual) > 0 else 1, step=1)

        if st.button("✅ Confirmar Baixa"):
            if not tecnico:
                st.error(
                    "Erro: Você precisa informar o nome do técnico para realizar a baixa!")
            elif qtd_atual < qtd_retirar:
                st.error("Quantidade insuficiente em estoque!")
            else:
                # Registra sem o campo de Cliente/OS (passando string vazia)
                registrar_movimentacao(
                    item_sel, -qtd_retirar, tecnico, "", "SAÍDA")
                st.success(
                    f"Baixa de {qtd_retirar} {item_sel} registrada por {tecnico}!")
                st.balloons()

elif escolha == "⬆️ Adicionar Item":
    st.subheader("Entrada de Material")
    df = get_data()

    novo_ou_existente = st.radio(
        "Tipo de entrada", ["Item Existente", "Novo Produto"])

    if novo_ou_existente == "Item Existente":
        if df.empty:
            st.warning(
                "Não existem itens cadastrados. Utilize a opção 'Novo Produto'.")
        else:
            item_sel = st.selectbox("Selecione o Item", df["Item"])
            qtd_add = st.number_input(
                "Quantidade a adicionar", min_value=1, step=1)

            if st.button("➕ Confirmar Entrada"):
                # Registra a entrada de forma genérica
                registrar_movimentacao(
                    item_sel, qtd_add, "Almoxarifado", "Reposição", "ENTRADA")
                st.success(f"Reposição de {qtd_add} {item_sel} realizada!")
    else:
        novo_item = st.text_input("Nome do Novo Item")
        qtd_inicial = st.number_input(
            "Quantidade Inicial", min_value=0, step=1)

        if st.button("💾 Cadastrar e Dar Entrada"):
            if not novo_item:
                st.error("Preencha o nome do item!")
            else:
                try:
                    conn = sqlite3.connect("solutel_mobile.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO estoque_tecnico (item, quantidade) VALUES (?, ?)", (novo_item, 0))
                    conn.commit()
                    conn.close()
                    # Registra o cadastro inicial de forma genérica
                    registrar_movimentacao(
                        novo_item, qtd_inicial, "Almoxarifado", "Cadastro Inicial", "ENTRADA")
                    st.success(f"{novo_item} cadastrado com sucesso!")
                except Exception as e:
                    st.error(
                        f"Erro: Este item já existe ou ocorreu um problema: {e}")

elif escolha == "📜 Histórico":
    st.subheader("Histórico de Movimentações")
    df_hist = get_history()
    if df_hist.empty:
        st.info("Nenhuma movimentação registrada até o momento.")
    else:
        # Filtro simples por técnico
        tecnicos_lista = ["Todos"] + \
            sorted(df_hist["Técnico"].unique().tolist())
        filtro_tec = st.selectbox("Filtrar por Técnico:", tecnicos_lista)

        if filtro_tec != "Todos":
            df_hist = df_hist[df_hist["Técnico"] == filtro_tec]

        st.dataframe(df_hist, use_container_width=True, hide_index=True)

elif escolha == "🗑️ Remover Item":
    st.subheader("Remover do Catálogo")
    st.warning("Cuidado: Isso remove o item permanentemente do sistema.")

    df = get_data()
    if df.empty:
        st.info("Não há itens para remover.")
    else:
        item_para_remover = st.selectbox("Item para eliminar", df["Item"])
        confirmar = st.checkbox(
            f"Confirmo a exclusão de '{item_para_remover}'")

        if st.button("❌ Apagar Item"):
            if confirmar:
                delete_item(item_para_remover)
                st.success(f"Item '{item_para_remover}' removido!")
                st.rerun()
            else:
                st.error("Marque a caixa de confirmação.")

# Rodapé
st.markdown("---")
st.caption(f"Solutel Mobile v1.3 - Sistema de Gestão Simplificado")
