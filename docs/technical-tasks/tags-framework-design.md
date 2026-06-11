# Tags Framework Design - CauSium

**Versão:** 1.1.0  
**Data:** 2026-06-11  
**Status:** Design técnico - NÃO IMPLEMENTAR  
**Tipo:** Planejamento apenas  

---

## Objetivo

Projetar a implementação do Tags Framework como primeira funcionalidade da Fase 2 (FinOps Essencial).

O Tags Framework é a **fundação da governança FinOps** - todas as outras funcionalidades (Untagged Resources, Cost Allocation, Teams) dependem dele.

---

## 0. ABORDAGENS DE IMPLEMENTAÇÃO

### ⚠️ CONTEXTO: Alembic Bloqueado

Devido ao problema de **Alembic Multiple Heads** documentado em `docs/technical-tasks/alembic-priority-assessment.md`, migrations estão bloqueadas no momento.

Portanto, apresentamos duas abordagens:

---

### OPÇÃO A - Full Implementation (BLOQUEADA)

| Aspecto | Descrição |
|---------|-----------|
| **Status** | 🔴 BLOQUEADA - Requer Alembic resolvido |
| **Models** | Tag, ResourceTag, TagCompliance (3 novos) |
| **Tabelas** | 3 novas tabelas no PostgreSQL |
| **Migrations** | Requer alembic upgrade head |
| **APIs** | CRUD completo + write path |
| **Complexidade** | Alta |
| **Risco** | 🟡 Médio - Requer schema change |
| **Tempo** | 9-15 dias |

#### Quando pode ser executada:
- ❌ Agora (Alembic bloqueado)
- ✅ Após resolver Alembic Multiple Heads
- ✅ Após 90 dias (deadline para Alembic)

#### Requisitos:
- ✅ Backup PostgreSQL
- ✅ Backup ClickHouse
- ✅ Staging configurado
- ✅ Rollback documentado
- ✅ Aprovação explícita

---

### OPÇÃO B - MVP Sem Migration (RECOMENDADA) ✅

| Aspecto | Descrição |
|---------|-----------|
| **Status** | ✅ DISPONÍVEL - Pode ser executada agora |
| **Models** | Nenhum novo |
| **Tabelas** | Nenhuma nova |
| **Migrations** | ❌ NENHUMA |
| **APIs** | Read-only (queries no ClickHouse) |
| **Complexidade** | Baixa |
| **Risco** | 🟢 Baixo - Não altera banco |
| **Tempo** | 3-5 dias |

#### Vantagens:
- ✅ Entrega valor ao cliente imediatamente
- ✅ Não requer Alembic
- ✅ Não altera schema
- ✅ Reduz risco
- ✅ Compatível com produção protegida
- ✅ Pode ser iterado depois

#### O que entrega:
- Tag Coverage (percentual de recursos com tags)
- Untagged Cost (custo de recursos sem tags)
- Cost by Tag Key (custos segmentados por tag)
- Top Untagged Subscriptions
- Tag Compliance Summary

---

### RECOMENDAÇÃO

**RECOMENDADO: OPÇÃO B - MVP SEM MIGRATION**

### Justificativa

| Fator | Avaliação |
|-------|-----------|
| **Entrega de valor** | Imediata |
| **Risco** | Mínimo (read-only) |
| **Dependência Alembic** | Nenhuma |
| **Schema change** | Nenhum |
| **Compatibilidade produção** | Total |
| **Iteração futura** | Pode evoluir para Opção A |

### Plano de Evolução

```
IMEDIATO (Opção B):
├── Tags read-only API (ClickHouse)
├── Tag Coverage Dashboard
└── Untagged Cost Analysis

APÓS RESOLVER ALEMBIC (Opção A):
├── Migration de tables
├── CRUD completo
├── Write path
└── Alertas de compliance
```

---

## OPÇÃO B - MVP SEM MIGRATION (IMPLEMENTAR AGORA)

> Esta seção documenta a Opção B que deve ser implementada agora.
> Opção B é read-only, não requer migrations, e entrega valor imediato.

### B.1 Arquitetura MVP

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │Tag Coverage  │  │Untagged Cost │  │Cost by Tag   │    │
│  │   Widget     │  │   Widget     │  │   Widget     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Gov Service (Read-Only)               │  │
│  │  - get_tag_coverage()                               │  │
│  │  - get_untagged_cost()                              │  │
│  │  - get_cost_by_tag()                               │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       CLICKHOUSE                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                cost_facts table                     │  │
│  │  - tags (Json)                                      │  │
│  │  - subscription_id                                 │  │
│  │  - resource_id                                     │  │
│  │  - cost_usd                                        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### B.2 APIs MVP (Read-Only)

#### Endpoint 1: Tag Coverage

