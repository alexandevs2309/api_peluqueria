#!/usr/bin/env python
"""
Script de Validación de Seguridad RBAC
Detecta ViewSets y APIViews sin protección adecuada
"""
import os
import re
from pathlib import Path

# Colores para output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def find_python_files(base_path):
    """Encuentra todos los archivos views.py en apps/"""
    views_files = []
    apps_path = Path(base_path) / 'apps'
    
    for views_file in apps_path.rglob('*views.py'):
        views_files.append(views_file)
    
    return views_files

def check_viewset_protection(file_path):
    """Verifica si ViewSets tienen TenantPermissionByAction"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar ViewSets
    viewset_pattern = r'class\s+(\w+)\(.*ViewSet.*\):'
    viewsets = re.findall(viewset_pattern, content)
    
    vulnerabilities = []
    
    for viewset in viewsets:
        # Buscar permission_classes para este ViewSet
        viewset_block = re.search(
            rf'class\s+{viewset}\(.*?\):(.*?)(?=class\s+\w+|$)',
            content,
            re.DOTALL
        )
        
        if viewset_block:
            block_content = viewset_block.group(1)
            
            # Verificar si tiene TenantPermissionByAction
            has_tenant_permission = 'TenantPermissionByAction' in block_content
            has_is_authenticated_only = (
                'IsAuthenticated' in block_content and 
                'TenantPermissionByAction' not in block_content
            )
            has_permission_map = 'permission_map' in block_content
            
            # Buscar @action sin permission_map
            actions = re.findall(r'@action\(.*?\)\s+def\s+(\w+)', block_content)
            
            if has_is_authenticated_only:
                vulnerabilities.append({
                    'type': 'ViewSet',
                    'name': viewset,
                    'file': str(file_path),
                    'issue': 'Solo IsAuthenticated - sin TenantPermissionByAction',
                    'severity': 'ALTA',
                    'actions': actions
                })
            elif has_tenant_permission and not has_permission_map:
                vulnerabilities.append({
                    'type': 'ViewSet',
                    'name': viewset,
                    'file': str(file_path),
                    'issue': 'TenantPermissionByAction sin permission_map',
                    'severity': 'ALTA',
                    'actions': actions
                })
            elif has_tenant_permission and has_permission_map and actions:
                # Verificar si todas las actions están en permission_map
                permission_map_content = re.search(
                    r'permission_map\s*=\s*\{(.*?)\}',
                    block_content,
                    re.DOTALL
                )
                
                if permission_map_content:
                    mapped_actions = re.findall(
                        r"['\"](\w+)['\"]:",
                        permission_map_content.group(1)
                    )
                    
                    unmapped_actions = [a for a in actions if a not in mapped_actions]
                    
                    if unmapped_actions:
                        vulnerabilities.append({
                            'type': 'ViewSet',
                            'name': viewset,
                            'file': str(file_path),
                            'issue': f'Acciones sin mapeo: {", ".join(unmapped_actions)}',
                            'severity': 'MEDIA',
                            'actions': unmapped_actions
                        })
    
    return vulnerabilities

def check_apiview_protection(file_path):
    """Verifica si APIViews tienen protección adecuada"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar APIViews
    apiview_pattern = r'class\s+(\w+)\(.*APIView.*\):'
    apiviews = re.findall(apiview_pattern, content)
    
    vulnerabilities = []
    
    for apiview in apiviews:
        # Buscar permission_classes para este APIView
        apiview_block = re.search(
            rf'class\s+{apiview}\(.*?\):(.*?)(?=class\s+\w+|$)',
            content,
            re.DOTALL
        )
        
        if apiview_block:
            block_content = apiview_block.group(1)
            
            # Verificar si tiene protección adecuada
            has_tenant_permission = 'TenantPermissionByAction' in block_content
            has_is_authenticated_only = (
                'IsAuthenticated' in block_content and 
                'TenantPermissionByAction' not in block_content and
                'IsSuperAdmin' not in block_content
            )
            
            if has_is_authenticated_only:
                vulnerabilities.append({
                    'type': 'APIView',
                    'name': apiview,
                    'file': str(file_path),
                    'issue': 'Solo IsAuthenticated - sin TenantPermissionByAction',
                    'severity': 'ALTA',
                    'actions': []
                })
    
    return vulnerabilities

