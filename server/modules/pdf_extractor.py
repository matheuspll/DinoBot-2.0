"""
Extração estruturada de acórdãos PDF para JSON.

Pipeline: PDF → Markdown → Regex (estrutura) → LLM (fallback) → JSON validado

Abordagem híbrida:
- Usa regex para campos estruturados conhecidos
- Usa LLM (Groq) para textos complexos e variações
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from pypdf import PdfReader
from groq import Groq
import os
from dotenv import load_dotenv

from server.modules.schemas import (
    AcordaoDocumento,
    Ementa,
    Acordao,
    Assinatura,
    Relator,
    ExtractionResult
)
from server.logger import setup_logger

load_dotenv()
log = setup_logger(__name__)


class AcordaoExtractor:
    """Extrator híbrido de acórdãos PDF."""

    def __init__(self):
        """Inicializa extrator com cliente Groq."""
        self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.llm_model = "llama-3.3-70b-versatile"  # Modelo atualizado

    def pdf_to_text(self, pdf_path: Path) -> str:
        """
        Extrai texto bruto do PDF usando PyPDF.

        Args:
            pdf_path: Caminho do PDF

        Returns:
            Texto completo extraído
        """
        log.info(f"Extraindo texto de: {pdf_path.name}")
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        log.debug(f"Extraídos {len(text)} caracteres")
        return text

    def clean_text(self, text: str) -> str:
        """
        Remove ruído do texto (cabeçalhos, footers repetitivos).

        Args:
            text: Texto bruto

        Returns:
            Texto limpo
        """
        # Remover múltiplos espaços/quebras de linha
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        # Remover cabeçalhos visuais repetitivos
        text = re.sub(r'ESTADO DO ACRE\s+Secretaria.*?Conselho.*?\n', '', text, flags=re.IGNORECASE)

        return text.strip()

    def extract_metadata_regex(self, text: str) -> Dict:
        """
        Extrai metadados usando regex (campos estruturados).

        Args:
            text: Texto do PDF

        Returns:
            Dicionário com metadados extraídos
        """
        metadata = {}

        # Acórdão número
        match = re.search(r'ACÓRDÃO\s+N[º°]\s*(\d+/\d{4})', text, re.IGNORECASE)
        if match:
            metadata['acordao_numero'] = match.group(1)

        # Processo
        match = re.search(r'PROCESSO\s+N[º°]\s*([\d/]+)', text, re.IGNORECASE)
        if match:
            metadata['processo'] = match.group(1)

        # Recorrente
        match = re.search(r'RECORRENTE:\s*(.+?)(?:\n|ADVOGADO)', text, re.IGNORECASE)
        if match:
            metadata['recorrente'] = match.group(1).strip()

        # Advogado
        match = re.search(r'ADVOGADO[S]?:\s*(.+?)(?:\n|RECORRIDA)', text, re.IGNORECASE)
        if match:
            metadata['advogado'] = match.group(1).strip()

        # Recorrida
        match = re.search(r'RECORRIDA:\s*(.+?)(?:\n|PROCURADOR)', text, re.IGNORECASE)
        if match:
            metadata['recorrida'] = match.group(1).strip()

        # Procurador Fiscal
        match = re.search(r'PROCURADOR\s+FISCAL:\s*(.+?)(?:\n|RELATOR)', text, re.IGNORECASE)
        if match:
            metadata['procurador_fiscal'] = match.group(1).strip()

        # Relator (pode ser RELATOR ou CONSELHEIRO RELATOR)
        match = re.search(r'(?:CONSELHEIRO\s+)?RELATOR:\s*(?:Cons\.\s*)?(.+?)(?:\n|REDATOR|DATA)', text, re.IGNORECASE)
        if match:
            nome_relator = match.group(1).strip()
            # Detectar tipo (Cons., CONSELHEIRO TITULAR, etc.)
            tipo_match = re.search(r'(Cons\.|CONSELHEIRO\s+TITULAR)', nome_relator, re.IGNORECASE)
            tipo = tipo_match.group(1) if tipo_match else None
            nome_limpo = re.sub(r'(Cons\.|CONSELHEIRO\s+TITULAR)\s*', '', nome_relator, flags=re.IGNORECASE).strip()
            metadata['relator'] = {'nome': nome_limpo, 'tipo': tipo}

        # Redator do Acórdão (se existir)
        match = re.search(r'REDATOR\s+DO\s+AC[ÓO]RD[ÃA]O[:\s]+(?:Cons\.\s*)?(.+?)(?:\n|DATA)', text, re.IGNORECASE)
        if match:
            nome_redator = match.group(1).strip()
            tipo_match = re.search(r'(Cons\.|CONSELHEIRO)', nome_redator, re.IGNORECASE)
            tipo = tipo_match.group(1) if tipo_match else None
            nome_limpo = re.sub(r'(Cons\.|CONSELHEIRO)\s*', '', nome_redator, flags=re.IGNORECASE).strip()
            metadata['redator'] = {'nome': nome_limpo, 'tipo': tipo}

        # Data da sessão (padrão: "10 de agosto de 2017" ou "30 de agosto de 2017")
        match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', text, re.IGNORECASE)
        if match:
            dia, mes_texto, ano = match.groups()
            meses = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            mes = meses.get(mes_texto.lower())
            if mes:
                metadata['data_sessao'] = f"{ano}-{mes:02d}-{int(dia):02d}"

        log.debug(f"Metadados extraídos via regex: {list(metadata.keys())}")
        return metadata

    def extract_ementa(self, text: str) -> Optional[Dict]:
        """
        Extrai seção EMENTA usando regex.

        Args:
            text: Texto do PDF

        Returns:
            Dicionário com ementa
        """
        # Regex para capturar ementa (entre "E M E N T A" e "A C Ó R D Ã O")
        match = re.search(
            r'E\s*M\s*E\s*N\s*T\s*A\s*(.+?)A\s*C\s*[ÓO]\s*R\s*D\s*[ÃA]\s*O',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not match:
            log.warning("Ementa não encontrada via regex")
            return None

        texto_ementa = match.group(1).strip()

        # Extrair palavras-chave (primeira linha geralmente contém)
        primeira_linha = texto_ementa.split('\n')[0]
        palavras_chave = []
        tipo_tributo = None

        # Detectar tipo de tributo
        if re.search(r'\bICMS\b', primeira_linha, re.IGNORECASE):
            tipo_tributo = 'ICMS'
            palavras_chave.append('ICMS')
        elif re.search(r'\bIPVA\b', primeira_linha, re.IGNORECASE):
            tipo_tributo = 'IPVA'
            palavras_chave.append('IPVA')
        elif re.search(r'\bITCD\b', primeira_linha, re.IGNORECASE):
            tipo_tributo = 'ITCD'
            palavras_chave.append('ITCD')

        # Detectar temas comuns
        temas = {
            'BENEFÍCIO FISCAL': r'BENEF[IÍ]CIO\s+FISCAL',
            'ISENÇÃO': r'ISEN[ÇC][ÃA]O',
            'SUBSTITUIÇÃO TRIBUTÁRIA': r'SUBSTITUI[ÇC][ÃA]O\s+TRIBUT[ÁA]RIA',
            'OBRIGAÇÃO ACESSÓRIA': r'OBRIGA[ÇC][ÃA]O\s+ACESS[ÓO]RIA',
        }

        for tema, padrao in temas.items():
            if re.search(padrao, texto_ementa, re.IGNORECASE):
                palavras_chave.append(tema)

        return {
            'texto_completo': texto_ementa,
            'palavras_chave': palavras_chave,
            'tipo_tributo': tipo_tributo
        }

    def extract_acordao_llm(self, text: str) -> Optional[Dict]:
        """
        Extrai conteúdo do acórdão usando LLM (decisão, votação, participantes).

        Args:
            text: Texto do PDF

        Returns:
            Dicionário com dados do acórdão
        """
        # Primeiro, tentar extrair a seção ACÓRDÃO via regex
        match = re.search(
            r'A\s*C\s*[ÓO]\s*R\s*D\s*[ÃA]\s*O\s*(.+?)(?:Nabil|Sala\s+das\s+Sess)',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not match:
            log.warning("Seção ACÓRDÃO não encontrada")
            return None

        texto_acordao = match.group(1).strip()

        # Usar LLM para extrair decisão e votação
        prompt = f"""Analise este texto de acórdão e extraia:
1. Decisão final: "provido", "improvido", "parcial"
2. Tipo de votação: "unanimidade", "maioria", ou null
3. Lista de participantes (conselheiros mencionados)

Texto do acórdão:
{texto_acordao[:1500]}

Responda APENAS com JSON válido no formato:
{{
    "decisao": "improvido",
    "votacao": "unanimidade",
    "participantes": ["Nome 1", "Nome 2"]
}}"""

        try:
            response = self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )

            llm_output = response.choices[0].message.content.strip()

            # Extrair JSON da resposta (pode vir com markdown)
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                result['texto_completo'] = texto_acordao
                log.info("Acórdão extraído via LLM com sucesso")
                return result
            else:
                log.error("LLM não retornou JSON válido")
                return None

        except Exception as e:
            log.error(f"Erro ao usar LLM: {e}")
            return None

    def extract_assinaturas(self, text: str) -> List[Dict]:
        """
        Extrai assinaturas do final do documento.

        Args:
            text: Texto do PDF

        Returns:
            Lista de assinaturas
        """
        assinaturas = []

        # Padrão: Nome seguido de cargo (última seção do documento)
        # Exemplo:
        # Nabil Ibrahim Chamchoum     Breno Geovane Azevedo Caetano
        # Presidente                  Conselheiro - Relator

        # Pegar últimas linhas (onde ficam assinaturas)
        linhas = text.split('\n')[-15:]  # Últimas 15 linhas
        texto_assinaturas = '\n'.join(linhas)

        # Detectar padrão: Nome + Cargo (abaixo ou ao lado)
        # Padrão 1: Presidente
        match = re.search(r'(\w[\w\s]+?)\s+Presidente', texto_assinaturas, re.IGNORECASE)
        if match:
            assinaturas.append({'nome': match.group(1).strip(), 'cargo': 'Presidente'})

        # Padrão 2: Conselheiro - Relator ou Conselheiro Suplente
        matches = re.finditer(
            r'(\w[\w\s]+?)\s+(Conselheiro\s*-?\s*(?:Relator|Suplente|Redator(?:\s+do\s+Ac[óo]rd[ãa]o)?))',
            texto_assinaturas,
            re.IGNORECASE
        )
        for match in matches:
            nome = match.group(1).strip()
            cargo = match.group(2).strip()
            # Evitar duplicatas
            if not any(a['nome'] == nome for a in assinaturas):
                assinaturas.append({'nome': nome, 'cargo': cargo})

        # Padrão 3: Procurador Fiscal
        match = re.search(r'(\w[\w\s]+?)\s+Procurador\s+Fiscal', texto_assinaturas, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            if not any(a['nome'] == nome for a in assinaturas):
                assinaturas.append({'nome': nome, 'cargo': 'Procurador Fiscal'})

        log.debug(f"Assinaturas extraídas: {len(assinaturas)}")
        return assinaturas

    def extract_acordao(self, pdf_path: Path) -> ExtractionResult:
        """
        Pipeline completo de extração de PDF → JSON.

        Args:
            pdf_path: Caminho do PDF

        Returns:
            ExtractionResult com documento validado ou erros
        """
        log.info(f"Iniciando extração de: {pdf_path.name}")
        errors = []
        warnings = []

        try:
            # 1. PDF → Texto
            text = self.pdf_to_text(pdf_path)
            cleaned_text = self.clean_text(text)

            # 2. Extrair componentes
            metadata = self.extract_metadata_regex(cleaned_text)
            ementa_data = self.extract_ementa(cleaned_text)
            acordao_data = self.extract_acordao_llm(cleaned_text)
            assinaturas_data = self.extract_assinaturas(cleaned_text)

            # 3. Validar campos obrigatórios
            campos_obrigatorios = ['acordao_numero', 'processo', 'recorrente']
            faltando = [c for c in campos_obrigatorios if c not in metadata]

            if faltando:
                errors.append(f"Campos obrigatórios faltando: {faltando}")

            if not ementa_data:
                errors.append("Ementa não extraída")

            if not acordao_data:
                errors.append("Acórdão não extraído")

            if not assinaturas_data:
                warnings.append("Nenhuma assinatura extraída")

            # 4. Construir documento
            if errors:
                log.error(f"Erros na extração: {errors}")
                return ExtractionResult(
                    success=False,
                    errors=errors,
                    warnings=warnings,
                    raw_markdown=cleaned_text,
                    source_file=pdf_path.name
                )

            # 5. Montar objeto Pydantic
            documento_dict = {
                **metadata,
                'ementa': ementa_data,
                'acordao': acordao_data,
                'assinaturas': assinaturas_data,
                'source_file': pdf_path.name
            }

            # 6. Validar com Pydantic
            documento = AcordaoDocumento(**documento_dict)

            log.info(f"✓ Extração bem-sucedida: {pdf_path.name}")
            return ExtractionResult(
                success=True,
                documento=documento,
                warnings=warnings,
                raw_markdown=cleaned_text,
                source_file=pdf_path.name
            )

        except Exception as e:
            log.exception(f"Erro inesperado na extração: {e}")
            return ExtractionResult(
                success=False,
                errors=[f"Erro inesperado: {str(e)}"],
                source_file=pdf_path.name
            )


# Função de conveniência
def extract_pdf_to_json(pdf_path: Path) -> ExtractionResult:
    """
    Extrai PDF para JSON validado.

    Args:
        pdf_path: Caminho do PDF

    Returns:
        ExtractionResult
    """
    extractor = AcordaoExtractor()
    return extractor.extract_acordao(pdf_path)