```python
# backend/app/domains/gov/service.py

class TagCoverageService:
    """Service for tag coverage analysis - Read-Only."""
    
    def get_tag_coverage(
        self,
        workspace_id: UUID,
        tag_key: str = "team",
        start_date: date = None,
        end_date: date = None
    ) -> TagCoverageResponse:
        """
        Get percentage of resources with a specific tag.
        
        Returns:
        - total_resources: Total resources in period
        - tagged_resources: Resources with tag
        - untagged_resources: Resources without tag
        - coverage_percentage: % of tagged resources
        """
        
        start_date = start_date or (date.today() - timedelta(days=30))
        end_date = end_date or date.today()
        
        query = f"""
        SELECT
            count(DISTINCT resource_id) as total_resources,
            countIf(DISTINCT resource_id, has(tags, '{tag_key}')) as tagged_resources,
            countIf(DISTINCT resource_id, NOT has(tags, '{tag_key}')) as untagged_resources
        FROM cost_facts
        WHERE workspace_id = '{workspace_id}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        """
        
        result = self.clickhouse_client.query(query)
        row = result[0]
        
        total = row.total_resources or 0
        tagged = row.tagged_resources or 0
        untagged = row.untagged_resources or 0
        coverage = (tagged / total * 100) if total > 0 else 0
        
        return TagCoverageResponse(
            tag_key=tag_key,
            total_resources=total,
            tagged_resources=tagged,
            untagged_resources=untagged,
            coverage_percentage=round(coverage, 2),
            period_start=start_date,
            period_end=end_date
        )
```

#### Endpoint 2: Untagged Cost

```python
class UntaggedCostService:
    """Service for untagged cost analysis - Read-Only."""
    
    def get_untagged_cost(
        self,
        workspace_id: UUID,
        tag_key: str = "team",
        start_date: date = None,
        end_date: date = None
    ) -> UntaggedCostResponse:
        """
        Get cost of resources without a specific tag.
        
        Returns:
        - total_cost: Total cost in period
        - tagged_cost: Cost of tagged resources
        - untagged_cost: Cost of untagged resources
        - untagged_percentage: % of cost from untagged
        """
        
        start_date = start_date or (date.today() - timedelta(days=30))
        end_date = end_date or date.today()
        
        query = f"""
        SELECT
            sum(cost_usd) as total_cost,
            sumIf(cost_usd, has(tags, '{tag_key}')) as tagged_cost,
            sumIf(cost_usd, NOT has(tags, '{tag_key}')) as untagged_cost
        FROM cost_facts
        WHERE workspace_id = '{workspace_id}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        """
        
        result = self.clickhouse_client.query(query)
        row = result[0]
        
        total = row.total_cost or 0
        tagged = row.tagged_cost or 0
        untagged = row.untagged_cost or 0
        untagged_pct = (untagged / total * 100) if total > 0 else 0
        
        return UntaggedCostResponse(
            tag_key=tag_key,
            total_cost=total,
            tagged_cost=tagged,
            untagged_cost=untagged,
            untagged_percentage=round(untagged_pct, 2),
            period_start=start_date,
            period_end=end_date
        )
```

#### Endpoint 3: Cost by Tag

```python
class CostByTagService:
    """Service for cost breakdown by tag - Read-Only."""
    
    def get_cost_by_tag(
        self,
        workspace_id: UUID,
        tag_key: str = "environment",
        start_date: date = None,
        end_date: date = None
    ) -> CostByTagResponse:
        """
        Get cost breakdown by tag value.
        
        Returns:
        - List of tag values with costs
        - Sorted by total cost descending
        """
        
        start_date = start_date or (date.today() - timedelta(days=30))
        end_date = end_date or date.today()
        
        query = f"""
        SELECT
            JSONExtractString(tags, '{tag_key}') as tag_value,
            sum(cost_usd) as total_cost,
            count(DISTINCT resource_id) as resource_count,
            avg(cost_usd) as avg_cost
        FROM cost_facts
        WHERE workspace_id = '{workspace_id}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
          AND JSONExtractString(tags, '{tag_key}') != ''
        GROUP BY tag_value
        ORDER BY total_cost DESC
        LIMIT 50
        """
        
        result = self.clickhouse_client.query(query)
        
        rows = [
            TagValueCost(
                tag_value=row.tag_value or "untagged",
                total_cost=row.total_cost or 0,
                resource_count=row.resource_count or 0,
                avg_cost=row.avg_cost or 0
            )
            for row in result
        ]
        
        return CostByTagResponse(
            tag_key=tag_key,
            values=rows,
            period_start=start_date,
            period_end=end_date
        )
```

#### Endpoint 4: Top Untagged Subscriptions

