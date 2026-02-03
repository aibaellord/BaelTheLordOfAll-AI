#!/usr/bin/env python3
"""
BAEL - Query Builder
Comprehensive SQL-like query building system.

This module provides a complete query builder for
constructing database queries in a fluent manner.

Features:
- SELECT, INSERT, UPDATE, DELETE
- WHERE clauses with operators
- JOINs (inner, left, right, full)
- GROUP BY and HAVING
- ORDER BY with direction
- LIMIT and OFFSET
- Subqueries
- Aggregations
- Raw expressions
- Query compilation
- Parameter binding
"""

import asyncio
import json
import logging
import re
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Awaitable, Callable, Dict, Generic, List, Optional,
                    Set, Tuple, Type, TypeVar, Union)

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# ENUMS
# =============================================================================

class QueryType(Enum):
    """Query operation types."""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class JoinType(Enum):
    """JOIN types."""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"
    CROSS = "CROSS JOIN"


class OrderDirection(Enum):
    """ORDER BY direction."""
    ASC = "ASC"
    DESC = "DESC"


class WhereOperator(Enum):
    """WHERE clause operators."""
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    IN = "IN"
    NOT_IN = "NOT IN"
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"
    BETWEEN = "BETWEEN"
    EXISTS = "EXISTS"


class LogicalOp(Enum):
    """Logical operators."""
    AND = "AND"
    OR = "OR"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class QueryColumn:
    """Represents a column in a query."""
    name: str
    alias: Optional[str] = None
    table: Optional[str] = None

    def to_sql(self) -> str:
        parts = []
        if self.table:
            parts.append(f"{self.table}.")
        parts.append(self.name)
        if self.alias:
            parts.append(f" AS {self.alias}")
        return "".join(parts)


@dataclass
class WhereClause:
    """Represents a WHERE condition."""
    column: str
    operator: WhereOperator
    value: Any = None
    logical_op: LogicalOp = LogicalOp.AND
    is_raw: bool = False

    def to_sql(self, param_index: int = 0) -> Tuple[str, List[Any]]:
        if self.is_raw:
            return self.column, []

        params = []

        if self.operator == WhereOperator.IS_NULL:
            return f"{self.column} IS NULL", params

        if self.operator == WhereOperator.IS_NOT_NULL:
            return f"{self.column} IS NOT NULL", params

        if self.operator == WhereOperator.IN:
            placeholders = ", ".join(["?" for _ in self.value])
            params.extend(self.value)
            return f"{self.column} IN ({placeholders})", params

        if self.operator == WhereOperator.NOT_IN:
            placeholders = ", ".join(["?" for _ in self.value])
            params.extend(self.value)
            return f"{self.column} NOT IN ({placeholders})", params

        if self.operator == WhereOperator.BETWEEN:
            params.extend([self.value[0], self.value[1]])
            return f"{self.column} BETWEEN ? AND ?", params

        if self.operator == WhereOperator.EXISTS:
            return f"EXISTS ({self.value})", params

        params.append(self.value)
        return f"{self.column} {self.operator.value} ?", params


@dataclass
class JoinClause:
    """Represents a JOIN clause."""
    table: str
    condition: str
    join_type: JoinType = JoinType.INNER
    alias: Optional[str] = None

    def to_sql(self) -> str:
        table_ref = f"{self.table}" if not self.alias else f"{self.table} AS {self.alias}"
        return f"{self.join_type.value} {table_ref} ON {self.condition}"


@dataclass
class OrderClause:
    """Represents an ORDER BY clause."""
    column: str
    direction: OrderDirection = OrderDirection.ASC

    def to_sql(self) -> str:
        return f"{self.column} {self.direction.value}"


@dataclass
class CompiledQuery:
    """A compiled query ready for execution."""
    sql: str
    params: List[Any] = field(default_factory=list)
    query_type: QueryType = QueryType.SELECT


# =============================================================================
# RAW EXPRESSION
# =============================================================================

