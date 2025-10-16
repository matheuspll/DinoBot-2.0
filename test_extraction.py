"""
Script de teste para extração de acórdãos.

Processa os 3 PDFs de teste e gera relatório de assertividade.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Adicionar server ao path
sys.path.insert(0, str(Path(__file__).parent))

from server.modules.pdf_extractor import extract_pdf_to_json
from server.modules.schemas import ExtractionResult

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(text: str):
    """Print header formatado."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_success(text: str):
    """Print sucesso."""
    print(f"{GREEN}✓{RESET} {text}")


def print_error(text: str):
    """Print erro."""
    print(f"{RED}✗{RESET} {text}")


def print_warning(text: str):
    """Print warning."""
    print(f"{YELLOW}!{RESET} {text}")


def validate_field(value, field_name: str) -> bool:
    """Valida se campo foi extraído corretamente."""
    if value is None:
        print_error(f"  {field_name}: NOT FOUND")
        return False
    elif isinstance(value, str) and len(value) < 3:
        print_warning(f"  {field_name}: EMPTY or TOO SHORT")
        return False
    else:
        preview = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
        print_success(f"  {field_name}: {preview}")
        return True


def test_single_pdf(pdf_path: Path) -> dict:
    """
    Testa extração de um único PDF.

    Returns:
        Dict com estatísticas
    """
    print_header(f"TESTANDO: {pdf_path.name}")

    result: ExtractionResult = extract_pdf_to_json(pdf_path)

    stats = {
        'file': pdf_path.name,
        'success': result.success,
        'errors': result.errors,
        'warnings': result.warnings,
        'campos_obrigatorios': 0,
        'campos_opcionais': 0,
        'total_campos': 0
    }

    if not result.success:
        print_error(f"FALHA NA EXTRAÇÃO!")
        for error in result.errors:
            print_error(f"  - {error}")
        return stats

    doc = result.documento

    # Validar campos obrigatórios
    print(f"\n{BOLD}Campos Obrigatórios:{RESET}")
    obrigatorios = [
        ('acordao_numero', doc.acordao_numero),
        ('processo', doc.processo),
        ('recorrente', doc.recorrente),
        ('ementa.texto_completo', doc.ementa.texto_completo if doc.ementa else None),
        ('acordao.texto_completo', doc.acordao.texto_completo if doc.acordao else None),
        ('acordao.decisao', doc.acordao.decisao if doc.acordao else None),
        ('assinaturas', f"{len(doc.assinaturas)} assinaturas" if doc.assinaturas else None),
    ]

    for field_name, value in obrigatorios:
        if validate_field(value, field_name):
            stats['campos_obrigatorios'] += 1
        stats['total_campos'] += 1

    # Validar campos opcionais
    print(f"\n{BOLD}Campos Opcionais:{RESET}")
    opcionais = [
        ('advogado', doc.advogado),
        ('recorrida', doc.recorrida),
        ('procurador_fiscal', doc.procurador_fiscal),
        ('relator.nome', doc.relator.nome if doc.relator else None),
        ('data_sessao', str(doc.data_sessao) if doc.data_sessao else None),
        ('ementa.tipo_tributo', doc.ementa.tipo_tributo if doc.ementa else None),
        ('ementa.palavras_chave', f"{len(doc.ementa.palavras_chave)} palavras" if doc.ementa else None),
    ]

    for field_name, value in opcionais:
        if validate_field(value, field_name):
            stats['campos_opcionais'] += 1
        stats['total_campos'] += 1

    # Warnings
    if result.warnings:
        print(f"\n{BOLD}Warnings:{RESET}")
        for warning in result.warnings:
            print_warning(f"  - {warning}")

    # Calcular % de sucesso
    sucesso_obrigatorios = (stats['campos_obrigatorios'] / len(obrigatorios)) * 100
    sucesso_opcionais = (stats['campos_opcionais'] / len(opcionais)) * 100

    print(f"\n{BOLD}Estatísticas:{RESET}")
    print(f"  Campos obrigatórios: {stats['campos_obrigatorios']}/{len(obrigatorios)} ({sucesso_obrigatorios:.1f}%)")
    print(f"  Campos opcionais: {stats['campos_opcionais']}/{len(opcionais)} ({sucesso_opcionais:.1f}%)")

    stats['sucesso_obrigatorios_pct'] = sucesso_obrigatorios
    stats['sucesso_opcionais_pct'] = sucesso_opcionais

    # Salvar JSON extraído
    output_dir = Path("extracted_json")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(doc.model_dump(mode='json'), f, indent=2, ensure_ascii=False, default=str)

    print_success(f"\nJSON salvo em: {output_file}")

    return stats


def main():
    """Executa testes em todos os PDFs."""
    print_header("TESTE DE EXTRAÇÃO DE ACÓRDÃOS - RagBot 2.0")

    # Localizar PDFs
    pdf_dir = Path("acordaos_pdf")
    if not pdf_dir.exists():
        print_error(f"Diretório não encontrado: {pdf_dir}")
        return

    pdfs = list(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print_error(f"Nenhum PDF encontrado em: {pdf_dir}")
        return

    print(f"Encontrados {len(pdfs)} PDFs para processar\n")

    # Processar cada PDF
    all_stats = []
    for pdf in pdfs:
        stats = test_single_pdf(pdf)
        all_stats.append(stats)

    # Relatório final
    print_header("RELATÓRIO FINAL DE ASSERTIVIDADE")

    sucessos = sum(1 for s in all_stats if s['success'])
    falhas = len(all_stats) - sucessos

    print(f"{BOLD}Resumo Geral:{RESET}")
    print(f"  Total de PDFs: {len(all_stats)}")
    print_success(f"  Sucessos: {sucessos}")
    if falhas > 0:
        print_error(f"  Falhas: {falhas}")

    if sucessos > 0:
        # Média de assertividade
        media_obrigatorios = sum(s['sucesso_obrigatorios_pct'] for s in all_stats if s['success']) / sucessos
        media_opcionais = sum(s['sucesso_opcionais_pct'] for s in all_stats if s['success']) / sucessos

        print(f"\n{BOLD}Assertividade Média:{RESET}")
        print(f"  Campos obrigatórios: {media_obrigatorios:.1f}%")
        print(f"  Campos opcionais: {media_opcionais:.1f}%")

        # Critério de sucesso
        print(f"\n{BOLD}Avaliação:{RESET}")
        if media_obrigatorios == 100 and media_opcionais >= 90:
            print_success("  EXCELENTE - Todos os critérios atendidos!")
        elif media_obrigatorios == 100:
            print_success("  BOM - Campos obrigatórios 100%, opcionais podem melhorar")
        elif media_obrigatorios >= 90:
            print_warning("  ACEITÁVEL - Pequenos ajustes necessários")
        else:
            print_error("  INSATISFATÓRIO - Requer melhorias significativas")

    # Salvar relatório
    report_file = Path("relatorio_extracao.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_pdfs': len(all_stats),
            'sucessos': sucessos,
            'falhas': falhas,
            'detalhes': all_stats
        }, f, indent=2, ensure_ascii=False)

    print_success(f"\nRelatório completo salvo em: {report_file}")


if __name__ == "__main__":
    main()