```python
class TopUntaggedService:
    """Service for top untagged subscriptions - Read-Only."""
    
    def get_top_untagged_subscriptions(
        self,
        workspace_id: UUID,
        tag_key: str = "team",
        limit: int = 10,
        start_date: date = None,
        end_date: date = None
    ) -> TopUntaggedResponse:
        """
        Get subscriptions with highest untagged costs.
        
        Returns:
        - List of subscriptions ranked by untagged cost
        """
        
        start_date = start_date or (date.today() - timedelta(days=30))
        end_date = end_date or date.today()
        
        query = f"""
        SELECT
            subscription_id,
            subscription_name,
            sum(cost_usd) as total_cost,
            sumIf(cost_usd, NOT has(tags, '{tag_key}')) as untagged_cost,
            count(DISTINCT resource_id) as resource_count
        FROM cost_facts
        WHERE workspace_id = '{workspace_id}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        GROUP BY subscription_id, subscription_name
        ORDER BY untagged_cost DESC
        LIMIT {limit}
        """
        
        result = self.clickhouse_client.query(query)
        
        rows = [
            SubscriptionUntagged(
                subscription_id=row.subscription_id,
                subscription_name=row.subscription_name or "Unknown",
                total_cost=row.total_cost or 0,
                untagged_cost=row.untagged_cost or 0,
                resource_count=row.resource_count or 0
            )
            for row in result
        ]
        
        return TopUntaggedResponse(
            tag_key=tag_key,
            subscriptions=rows,
            period_start=start_date,
            period_end=end_date
        )
```

### B.3 Schemas MVP

```python
# backend/app/domains/gov/schemas.py

from pydantic import BaseModel, Field
from datetime import date, datetime
from uuid import UUID
from typing import List, Optional

class TagCoverageResponse(BaseModel):
    tag_key: str
    total_resources: int
    tagged_resources: int
    untagged_resources: int
    coverage_percentage: float
    period_start: date
    period_end: date

class UntaggedCostResponse(BaseModel):
    tag_key: str
    total_cost: float
    tagged_cost: float
    untagged_cost: float
    untagged_percentage: float
    period_start: date
    period_end: date

class TagValueCost(BaseModel):
    tag_value: str
    total_cost: float
    resource_count: int
    avg_cost: float

class CostByTagResponse(BaseModel):
    tag_key: str
    values: List[TagValueCost]
    period_start: date
    period_end: date

class SubscriptionUntagged(BaseModel):
    subscription_id: str
    subscription_name: str
    total_cost: float
    untagged_cost: float
    resource_count: int

class TopUntaggedResponse(BaseModel):
    tag_key: str
    subscriptions: List[SubscriptionUntagged]
    period_start: date
    period_end: date

class TagComplianceSummary(BaseModel):
    tag_key: str
    coverage_percentage: float
    total_cost: float
    untagged_cost: float
    top_untagged_subscription: Optional[str]
```

### B.4 Router MVP

```python
# backend/app/domains/gov/router.py

from fastapi import APIRouter, Query
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/api/v1/gov", tags=["governance"])

@router.get("/tag-coverage")
async def get_tag_coverage(
    workspace_id: UUID,
    tag_key: str = Query("team", description="Tag key to analyze"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> TagCoverageResponse:
    """Get tag coverage percentage for a workspace."""
    service = TagCoverageService()
    return service.get_tag_coverage(workspace_id, tag_key, start_date, end_date)

@router.get("/untagged-cost")
async def get_untagged_cost(
    workspace_id: UUID,
    tag_key: str = Query("team", description="Tag key to analyze"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> UntaggedCostResponse:
    """Get cost of untagged resources."""
    service = UntaggedCostService()
    return service.get_untagged_cost(workspace_id, tag_key, start_date, end_date)

@router.get("/cost-by-tag")
async def get_cost_by_tag(
    workspace_id: UUID,
    tag_key: str = Query("environment", description="Tag key to analyze"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> CostByTagResponse:
    """Get cost breakdown by tag value."""
    service = CostByTagService()
    return service.get_cost_by_tag(workspace_id, tag_key, start_date, end_date)

@router.get("/top-untagged-subscriptions")
async def get_top_untagged_subscriptions(
    workspace_id: UUID,
    tag_key: str = Query("team", description="Tag key to analyze"),
    limit: int = Query(10, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> TopUntaggedResponse:
    """Get top subscriptions by untagged cost."""
    service = TopUntaggedService()
    return service.get_top_untagged_subscriptions(workspace_id, tag_key, limit, start_date, end_date)

@router.get("/tag-compliance-summary")
async def get_tag_compliance_summary(
    workspace_id: UUID,
    tag_keys: str = Query("team,environment,costcenter", description="Comma-separated tag keys"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[TagComplianceSummary]:
    """Get compliance summary for multiple tag keys."""
    service = TagComplianceService()
    keys = [k.strip() for k in tag_keys.split(",")]
    return [
        service.get_summary(workspace_id, key, start_date, end_date)
        for key in keys
    ]
```