def check_adhoc_validations(file_path):
    """Detecta validaciones ad-hoc de roles"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    vulnerabilities = []
    
    # Buscar user.roles.filter
    if 'user.roles.filter' in content:
        matches = re.findall(r'user\.roles\.filter\(.*?\)', content)
        if matches:
            vulnerabilities.append({
                'type': 'AdHoc',
                'name': 'Validación roles.filter',
                'file': str(file_path),
                'issue': f'Validación ad-hoc encontrada: {len(matches)} ocurrencias',
                'severity': 'MEDIA',
                'actions': []
            })
    
    # Buscar is_superuser en get_queryset (excepto comentarios)
    queryset_blocks = re.findall(
        r'def get_queryset\(.*?\):(.*?)(?=def\s+\w+|class\s+\w+|$)',
        content,
        re.DOTALL
    )
    
    for block in queryset_blocks:
        if 'is_superuser' in block and '# SuperAdmin' not in block:
            vulnerabilities.append({
                'type': 'AdHoc',
                'name': 'Validación is_superuser en get_queryset',
                'file': str(file_path),
                'issue': 'Validación ad-hoc en get_queryset',
                'severity': 'MEDIA',
                'actions': []
            })
    
    return vulnerabilities

def check_fallback_security():
    """Verifica el fallback de TenantPermissionByAction"""
    tenant_permissions_file = Path('apps/core/tenant_permissions.py')
    
    if not tenant_permissions_file.exists():
        return [{
            'type': 'Config',
            'name': 'TenantPermissionByAction',
            'file': 'apps/core/tenant_permissions.py',
            'issue': 'Archivo no encontrado',
            'severity': 'CRÍTICA',
            'actions': []
        }]
    
    with open(tenant_permissions_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar el fallback
    fallback_pattern = r"if not action or action not in permission_map:\s*return\s+(.*)"
    match = re.search(fallback_pattern, content)
    
    if match:
        return_value = match.group(1).strip()
        
        if 'GET' in return_value or 'True' in return_value:
            return [{
                'type': 'Config',
                'name': 'TenantPermissionByAction fallback',
                'file': 'apps/core/tenant_permissions.py',
                'issue': f'Fallback inseguro: {return_value}',
                'severity': 'CRÍTICA',
                'actions': []
            }]
    
    return []

def generate_report(all_vulnerabilities):
    """Genera reporte de vulnerabilidades"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}REPORTE DE AUDITORÍA DE SEGURIDAD RBAC{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    # Agrupar por severidad
    critical = [v for v in all_vulnerabilities if v['severity'] == 'CRÍTICA']
    high = [v for v in all_vulnerabilities if v['severity'] == 'ALTA']
    medium = [v for v in all_vulnerabilities if v['severity'] == 'MEDIA']
    
    total = len(all_vulnerabilities)
    
    print(f"{RED}CRÍTICAS: {len(critical)}{RESET}")
    print(f"{YELLOW}ALTAS: {len(high)}{RESET}")
    print(f"{BLUE}MEDIAS: {len(medium)}{RESET}")
    print(f"\nTOTAL: {total} vulnerabilidades detectadas\n")
    
    # Mostrar críticas
    if critical:
        print(f"\n{RED}{'='*80}")
        print(f"VULNERABILIDADES CRÍTICAS ({len(critical)})")
        print(f"{'='*80}{RESET}\n")
        
        for vuln in critical:
            print(f"{RED}[{vuln['type']}] {vuln['name']}{RESET}")
            print(f"  Archivo: {vuln['file']}")
            print(f"  Problema: {vuln['issue']}")
            if vuln['actions']:
                print(f"  Acciones: {', '.join(vuln['actions'])}")
            print()
    
    # Mostrar altas
    if high:
        print(f"\n{YELLOW}{'='*80}")
        print(f"VULNERABILIDADES ALTAS ({len(high)})")
        print(f"{'='*80}{RESET}\n")
        
        for vuln in high:
            print(f"{YELLOW}[{vuln['type']}] {vuln['name']}{RESET}")
            print(f"  Archivo: {vuln['file']}")
            print(f"  Problema: {vuln['issue']}")
            if vuln['actions']:
                print(f"  Acciones: {', '.join(vuln['actions'])}")
            print()
    
    # Resumen por tipo
    print(f"\n{BLUE}{'='*80}")
    print(f"RESUMEN POR TIPO")
    print(f"{'='*80}{RESET}\n")
    
    types_count = {}
    for vuln in all_vulnerabilities:
        types_count[vuln['type']] = types_count.get(vuln['type'], 0) + 1
    
    for vtype, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {vtype}: {count}")
    
    # Calcular cobertura
    print(f"\n{BLUE}{'='*80}")
    print(f"COBERTURA RBAC")
    print(f"{'='*80}{RESET}\n")
    
    viewsets_vulnerable = len([v for v in all_vulnerabilities if v['type'] == 'ViewSet'])
    apiviews_vulnerable = len([v for v in all_vulnerabilities if v['type'] == 'APIView'])
    
    # Estimación (ajustar según proyecto)
    total_viewsets = 16
    total_apiviews = 10
    
    viewsets_protected = total_viewsets - viewsets_vulnerable
    apiviews_protected = total_apiviews - apiviews_vulnerable
    
    viewsets_coverage = (viewsets_protected / total_viewsets) * 100
    apiviews_coverage = (apiviews_protected / total_apiviews) * 100
    overall_coverage = ((viewsets_protected + apiviews_protected) / (total_viewsets + total_apiviews)) * 100
    
    print(f"  ViewSets protegidos: {viewsets_protected}/{total_viewsets} ({viewsets_coverage:.1f}%)")
    print(f"  APIViews protegidos: {apiviews_protected}/{total_apiviews} ({apiviews_coverage:.1f}%)")
    print(f"  Cobertura general: {overall_coverage:.1f}%")
    
    # Estado de seguridad
    print(f"\n{BLUE}{'='*80}")
    print(f"ESTADO DE SEGURIDAD")
    print(f"{'='*80}{RESET}\n")
    
    if overall_coverage >= 95:
        status = f"{GREEN}SEGURO{RESET}"
    elif overall_coverage >= 70:
        status = f"{YELLOW}PARCIALMENTE PROTEGIDO{RESET}"
    elif overall_coverage >= 30:
        status = f"{YELLOW}VULNERABLE POR OMISIONES{RESET}"
    else:
        status = f"{RED}CRÍTICAMENTE EXPUESTO{RESET}"
    
    print(f"  Estado: {status}")
    print(f"  Cobertura: {overall_coverage:.1f}%")
    print(f"  Vulnerabilidades: {total}")
    
    print(f"\n{BLUE}{'='*80}{RESET}\n")

