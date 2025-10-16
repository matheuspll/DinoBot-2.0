"""
Script para reindexar PDFs usando chunking estrutural e metadados enriquecidos.

Este script:
1. Extrai estrutura de PDFs para JSON (se ainda não existir)
2. Cria chunks estruturados baseados nas seções (ementa, acórdão)
3. Adiciona metadados ricos ao vectorstore
4. Permite reconstruir o vectorstore do zero com as melhorias

Uso:
    python reindex_with_structured_chunking.py
"""

import sys
import os
from pathlib import Path
import json
import shutil

# Adicionar server ao path
sys.path.insert(0, str(Path(__file__).parent / 'server'))

from server.modules.pdf_extractor import extract_pdf_to_json
from server.modules.load_vectorstore import add_documents_with_structured_chunking, PERSIST_DIR, EXTRACTED_JSON_DIR
from server.logger import setup_logger

log = setup_logger(__name__)

# Cores para output
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(text: str):
    """Print header formatado."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def main():
    """Reindexação completa com chunking estrutural."""
    print_header("REINDEXAÇÃO COM CHUNKING ESTRUTURAL + METADADOS ENRIQUECIDOS")

    # 1. Localizar PDFs
    pdf_dir = Path("uploaded_pdfs")
    if not pdf_dir.exists():
        print(f"{RED}Erro: Diretório 'uploaded_pdfs/' não encontrado.{RESET}")
        print(f"{YELLOW}Faça upload de PDFs via interface antes de reindexar.{RESET}")
        return

    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"{RED}Erro: Nenhum PDF encontrado em 'uploaded_pdfs/'.{RESET}")
        return

    print(f"Encontrados {GREEN}{len(pdfs)}{RESET} PDFs para processar\n")

    # 2. Perguntar se deseja limpar vectorstore existente
    if os.path.exists(PERSIST_DIR):
        print(f"{YELLOW}⚠ Vectorstore existente detectado em '{PERSIST_DIR}'{RESET}")
        resposta = input("Deseja DELETAR e recriar do zero? (s/N): ").strip().lower()

        if resposta == 's':
            print(f"{YELLOW}Deletando vectorstore antigo...{RESET}")
            shutil.rmtree(PERSIST_DIR)
            print(f"{GREEN}✓ Vectorstore deletado{RESET}")
        else:
            print(f"{BLUE}→ Adicionando documentos ao vectorstore existente{RESET}")

    # 3. Criar diretório para JSONs extraídos
    Path(EXTRACTED_JSON_DIR).mkdir(exist_ok=True)

    # 4. Processar cada PDF
    sucessos = 0
    falhas = 0

    for i, pdf_path in enumerate(pdfs, 1):
        print(f"\n{BOLD}[{i}/{len(pdfs)}] Processando: {pdf_path.name}{RESET}")

        # Verificar se JSON já existe
        json_path = Path(EXTRACTED_JSON_DIR) / f"{pdf_path.stem}.json"

        if json_path.exists():
            print(f"  {BLUE}→ JSON já existe, carregando...{RESET}")
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            extraction_success = True
        else:
            # Extrair estrutura do PDF
            print(f"  {BLUE}→ Extraindo estrutura do PDF...{RESET}")
            result = extract_pdf_to_json(pdf_path)

            if result.success:
                json_data = result.documento.model_dump(mode='json')
                # Salvar JSON
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
                print(f"  {GREEN}✓ Estrutura extraída e salva em {json_path.name}{RESET}")
                extraction_success = True
            else:
                print(f"  {RED}✗ Falha na extração: {', '.join(result.errors)}{RESET}")
                extraction_success = False
                json_data = None

        # Indexar com chunking estrutural
        if extraction_success:
            print(f"  {BLUE}→ Criando chunks estruturados e indexando...{RESET}")
            try:
                vectorstore = add_documents_with_structured_chunking(
                    pdf_path=pdf_path,
                    json_data=json_data
                )

                if vectorstore:
                    print(f"  {GREEN}✓ Indexado com sucesso{RESET}")
                    sucessos += 1
                else:
                    print(f"  {RED}✗ Falha na indexação{RESET}")
                    falhas += 1
            except Exception as e:
                print(f"  {RED}✗ Erro na indexação: {e}{RESET}")
                falhas += 1
        else:
            falhas += 1

    # 5. Relatório final
    print_header("RELATÓRIO FINAL DE REINDEXAÇÃO")

    print(f"{BOLD}Resumo:{RESET}")
    print(f"  Total de PDFs: {len(pdfs)}")
    print(f"  {GREEN}Sucessos: {sucessos}{RESET}")

    if falhas > 0:
        print(f"  {RED}Falhas: {falhas}{RESET}")

    if sucessos > 0:
        print(f"\n{GREEN}✓ Reindexação concluída com sucesso!{RESET}")
        print(f"{BOLD}Melhorias aplicadas:{RESET}")
        print(f"  • Chunking estrutural por seções (ementa, acórdão)")
        print(f"  • Metadados enriquecidos (tipo_tributo, decisão, ano, etc.)")
        print(f"  • Pesos de relevância jurídica por seção")
        print(f"  • Prompt engineering especializado")
        print(f"  • Reranking automático de resultados")

        print(f"\n{BLUE}Próximos passos:{RESET}")
        print(f"  1. Reinicie o servidor: cd server && uvicorn main:app --reload")
        print(f"  2. Teste o sistema com perguntas")
        print(f"  3. Compare a qualidade das respostas com o sistema anterior")
    else:
        print(f"\n{RED}✗ Nenhum documento foi indexado com sucesso.{RESET}")


if __name__ == "__main__":
    main()