### B.5 Frontend MVP Widget

```typescript
// frontend/src/components/Gov/TagComplianceWidget.tsx

interface TagComplianceWidgetProps {
  tagKey: string;
  title: string;
}

export function TagComplianceWidget({ tagKey, title }: TagComplianceWidgetProps) {
  const { data: coverage } = useQuery(
    ['tag-coverage', tagKey],
    () => govApi.getTagCoverage(tagKey)
  );
  
  const { data: untaggedCost } = useQuery(
    ['untagged-cost', tagKey],
    () => govApi.getUntaggedCost(tagKey)
  );
  
  const coverageColor = coverage?.coverage_percentage >= 90 
    ? 'text-emerald-600' 
    : coverage?.coverage_percentage >= 70 
    ? 'text-amber-600' 
    : 'text-red-600';
  
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold">{title}</h3>
      
      <div className="mt-4">
        <div className="flex justify-between items-center">
          <span className="text-gray-600">Coverage</span>
          <span className={`text-2xl font-bold ${coverageColor}`}>
            {coverage?.coverage_percentage.toFixed(1)}%
          </span>
        </div>
        
        <div className="mt-2 h-2 bg-gray-200 rounded-full">
          <div 
            className={`h-2 rounded-full ${
              coverage?.coverage_percentage >= 90 ? 'bg-emerald-500' :
              coverage?.coverage_percentage >= 70 ? 'bg-amber-500' : 'bg-red-500'
            }`}
            style={{ width: `${coverage?.coverage_percentage || 0}%` }}
          />
        </div>
        
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Tagged</div>
            <div className="font-semibold text-emerald-600">
              {coverage?.tagged_resources.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Untagged</div>
            <div className="font-semibold text-red-600">
              {coverage?.untagged_resources.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-gray-500">Untagged Cost</div>
            <div className="font-semibold text-red-600">
              {formatCurrency(untaggedCost?.untagged_cost || 0)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### B.6 Critérios de Aceite MVP

| Critério | Descrição | Validação |
|---------|-----------|-----------|
| **Tag Coverage API** | Retorna % de recursos com tag | Testar com team, environment, costcenter |
| **Untagged Cost API** | Retorna custo de recursos sem tag | Validar valores com ClickHouse |
| **Cost by Tag API** | Retorna breakdown por valor da tag | Verificar ordenação |
| **Top Untagged Subscriptions** | Retorna subscriptions ordenadas | Validar limites |
| **Dashboard Widget** | Mostra coverage e custo | UI test |
| **No Migration** | API funciona sem tabela nova | Confirmar que não cria tabela |
| **Read-Only** | Nenhum write path | Verificar que não há INSERT/UPDATE |
| **Performance** | Response time < 2s | Load test |

### B.7 Riscos MVP

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Tags não existem no ClickHouse** | 🟡 Média | 🟢 Baixo | API retorna 0%, graceful degradation |
| **Query performance** | 🟡 Média | 🟡 Médio | Indexes no ClickHouse, pagination |
| **Tag key não encontrado** | 🟡 Média | 🟢 Baixo | Retornar empty results |

### B.8 Rollback MVP

```bash
# Se algo der errado com MVP:
# Simply revert the code changes
git revert <commit-sha>

# Não há migration para reverter
# Não há tabela para drop
# Sistema volta ao estado anterior automaticamente
```

### B.9 Tempo Estimado MVP

| Fase | Descrição | Tempo |
|------|-----------|-------|
| **B.1** | Services + Schemas | 1-2 dias |
| **B.2** | Router + Endpoints | 1 dia |
| **B.3** | Frontend Widget | 1-2 dias |
| **B.4** | Integration Tests | 1 dia |
| **TOTAL** | | **4-6 dias** |

---

## RESTO DO DOCUMENTO - OPÇÃO A (FULL IMPLEMENTATION)

### 1.1 Tag Model

```python
# backend/app/domains/tags/models.py

class Tag(Base):
    """Tag definition for cost governance."""
    
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    # Tag identification
    name = Column(String(256), nullable=False)  # e.g., "Environment", "Team", "CostCenter"
    value = Column(String(256), nullable=False)  # e.g., "production", "engineering", "IT"
    
    # Metadata
    category = Column(String(128), nullable=True)  # e.g., "Environment", "Team", "Business"
    pattern = Column(String(512), nullable=True)  # Regex pattern for auto-capture
    is_required = Column(Boolean, default=False)  # Tag must be present
    is_system = Column(Boolean, default=False)  # System-generated tag
    
    # Governance
    compliance_threshold = Column(Float, default=0.0)  # Min % compliance required
    alert_on_missing = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="tags")
    resource_tags = relationship("ResourceTag", back_populates="tag", cascade="all, delete-orphan")
