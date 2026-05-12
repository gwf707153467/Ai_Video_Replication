# Tests Notes

## DB-backed unittests

对需要真实 PostgreSQL 连接的 unittest，统一使用 `tests/_db_test_helper.py` 中的 `resolve_test_database_url()`，不要在单个测试文件内重复实现 `_resolve_database_url()` 或自行拼接 / 改写 DSN。

推荐写法：

```python
from _db_test_helper import resolve_test_database_url

engine = create_engine(resolve_test_database_url(), future=True)
```

当前 URL 解析优先级：

1. `RUNTIME_TERMINAL_TEST_DATABASE_URL`
2. `DATABASE_URL`
3. `settings.database_url`，并将 `@postgres:` 改写为 `@host.docker.internal:`
4. 最后回退为将 `settings.database_url` 中的 `@postgres:` 改写为 `@127.0.0.1:`

说明：当前 sandbox / Docker 映射场景下，`host.docker.internal` 是优先可达入口；保留 `127.0.0.1` 作为最后回退。

## Test environment

优先使用项目共享虚拟环境运行测试：

```bash
source /mnt/user-data/workspace/.venv/bin/activate
cd /mnt/user-data/workspace/Ai_Videos_Replication
python -m unittest discover -s tests -p 'test_compiler_service_runtime_payload.py'
```

同类 DB-backed suites 可替换 `-p` 为：

- `test_runtime_terminal_repository_transactions.py`
- `test_runtime_terminal_repository_transaction_conflicts.py`

## Conventions

- tests-only 数据库入口标准化优先走共享 helper
- 新增 DB-backed unittest 时，默认沿用 `resolve_test_database_url()`
- `datetime.utcnow()` 相关 deprecation warning 当前不在这一轮清理范围内