def main():
    """Función principal"""
    base_path = Path(__file__).parent.parent
    
    print(f"\n{BLUE}Iniciando auditoría de seguridad RBAC...{RESET}\n")
    
    # Verificar fallback
    print("Verificando configuración de TenantPermissionByAction...")
    fallback_vulns = check_fallback_security()
    
    # Buscar archivos views.py
    print("Buscando archivos views.py...")
    views_files = find_python_files(base_path)
    print(f"Encontrados {len(views_files)} archivos\n")
    
    all_vulnerabilities = fallback_vulns.copy()
    
    # Analizar cada archivo
    for views_file in views_files:
        print(f"Analizando {views_file.relative_to(base_path)}...")
        
        # Verificar ViewSets
        viewset_vulns = check_viewset_protection(views_file)
        all_vulnerabilities.extend(viewset_vulns)
        
        # Verificar APIViews
        apiview_vulns = check_apiview_protection(views_file)
        all_vulnerabilities.extend(apiview_vulns)
        
        # Verificar validaciones ad-hoc
        adhoc_vulns = check_adhoc_validations(views_file)
        all_vulnerabilities.extend(adhoc_vulns)
    
    # Generar reporte
    generate_report(all_vulnerabilities)
    
    # Retornar código de salida
    return 1 if all_vulnerabilities else 0

if __name__ == '__main__':
    exit(main())