```

### 1.2 ResourceTag Model (Many-to-Many)

```python
class ResourceTag(Base):
    """Association between resources and tags."""
    
    __tablename__ = "resource_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Resource identification (from cloud provider)
    resource_id = Column(String(512), nullable=False)  # Azure resource ID
    provider = Column(String(32), nullable=False)  # azure, aws, gcp
    subscription_id = Column(String(128), nullable=True)
    
    # Tag reference
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False)
    
    # Metadata
    tag_source = Column(String(32), default="manual")  # manual, auto, imported
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tag = relationship("Tag", back_populates="resource_tags")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("resource_id", "tag_id", name="uq_resource_tag"),
        Index("ix_resource_tags_resource_id", "resource_id"),
        Index("ix_resource_tags_tag_id", "tag_id"),
    )
```

### 1.3 Tag Compliance Model

```python
class TagCompliance(Base):
    """Compliance metrics for tags."""
    
    __tablename__ = "tag_compliance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    # Tag reference
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True)
    
    # Metrics
    total_resources = Column(Integer, default=0)
    tagged_resources = Column(Integer, default=0)
    compliance_percentage = Column(Float, default=0.0)
    
    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    workspace = relationship("Workspace")
    tag = relationship("Tag")
```

### 1.4 Migration

```python
# backend/alembic/versions/XXXX_tags_framework.py

def upgrade():
    # Create tags table
    op.create_table(
        "tags",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False),
        Column("name", String(256), nullable=False),
        Column("value", String(256), nullable=False),
        Column("category", String(128), nullable=True),
        Column("pattern", String(512), nullable=True),
        Column("is_required", Boolean, default=False),
        Column("is_system", Boolean, default=False),
        Column("compliance_threshold", Float, default=0.0),
        Column("alert_on_missing", Boolean, default=True),
        Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
        Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index("ix_tags_workspace_id", "tags", ["workspace_id"])
    op.create_index("ix_tags_name", "tags", ["name"])
    
    # Create resource_tags table
    op.create_table(
        "resource_tags",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("resource_id", String(512), nullable=False),
        Column("provider", String(32), nullable=False),
        Column("subscription_id", String(128), nullable=True),
        Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False),
        Column("tag_source", String(32), default="manual"),
        Column("detected_at", DateTime, nullable=False, default=datetime.utcnow),
        Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
        Column("updated_at", DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
    )
    op.create_index("ix_resource_tags_resource_id", "resource_tags", ["resource_id"])
    op.create_index("ix_resource_tags_tag_id", "resource_tags", ["tag_id"])
    op.create_unique_constraint("uq_resource_tag", "resource_tags", ["resource_id", "tag_id"])
    
    # Create tag_compliance table
    op.create_table(
        "tag_compliance",
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False),
        Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True),
        Column("total_resources", Integer, default=0),
        Column("tagged_resources", Integer, default=0),
        Column("compliance_percentage", Float, default=0.0),
        Column("period_start", Date, nullable=False),
        Column("period_end", Date, nullable=False),
        Column("calculated_at", DateTime, nullable=False, default=datetime.utcnow),
    )
    op.create_index("ix_tag_compliance_workspace_id", "tag_compliance", ["workspace_id"])
    op.create_index("ix_tag_compliance_period", "tag_compliance", ["period_start", "period_end"])

def downgrade():
    op.drop_table("tag_compliance")
    op.drop_table("resource_tags")
    op.drop_table("tags")
```

---

## 2. APIS NECESSÁRIAS

### 2.1 Tags CRUD

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/tags` | GET | Listar tags do workspace |
| `/api/v1/tags` | POST | Criar nova tag |
| `/api/v1/tags/{id}` | GET | Obter tag por ID |
| `/api/v1/tags/{id}` | PUT | Atualizar tag |
| `/api/v1/tags/{id}` | DELETE | Deletar tag |

### 2.2 Resource Tags

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/resources/tags` | GET | Listar tags de recursos |
| `/api/v1/resources/tags` | POST | Associar tag a recurso |
| `/api/v1/resources/tags/{id}` | DELETE | Remover tag de recurso |
| `/api/v1/resources/untagged` | GET | Listar recursos sem tags |

### 2.3 Compliance

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/tags/compliance` | GET | Métricas de compliance |
| `/api/v1/tags/compliance/{tag_id}` | GET | Compliance por tag |
| `/api/v1/tags/patterns` | GET | Listar padrões |
| `/api/v1/tags/patterns` | POST | Criar padrão auto-capture |

### 2.4 Schema