class RawExpression:
    """Raw SQL expression."""

    def __init__(self, expression: str, params: List[Any] = None):
        self.expression = expression
        self.params = params or []

    def to_sql(self) -> Tuple[str, List[Any]]:
        return self.expression, self.params


# =============================================================================
# AGGREGATE FUNCTIONS
# =============================================================================

class Aggregate:
    """SQL aggregate function."""

    @staticmethod
    def count(column: str = "*", alias: str = None) -> str:
        result = f"COUNT({column})"
        return f"{result} AS {alias}" if alias else result

    @staticmethod
    def sum(column: str, alias: str = None) -> str:
        result = f"SUM({column})"
        return f"{result} AS {alias}" if alias else result

    @staticmethod
    def avg(column: str, alias: str = None) -> str:
        result = f"AVG({column})"
        return f"{result} AS {alias}" if alias else result

    @staticmethod
    def min(column: str, alias: str = None) -> str:
        result = f"MIN({column})"
        return f"{result} AS {alias}" if alias else result

    @staticmethod
    def max(column: str, alias: str = None) -> str:
        result = f"MAX({column})"
        return f"{result} AS {alias}" if alias else result

    @staticmethod
    def distinct(column: str) -> str:
        return f"DISTINCT {column}"


# =============================================================================
# QUERY BUILDER
# =============================================================================

