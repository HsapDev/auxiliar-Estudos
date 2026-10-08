import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from logger import log_info, log_sucesso, log_aviso, log_erro

# Carrega configurações do .env
load_dotenv()

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_DB = os.getenv("PG_DB", "bilau_estudos")


def obter_conexao(autocommit: bool = False):
    """Cria conexão com o banco PostgreSQL e registra o tipo vector."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DB
        )
        conn.autocommit = autocommit
        try:
            register_vector(conn)
        except Exception:
            # Extensão pode não estar instalada ainda se for primeira inicialização
            pass
        return conn
    except psycopg2.OperationalError as e:
        log_erro(f"Falha de conexão com PostgreSQL em {PG_HOST}:{PG_PORT}/{PG_DB}: {e}", "Database")
        raise e


def inicializar_banco() -> bool:
    """
    Cria o banco de dados se não existir e aplica o DDL unificado dos 3 núcleos:
    - Conteúdo (materias, topicos, conteudos_rag)
    - Estudante (perfil_estudante, desempenho_topicos)
    - Mapeamento Informal (contextos_professores)
    """
    # 1. Garante que o banco de dados bilau_estudos exista
    try:
        conn_adm = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname="postgres"
        )
        conn_adm.autocommit = True
        with conn_adm.cursor() as cur:
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (PG_DB,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{PG_DB}";')
                log_sucesso(f"Banco de dados '{PG_DB}' criado com sucesso!", "Database")
        conn_adm.close()
    except Exception as e:
        log_aviso(f"Verificação de criação de banco postgres raiz: {e}", "Database")

    # 2. Aplica extensões e tabelas no banco destino
    try:
        conn = obter_conexao(autocommit=True)
        with conn.cursor() as cur:
            # Habilita extensão pgvector
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                register_vector(conn)
            except Exception as e_vec:
                log_aviso(f"Extensão vector não pôde ser ativada diretamente: {e_vec}", "Database")

            # Núcleo 1: Conteúdo RAG
            cur.execute("""
                CREATE TABLE IF NOT EXISTS materias (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(150) UNIQUE NOT NULL,
                    descricao TEXT,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS topicos (
                    id SERIAL PRIMARY KEY,
                    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
                    nome VARCHAR(200) NOT NULL,
                    dias_atraso INT DEFAULT 0,
                    score INT DEFAULT 0,
                    facilidade VARCHAR(20) DEFAULT 'medio',
                    proxima_revisao DATE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(materia_id, nome)
                );

                CREATE TABLE IF NOT EXISTS conteudos_rag (
                    id SERIAL PRIMARY KEY,
                    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
                    topico_id INT REFERENCES topicos(id) ON DELETE SET NULL,
                    arquivo_origem VARCHAR(255),
                    chunk_indice INT DEFAULT 0,
                    texto TEXT NOT NULL,
                    embedding vector(384),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Núcleo 2: Perfil do Estudante & Desempenho
                CREATE TABLE IF NOT EXISTS perfil_estudante (
                    id SERIAL PRIMARY KEY,
                    chave VARCHAR(100) UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    modo_aprendizado VARCHAR(100),
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS desempenho_topicos (
                    id SERIAL PRIMARY KEY,
                    topico_id INT REFERENCES topicos(id) ON DELETE CASCADE UNIQUE,
                    acertos INT DEFAULT 0,
                    erros INT DEFAULT 0,
                    nivel_dificuldade VARCHAR(20) DEFAULT 'medio',
                    historico_erros JSONB DEFAULT '[]'::jsonb,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Núcleo 3: Mapeamento Informal de Professores e Apelidos
                CREATE TABLE IF NOT EXISTS contextos_professores (
                    id SERIAL PRIMARY KEY,
                    materia_id INT REFERENCES materias(id) ON DELETE CASCADE,
                    apelido_ou_termo VARCHAR(150) NOT NULL,
                    nome_professor VARCHAR(150),
                    observacoes TEXT,
                    UNIQUE(materia_id, apelido_ou_termo)
                );

                -- Índices de busca e vetoriais
                CREATE INDEX IF NOT EXISTS idx_contextos_apelido ON contextos_professores(apelido_ou_termo);
            """)

            # Tenta criar índice IVFFlat se o pgvector estiver habilitado
            try:
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conteudos_rag_embedding 
                    ON conteudos_rag USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
            except Exception:
                pass

            # Seed inicial do perfil caso esteja vazio
            cur.execute("SELECT COUNT(*) FROM perfil_estudante;")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    INSERT INTO perfil_estudante (chave, valor, modo_aprendizado) VALUES
                    ('estilo_explicacao', 'Direto ao ponto, exemplos em código e analogias práticas sem rodeios', 'pratico_codigo'),
                    ('tom_conversa', 'Informal, descontraído, sem enrolação ou formalidades acadêmicas vazias', 'informal')
                    ON CONFLICT DO NOTHING;
                """)

        conn.close()
        log_sucesso("Estrutura do banco de dados relacional verificada/inicializada com sucesso!", "Database")
        return True
    except Exception as e:
        log_erro("Erro ao aplicar DDL das tabelas no PostgreSQL", "Database", exc=e)
        return False


def obter_ou_criar_materia(nome: str, descricao: str = "") -> int:
    """Busca ID da matéria ou cadastra nova se não existir."""
    conn = obter_conexao(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM materias WHERE LOWER(nome) = LOWER(%s);", (nome.strip(),))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("INSERT INTO materias (nome, descricao) VALUES (%s, %s) RETURNING id;", (nome.strip(), descricao))
            return cur.fetchone()[0]
    finally:
        conn.close()


def obter_ou_criar_topico(materia_id: int, nome: str) -> int:
    """Busca ID do tópico ou cadastra novo sob a matéria informada."""
    conn = obter_conexao(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM topicos WHERE materia_id = %s AND LOWER(nome) = LOWER(%s);", (materia_id, nome.strip()))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("INSERT INTO topicos (materia_id, nome) VALUES (%s, %s) RETURNING id;", (materia_id, nome.strip()))
            return cur.fetchone()[0]
    finally:
        conn.close()


def salvar_chunk_rag(materia_id: int, topico_id: Optional[int], arquivo: str, indice: int, texto: str, embedding: List[float]):
    """Insere um pedaço de texto e seu vetor na tabela conteudos_rag."""
    conn = obter_conexao(autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO conteudos_rag (materia_id, topico_id, arquivo_origem, chunk_indice, texto, embedding)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (materia_id, topico_id, arquivo, indice, texto, embedding))
    finally:
        conn.close()


def buscar_contexto_rag(query_embedding: List[float], limite: int = 4, materia_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Realiza busca vetorial semântica por proximidade de cosseno (pgvector)."""
    conn = obter_conexao()
    resultados = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if materia_id:
                cur.execute("""
                    SELECT c.id, c.texto, c.arquivo_origem, m.nome as materia_nome,
                           1 - (c.embedding <=> %s::vector) AS similaridade
                    FROM conteudos_rag c
                    JOIN materias m ON m.id = c.materia_id
                    WHERE c.materia_id = %s
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s;
                """, (query_embedding, materia_id, query_embedding, limite))
            else:
                cur.execute("""
                    SELECT c.id, c.texto, c.arquivo_origem, m.nome as materia_nome,
                           1 - (c.embedding <=> %s::vector) AS similaridade
                    FROM conteudos_rag c
                    JOIN materias m ON m.id = c.materia_id
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s;
                """, (query_embedding, query_embedding, limite))
            resultados = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        log_erro("Erro na busca vetorial pgvector", "Database", exc=e)
    finally:
        conn.close()
    return resultados


def mapear_apelido(termo_ou_apelido: str) -> Optional[Dict[str, Any]]:
    """Consulta contextos_professores para resolver apelidos informais à matéria."""
    conn = obter_conexao()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT cp.apelido_ou_termo, cp.nome_professor, m.id as materia_id, m.nome as materia_nome
                FROM contextos_professores cp
                JOIN materias m ON m.id = cp.materia_id
                WHERE %s ILIKE ('%%' || cp.apelido_ou_termo || '%%')
                   OR %s ILIKE ('%%' || cp.nome_professor || '%%')
                LIMIT 1;
            """, (termo_ou_apelido, termo_ou_apelido))
            return cur.fetchone()
    finally:
        conn.close()


def obter_perfil_estudante() -> Dict[str, str]:
    """Retorna mapa de preferências do aluno registradas no banco."""
    conn = obter_conexao()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT chave, valor, modo_aprendizado FROM perfil_estudante;")
            return {r["chave"]: r["valor"] for r in cur.fetchall()}
    finally:
        conn.close()


def obter_desempenho_materia(materia_id: int) -> List[Dict[str, Any]]:
    """Retorna estatísticas de erros e tópicos críticos da matéria."""
    conn = obter_conexao()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.nome as topico, dt.acertos, dt.erros, dt.nivel_dificuldade, dt.historico_erros
                FROM desempenho_topicos dt
                JOIN topicos t ON t.id = dt.topico_id
                WHERE t.materia_id = %s
                ORDER BY dt.erros DESC;
            """, (materia_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