```python
# backend/app/domains/tags/schemas.py

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List

class TagBase(BaseModel):
    name: str = Field(..., max_length=256)
    value: str = Field(..., max_length=256)
    category: Optional[str] = Field(None, max_length=128)
    pattern: Optional[str] = Field(None, max_length=512)
    is_required: bool = False
    is_system: bool = False
    compliance_threshold: float = 0.0
    alert_on_missing: bool = True

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    value: Optional[str] = Field(None, max_length=256)
    category: Optional[str] = Field(None, max_length=128)
    pattern: Optional[str] = Field(None, max_length=512)
    is_required: Optional[bool] = None
    compliance_threshold: Optional[float] = None
    alert_on_missing: Optional[bool] = None

class Tag(TagBase):
    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ResourceTagCreate(BaseModel):
    resource_id: str = Field(..., max_length=512)
    provider: str = Field(..., max_length=32)
    subscription_id: Optional[str] = Field(None, max_length=128)
    tag_id: UUID
    tag_source: str = "manual"

class ResourceTag(ResourceTagCreate):
    id: UUID
    detected_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TagComplianceResponse(BaseModel):
    tag_id: Optional[UUID]
    tag_name: Optional[str]
    total_resources: int
    tagged_resources: int
    compliance_percentage: float
    period_start: datetime
    period_end: datetime

class UntaggedResourceResponse(BaseModel):
    resource_id: str
    provider: str
    subscription_id: Optional[str]
    resource_type: Optional[str]
    resource_name: Optional[str]
    first_seen: Optional[datetime]
```

---

## 3. INTEGRAÇÃO COM CUSTOS

### 3.1 ClickHouse Query

```sql
-- Join cost_facts with resource_tags for tag-based cost allocation

SELECT 
    t.name as tag_name,
    t.value as tag_value,
    SUM(cf.cost_usd) as total_cost,
    COUNT(DISTINCT cf.resource_id) as resource_count
FROM cost_facts cf
LEFT JOIN resource_tags rt ON cf.resource_id = rt.resource_id
LEFT JOIN tags t ON rt.tag_id = t.id
WHERE cf.date >= '2026-06-01'
  AND cf.workspace_id = :workspace_id
GROUP BY t.name, t.value
ORDER BY total_cost DESC
```

### 3.2 Cost by Tag Endpoint

```python
# backend/app/domains/tags/service.py

class TagCostService:
    def get_cost_by_tags(
        self,
        workspace_id: UUID,
        start_date: date,
        end_date: date,
        tag_name: Optional[str] = None
    ) -> List[TagCostSummary]:
        """Get cost breakdown by tags."""
        
        query = f"""
        SELECT 
            t.name as tag_name,
            t.value as tag_value,
            SUM(cf.cost_usd) as total_cost,
            COUNT(DISTINCT cf.resource_id) as resource_count,
            AVG(cf.cost_usd) as avg_cost
        FROM cost_facts cf
        LEFT JOIN resource_tags rt ON cf.resource_id = rt.resource_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        WHERE cf.date >= '{start_date}'
          AND cf.date <= '{end_date}'
          AND cf.workspace_id = :workspace_id
        """
        
        if tag_name:
            query += f" AND t.name = '{tag_name}'"
        
        query += " GROUP BY t.name, t.value ORDER BY total_cost DESC"
        
        return self.clickhouse_client.query(query)
```

---

## 4. INTEGRAÇÃO COM COST ALLOCATION

### 4.1 Allocation Rules

```python
class CostAllocationRule(Base):
    """Rule for allocating costs based on tags."""
    
    __tablename__ = "cost_allocation_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    # Rule definition
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    
    # Tag-based allocation
    tag_name = Column(String(128), nullable=False)  # e.g., "Team"
    tag_value = Column(String(256), nullable=True)  # e.g., "Engineering"
    
    # Allocation target
    allocation_type = Column(String(32), nullable=False)  # team, project, department
    allocation_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Percentage
    allocation_percentage = Column(Float, default=100.0)
    
    # Active
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### 4.2 Integration Flow

```
Tag Created
    ↓
Tag Associated to Resource
    ↓
Cost Ingestion
    ↓
Cost Allocation Rules Applied
    ↓
Costs Segmented by Tag
    ↓
Dashboard Shows Costs by Tag
```

---

## 5. INTEGRAÇÃO COM UNTAGGED RESOURCES

### 5.1 Detection Logic

```python
# backend/app/domains/tags/service.py

