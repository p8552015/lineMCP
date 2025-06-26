# `apps/bot` Directory Structure

This document outlines the file and directory structure of the `apps/bot` application.

```
apps/bot/
├── DI_CONTAINER_QUICK_START.md
├── Dockerfile
├── Dockerfile.optimized
├── README.md
├── alembic
│   ├── README
│   ├── __pycache__
│   │   └── env.cpython-311.pyc
│   ├── env.py
│   ├── script.py.mako
│   └── versions
│       ├── __pycache__
│       │   ├── 66fca70b97ae_test_migration_add_machine_type_column.cpython-311.pyc
│       │   ├── d2964dc9ce17_initial_production_schema_baseline.cpython-311.pyc
│       │   └── db355212fdcf_initial_database_schema.cpython-311.pyc
│       └── d2964dc9ce17_initial_production_schema_baseline.py
├── alembic.ini
├── performance_tests
│   ├── __init__.py
│   ├── ci_config.py
│   ├── locustfile.py
│   └── scenarios.py
├── poetry.lock
├── poetry.toml
├── pyproject.toml
├── src
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-311.pyc
│   │   ├── config.cpython-311.pyc
│   │   ├── main.cpython-311.pyc
│   │   └── middleware.cpython-311.pyc
│   ├── application
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── application_facade.py
│   │   ├── base_service.py
│   │   ├── messaging_service.py
│   │   ├── monitoring_service.py
│   │   └── query_service.py
│   ├── commands
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── help_command.py
│   │   ├── info_command.py
│   │   ├── models_command.py
│   │   ├── postgres_command.py
│   │   ├── postgres_command_handler.py
│   │   ├── sql_command.py
│   │   ├── status_command.py
│   │   └── tables_command.py
│   ├── config
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── enhanced_mcp_config.py
│   │   └── mcp_config.py
│   ├── config.py
│   ├── domain
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── command_executor.py
│   │   ├── command_handler.py
│   │   └── exceptions.py
│   ├── infrastructure
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── application_services_registry.py
│   │   ├── circular_dependency_detector.py
│   │   ├── core_services_registry.py
│   │   ├── dependency_injection_guard.py
│   │   ├── enhanced_service_factory.py
│   │   ├── error_handler.py
│   │   ├── infrastructure_services_registry.py
│   │   ├── lazy_initialization_error_handler.py
│   │   ├── service_factory_interface.py
│   │   ├── service_registry.py
│   │   └── user_experience_enhancer.py
│   ├── main.py
│   ├── middleware.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── commands.py
│   │   ├── current_database.py
│   │   ├── database.py
│   │   └── mcp_manifest.py
│   ├── monitoring
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── metrics.py
│   ├── nodecomman
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── config
│   │   ├── implementations
│   │   ├── interfaces
│   │   ├── tests
│   │   └── utils
│   ├── routes
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   └── webhook.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── ai_model_service.py
│   │   ├── ai_model_service_enhanced.py
│   │   ├── cost_tracker.py
│   │   ├── database_service.py
│   │   ├── enhanced_mcp_client.py
│   │   ├── error_handlers.py
│   │   ├── mcp_connection_pool.py
│   │   ├── mcp_response_parser.py
│   │   ├── message_formatter.py
│   │   ├── message_handler_di.py
│   │   ├── nl_to_sql
│   │   ├── nl_to_sql_service.py
│   │   ├── openai_client.py
│   │   ├── production_mcp_client.py
│   │   └── unified_mcp_client.py
│   └── utils
│       ├── __init__.py
│       ├── __pycache__
│       ├── database_health_check.py
│       ├── observability.py
│       ├── redis_client.py
│       ├── signature_validator.py
│       └── startup_health_check.py
└── tests
    ├── __init__.py
    ├── __pycache__
    ├── application
    ├── conftest.py
    ├── domain
    ├── fixtures
    ├── infrastructure
    ├── integration
    ├── nodecomman
    ├── services
    └── unit
``` 