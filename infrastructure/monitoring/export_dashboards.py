#!/usr/bin/env python3
"""
Export Grafana dashboards from Python configuration to JSON files.

This script reads dashboard configurations from backend/app/monitoring/dashboard_config.py
and exports them as JSON files that Grafana can load automatically.

Usage:
    python export_dashboards.py
"""

import json
import os
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

try:
    from app.monitoring.dashboard_config import (
        SYSTEM_OVERVIEW_DASHBOARD,
        DOCUMENT_PROCESSING_DASHBOARD,
        COST_DASHBOARD
    )
except ImportError as e:
    print(f"Error importing dashboard configs: {e}")
    print(f"Make sure the backend module is available at: {backend_path}")
    sys.exit(1)


def export_dashboards():
    """Export all dashboards as JSON files."""

    # Create dashboards directory if it doesn't exist
    dashboards_dir = Path(__file__).parent / 'grafana' / 'dashboards'
    dashboards_dir.mkdir(parents=True, exist_ok=True)

    dashboards = {
        'system_overview': SYSTEM_OVERVIEW_DASHBOARD,
        'document_processing': DOCUMENT_PROCESSING_DASHBOARD,
        'cost_tracking': COST_DASHBOARD
    }

    print("Exporting Grafana dashboards...")
    print(f"Output directory: {dashboards_dir}")
    print()

    for name, config in dashboards.items():
        output_file = dashboards_dir / f'{name}.json'

        # Add UID and other required Grafana fields
        dashboard = config['dashboard']
        dashboard['uid'] = name.replace('_', '-')
        dashboard['editable'] = True
        dashboard['graphTooltip'] = 1  # Shared crosshair

        # Wrap in the format Grafana expects
        grafana_export = {
            'dashboard': dashboard,
            'overwrite': True,
            'folderId': 0,
            'folderUid': '',
            'message': f'Auto-exported {name} dashboard'
        }

        # Write JSON file
        with open(output_file, 'w') as f:
            json.dump(grafana_export, f, indent=2)

        print(f"✓ Exported {name} → {output_file.name}")

    print()
    print("Dashboard export complete!")
    print()
    print("Next steps:")
    print("1. Start the monitoring stack: docker-compose up -d")
    print("2. Access Grafana at http://localhost:3000")
    print("3. Dashboards will be auto-loaded in the 'PM Document Intelligence' folder")


def validate_dashboards():
    """Validate dashboard configurations."""

    print("Validating dashboard configurations...")

    dashboards = {
        'system_overview': SYSTEM_OVERVIEW_DASHBOARD,
        'document_processing': DOCUMENT_PROCESSING_DASHBOARD,
        'cost_tracking': COST_DASHBOARD
    }

    for name, config in dashboards.items():
        # Check required fields
        if 'dashboard' not in config:
            print(f"✗ {name}: Missing 'dashboard' key")
            continue

        dashboard = config['dashboard']

        required_fields = ['title', 'panels']
        for field in required_fields:
            if field not in dashboard:
                print(f"✗ {name}: Missing required field '{field}'")
                continue

        # Check panels
        if not isinstance(dashboard['panels'], list):
            print(f"✗ {name}: 'panels' must be a list")
            continue

        if len(dashboard['panels']) == 0:
            print(f"⚠ {name}: No panels defined")

        # Validate each panel
        for i, panel in enumerate(dashboard['panels']):
            if 'id' not in panel:
                print(f"⚠ {name}: Panel {i} missing 'id'")
            if 'title' not in panel:
                print(f"⚠ {name}: Panel {i} missing 'title'")
            if 'targets' not in panel:
                print(f"⚠ {name}: Panel {i} missing 'targets'")

        print(f"✓ {name}: Valid ({len(dashboard['panels'])} panels)")

    print()


if __name__ == '__main__':
    validate_dashboards()
    export_dashboards()