class UntaggedResourcesService:
    def detect_untagged(
        self,
        workspace_id: UUID,
        required_tags: List[str]
    ) -> List[UntaggedResource]:
        """Detect resources without required tags."""
        
        # Get all resources from cost_facts
        resources = self.get_all_resources(workspace_id)
        
        # Get tags for each resource
        tagged_resource_ids = self.get_tagged_resource_ids(workspace_id)
        
        # Filter untagged
        untagged = []
        for resource in resources:
            if resource.id not in tagged_resource_ids:
                untagged.append(resource)
        
        return untagged
    
    def calculate_compliance(
        self,
        workspace_id: UUID
    ) -> TagCompliance:
        """Calculate tag compliance percentage."""
        
        total = self.count_resources(workspace_id)
        tagged = self.count_tagged_resources(workspace_id)
        
        compliance = (tagged / total * 100) if total > 0 else 0
        
        return TagCompliance(
            workspace_id=workspace_id,
            total_resources=total,
            tagged_resources=tagged,
            compliance_percentage=compliance
        )
```

### 5.2 Alert on Missing Tag

```python
# Worker: tag_compliance_worker.py

class TagComplianceWorker:
    def check_untagged_alerts(self):
        """Check for new untagged resources and send alerts."""
        
        workspace = get_current_workspace()
        
        # Get tags with alert_on_missing=True
        required_tags = self.tag_service.get_required_tags(workspace.id)
        
        # Detect untagged
        untagged = self.untagged_service.detect_untagged(
            workspace.id,
            [t.name for t in required_tags]
        )
        
        # Send alert if new untagged found
        if untagged:
            self.notification_service.send_alert(
                workspace=workspace,
                alert_type="untagged_resources",
                data={
                    "count": len(untagged),
                    "tags": [t.name for t in required_tags],
                    "resources": [r.id for r in untagged[:10]]  # First 10
                }
            )
```

---

## 6. INTEGRAÇÃO COM GOVERNANCE

### 6.1 Governance Rules

```python
# backend/app/domains/tags/governance.py

class TagGovernance:
    """Governance rules for tags."""
    
    def enforce_required_tags(
        self,
        workspace_id: UUID,
        resource_id: str
    ) -> GovernanceResult:
        """Check if resource has required tags."""
        
        required_tags = self.tag_service.get_required_tags(workspace_id)
        resource_tags = self.tag_service.get_resource_tags(resource_id)
        
        missing_tags = []
        for required in required_tags:
            if not any(t.name == required.name for t in resource_tags):
                missing_tags.append(required)
        
        if missing_tags:
            return GovernanceResult(
                compliant=False,
                violations=[
                    f"Missing required tag: {t.name}" 
                    for t in missing_tags
                ]
            )
        
        return GovernanceResult(compliant=True, violations=[])
```

### 6.2 Compliance Dashboard

```python
# frontend/src/pages/Gov/CompliancePanel.tsx

interface TagComplianceMetrics {
    overallCompliance: number;  // 0-100
    totalResources: number;
    taggedResources: number;
    untaggedResources: number;
    complianceByTag: TagCompliance[];
    complianceBySubscription: SubscriptionCompliance[];
}
```

---

## 7. DEPENDÊNCIAS

### 7.1 Dependências Internas

| Dependência | Tipo | Descrição |
|-------------|------|-----------|
| **Workspaces** | ✅ Existente | Workspace model já existe |
| **Auth** | ✅ Existente | Autenticação já existe |
| **Cloud Accounts** | ✅ Existente | Subscription context |
| **Cost Facts** | ✅ Existente | ClickHouse queries |
| **Notifications** | ✅ Existente | Alert system |

### 7.2 Dependências Externas

| Dependência | Tipo | Descrição |
|-------------|------|-----------|
| **Azure Resource Graph** | ⚠️ Necessário | Para descobrir recursos |
| **Azure Cost Management** | ⚠️ Necessário | Para custos |
| **AWS Cost Explorer** | ⚠️ Planejado | Para AWS (Futuro) |
| **GCP BigQuery** | ⚠️ Planejado | Para GCP (Futuro) |

### 7.3 Dependências de Features

```
Tags Framework
    ↓ (depende de)
├── Workspaces ✅
├── Auth ✅
└── Database migrations ❌ (Alembic - em análise)
    ↓ (bloqueia)