class QueryBuilder:
    """
    Fluent SQL query builder.
    """

    def __init__(self, table: str = None):
        self._table = table
        self._table_alias: Optional[str] = None
        self._type = QueryType.SELECT

        # SELECT
        self._columns: List[str] = []
        self._distinct = False

        # WHERE
        self._wheres: List[WhereClause] = []
        self._where_groups: List[List[WhereClause]] = []

        # JOIN
        self._joins: List[JoinClause] = []

        # GROUP BY
        self._group_by: List[str] = []
        self._having: List[WhereClause] = []

        # ORDER BY
        self._order_by: List[OrderClause] = []

        # LIMIT/OFFSET
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

        # INSERT/UPDATE
        self._values: Dict[str, Any] = {}
        self._insert_columns: List[str] = []
        self._insert_rows: List[Dict[str, Any]] = []

        # Subqueries
        self._subqueries: Dict[str, 'QueryBuilder'] = {}

    # =========================================================================
    # TABLE
    # =========================================================================

    def table(self, table: str, alias: str = None) -> 'QueryBuilder':
        """Set the table."""
        self._table = table
        self._table_alias = alias
        return self

    def from_(self, table: str, alias: str = None) -> 'QueryBuilder':
        """Alias for table()."""
        return self.table(table, alias)

    # =========================================================================
    # SELECT
    # =========================================================================

    def select(self, *columns: str) -> 'QueryBuilder':
        """Set SELECT columns."""
        self._type = QueryType.SELECT
        self._columns.extend(columns)
        return self

    def select_raw(self, expression: str) -> 'QueryBuilder':
        """Add raw SELECT expression."""
        self._columns.append(expression)
        return self

    def distinct(self) -> 'QueryBuilder':
        """Add DISTINCT."""
        self._distinct = True
        return self

    def add_select(self, *columns: str) -> 'QueryBuilder':
        """Add more columns to SELECT."""
        self._columns.extend(columns)
        return self

    # =========================================================================
    # WHERE
    # =========================================================================

    def where(
        self,
        column: str,
        operator: Union[WhereOperator, str] = WhereOperator.EQ,
        value: Any = None
    ) -> 'QueryBuilder':
        """Add WHERE clause."""
        if isinstance(operator, str) and value is None:
            # Short form: where("column", "value")
            value = operator
            operator = WhereOperator.EQ
        elif isinstance(operator, str):
            operator = WhereOperator(operator)

        self._wheres.append(WhereClause(
            column=column,
            operator=operator,
            value=value,
            logical_op=LogicalOp.AND
        ))
        return self

    def or_where(
        self,
        column: str,
        operator: Union[WhereOperator, str] = WhereOperator.EQ,
        value: Any = None
    ) -> 'QueryBuilder':
        """Add OR WHERE clause."""
        if isinstance(operator, str) and value is None:
            value = operator
            operator = WhereOperator.EQ
        elif isinstance(operator, str):
            operator = WhereOperator(operator)

        self._wheres.append(WhereClause(
            column=column,
            operator=operator,
            value=value,
            logical_op=LogicalOp.OR
        ))
        return self

    def where_in(self, column: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE IN clause."""
        return self.where(column, WhereOperator.IN, values)

    def where_not_in(self, column: str, values: List[Any]) -> 'QueryBuilder':
        """Add WHERE NOT IN clause."""
        return self.where(column, WhereOperator.NOT_IN, values)

    def where_null(self, column: str) -> 'QueryBuilder':
        """Add WHERE IS NULL clause."""
        return self.where(column, WhereOperator.IS_NULL)

    def where_not_null(self, column: str) -> 'QueryBuilder':
        """Add WHERE IS NOT NULL clause."""
        return self.where(column, WhereOperator.IS_NOT_NULL)

    def where_between(
        self,
        column: str,
        start: Any,
        end: Any
    ) -> 'QueryBuilder':
        """Add WHERE BETWEEN clause."""
        return self.where(column, WhereOperator.BETWEEN, [start, end])

    def where_like(self, column: str, pattern: str) -> 'QueryBuilder':
        """Add WHERE LIKE clause."""
        return self.where(column, WhereOperator.LIKE, pattern)

    def where_raw(self, expression: str) -> 'QueryBuilder':
        """Add raw WHERE clause."""
        self._wheres.append(WhereClause(
            column=expression,
            operator=WhereOperator.EQ,
            is_raw=True,
            logical_op=LogicalOp.AND
        ))
        return self

    def where_exists(self, subquery: 'QueryBuilder') -> 'QueryBuilder':
        """Add WHERE EXISTS clause."""
        compiled = subquery.compile()
        self._wheres.append(WhereClause(
            column="",
            operator=WhereOperator.EXISTS,
            value=compiled.sql
        ))
        return self

    # =========================================================================
    # JOIN
    # =========================================================================

    def join(
        self,
        table: str,
        first: str,
        operator: str = "=",
        second: str = None,
        join_type: JoinType = JoinType.INNER,
        alias: str = None
    ) -> 'QueryBuilder':
        """Add JOIN clause."""
        if second is None:
            condition = first  # Raw condition
        else:
            condition = f"{first} {operator} {second}"

        self._joins.append(JoinClause(
            table=table,
            condition=condition,
            join_type=join_type,
            alias=alias
        ))
        return self

    def left_join(
        self,
        table: str,
        first: str,
        operator: str = "=",
        second: str = None
    ) -> 'QueryBuilder':
        """Add LEFT JOIN."""
        return self.join(table, first, operator, second, JoinType.LEFT)

    def right_join(
        self,
        table: str,
        first: str,
        operator: str = "=",
        second: str = None
    ) -> 'QueryBuilder':
        """Add RIGHT JOIN."""
        return self.join(table, first, operator, second, JoinType.RIGHT)

    def full_join(
        self,
        table: str,
        first: str,
        operator: str = "=",
        second: str = None
    ) -> 'QueryBuilder':
        """Add FULL OUTER JOIN."""
        return self.join(table, first, operator, second, JoinType.FULL)

    def cross_join(self, table: str) -> 'QueryBuilder':
        """Add CROSS JOIN."""
        self._joins.append(JoinClause(
            table=table,
            condition="1=1",
            join_type=JoinType.CROSS
        ))
        return self

    # =========================================================================
    # GROUP BY / HAVING
    # =========================================================================

    def group_by(self, *columns: str) -> 'QueryBuilder':
        """Add GROUP BY clause."""
        self._group_by.extend(columns)
        return self

    def having(
        self,
        column: str,
        operator: Union[WhereOperator, str] = WhereOperator.EQ,
        value: Any = None
    ) -> 'QueryBuilder':
        """Add HAVING clause."""
        if isinstance(operator, str) and value is None:
            value = operator
            operator = WhereOperator.EQ
        elif isinstance(operator, str):
            operator = WhereOperator(operator)

        self._having.append(WhereClause(
            column=column,
            operator=operator,
            value=value
        ))
        return self

    # =========================================================================
    # ORDER BY
    # =========================================================================

    def order_by(
        self,
        column: str,
        direction: Union[OrderDirection, str] = OrderDirection.ASC
    ) -> 'QueryBuilder':
        """Add ORDER BY clause."""
        if isinstance(direction, str):
            direction = OrderDirection(direction.upper())

        self._order_by.append(OrderClause(column=column, direction=direction))
        return self

    def order_by_desc(self, column: str) -> 'QueryBuilder':
        """Add ORDER BY DESC."""
        return self.order_by(column, OrderDirection.DESC)

    def latest(self, column: str = "created_at") -> 'QueryBuilder':
        """Order by latest."""
        return self.order_by_desc(column)

    def oldest(self, column: str = "created_at") -> 'QueryBuilder':
        """Order by oldest."""
        return self.order_by(column, OrderDirection.ASC)

    # =========================================================================
    # LIMIT / OFFSET
    # =========================================================================

    def limit(self, limit: int) -> 'QueryBuilder':
        """Set LIMIT."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'QueryBuilder':
        """Set OFFSET."""
        self._offset = offset
        return self

    def take(self, count: int) -> 'QueryBuilder':
        """Alias for limit()."""
        return self.limit(count)

    def skip(self, count: int) -> 'QueryBuilder':
        """Alias for offset()."""
        return self.offset(count)

    def paginate(self, page: int, per_page: int = 10) -> 'QueryBuilder':
        """Apply pagination."""
        return self.limit(per_page).offset((page - 1) * per_page)

    # =========================================================================
    # INSERT
    # =========================================================================

    def insert(self, data: Dict[str, Any]) -> 'QueryBuilder':
        """Set INSERT data."""
        self._type = QueryType.INSERT
        self._values = data
        return self

    def insert_many(self, rows: List[Dict[str, Any]]) -> 'QueryBuilder':
        """Set INSERT data for multiple rows."""
        self._type = QueryType.INSERT
        self._insert_rows = rows
        return self

    # =========================================================================
    # UPDATE
    # =========================================================================

    def update(self, data: Dict[str, Any]) -> 'QueryBuilder':
        """Set UPDATE data."""
        self._type = QueryType.UPDATE
        self._values = data
        return self

    def set(self, column: str, value: Any) -> 'QueryBuilder':
        """Set a single column for UPDATE."""
        self._type = QueryType.UPDATE
        self._values[column] = value
        return self

    def increment(self, column: str, amount: int = 1) -> 'QueryBuilder':
        """Increment a column."""
        self._type = QueryType.UPDATE
        self._values[column] = RawExpression(f"{column} + ?", [amount])
        return self

    def decrement(self, column: str, amount: int = 1) -> 'QueryBuilder':
        """Decrement a column."""
        self._type = QueryType.UPDATE
        self._values[column] = RawExpression(f"{column} - ?", [amount])
        return self

    # =========================================================================
    # DELETE
    # =========================================================================

    def delete(self) -> 'QueryBuilder':
        """Set DELETE operation."""
        self._type = QueryType.DELETE
        return self

    # =========================================================================
    # COMPILE
    # =========================================================================

    def compile(self) -> CompiledQuery:
        """Compile the query to SQL."""
        if self._type == QueryType.SELECT:
            return self._compile_select()
        elif self._type == QueryType.INSERT:
            return self._compile_insert()
        elif self._type == QueryType.UPDATE:
            return self._compile_update()
        elif self._type == QueryType.DELETE:
            return self._compile_delete()
        else:
            raise ValueError(f"Unknown query type: {self._type}")

    def _compile_select(self) -> CompiledQuery:
        """Compile SELECT query."""
        params = []
        parts = []

        # SELECT
        columns = ", ".join(self._columns) if self._columns else "*"
        distinct = "DISTINCT " if self._distinct else ""
        parts.append(f"SELECT {distinct}{columns}")

        # FROM
        table_ref = self._table
        if self._table_alias:
            table_ref = f"{self._table} AS {self._table_alias}"
        parts.append(f"FROM {table_ref}")

        # JOIN
        for join in self._joins:
            parts.append(join.to_sql())

        # WHERE
        where_sql, where_params = self._compile_wheres()
        if where_sql:
            parts.append(f"WHERE {where_sql}")
            params.extend(where_params)

        # GROUP BY
        if self._group_by:
            parts.append(f"GROUP BY {', '.join(self._group_by)}")

        # HAVING
        having_sql, having_params = self._compile_having()
        if having_sql:
            parts.append(f"HAVING {having_sql}")
            params.extend(having_params)

        # ORDER BY
        if self._order_by:
            order_parts = [o.to_sql() for o in self._order_by]
            parts.append(f"ORDER BY {', '.join(order_parts)}")

        # LIMIT
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")

        # OFFSET
        if self._offset is not None:
            parts.append(f"OFFSET {self._offset}")

        return CompiledQuery(
            sql=" ".join(parts),
            params=params,
            query_type=QueryType.SELECT
        )

    def _compile_insert(self) -> CompiledQuery:
        """Compile INSERT query."""
        params = []

        if self._insert_rows:
            # Multi-row insert
            columns = list(self._insert_rows[0].keys())
            column_list = ", ".join(columns)

            value_groups = []
            for row in self._insert_rows:
                placeholders = ", ".join(["?" for _ in columns])
                value_groups.append(f"({placeholders})")
                params.extend([row.get(c) for c in columns])

            sql = f"INSERT INTO {self._table} ({column_list}) VALUES {', '.join(value_groups)}"
        else:
            # Single row insert
            columns = list(self._values.keys())
            column_list = ", ".join(columns)
            placeholders = ", ".join(["?" for _ in columns])

            for col in columns:
                value = self._values[col]
                if isinstance(value, RawExpression):
                    params.extend(value.params)
                else:
                    params.append(value)

            sql = f"INSERT INTO {self._table} ({column_list}) VALUES ({placeholders})"

        return CompiledQuery(
            sql=sql,
            params=params,
            query_type=QueryType.INSERT
        )

    def _compile_update(self) -> CompiledQuery:
        """Compile UPDATE query."""
        params = []
        set_parts = []

        for column, value in self._values.items():
            if isinstance(value, RawExpression):
                set_parts.append(f"{column} = {value.expression}")
                params.extend(value.params)
            else:
                set_parts.append(f"{column} = ?")
                params.append(value)

        sql = f"UPDATE {self._table} SET {', '.join(set_parts)}"

        # WHERE
        where_sql, where_params = self._compile_wheres()
        if where_sql:
            sql += f" WHERE {where_sql}"
            params.extend(where_params)

        return CompiledQuery(
            sql=sql,
            params=params,
            query_type=QueryType.UPDATE
        )

    def _compile_delete(self) -> CompiledQuery:
        """Compile DELETE query."""
        params = []
        sql = f"DELETE FROM {self._table}"

        # WHERE
        where_sql, where_params = self._compile_wheres()
        if where_sql:
            sql += f" WHERE {where_sql}"
            params.extend(where_params)

        return CompiledQuery(
            sql=sql,
            params=params,
            query_type=QueryType.DELETE
        )

    def _compile_wheres(self) -> Tuple[str, List[Any]]:
        """Compile WHERE clauses."""
        if not self._wheres:
            return "", []

        parts = []
        params = []

        for i, where in enumerate(self._wheres):
            clause_sql, clause_params = where.to_sql()

            if i > 0:
                parts.append(where.logical_op.value)

            parts.append(clause_sql)
            params.extend(clause_params)

        return " ".join(parts), params

    def _compile_having(self) -> Tuple[str, List[Any]]:
        """Compile HAVING clauses."""
        if not self._having:
            return "", []

        parts = []
        params = []

        for i, having in enumerate(self._having):
            clause_sql, clause_params = having.to_sql()

            if i > 0:
                parts.append(LogicalOp.AND.value)

            parts.append(clause_sql)
            params.extend(clause_params)

        return " ".join(parts), params

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def to_sql(self) -> str:
        """Get SQL string."""
        return self.compile().sql

    def get_bindings(self) -> List[Any]:
        """Get query parameter bindings."""
        return self.compile().params

    def clone(self) -> 'QueryBuilder':
        """Clone the query builder."""
        import copy
        return copy.deepcopy(self)

    def __str__(self) -> str:
        return self.to_sql()

    def __repr__(self) -> str:
        compiled = self.compile()
        return f"QueryBuilder({compiled.sql}, params={compiled.params})"


# =============================================================================
# QUERY FACTORY
# =============================================================================

class Query:
    """Factory for creating query builders."""

    @staticmethod
    def table(name: str, alias: str = None) -> QueryBuilder:
        """Create query builder for table."""
        return QueryBuilder(name).table(name, alias)

    @staticmethod
    def select(*columns: str) -> QueryBuilder:
        """Create SELECT query."""
        return QueryBuilder().select(*columns)

    @staticmethod
    def raw(expression: str, params: List[Any] = None) -> RawExpression:
        """Create raw expression."""
        return RawExpression(expression, params)


# =============================================================================
# QUERY MANAGER
# =============================================================================

class QueryManager:
    """
    Query builder manager for BAEL.
    """

    def __init__(self):
        self.queries: Dict[str, CompiledQuery] = {}
        self.statistics = {
            "total_queries": 0,
            "select": 0,
            "insert": 0,
            "update": 0,
            "delete": 0
        }

    def table(self, name: str, alias: str = None) -> QueryBuilder:
        """Create query for table."""
        return Query.table(name, alias)

    def raw(self, expression: str, params: List[Any] = None) -> RawExpression:
        """Create raw expression."""
        return Query.raw(expression, params)

    def compile_and_store(
        self,
        name: str,
        builder: QueryBuilder
    ) -> CompiledQuery:
        """Compile and store a named query."""
        compiled = builder.compile()
        self.queries[name] = compiled

        self.statistics["total_queries"] += 1
        self.statistics[compiled.query_type.value] += 1

        return compiled

    def get_stored(self, name: str) -> Optional[CompiledQuery]:
        """Get a stored query."""
        return self.queries.get(name)

    def get_statistics(self) -> Dict[str, Any]:
        """Get query statistics."""
        return self.statistics.copy()


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the Query Builder."""
    print("=" * 70)
    print("BAEL - QUERY BUILDER DEMO")
    print("Fluent SQL Query Construction")
    print("=" * 70)
    print()

    manager = QueryManager()

    # 1. Simple SELECT
    print("1. SIMPLE SELECT:")
    print("-" * 40)

    query = (
        manager.table("users")
        .select("id", "name", "email")
        .where("status", "active")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 2. SELECT with Multiple WHERE
    print("2. MULTIPLE WHERE:")
    print("-" * 40)

    query = (
        manager.table("products")
        .select("*")
        .where("category", "electronics")
        .where("price", WhereOperator.GT, 100)
        .where("stock", WhereOperator.GTE, 1)
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 3. OR WHERE
    print("3. OR WHERE:")
    print("-" * 40)

    query = (
        manager.table("users")
        .select("*")
        .where("role", "admin")
        .or_where("role", "moderator")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 4. WHERE IN
    print("4. WHERE IN:")
    print("-" * 40)

    query = (
        manager.table("orders")
        .select("*")
        .where_in("status", ["pending", "processing", "shipped"])
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 5. BETWEEN
    print("5. BETWEEN:")
    print("-" * 40)

    query = (
        manager.table("events")
        .select("*")
        .where_between("date", "2024-01-01", "2024-12-31")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 6. JOIN
    print("6. JOIN:")
    print("-" * 40)

    query = (
        manager.table("orders", "o")
        .select("o.id", "o.total", "u.name", "u.email")
        .join("users", "o.user_id", "=", "users.id")
        .where("o.status", "completed")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 7. LEFT JOIN
    print("7. LEFT JOIN:")
    print("-" * 40)

    query = (
        manager.table("users", "u")
        .select("u.name", Aggregate.count("o.id", "order_count"))
        .left_join("orders", "u.id", "=", "o.user_id")
        .group_by("u.id")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 8. GROUP BY with HAVING
    print("8. GROUP BY with HAVING:")
    print("-" * 40)

    query = (
        manager.table("orders")
        .select("user_id", Aggregate.sum("total", "total_spent"))
        .group_by("user_id")
        .having("total_spent", WhereOperator.GT, 1000)
        .order_by_desc("total_spent")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 9. ORDER BY with LIMIT
    print("9. ORDER BY with LIMIT:")
    print("-" * 40)

    query = (
        manager.table("products")
        .select("*")
        .order_by("price", OrderDirection.DESC)
        .limit(10)
        .offset(20)
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 10. PAGINATION
    print("10. PAGINATION:")
    print("-" * 40)

    query = (
        manager.table("posts")
        .select("*")
        .where("published", True)
        .latest("created_at")
        .paginate(page=3, per_page=15)
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 11. INSERT
    print("11. INSERT:")
    print("-" * 40)

    query = (
        manager.table("users")
        .insert({
            "name": "John Doe",
            "email": "john@example.com",
            "password": "hashed_password"
        })
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 12. INSERT MANY
    print("12. INSERT MANY:")
    print("-" * 40)

    query = (
        manager.table("tags")
        .insert_many([
            {"name": "python", "slug": "python"},
            {"name": "javascript", "slug": "javascript"},
            {"name": "rust", "slug": "rust"}
        ])
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 13. UPDATE
    print("13. UPDATE:")
    print("-" * 40)

    query = (
        manager.table("users")
        .update({
            "name": "Jane Doe",
            "updated_at": "2024-01-01"
        })
        .where("id", 123)
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 14. INCREMENT
    print("14. INCREMENT:")
    print("-" * 40)

    query = (
        manager.table("products")
        .increment("views", 1)
        .where("id", 456)
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 15. DELETE
    print("15. DELETE:")
    print("-" * 40)

    query = (
        manager.table("sessions")
        .delete()
        .where("expires_at", WhereOperator.LT, "2024-01-01")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 16. DISTINCT
    print("16. DISTINCT:")
    print("-" * 40)

    query = (
        manager.table("orders")
        .distinct()
        .select("user_id")
        .where("status", "completed")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 17. AGGREGATES
    print("17. AGGREGATES:")
    print("-" * 40)

    query = (
        manager.table("products")
        .select(
            Aggregate.count("*", "total"),
            Aggregate.avg("price", "avg_price"),
            Aggregate.min("price", "min_price"),
            Aggregate.max("price", "max_price")
        )
        .where("category", "electronics")
    )

    compiled = query.compile()
    print(f"   SQL: {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    # 18. COMPLEX QUERY
    print("18. COMPLEX QUERY:")
    print("-" * 40)

    query = (
        manager.table("orders", "o")
        .select(
            "o.id",
            "o.total",
            "u.name AS customer_name",
            "p.name AS product_name"
        )
        .join("users", "o.user_id", "=", "users.id", alias="u")
        .join("order_items", "o.id", "=", "order_items.order_id", alias="oi")
        .join("products", "oi.product_id", "=", "products.id", alias="p")
        .where("o.status", "completed")
        .where("o.total", WhereOperator.GT, 100)
        .where_not_null("o.shipped_at")
        .order_by_desc("o.created_at")
        .limit(50)
    )

    compiled = query.compile()
    print(f"   SQL:")
    print(f"   {compiled.sql}")
    print(f"   Params: {compiled.params}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - Query Builder Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
