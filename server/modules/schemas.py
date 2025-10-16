"""
Schemas Pydantic para validação de acórdãos extraídos.

Estrutura baseada nos acórdãos da SEFAZ Acre.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import date


class Relator(BaseModel):
    """Dados do relator/redator do acórdão."""
    nome: str = Field(..., min_length=3, description="Nome completo do relator")
    tipo: Optional[str] = Field(None, description="Tipo: 'Cons.', 'CONSELHEIRO TITULAR', etc.")


class Assinatura(BaseModel):
    """Assinatura de participante do julgamento."""
    nome: str = Field(..., min_length=3, description="Nome completo")
    cargo: str = Field(..., min_length=3, description="Cargo: 'Presidente', 'Conselheiro - Relator', etc.")


class Ementa(BaseModel):
    """Conteúdo da ementa do acórdão."""
    texto_completo: str = Field(..., min_length=50, description="Texto integral da ementa")
    palavras_chave: Optional[List[str]] = Field(default_factory=list, description="Temas principais: ICMS, IPVA, etc.")
    tipo_tributo: Optional[str] = Field(None, description="Tipo de tributo: ICMS, IPVA, etc.")


class Acordao(BaseModel):
    """Conteúdo do acórdão (decisão)."""
    texto_completo: str = Field(..., min_length=50, description="Texto integral do acórdão")
    decisao: str = Field(..., description="Resultado: 'improvido', 'provido', 'parcial', etc.")
    votacao: Optional[str] = Field(None, description="'unanimidade', 'maioria', etc.")
    participantes: Optional[List[str]] = Field(default_factory=list, description="Lista de conselheiros")

    @field_validator('decisao', mode='before')
    @classmethod
    def normalizar_decisao(cls, v: str) -> str:
        """Normaliza decisão para lowercase e remove acentos."""
        if v:
            v = v.lower().strip()
            # Mapear variações comuns
            mapeamento = {
                'improvido': 'improvido',
                'não provido': 'improvido',
                'negado': 'improvido',
                'provido': 'provido',
                'deferido': 'provido',
                'provido parcialmente': 'parcial',
                'parcialmente provido': 'parcial',
            }
            return mapeamento.get(v, v)
        return v


class AcordaoDocumento(BaseModel):
    """
    Schema completo de um acórdão da SEFAZ Acre.

    Campos obrigatórios mínimos:
    - acordao_numero, processo, recorrente, ementa, acordao, assinaturas

    Campos opcionais para lidar com variações:
    - advogado, recorrida, procurador_fiscal, relator, redator, data_sessao
    """

    # ===== CAMPOS OBRIGATÓRIOS =====
    acordao_numero: str = Field(..., description="Número do acórdão: '11/2017', '23/2017', etc.")
    processo: str = Field(..., description="Número do processo: '2014/10/32144', etc.")
    recorrente: str = Field(..., min_length=3, description="Nome do recorrente")
    ementa: Ementa = Field(..., description="Conteúdo da ementa")
    acordao: Acordao = Field(..., description="Conteúdo do acórdão")
    assinaturas: List[Assinatura] = Field(..., min_items=1, description="Assinaturas (geralmente 3)")

    # ===== CAMPOS OPCIONAIS (lidar com variações) =====
    advogado: Optional[str] = Field(None, description="Nome do(s) advogado(s) ou 'NÃO CONSTA'")
    recorrida: Optional[str] = Field(None, description="Nome da recorrida (geralmente Fazenda Pública)")
    procurador_fiscal: Optional[str] = Field(None, description="Nome do procurador fiscal")
    relator: Optional[Relator] = Field(None, description="Dados do relator")
    redator: Optional[Relator] = Field(None, description="Dados do redator (quando diferente do relator)")
    data_sessao: Optional[date] = Field(None, description="Data da sessão de julgamento")
    data_publicacao: Optional[date] = Field(None, description="Data de publicação")

    # Metadados de origem
    source_file: Optional[str] = Field(None, description="Nome do arquivo PDF original")

    @field_validator('acordao_numero', mode='before')
    @classmethod
    def normalizar_acordao_numero(cls, v: str) -> str:
        """Remove espaços e normaliza formato."""
        if v:
            return v.strip().replace(' ', '')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "acordao_numero": "11/2017",
                "processo": "2014/10/32144",
                "recorrente": "BARREIROS E ALMEIDA IMPORTAÇAO E EXPORTAÇAO LTDA",
                "advogado": "NÃO CONSTA",
                "recorrida": "FAZENDA PÚBLICA ESTADUAL",
                "procurador_fiscal": "LUIZ ROGÉRIO AMARAL COLTURATO",
                "relator": {
                    "nome": "BRENO GEOVANE AZEVEDO CAETANO",
                    "tipo": "Cons."
                },
                "ementa": {
                    "texto_completo": "ADMINISTRATIVO. TRIBUTÁRIO. ICMS...",
                    "palavras_chave": ["ICMS", "BENEFÍCIO FISCAL"],
                    "tipo_tributo": "ICMS"
                },
                "acordao": {
                    "texto_completo": "Vistos, relatados e discutidos...",
                    "decisao": "improvido",
                    "votacao": "unanimidade",
                    "participantes": ["Nabil Ibrahim Chamchoum", "..."]
                },
                "assinaturas": [
                    {"nome": "Nabil Ibrahim Chamchoum", "cargo": "Presidente"},
                    {"nome": "Breno Geovane Azevedo Caetano", "cargo": "Conselheiro - Relator"},
                    {"nome": "Luiz Rogério Amaral Colturato", "cargo": "Procurador Fiscal"}
                ],
                "data_sessao": "2017-08-10",
                "source_file": "Acórdão-2017-011.pdf"
            }
        }


class ExtractionResult(BaseModel):
    """Resultado da extração de um PDF."""
    success: bool
    documento: Optional[AcordaoDocumento] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    raw_markdown: Optional[str] = Field(None, description="Markdown bruto do PDF")
    source_file: str
