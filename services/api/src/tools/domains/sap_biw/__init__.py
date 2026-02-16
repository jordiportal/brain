"""
SAP BIW Tools - Business Intelligence Warehouse integration

Cada herramienta BIW sigue un patron de "delegacion con fallback":
  1. Busca una herramienta OpenAPI real en el tool_registry
     (conexion remota SAP via RFC/OData configurada en Tools > OpenAPI)
  2. Si la encuentra, delega la ejecucion al endpoint real
  3. Si no, usa la implementacion mock parametrica local

Esto permite:
  - Desarrollo/demo sin SAP real (mocks parametricos)
  - Produccion con SAP real (OpenAPI connection activa)
  - Transicion transparente: mismos IDs de tools, mismo flujo del agente
"""

import random
import hashlib
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()

# Prefijos de slug conocidos para conexiones SAP OpenAPI
_SAP_SLUGS = ["sap_btp_gateway", "sap_gateway", "sap_biw", "sap_odata", "sap"]


async def _try_openapi_delegate(biw_tool_name: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Intenta delegar la ejecucion a una tool OpenAPI real registrada en el registry.
    
    Busca una tool OpenAPI cuyo ID coincida con el patron:
      {sap_slug}_{biw_tool_name}  (ej: sap_btp_gateway_biw_get_cube_data)
    o:
      {sap_slug}_{operation_id}   donde operation_id mapea al biw_tool_name
    
    Args:
        biw_tool_name: Nombre de la tool BIW (ej: "biw_get_cube_data")
        **kwargs: Parametros a pasar a la tool OpenAPI
    
    Returns:
        Resultado de la tool OpenAPI si se encontro y ejecuto exitosamente.
        None si no hay tool OpenAPI disponible (= usar mock).
    """
    try:
        from ...tool_registry import tool_registry, ToolType
        
        # Buscar tool OpenAPI con cualquiera de los prefijos SAP conocidos
        for slug in _SAP_SLUGS:
            # Patron 1: {slug}_{biw_tool_name} (ej: sap_btp_gateway_biw_get_cube_data)
            candidate_id = f"{slug}_{biw_tool_name}"
            tool = tool_registry.get(candidate_id)
            
            if tool and tool.type == ToolType.OPENAPI and tool.handler:
                logger.info(
                    f"📡 BIW delegating to OpenAPI: {candidate_id}",
                    biw_tool=biw_tool_name, params=list(kwargs.keys())
                )
                result = await tool.handler(**kwargs)
                
                if isinstance(result, dict) and result.get("success"):
                    logger.info(f"✅ OpenAPI delegation successful: {candidate_id}")
                    return result
                elif isinstance(result, dict) and result.get("error"):
                    logger.warning(
                        f"⚠️ OpenAPI tool returned error, falling back to mock: {result.get('error')}",
                        tool=candidate_id
                    )
                    return None
                else:
                    return result
        
        # Patron 2: Buscar por nombre parcial en todas las tools OpenAPI
        for tool in tool_registry.list(ToolType.OPENAPI):
            # Buscar si el tool_id contiene el nombre BIW (ej: ..._get_cube_data)
            # Eliminar el prefijo "biw_" para buscar mas ampliamente
            short_name = biw_tool_name.replace("biw_", "")
            if short_name in tool.id and tool.handler:
                logger.info(
                    f"📡 BIW delegating to OpenAPI (partial match): {tool.id}",
                    biw_tool=biw_tool_name
                )
                result = await tool.handler(**kwargs)
                if isinstance(result, dict) and result.get("success"):
                    return result
                return None
        
        # No se encontro ninguna tool OpenAPI
        return None
        
    except ImportError:
        # Si no se puede importar el registry (ej: test aislado), usar mock
        return None
    except Exception as e:
        logger.warning(f"⚠️ Error in OpenAPI delegation for {biw_tool_name}: {e}")
        return None


def _seed_from(text: str) -> int:
    """Genera una seed determinista a partir de un texto para datos reproducibles."""
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _generate_mock_rows(
    cube_name: str,
    characteristics: Optional[List[str]] = None,
    key_figures: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    num_rows: int = 5
) -> List[Dict[str, Any]]:
    """
    Genera filas de datos mock parametrizadas según los inputs.
    Las características y key_figures se usan como columnas.
    Los valores se generan pseudo-aleatoriamente pero deterministas por cube_name.
    """
    rng = random.Random(_seed_from(cube_name))
    
    chars = characteristics or ["region", "category"]
    kfs = key_figures or ["amount", "quantity"]
    
    # Valores posibles por tipo de característica (heurísticos)
    char_values: Dict[str, List[str]] = {
        "region": ["Norte", "Sur", "Este", "Oeste", "Centro"],
        "country": ["España", "Francia", "Alemania", "Italia", "Portugal"],
        "product": ["P001", "P002", "P003", "P004", "P005"],
        "product_group": ["Electrónica", "Textil", "Alimentación", "Industrial", "Servicios"],
        "category": ["Cat-A", "Cat-B", "Cat-C", "Cat-D"],
        "customer": ["C001", "C002", "C003", "C004", "C005"],
        "year": ["2022", "2023", "2024", "2025"],
        "quarter": ["Q1", "Q2", "Q3", "Q4"],
        "month": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
        "department": ["Ventas", "Compras", "Producción", "Logística", "RRHH"],
        "plant": ["Planta-1000", "Planta-2000", "Planta-3000"],
        "material": ["MAT-100", "MAT-200", "MAT-300", "MAT-400"],
        "vendor": ["Proveedor-A", "Proveedor-B", "Proveedor-C"],
        "sales_org": ["SO-1000", "SO-2000", "SO-3000"],
        "division": ["División-01", "División-02", "División-03"],
        "channel": ["Online", "Retail", "Distribuidores", "Directo"],
        "cost_center": ["CC-1000", "CC-2000", "CC-3000", "CC-4000"],
        "profit_center": ["PC-100", "PC-200", "PC-300"],
        "employee": ["EMP-001", "EMP-002", "EMP-003", "EMP-004", "EMP-005"],
    }
    
    # Para características desconocidas, generar valores genéricos
    def get_char_values(char_name: str) -> List[str]:
        key = char_name.lower().replace(" ", "_")
        if key in char_values:
            return char_values[key]
        # Genérico basado en el nombre
        return [f"{char_name}-{i+1}" for i in range(5)]
    
    rows = []
    for i in range(num_rows):
        row: Dict[str, Any] = {}
        
        # Generar valor para cada característica
        for char in chars:
            # Respetar filtros si los hay
            if filters and char in filters:
                row[char] = filters[char]
            else:
                values = get_char_values(char)
                row[char] = rng.choice(values)
        
        # Generar valor para cada key figure
        for kf in kfs:
            kf_lower = kf.lower()
            if any(w in kf_lower for w in ["amount", "sales", "revenue", "ventas", "importe"]):
                row[kf] = round(rng.uniform(10000, 500000), 2)
            elif any(w in kf_lower for w in ["cost", "coste", "gasto", "expense"]):
                row[kf] = round(rng.uniform(5000, 300000), 2)
            elif any(w in kf_lower for w in ["margin", "margen", "profit", "beneficio"]):
                row[kf] = round(rng.uniform(1000, 150000), 2)
            elif any(w in kf_lower for w in ["quantity", "cantidad", "qty", "units", "unidades"]):
                row[kf] = rng.randint(10, 5000)
            elif any(w in kf_lower for w in ["percent", "ratio", "rate", "porcentaje", "tasa"]):
                row[kf] = round(rng.uniform(1, 99), 1)
            elif any(w in kf_lower for w in ["count", "numero", "number"]):
                row[kf] = rng.randint(1, 1000)
            elif any(w in kf_lower for w in ["price", "precio"]):
                row[kf] = round(rng.uniform(5, 5000), 2)
            elif any(w in kf_lower for w in ["weight", "peso"]):
                row[kf] = round(rng.uniform(0.1, 1000), 2)
            elif any(w in kf_lower for w in ["hours", "horas"]):
                row[kf] = round(rng.uniform(1, 200), 1)
            else:
                row[kf] = round(rng.uniform(100, 100000), 2)
        
        rows.append(row)
    
    return rows


async def biw_get_cube_data(
    cube_name: str,
    characteristics: Optional[List[str]] = None,
    key_figures: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    drilldown: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Extrae datos de un InfoCube (cubo OLAP) de SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Extracting cube data: {cube_name}", 
                chars=characteristics, kfs=key_figures, filters=filters)
    
    # Intentar delegacion a OpenAPI real
    real_result = await _try_openapi_delegate(
        "biw_get_cube_data",
        cube_name=cube_name, characteristics=characteristics,
        key_figures=key_figures, filters=filters, drilldown=drilldown
    )
    if real_result is not None:
        return real_result
    
    # Fallback: mock parametrico
    chars = characteristics or drilldown or ["region", "period"]
    kfs = key_figures or ["amount", "quantity"]
    rows = _generate_mock_rows(cube_name, chars, kfs, filters, num_rows=6)
    
    return {
        "success": True,
        "cube_name": cube_name,
        "source": "mock",
        "data": {
            "rows": rows,
            "metadata": {
                "total_rows": len(rows),
                "characteristics_used": chars,
                "key_figures_used": kfs,
                "filters_applied": filters or {}
            }
        }
    }


async def biw_get_dso_data(
    dso_name: str,
    fields: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    max_rows: int = 1000
) -> Dict[str, Any]:
    """
    Extrae datos de un DataStore Object (DSO) de SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Extracting DSO data: {dso_name}", fields=fields, filters=filters)
    
    real_result = await _try_openapi_delegate(
        "biw_get_dso_data",
        dso_name=dso_name, fields=fields, filters=filters, max_rows=max_rows
    )
    if real_result is not None:
        return real_result
    
    rng = random.Random(_seed_from(dso_name))
    resolved_fields = fields or ["id", "name", "category", "value"]
    num_rows = min(max_rows, 6)
    
    rows = []
    for i in range(num_rows):
        row: Dict[str, Any] = {}
        for field in resolved_fields:
            fl = field.lower()
            if filters and field in filters:
                row[field] = filters[field]
            elif any(w in fl for w in ["id", "code", "key", "numero"]):
                row[field] = f"{field.upper()[:3]}-{rng.randint(1000, 9999)}"
            elif any(w in fl for w in ["name", "nombre", "description", "text"]):
                prefixes = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
                row[field] = f"{rng.choice(prefixes)} {rng.choice(['Corp', 'SL', 'SA', 'GmbH', 'Ltd'])}"
            elif any(w in fl for w in ["city", "ciudad"]):
                row[field] = rng.choice(["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao", "Zaragoza"])
            elif any(w in fl for w in ["country", "pais"]):
                row[field] = rng.choice(["ES", "FR", "DE", "IT", "PT", "UK"])
            elif any(w in fl for w in ["region", "zone", "area"]):
                row[field] = rng.choice(["Norte", "Sur", "Este", "Oeste", "Centro"])
            elif any(w in fl for w in ["department", "depart", "dept"]):
                row[field] = rng.choice(["Ventas", "Compras", "Producción", "Logística", "RRHH", "Finanzas", "IT"])
            elif any(w in fl for w in ["status", "estado"]):
                row[field] = rng.choice(["Activo", "Inactivo", "Pendiente", "Bloqueado"])
            elif any(w in fl for w in ["date", "fecha"]):
                row[field] = f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
            elif any(w in fl for w in ["salary", "sueldo", "wage"]):
                row[field] = round(rng.uniform(25000, 85000), 2)
            elif any(w in fl for w in ["amount", "sales", "value", "importe", "total"]):
                row[field] = round(rng.uniform(1000, 500000), 2)
            elif any(w in fl for w in ["quantity", "qty", "cantidad"]):
                row[field] = rng.randint(1, 5000)
            elif any(w in fl for w in ["email", "correo"]):
                row[field] = f"contact{rng.randint(1,99)}@example.com"
            elif any(w in fl for w in ["phone", "telefono"]):
                row[field] = f"+34 {rng.randint(600,699)} {rng.randint(100,999)} {rng.randint(100,999)}"
            else:
                row[field] = f"{field}-{rng.randint(1, 100)}"
        rows.append(row)
    
    return {
        "success": True,
        "dso_name": dso_name,
        "source": "mock",
        "data": {
            "rows": rows,
            "metadata": {
                "total_rows": len(rows),
                "fields": resolved_fields,
                "filters_applied": filters or {}
            }
        }
    }


async def biw_get_bex_query(
    query_name: str,
    variables: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Ejecuta una query BEx (Business Explorer) de SAP.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Executing BEx query: {query_name}", variables=variables, filters=filters)
    
    real_result = await _try_openapi_delegate(
        "biw_get_bex_query",
        query_name=query_name, variables=variables, filters=filters
    )
    if real_result is not None:
        return real_result
    
    rng = random.Random(_seed_from(query_name))
    
    # Inferir columnas de la query a partir del nombre
    qn = query_name.lower()
    if any(w in qn for w in ["sales", "ventas", "revenue"]):
        cols = ["period", "sales_amount", "quantity", "avg_price", "margin"]
    elif any(w in qn for w in ["cost", "coste", "expense", "gasto"]):
        cols = ["period", "cost_amount", "budget", "variance", "variance_pct"]
    elif any(w in qn for w in ["stock", "inventory", "inventario"]):
        cols = ["material", "plant", "stock_qty", "stock_value", "reorder_point"]
    elif any(w in qn for w in ["customer", "cliente"]):
        cols = ["customer", "region", "revenue", "orders", "avg_order_value"]
    elif any(w in qn for w in ["hr", "employee", "personal"]):
        cols = ["department", "headcount", "avg_salary", "overtime_hours", "turnover_rate"]
    elif any(w in qn for w in ["production", "produccion", "manufacturing"]):
        cols = ["plant", "product", "produced_qty", "defect_rate", "efficiency"]
    elif any(w in qn for w in ["profit", "pnl", "beneficio"]):
        cols = ["period", "revenue", "costs", "gross_profit", "net_profit"]
    else:
        cols = ["dimension", "measure_1", "measure_2", "measure_3"]
    
    periods = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024", "Q1 2025", "Q2 2025"]
    departments = ["Ventas", "Compras", "Producción", "Logística", "RRHH", "IT"]
    materials = ["MAT-100", "MAT-200", "MAT-300", "MAT-400", "MAT-500", "MAT-600"]
    customers = ["Cliente Alpha", "Cliente Beta", "Cliente Gamma", "Cliente Delta", "Cliente Epsilon", "Cliente Zeta"]
    plants = ["Planta-1000", "Planta-2000", "Planta-3000", "Planta-1000", "Planta-2000", "Planta-3000"]
    products = ["Producto-A", "Producto-B", "Producto-C", "Producto-D", "Producto-E", "Producto-F"]
    
    rows = []
    for i in range(min(6, len(periods))):
        row: Dict[str, Any] = {}
        for col in cols:
            cl = col.lower()
            if any(w in cl for w in ["period", "quarter"]) or cl == "time":
                row[col] = periods[i]
            elif any(w in cl for w in ["dimension"]):
                row[col] = f"Dim-{i+1}"
            elif any(w in cl for w in ["department", "dept"]):
                row[col] = departments[i % len(departments)]
            elif any(w in cl for w in ["material"]):
                row[col] = materials[i % len(materials)]
            elif any(w in cl for w in ["customer", "client"]):
                row[col] = customers[i % len(customers)]
            elif any(w in cl for w in ["plant", "planta"]):
                row[col] = plants[i % len(plants)]
            elif any(w in cl for w in ["product", "producto"]):
                row[col] = products[i % len(products)]
            elif any(w in cl for w in ["pct", "rate", "efficiency", "turnover", "defect"]):
                row[col] = round(rng.uniform(1, 50), 1)
            elif any(w in cl for w in ["qty", "quantity", "headcount", "orders", "count"]):
                row[col] = rng.randint(10, 5000)
            elif any(w in cl for w in ["hours", "horas", "overtime"]):
                row[col] = round(rng.uniform(10, 200), 1)
            elif any(w in cl for w in ["salary", "sueldo", "avg_salary"]):
                row[col] = round(rng.uniform(25000, 85000), 2)
            elif any(w in cl for w in ["point"]):
                row[col] = rng.randint(50, 500)
            else:
                row[col] = round(rng.uniform(10000, 500000), 2)
        rows.append(row)
    
    return {
        "success": True,
        "query_name": query_name,
        "source": "mock",
        "data": {
            "results": rows,
            "metadata": {
                "query_name": query_name,
                "variables_applied": variables or {},
                "filters_applied": filters or {},
                "columns": cols
            }
        }
    }


async def biw_get_master_data(
    object_name: str,
    attributes: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Obtiene datos maestros (Master Data) de SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Getting master data: {object_name}", attributes=attributes, filters=filters)
    
    real_result = await _try_openapi_delegate(
        "biw_get_master_data",
        object_name=object_name, attributes=attributes, filters=filters
    )
    if real_result is not None:
        return real_result
    
    rng = random.Random(_seed_from(object_name))
    attrs = attributes or ["name", "city", "country", "status"]
    
    records = []
    for i in range(5):
        key = f"{object_name[:3].upper()}-{rng.randint(1000, 9999)}"
        attr_values: Dict[str, Any] = {}
        for attr in attrs:
            al = attr.lower()
            if any(w in al for w in ["name", "nombre"]):
                names = ["Alpha Corp", "Beta SL", "Gamma SA", "Delta GmbH", "Epsilon Ltd"]
                attr_values[attr] = names[i % len(names)]
            elif any(w in al for w in ["city", "ciudad"]):
                attr_values[attr] = rng.choice(["Madrid", "Barcelona", "Valencia", "Sevilla", "Bilbao"])
            elif any(w in al for w in ["country", "pais"]):
                attr_values[attr] = rng.choice(["ES", "FR", "DE", "IT", "PT"])
            elif any(w in al for w in ["status", "estado"]):
                attr_values[attr] = rng.choice(["Activo", "Inactivo", "Pendiente"])
            elif any(w in al for w in ["type", "tipo", "category", "grupo"]):
                attr_values[attr] = rng.choice(["Tipo-A", "Tipo-B", "Tipo-C"])
            elif any(w in al for w in ["email", "correo"]):
                attr_values[attr] = f"info{rng.randint(1,50)}@example.com"
            elif any(w in al for w in ["phone", "tel"]):
                attr_values[attr] = f"+34 {rng.randint(600,699)} {rng.randint(100,999)} {rng.randint(100,999)}"
            else:
                attr_values[attr] = f"{attr}-{rng.randint(1, 100)}"
        
        records.append({"key": key, "attributes": attr_values})
    
    return {
        "success": True,
        "object_name": object_name,
        "source": "mock",
        "data": {
            "records": records,
            "metadata": {
                "total_records": len(records),
                "attributes": attrs,
                "filters_applied": filters or {}
            }
        }
    }


async def biw_get_hierarchy(
    hierarchy_name: str,
    level: Optional[int] = None,
    node: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtiene una jerarquía (Hierarchy) de SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Getting hierarchy: {hierarchy_name}", level=level, node=node)
    
    real_result = await _try_openapi_delegate(
        "biw_get_hierarchy",
        hierarchy_name=hierarchy_name, level=level, node=node
    )
    if real_result is not None:
        return real_result
    
    # Inferir tipo de jerarquía del nombre
    hn = hierarchy_name.lower()
    if any(w in hn for w in ["region", "geo", "territory"]):
        nodes = [
            {"id": "1", "parent_id": None, "name": "Global", "level": 0},
            {"id": "2", "parent_id": "1", "name": "Europa", "level": 1},
            {"id": "3", "parent_id": "1", "name": "América", "level": 1},
            {"id": "4", "parent_id": "2", "name": "España", "level": 2},
            {"id": "5", "parent_id": "2", "name": "Francia", "level": 2},
            {"id": "6", "parent_id": "3", "name": "EEUU", "level": 2},
            {"id": "7", "parent_id": "4", "name": "Madrid", "level": 3},
            {"id": "8", "parent_id": "4", "name": "Barcelona", "level": 3},
        ]
    elif any(w in hn for w in ["product", "material", "article"]):
        nodes = [
            {"id": "1", "parent_id": None, "name": "Todos los productos", "level": 0},
            {"id": "2", "parent_id": "1", "name": "Categoría A", "level": 1},
            {"id": "3", "parent_id": "1", "name": "Categoría B", "level": 1},
            {"id": "4", "parent_id": "2", "name": "Subcategoría A1", "level": 2},
            {"id": "5", "parent_id": "2", "name": "Subcategoría A2", "level": 2},
            {"id": "6", "parent_id": "3", "name": "Subcategoría B1", "level": 2},
        ]
    elif any(w in hn for w in ["org", "company", "department"]):
        nodes = [
            {"id": "1", "parent_id": None, "name": "Corporación", "level": 0},
            {"id": "2", "parent_id": "1", "name": "Dirección General", "level": 1},
            {"id": "3", "parent_id": "1", "name": "Operaciones", "level": 1},
            {"id": "4", "parent_id": "2", "name": "Finanzas", "level": 2},
            {"id": "5", "parent_id": "2", "name": "RRHH", "level": 2},
            {"id": "6", "parent_id": "3", "name": "Producción", "level": 2},
            {"id": "7", "parent_id": "3", "name": "Logística", "level": 2},
        ]
    else:
        nodes = [
            {"id": "1", "parent_id": None, "name": f"{hierarchy_name} - Root", "level": 0},
            {"id": "2", "parent_id": "1", "name": "Nodo-A", "level": 1},
            {"id": "3", "parent_id": "1", "name": "Nodo-B", "level": 1},
            {"id": "4", "parent_id": "2", "name": "Nodo-A1", "level": 2},
            {"id": "5", "parent_id": "3", "name": "Nodo-B1", "level": 2},
        ]
    
    # Filtrar por nivel si se especifica
    if level is not None:
        nodes = [n for n in nodes if n["level"] <= level]
    
    # Filtrar por nodo padre si se especifica
    if node:
        parent = next((n for n in nodes if n["name"] == node or n["id"] == node), None)
        if parent:
            pid = parent["id"]
            nodes = [parent] + [n for n in nodes if n.get("parent_id") == pid]
    
    max_level = max((n["level"] for n in nodes), default=0)
    
    return {
        "success": True,
        "hierarchy_name": hierarchy_name,
        "source": "mock",
        "data": {
            "nodes": nodes,
            "metadata": {
                "total_nodes": len(nodes),
                "max_level": max_level
            }
        }
    }


async def biw_get_texts(
    object_name: str,
    language: str = "ES",
    keys: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Obtiene textos descriptivos de objetos SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Getting texts for: {object_name} (lang: {language})")
    
    real_result = await _try_openapi_delegate(
        "biw_get_texts",
        object_name=object_name, language=language, keys=keys
    )
    if real_result is not None:
        return real_result
    
    rng = random.Random(_seed_from(object_name + language))
    
    resolved_keys = keys or [f"K{rng.randint(100,999)}" for _ in range(4)]
    
    texts = []
    for key in resolved_keys:
        base = f"{object_name.replace('Z', '').replace('_', ' ').title()} {key}"
        texts.append({
            "key": key,
            "short_text": base[:20],
            "medium_text": base,
            "long_text": f"{base} - Descripción completa ({language})"
        })
    
    return {
        "success": True,
        "object_name": object_name,
        "language": language,
        "source": "mock",
        "data": {
            "texts": texts,
            "metadata": {
                "total_texts": len(texts),
                "language": language
            }
        }
    }


async def biw_get_ratios(
    cube_name: str,
    calculated_key_figures: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Obtiene ratios y Key Figures calculados (Calculated KFs) de SAP BW.
    Delega a OpenAPI SAP si hay conexión configurada, o usa mock como fallback.
    """
    logger.info(f"📊 Getting ratios for cube: {cube_name}", ckfs=calculated_key_figures)
    
    real_result = await _try_openapi_delegate(
        "biw_get_ratios",
        cube_name=cube_name, calculated_key_figures=calculated_key_figures, context=context
    )
    if real_result is not None:
        return real_result
    
    rng = random.Random(_seed_from(cube_name))
    
    # Generar ratios basados en los solicitados o defaults
    requested = calculated_key_figures or ["margin_percent", "growth_yoy", "avg_order_value"]
    
    ratio_templates = {
        "margin_percent": ("(revenue - costs) / revenue * 100", lambda r: round(r.uniform(15, 55), 1)),
        "growth_yoy": ("(current_year - previous_year) / previous_year * 100", lambda r: round(r.uniform(-10, 35), 1)),
        "avg_order_value": ("total_revenue / order_count", lambda r: round(r.uniform(200, 5000), 2)),
        "conversion_rate": ("orders / visits * 100", lambda r: round(r.uniform(1, 15), 1)),
        "return_rate": ("returns / sales * 100", lambda r: round(r.uniform(1, 12), 1)),
        "inventory_turnover": ("cogs / avg_inventory", lambda r: round(r.uniform(2, 20), 1)),
        "customer_lifetime_value": ("avg_revenue * avg_retention_years", lambda r: round(r.uniform(500, 50000), 2)),
        "roi": ("(gain - investment) / investment * 100", lambda r: round(r.uniform(5, 150), 1)),
        "cost_per_unit": ("total_costs / total_units", lambda r: round(r.uniform(5, 500), 2)),
        "productivity": ("output / labor_hours", lambda r: round(r.uniform(10, 200), 1)),
    }
    
    ratios = []
    for name in requested:
        nl = name.lower().replace(" ", "_")
        if nl in ratio_templates:
            formula, gen = ratio_templates[nl]
            ratios.append({"name": name, "value": gen(rng), "formula": formula})
        else:
            ratios.append({
                "name": name,
                "value": round(rng.uniform(1, 100), 2),
                "formula": f"calculated({name})"
            })
    
    return {
        "success": True,
        "cube_name": cube_name,
        "source": "mock",
        "data": {
            "ratios": ratios,
            "metadata": {
                "context": context or {},
                "formulas_applied": [r["name"] for r in ratios]
            }
        }
    }


# ============================================
# Tool Definitions para el Registry
# ============================================

BIW_TOOLS = {
    "biw_get_cube_data": {
        "id": "biw_get_cube_data",
        "name": "biw_get_cube_data",
        "description": """Extrae datos de un InfoCube (cubo OLAP) de SAP BW multidimensional.
        
Usa esta herramienta para obtener datos analíticos desde cubos OLAP.
Especifica las características (ejes de análisis) y ratios (medidas) que necesitas.

Ejemplo:
- cube_name: "ZC_SALES"
- characteristics: ["region", "product", "year"]
- key_figures: ["sales_amount", "quantity", "margin"]
- filters: {"region": "Norte", "year": "2024"}""",
        "parameters": {
            "type": "object",
            "properties": {
                "cube_name": {
                    "type": "string",
                    "description": "Nombre del InfoCube (ej: ZC_SALES, ZC_COSTS)"
                },
                "characteristics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Características/ejes de análisis (ej: region, product, time)"
                },
                "key_figures": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ratios/medidas a extraer (ej: sales, costs, margin)"
                },
                "filters": {
                    "type": "object",
                    "description": "Filtros a aplicar (ej: {\"region\": \"Norte\", \"year\": \"2024\"})"
                },
                "drilldown": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Jerarquía de drill-down (ej: [\"year\", \"quarter\", \"month\"])"
                }
            },
            "required": ["cube_name"]
        },
        "handler": biw_get_cube_data
    },
    "biw_get_dso_data": {
        "id": "biw_get_dso_data",
        "name": "biw_get_dso_data",
        "description": "Extrae datos de un DataStore Object (DSO) de SAP BW. Usa para datos maestros o transaccionales.",
        "parameters": {
            "type": "object",
            "properties": {
                "dso_name": {"type": "string", "description": "Nombre del DSO"},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Campos específicos a extraer"},
                "filters": {"type": "object", "description": "Filtros a aplicar"},
                "max_rows": {"type": "integer", "default": 1000, "description": "Máximo número de filas"}
            },
            "required": ["dso_name"]
        },
        "handler": biw_get_dso_data
    },
    "biw_get_bex_query": {
        "id": "biw_get_bex_query",
        "name": "biw_get_bex_query",
        "description": "Ejecuta una query BEx (Business Explorer) de SAP BW con variables y filtros.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_name": {"type": "string", "description": "Nombre de la query BEx"},
                "variables": {"type": "object", "description": "Variables de la query"},
                "filters": {"type": "object", "description": "Filtros adicionales"}
            },
            "required": ["query_name"]
        },
        "handler": biw_get_bex_query
    },
    "biw_get_master_data": {
        "id": "biw_get_master_data",
        "name": "biw_get_master_data",
        "description": "Obtiene datos maestros (Master Data) de SAP BW con sus atributos.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Nombre del objeto maestro"},
                "attributes": {"type": "array", "items": {"type": "string"}, "description": "Atributos específicos"},
                "filters": {"type": "object", "description": "Filtros a aplicar"}
            },
            "required": ["object_name"]
        },
        "handler": biw_get_master_data
    },
    "biw_get_hierarchy": {
        "id": "biw_get_hierarchy",
        "name": "biw_get_hierarchy",
        "description": "Obtiene una jerarquía (Hierarchy) de SAP BW para drill-down.",
        "parameters": {
            "type": "object",
            "properties": {
                "hierarchy_name": {"type": "string", "description": "Nombre de la jerarquía"},
                "level": {"type": "integer", "description": "Nivel específico"},
                "node": {"type": "string", "description": "Nodo para sub-jerarquía"}
            },
            "required": ["hierarchy_name"]
        },
        "handler": biw_get_hierarchy
    },
    "biw_get_texts": {
        "id": "biw_get_texts",
        "name": "biw_get_texts",
        "description": "Obtiene textos descriptivos de objetos SAP BW en un idioma específico.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_name": {"type": "string", "description": "Nombre del objeto"},
                "language": {"type": "string", "default": "ES", "description": "Código de idioma (ES, EN, DE)"},
                "keys": {"type": "array", "items": {"type": "string"}, "description": "Keys específicos"}
            },
            "required": ["object_name"]
        },
        "handler": biw_get_texts
    },
    "biw_get_ratios": {
        "id": "biw_get_ratios",
        "name": "biw_get_ratios",
        "description": "Obtiene ratios y Key Figures calculados (Calculated KFs) de SAP BW.",
        "parameters": {
            "type": "object",
            "properties": {
                "cube_name": {"type": "string", "description": "Nombre del InfoCube"},
                "calculated_key_figures": {"type": "array", "items": {"type": "string"}, "description": "Ratios calculados específicos"},
                "context": {"type": "object", "description": "Contexto para cálculo"}
            },
            "required": ["cube_name"]
        },
        "handler": biw_get_ratios
    }
}