├── Untagged Resources
├── Cost Allocation
├── Teams
├── Budget Alerts
└── Anomaly Alerts
```

---

## 8. RISCOS

### 8.1 Riscos de Implementação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Alembic não funcionar** | 🟡 Média | 🔴 Crítico | Usar existing migrations como reference |
| **Performance query** | 🟡 Média | 🟡 Médio | Indexes em resource_id, tag_id |
| **Duplicação de tags** | 🟡 Média | 🟡 Médio | Unique constraint + validation |
| **Sincronização com cloud** | 🟡 Média | 🟡 Médio | Async worker + retry logic |

### 8.2 Riscos Operacionais

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Tags não detectados** | 🟡 Média | 🟡 Médio | Manual override option |
| **Compliance falso** | 🟢 Baixa | 🟡 Médio | Multiple data sources |
| **Performance degradação** | 🟢 Baixa | 🟡 Médio | Caching + pagination |

---

## 9. CRITÉRIOS DE ACEITE

### 9.1 Funcionalidade

| Critério | Descrição | Validação |
|---------|-----------|-----------|
| **CRUD Tags** | Criar, ler, atualizar, deletar tags | UI + API tests |
| **Associar Tags** | Associar tags a recursos | Manual + API tests |
| **Detectar Untagged** | Listar recursos sem tags | Query validation |
| **Compliance Metrics** | Calcular % de compliance | Dashboard verification |
| **Cost by Tag** | Mostrar custos por tag | ClickHouse query validation |

### 9.2 Performance

| Critério | Descrição | Target |
|---------|-----------|--------|
| **List Tags** | Response time | < 500ms |
| **Compliance Query** | Response time | < 2s |
| **Cost by Tag** | Response time | < 5s |

### 9.3 Testes

| Teste | Descrição |
|-------|-----------|
| **Unit Tests** | Tag service, models |
| **Integration Tests** | API endpoints |
| **E2E Tests** | Full flow (create tag → associate → view compliance) |

---

## 10. PLANO DE TESTES

### 10.1 Testes Unitários

```python
# backend/tests/unit/test_tags_service.py

class TestTagService:
    def test_create_tag(self):
        """Test tag creation."""
        pass
    
    def test_delete_tag_cascades(self):
        """Test tag deletion removes resource associations."""
        pass
    
    def test_compliance_calculation(self):
        """Test compliance percentage calculation."""
        pass
    
    def test_untagged_detection(self):
        """Test untagged resources detection."""
        pass
```

### 10.2 Testes de Integração

```python
# backend/tests/integration/test_tags_api.py

class TestTagsAPI:
    def test_list_tags(self):
        """Test GET /api/v1/tags"""
        pass
    
    def test_create_tag(self):
        """Test POST /api/v1/tags"""
        pass
    
    def test_associate_tag_to_resource(self):
        """Test POST /api/v1/resources/tags"""
        pass
    
    def test_get_untagged_resources(self):
        """Test GET /api/v1/resources/untagged"""
        pass
    
    def test_get_compliance(self):
        """Test GET /api/v1/tags/compliance"""
        pass
```

### 10.3 Testes E2E

```typescript
// frontend/tests/e2e/tags.spec.ts

describe('Tags Framework E2E', () => {
  it('should create tag and associate to resource', async () => {
    // 1. Login
    // 2. Navigate to Tags
    // 3. Create new tag
    // 4. Associate tag to resource
    // 5. Verify compliance updated
    // 6. Verify cost by tag shows data
  });
});
```

---

## 11. IMPLEMENTAÇÃO PLANEJADA

### 11.1 Fases de Implementação

| Fase | Descrição | Tempo |
|------|-----------|-------|
| **1.1** | Migration + Models | 1-2 dias |
| **1.2** | Tags CRUD API + Service | 2-3 dias |
| **1.3** | Resource Tags API | 1-2 dias |
| **1.4** | Compliance Service | 1-2 dias |
| **1.5** | Untagged Detection | 1 dia |
| **1.6** | Frontend UI | 2-3 dias |
| **1.7** | Integration Tests | 1-2 dias |
| **TOTAL** | | **9-15 dias** |

### 11.2 ordem de Implementação

```
Semana 1:
├── Dia 1-2: Migration + Models
├── Dia 3-5: Tags CRUD API + Service

Semana 2:
├── Dia 6-7: Resource Tags API
├── Dia 8-9: Compliance Service
├── Dia 10: Untagged Detection

Semana 3:
├── Dia 11-12: Frontend UI
├── Dia 13-14: Integration Tests + Staging
```

---

## 12. ROLLBACK

### 12.1 Estratégia de Rollback

```bash
# Se algo der errado:
git revert <commit-sha>

# Migration rollback:
alembic downgrade -1

# Verificar rollback:
alembic current
```

### 12.2 Checkpoints

| Checkpoint | Descrição |
|-----------|-----------|
| **After Migration** | `alembic current` mostra nova versão |
| **After CRUD API** | API responds correctly |
| **After Integration** | Full flow working |

---

## 13. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `docs/roadmap/finops-alignment-roadmap.md` | Roadmap completo |
| `docs/baseline/production-baseline-2026-06.md` | Baseline atual |
| `docs/technical-tasks/alembic-priority-assessment.md` | Priorização |
| `CLAUDE.md` | Regras de engenharia |

---

## 14. HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

**FIM DO DOCUMENTO**

Este documento é design técnico para implementação futura. Nenhuma implementação deve ser feita sem aprovação explícita e seguindo o fluxo:  
**Diagnóstico → Plano → Diff → Teste Local → Staging → Validação → Aprovação → Produção**